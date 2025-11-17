from flask import Flask, jsonify, render_template, request
from agent_core import MaddyBotAgent
import traceback
import time
import os
import tempfile
from werkzeug.utils import secure_filename
from utils.file_processor import extract_text_from_file, process_image, get_file_info
# Audio processing removed - using browser-based speech recognition

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

# Initialize agent with error handling
try:
    # Try to get API key from environment or .env file
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    agent = MaddyBotAgent(api_key=api_key)
    print("MaddyBot 2.0 initialized successfully with Gemini API!")
except Exception as e:
    print(f"Warning: Could not initialize agent: {e}")
    print("\nTo use Gemini API:")
    print("1. Get your API key from: https://makersuite.google.com/app/apikey")
    print("2. Create a .env file with: GOOGLE_API_KEY=your_key_here")
    print("3. Or set environment variable: GOOGLE_API_KEY=your_key_here")
    agent = None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/favicon.ico")
def favicon():
    # Return empty response for favicon to prevent 404 errors
    return "", 204


@app.route("/api/chat", methods=["POST"])
def chat():
    if agent is None:
        return jsonify({
            "reply": "Error: Agent not initialized. Please check if Ollama is running and the model is available."
        }), 500
    
    try:
        # Handle both JSON and form-data requests
        user_message = ""
        files_data = []
        images_data = []
        audio_data = None
        
        if request.is_json:
            # JSON request (text only or with base64 data)
            data = request.get_json() or {}
            user_message = data.get("message", "").strip()
            files_data = data.get("files", [])  # Array of file contents/text
            images_data = data.get("images", [])  # Array of base64 images
            audio_transcription = data.get("audio_transcription", "").strip()  # Speech-to-text transcription
            if audio_transcription:
                audio_data = {
                    "transcription": audio_transcription,
                    "success": True
                }
        else:
            # Form-data request (file uploads)
            user_message = request.form.get("message", "").strip()
            
            # Handle file uploads
            if 'files' in request.files:
                uploaded_files = request.files.getlist('files')
                for file in uploaded_files:
                    if file.filename:
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
                        file.save(file_path)
                        file_info = get_file_info(file_path)
                        file_result = extract_text_from_file(file_path, file_info['extension'])
                        files_data.append({
                            "name": file_info['name'],
                            "content": file_result.get("content", ""),
                            "type": file_info['extension'],
                            "success": file_result.get("success", False)
                        })
                        # Clean up temp file
                        try:
                            os.remove(file_path)
                        except:
                            pass
            
            # Handle image uploads
            if 'images' in request.files:
                uploaded_images = request.files.getlist('images')
                for image in uploaded_images:
                    if image.filename:
                        image_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(image.filename))
                        image.save(image_path)
                        image_result = process_image(image_path)
                        if image_result.get("success"):
                            images_data.append({
                                "base64": image_result.get("base64"),
                                "metadata": image_result.get("metadata", {})
                            })
                        # Clean up temp file
                        try:
                            os.remove(image_path)
                        except:
                            pass
            
            # Handle audio transcription (sent as text from browser speech recognition)
            if 'audio_transcription' in request.form:
                audio_transcription = request.form.get('audio_transcription', '').strip()
                if audio_transcription:
                    audio_data = {
                        "transcription": audio_transcription,
                        "success": True
                    }

        # Build context from files, images, and audio
        context_parts = []
        
        if files_data:
            context_parts.append("--- Uploaded Files ---")
            for file_data in files_data:
                if file_data.get("success") or file_data.get("content"):
                    context_parts.append(f"\n[File: {file_data.get('name', 'unknown')}]\n{file_data.get('content', '')}")
        
        if images_data:
            context_parts.append("\n--- Uploaded Images ---")
            for idx, img_data in enumerate(images_data):
                context_parts.append(f"\n[Image {idx + 1} - {img_data.get('metadata', {}).get('width', '?')}x{img_data.get('metadata', {}).get('height', '?')} pixels]")
            # Add images to agent for vision processing
            if images_data:
                user_message += "\n[User has attached images. Please analyze them if the model supports vision.]"
        
        if audio_data and audio_data.get("transcription"):
            context_parts.append("\n--- Audio Transcription ---")
            context_parts.append(f"\n[Transcribed audio: {audio_data.get('transcription', '')}]")
            if not user_message:
                user_message = audio_data.get("transcription", "")

        # Combine user message with context
        if context_parts:
            full_message = user_message + "\n\n" + "\n".join(context_parts) if user_message else "\n".join(context_parts)
        else:
            full_message = user_message

        if not full_message.strip():
            return jsonify({"reply": "I need a message, file, image, or audio to respond to."}), 400

        # Process with agent (pass images if available)
        start_time = time.time()
        try:
            if images_data:
                # Use vision model if available
                reply = agent.process_message_with_media(full_message, images=images_data)
            else:
                reply = agent.process_message(full_message)
        except Exception as e:
            error_msg = str(e)
            print(f"Agent processing error: {error_msg}")
            return jsonify({
                "reply": f"I encountered an error processing your request: {error_msg}. Please try again."
            }), 500
        
        elapsed = time.time() - start_time
        print(f"Response generated in {elapsed:.2f}s")
        
        # Warn if response is slow
        if elapsed > 10:
            print(f"Warning: Slow response ({elapsed:.2f}s). Consider optimizing context size.")
        
        return jsonify({"reply": reply})
        
    except Exception as e:
        error_msg = str(e)
        print(f"Error processing message: {error_msg}")
        print(traceback.format_exc())
        return jsonify({
            "reply": f"I encountered an error: {error_msg}. Please make sure Ollama is running and the model is available."
        }), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
