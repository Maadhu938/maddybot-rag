from flask import Flask, jsonify, render_template, request
from agent_core import MaddyBotAgent
import traceback
import time
import os
import tempfile
from werkzeug.utils import secure_filename
from utils.file_processor import extract_text_from_file, process_image, get_file_info
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

# Initialize agent with error handling
try:
    # Accept either GOOGLE_API_KEY or GEMINI_API_KEY environment variable
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    agent = MaddyBotAgent(api_key=api_key)
    print("MaddyBot 2.0 initialized successfully with provided API key.")
except Exception as e:
    # Keep the trace printed to logs for easier debugging
    print(f"Warning: Could not initialize agent: {e}")
    traceback.print_exc()
    print(
        "\nTo use Gemini/Google API:\n"
        "1. Get an API key (e.g. from Google's Makersuite if using Gemini).\n"
        "2. Create a .env file with: GOOGLE_API_KEY=your_key_here  (or set GEMINI_API_KEY)\n"
        "3. Or set environment variable in Railway/host directly.\n"
    )
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
    # If agent failed to initialize return a clear error
    if agent is None:
        return jsonify({
            "reply": "Error: Agent not initialized. Please set GOOGLE_API_KEY or GEMINI_API_KEY in environment."
        }), 500

    try:
        # Handle both JSON and form-data requests
        user_message = ""
        files_data = []
        images_data = []
        audio_data = None

        # JSON request path (text only or base64 images/files)
        if request.is_json:
            data = request.get_json() or {}
            user_message = (data.get("message") or "").strip()
            files_data = data.get("files", [])  # expecting list of dicts {name, content, ...}
            images_data = data.get("images", [])  # expecting list of base64 parts or metadata
            audio_transcription = (data.get("audio_transcription") or "").strip()
            if audio_transcription:
                audio_data = {"transcription": audio_transcription, "success": True}

        else:
            # Form-data (file uploads)
            user_message = (request.form.get("message") or "").strip()

            # Files
            if 'files' in request.files:
                uploaded_files = request.files.getlist('files')
                for file in uploaded_files:
                    if file and file.filename:
                        safe_name = secure_filename(file.filename)
                        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)
                        file.save(temp_path)
                        try:
                            file_info = get_file_info(temp_path)
                            file_result = extract_text_from_file(temp_path, file_info['extension'])
                            files_data.append({
                                "name": file_info['name'],
                                "content": file_result.get("content", ""),
                                "type": file_info['extension'],
                                "success": file_result.get("success", False)
                            })
                        except Exception as ex:
                            files_data.append({
                                "name": safe_name,
                                "content": "",
                                "type": os.path.splitext(safe_name)[1],
                                "success": False,
                                "error": str(ex)
                            })
                        finally:
                            # remove temp
                            try:
                                os.remove(temp_path)
                            except Exception:
                                pass

            # Images
            if 'images' in request.files:
                uploaded_images = request.files.getlist('images')
                for image in uploaded_images:
                    if image and image.filename:
                        safe_name = secure_filename(image.filename)
                        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)
                        image.save(temp_path)
                        try:
                            image_result = process_image(temp_path)
                            if image_result.get("success"):
                                images_data.append({
                                    "base64": image_result.get("base64"),
                                    "metadata": image_result.get("metadata", {})
                                })
                            else:
                                images_data.append({
                                    "base64": None,
                                    "metadata": {},
                                    "error": image_result.get("error")
                                })
                        except Exception as ex:
                            images_data.append({"base64": None, "metadata": {}, "error": str(ex)})
                        finally:
                            try:
                                os.remove(temp_path)
                            except Exception:
                                pass

            # Audio transcription from client (if any)
            if 'audio_transcription' in request.form:
                audio_transcription = (request.form.get('audio_transcription') or "").strip()
                if audio_transcription:
                    audio_data = {"transcription": audio_transcription, "success": True}

        # Build context parts from uploaded files/images/audio
        context_parts = []

        if files_data:
            context_parts.append("--- Uploaded Files ---")
            for file_data in files_data:
                # include text if available
                text = file_data.get("content", "")
                if file_data.get("success") or text:
                    context_parts.append(f"\n[File: {file_data.get('name','unknown')}]\n{text}")

        if images_data:
            context_parts.append("\n--- Uploaded Images ---")
            for idx, img_data in enumerate(images_data):
                meta = img_data.get("metadata", {}) or {}
                w = meta.get("width", "?")
                h = meta.get("height", "?")
                context_parts.append(f"\n[Image {idx + 1} - {w}x{h} pixels]")
            # hint to model that images exist
            if images_data:
                user_message = (user_message or "") + "\n[User has attached images. Please analyze them if the model supports vision.]"

        if audio_data and audio_data.get("transcription"):
            context_parts.append("\n--- Audio Transcription ---")
            context_parts.append(f"\n[Transcribed audio: {audio_data.get('transcription', '')}]")
            if not user_message:
                user_message = audio_data.get("transcription", "")

        # Combine everything into the final prompt
        if context_parts:
            full_message = (user_message + "\n\n" + "\n".join(context_parts)) if user_message else "\n".join(context_parts)
        else:
            full_message = user_message

        if not full_message.strip():
            return jsonify({"reply": "I need a message, file, image, or audio to respond to."}), 400

        # Process with agent (use media-aware method if images present)
        start_time = time.time()
        try:
            if images_data:
                reply = agent.process_message_with_media(full_message, images=images_data)
            else:
                reply = agent.process_message(full_message)
        except Exception as e:
            error_msg = str(e)
            print(f"Agent processing error: {error_msg}")
            traceback.print_exc()
            return jsonify({
                "reply": f"I encountered an error processing your request: {error_msg}. Please try again."
            }), 500

        elapsed = time.time() - start_time
        print(f"Response generated in {elapsed:.2f}s")
        if elapsed > 10:
            print(f"Warning: Slow response ({elapsed:.2f}s). Consider reducing context size.")

        return jsonify({"reply": reply})

    except Exception as e:
        error_msg = str(e)
        print(f"Error processing message: {error_msg}")
        traceback.print_exc()
        return jsonify({
            "reply": f"I encountered an internal error: {error_msg}."
        }), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

