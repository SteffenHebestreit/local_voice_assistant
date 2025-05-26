\
import os
import io
import logging
import torch # Added
from torch import serialization # Added
from typing import Optional # Added
from fastapi import FastAPI, Response, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set environment variable to accept license agreement
os.environ["COQUI_TOS_AGREED"] = "1"

# Attempt to make XttsConfig a safe global for torch.load
try:
    from TTS.tts.configs.xtts_config import XttsConfig
    from TTS.tts.models.xtts import XttsAudioConfig, XttsArgs # Added import for XttsArgs
    from TTS.config.shared_configs import BaseDatasetConfig
    serialization.add_safe_globals([XttsConfig, XttsAudioConfig, BaseDatasetConfig, XttsArgs]) # Added XttsArgs
    logger.info("Successfully added XttsConfig, XttsAudioConfig, BaseDatasetConfig, and XttsArgs to torch safe globals.")
except ImportError:
    logger.error("Failed to import one or more classes for torch.serialization.add_safe_globals. Model loading might fail.")
except AttributeError:
    logger.error("Failed to call torch.serialization.add_safe_globals. PyTorch version might be too old or API changed.")
except Exception as e:
    logger.error(f"An unexpected error occurred while trying to add classes to safe globals: {e}")


# Now import TTS after setting the environment variable
from TTS.api import TTS

# --- Configuration ---
# Model name or path from environment variable
# Example XTTS v2: "tts_models/multilingual/multi-dataset/xtts_v2"
# Example standard model: "tts_models/en/ljspeech/tacotron2-DDC"
DEFAULT_MODEL_NAME = "tts_models/en/ljspeech/tacotron2-DDC" # A faster, standard model as default
MODEL_NAME = os.environ.get("COQUI_MODEL", DEFAULT_MODEL_NAME)
# Path to speaker wav for XTTS models (optional, required for XTTS voice cloning)
SPEAKER_WAV_PATH = os.environ.get("COQUI_SPEAKER_WAV")
# Language for XTTS models (required if using XTTS)
LANGUAGE = os.environ.get("COQUI_LANGUAGE", "en")
# Use CUDA if available
USE_CUDA = os.environ.get("USE_CUDA", "true").lower() == "true"

# --- Model Loading ---
tts_instance = None

def load_model():
    global tts_instance
    logger.info(f"Loading Coqui TTS model: {MODEL_NAME}")
    logger.info(f"Using CUDA: {USE_CUDA}")

    # Diagnostic import
    try:
        from TTS.tts.configs.xtts_config import XttsConfig
        logger.info("Successfully imported TTS.tts.configs.xtts_config.XttsConfig")
    except ImportError as ie:
        logger.error(f"Failed to import XttsConfig directly: {ie}")
        # This might indicate a problem with the TTS library installation itself
    except Exception as e:
        logger.error(f"An unexpected error occurred during diagnostic import of XttsConfig: {e}")


    try:
        tts_instance = TTS(MODEL_NAME, gpu=USE_CUDA)
        if "xtts" in MODEL_NAME.lower() and SPEAKER_WAV_PATH:
             if not os.path.exists(SPEAKER_WAV_PATH):
                 logger.warning(f"Speaker WAV path specified but not found: {SPEAKER_WAV_PATH}. XTTS will use default voice.")
             else:
                 logger.info(f"XTTS model detected. Speaker WAV will be used: {SPEAKER_WAV_PATH}")
        elif "xtts" in MODEL_NAME.lower():
             logger.info("XTTS model detected, but no speaker WAV specified. Using default voice.")
        logger.info("Coqui TTS model loaded successfully.")
    except Exception as e:
        logger.error(f"Error loading Coqui TTS model: {e}", exc_info=True)
        # Depending on the error, you might want to exit or handle differently
        raise RuntimeError(f"Failed to load TTS model: {e}")

# Load model on startup
# Wrap in try-except to allow container to start even if model loading fails initially
try:
    load_model()
except RuntimeError as e:
    logger.error(f"Model loading failed on startup: {e}")
    # Keep tts_instance as None

# --- API Definition ---
app = FastAPI()

class TTSRequest(BaseModel):
    text: str
    speed: Optional[float] = 2.3 # Default to normal speed
    # Add other potential parameters like speaker_wav (base64?), language if needed

@app.post("/api/tts", responses={200: {"content": {"audio/wav": {}}}})
async def synthesize_speech(request: TTSRequest):
    if not tts_instance:
        # Attempt to reload model if it failed on startup
        try:
            logger.warning("TTS model not loaded. Attempting to reload...")
            load_model()
            if not tts_instance: # Check again after reload attempt
                 raise HTTPException(status_code=503, detail="TTS model is not available and failed to reload.")
        except Exception as e:
             logger.error(f"Failed to reload TTS model during request: {e}", exc_info=True)
             raise HTTPException(status_code=503, detail=f"TTS model is not available and failed to reload: {e}")


    text_to_synthesize = request.text
    if not text_to_synthesize:
        raise HTTPException(status_code=400, detail="Text input cannot be empty.")

    logger.info(f"Received TTS request for text: '{text_to_synthesize[:50]}...'")

    try:
        # Determine synthesis arguments
        synthesis_args = {
            "text": text_to_synthesize,
            "speed": request.speed, # Add speed parameter
        }
        if "xtts" in MODEL_NAME.lower():
            synthesis_args["language"] = LANGUAGE
            if SPEAKER_WAV_PATH and os.path.exists(SPEAKER_WAV_PATH):
                synthesis_args["speaker_wav"] = SPEAKER_WAV_PATH

        logger.info(f"Attempting TTS with args: {synthesis_args}")
        
        # Define an async generator to stream the audio chunks
        async def generate_audio_stream():
            import numpy as np
            import wave
            import struct
            import io
            
            # Define a default sample rate that will be used if we can't determine it from the model
            sample_rate = 22050  # Default sample rate
            
            try:
                # Process the TTS in chunks
                wav_data = tts_instance.tts(**synthesis_args)
                logger.info(f"Generated audio data, converting to WAV format")
                
                # Create a complete WAV file first
                wav_buffer = io.BytesIO()
                
                # Handle the audio output based on what the TTS returns
                if hasattr(tts_instance, 'synthesizer') and hasattr(tts_instance.synthesizer, 'ap'):
                    # Get the sample rate from the model config if available
                    if hasattr(tts_instance.synthesizer, 'tts_config') and hasattr(tts_instance.synthesizer.tts_config, 'audio'):
                        sample_rate = tts_instance.synthesizer.tts_config.audio.sample_rate
                    
                    # Create a WAV file in memory
                    tts_instance.synthesizer.ap.save_wav(wav_data, wav_buffer, sample_rate)
                else:
                    # Fallback approach for different model types
                    # Convert to numpy array if not already
                    if not isinstance(wav_data, np.ndarray):
                        wav_data = np.array(wav_data)
                    
                    # Normalize if needed
                    if wav_data.max() > 1.0 or wav_data.min() < -1.0:
                        wav_data = wav_data / np.max(np.abs(wav_data))
                    
                    # Convert to int16
                    wav_data = (wav_data * 32767).astype(np.int16)
                    
                    # Create a WAV file in memory
                    with wave.open(wav_buffer, 'wb') as wf:
                        wf.setnchannels(1)  # Mono
                        wf.setsampwidth(2)  # 16-bit
                        wf.setframerate(sample_rate)  # Sample rate is now always defined
                        wf.writeframes(struct.pack('<' + 'h' * len(wav_data), *wav_data))
                
                # Get the full WAV data
                wav_buffer.seek(0)
                wav_bytes = wav_buffer.read()
                
                # Yield as one chunk
                logger.info(f"Streaming WAV data ({len(wav_bytes)} bytes)")
                yield wav_bytes
            
            except Exception as e:
                logger.error(f"Error during TTS generation: {e}", exc_info=True)
                # We can't raise an HTTP exception inside the generator
                # The best we can do is log it and return an empty response
                yield b''
        
        # Return a streaming response with the audio chunks
        return StreamingResponse(
            generate_audio_stream(),
            media_type="audio/wav",
            headers={"X-Content-Type-Options": "nosniff"}
        )

    except Exception as e:
        logger.error(f"Error during TTS synthesis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"TTS synthesis failed: {e}")

@app.get("/health")
async def health_check():
    # Basic health check
    model_loaded_status = tts_instance is not None
    status = "ok" if model_loaded_status else "error"
    detail = "" if model_loaded_status else "TTS model may not be loaded correctly."

    return {"status": status, "model_loaded": model_loaded_status, "model_name": MODEL_NAME, "detail": detail}

if __name__ == "__main__":
    import uvicorn
    # Running with uvicorn directly might be useful for debugging
    # Production deployment should use the command in the Dockerfile
    # Note: Model loading happens before uvicorn starts if run this way
    uvicorn.run(app, host="0.0.0.0", port=5002)

