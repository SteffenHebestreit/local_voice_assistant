from flask import Flask, request, jsonify
import os
import whisper
import tempfile

app = Flask(__name__)

# Load the Whisper model
# Use environment variable ASR_MODEL, default to "base"
model_name = os.environ.get("ASR_MODEL", "base")
whisper_language = os.environ.get("WHISPER_LANGUAGE", "auto")
print(f"Loading Whisper model: {model_name}...")
print(f"Whisper language setting: {whisper_language}")
try:
    model = whisper.load_model(model_name)
    print(f"Whisper model '{model_name}' loaded successfully.")
except Exception as e:
    print(f"Error loading Whisper model '{model_name}': {e}")
    # Exit if model loading fails? Or handle gracefully? For now, print error.
    model = None # Indicate model failed to load

@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    """
    Endpoint to receive audio data and return transcription.
    Expects audio file in the request's 'file' field.
    """
    if model is None:
         return jsonify({"error": f"Whisper model '{model_name}' not loaded"}), 500

    if 'file' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files['file']    # Save the audio file temporarily
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            audio_file.save(temp_audio.name)
            temp_audio_path = temp_audio.name

        print(f"Audio saved temporarily to: {temp_audio_path}")

        # Transcribe the audio file with language specification
        transcribe_options = {"verbose": False}
        
        # Set language if specified (not 'auto')
        if whisper_language and whisper_language.lower() != 'auto':
            transcribe_options["language"] = whisper_language
            print(f"Using specified language: {whisper_language}")
        else:
            print("Using automatic language detection")
            
        result = model.transcribe(temp_audio_path, **transcribe_options)
        transcription = result["text"]
        detected_language = result.get("language", "unknown")

        print(f"Transcription result: {transcription}")
        print(f"Detected language: {detected_language}")

    except Exception as e:
        print(f"Error during transcription: {e}")
        return jsonify({"error": f"Transcription failed: {e}"}), 500
    finally:
    # Clean up the temporary file
        if 'temp_audio_path' in locals() and os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
            print(f"Temporary file removed: {temp_audio_path}")

    # Return in the format expected by the backend
    return jsonify({"text": transcription})

@app.route('/health', methods=['GET'])
def health_check():
    """Basic health check endpoint."""
    return jsonify({
        "status": "ok", 
        "model": model_name,
        "language": whisper_language
    }), 200

# Add an alias endpoint for compatibility
@app.route('/inference', methods=['POST'])
def inference_alias():
    """Alias for /transcribe endpoint for backward compatibility."""
    return transcribe_audio()

if __name__ == '__main__':
    # Listen on all network interfaces, port 9000
    app.run(host='0.0.0.0', port=9000, debug=False) # Disable debug for production