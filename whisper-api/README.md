# Whisper STT API Service

This service provides Speech-to-Text (STT) functionality using OpenAI's Whisper model. It transcribes audio input into text.

## Functionality

*   Exposes an HTTP endpoint (e.g., `/inference` or `/transcribe`, to be confirmed from `app.py`) for STT requests.
*   Accepts an audio file (e.g., WAV, MP3) via POST request (typically as multipart/form-data).
*   Transcribes the audio using the configured Whisper model.
*   Returns the transcribed text, usually in JSON format.
*   May include a `/health` endpoint for status checks.

## Configuration

Configuration is primarily done via environment variables, likely set in the main `.env` file and referenced in `docker-compose.yml` within the `whisper-api` service definition. Key variables would typically include:

*   `WHISPER_MODEL`: Specifies the Whisper model to load (e.g., `tiny`, `base`, `small`, `medium`, `large`, or specific versions like `small.en`).
*   `WHISPER_LANGUAGE`: Specifies the language for transcription (e.g., `en`, `de`, `fr`, `es`). Can often be set to `auto` for language detection.
*   `PORT` or `WHISPER_PORT`: The port on which the Whisper API service will listen (e.g., 9000).

Refer to the `app.py` in this directory, the `.env.example`, and `docker-compose.yml` for specific environment variable names and their usage.

## Model Management

*   **Whisper Models**: Whisper models are typically downloaded by the `openai-whisper` library on first use.
    *   To persist these models across container restarts and avoid repeated downloads, a Docker volume (e.g., `whisper-models`) is often mounted to the cache directory used by Whisper (e.g., `/root/.cache/whisper` or a similar path depending on the user inside the container).
    *   The `docker-compose.yml` should define this volume and mount.

## Running

The service is managed by `docker-compose`. It will be built and started along with other services.
Ensure:
1.  The `docker-compose.yml` correctly defines and mounts the volume for Whisper model caching if desired.
2.  Environment variables for the model name, language, and port are correctly set.

Monitor logs (`docker-compose logs -f whisper-api`) on first startup, especially if a new model is being used, as it will be downloaded.

## API Endpoints

Details based on `whisper-api/app.py`:

*   **`POST /transcribe`**: Transcribes an audio file.
    *   **Request**:
        *   Method: `POST`
        *   Body: `multipart/form-data` with an audio file part. The part should be named `file`.
        *   Example (using cURL):
            ```bash
            curl -X POST -F "file=@/path/to/your/audio.wav" http://localhost:9000/transcribe
            ```
    *   **Response**:
        *   Content-Type: `application/json`
        *   Body: A JSON object containing the transcribed text.
        *   Example:
            ```json
            {
              "text": "This is the transcribed text."
            }
            ```
*   **`GET /health`**: Checks the health of the service.
    *   **Request**:
        *   Method: `GET`
    *   **Response**:
        *   Content-Type: `application/json`
        *   Body: A JSON object indicating the service status.
        *   Example:
            ```json
            {
              "status": "ok"
            }
            ```

(Verify exact endpoint paths and request/response formats from `whisper-api/app.py`.)
