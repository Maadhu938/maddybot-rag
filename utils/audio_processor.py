"""Utility functions for processing audio files."""
import os
import subprocess
from typing import Optional, Dict
from pathlib import Path


def transcribe_audio_with_ollama(audio_path: str, model: str = "llama3") -> Dict[str, any]:
    """
    Transcribe audio using Ollama's whisper model.
    Note: Requires 'whisper' model to be pulled in Ollama.
    """
    result = {
        "success": False,
        "transcription": "",
        "error": None
    }
    
    try:
        # Check if whisper model is available
        # First, try to use Ollama's API for audio transcription
        # Note: This requires Ollama to have whisper support
        
        # Alternative: Use ollama's built-in audio support if available
        # For now, we'll return a message that user needs to install whisper
        result["error"] = "Audio transcription requires Ollama whisper model. Run: ollama pull whisper"
        result["transcription"] = "[Audio file received. Please install whisper model: 'ollama pull whisper']"
        result["success"] = False
        
        # TODO: Implement actual transcription when Ollama whisper is available
        # This would use: ollama run whisper <audio_file>
        
    except Exception as e:
        result["error"] = str(e)
        result["success"] = False
    
    return result


def get_audio_info(audio_path: str) -> Dict[str, any]:
    """Get basic audio file information."""
    try:
        stat = os.stat(audio_path)
        ext = Path(audio_path).suffix.lower()
        return {
            "name": os.path.basename(audio_path),
            "size": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "extension": ext,
            "supported_formats": ['.mp3', '.wav', '.ogg', '.m4a', '.flac'],
            "is_supported": ext in ['.mp3', '.wav', '.ogg', '.m4a', '.flac'],
            "exists": True
        }
    except Exception as e:
        return {
            "name": os.path.basename(audio_path),
            "exists": False,
            "error": str(e)
        }


def check_whisper_available() -> bool:
    """Check if whisper model is available in Ollama."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return "whisper" in result.stdout.lower()
    except:
        return False

