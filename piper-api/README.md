# Piper TTS API Service

This service provides Text-to-Speech (TTS) functionality using the Piper TTS engine. Piper is known for its speed and local processing capabilities, making it a lightweight alternative to Coqui TTS for some use cases.

## Functionality

*   Exposes an HTTP endpoint (e.g., `/api/tts` or similar, to be confirmed from `app.py`) for TTS requests.
*   Accepts text input via POST request.
*   Synthesizes speech using a configured Piper voice model.
*   Streams or returns the synthesized audio (likely as a WAV file).
*   May include a `/health` endpoint for status checks.

## Configuration

Configuration is primarily done via environment variables, likely set in the main `docker-compose.yml` file within the `piper-api` service definition. Key variables would typically include:

*   `PIPER_MODEL`: Specifies the Piper voice model to load (e.g., `en_US-lessac-medium.onnx`). Models need to be available within the container, often mounted via a volume.
*   `PIPER_VOICE_CONFIG`: Path to the `.onnx.json` configuration file associated with the model.
*   `PIPER_ESPEAK_DATA`: Path to eSpeak-ng data files, if required by Piper.
*   `PORT` or `PIPER_PORT`: The port on which the Piper API service will listen within the Docker network.

Refer to the `app.py` in this directory and the `docker-compose.yml` for specific environment variable names and their usage.

## Model Management

*   **Voice Models**: Piper voice models (usually `.onnx` files and their corresponding `.onnx.json` config files) need to be downloaded and made accessible to the container.
    *   This is typically handled by mounting a local directory (e.g., `./piper-models`) to a path inside the container (e.g., `/models`) using a Docker volume.
    *   The `PIPER_MODEL` and `PIPER_VOICE_CONFIG` environment variables would then point to the paths of these files *inside the container*.
*   **Model Source**: Piper models can be found on [Hugging Face](https://huggingface.co/rhasspy/piper-voices/tree/main) or other community sources.

## Running

The service is managed by `docker-compose`. It will be built and started along with other services.
Ensure:
1.  The necessary Piper model files are downloaded to your local models directory.
2.  The `docker-compose.yml` correctly mounts the model directory as a volume.
3.  Environment variables for model paths and port are correctly set in `docker-compose.yml` or an `.env` file.

Monitor logs (`docker-compose logs -f piper-api`) on first startup to ensure the model loads correctly and the service starts without errors.

## API Endpoints

*   **TTS Request**: Likely `POST /api/tts` (or similar)
    *   **Request Body**: JSON, e.g., `{"text": "Hello world"}`
    *   **Response**: Audio stream (e.g., `audio/wav`)
*   **Health Check**: Likely `GET /health`
    *   **Response**: JSON, e.g., `{"status": "ok"}`

(Verify exact endpoint paths and request/response formats from `piper-api/app.py`.)
