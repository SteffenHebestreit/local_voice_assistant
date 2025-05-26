\
# Coqui TTS API Service

This service provides Text-to-Speech (TTS) functionality using the Coqui TTS engine.

## Functionality

*   Exposes an HTTP endpoint (`/api/tts`).
*   Accepts text input via POST request.
*   Synthesizes speech using the configured Coqui TTS model.
*   Supports standard models and XTTS models (including voice cloning via speaker WAV).
*   Streams the synthesized audio back as a WAV file.
*   Includes a `/health` endpoint for basic status checks.

## Configuration

Configuration is primarily done via environment variables set in `docker-compose.yml`:

*   `COQUI_MODEL`: Specifies the Coqui TTS model to load.
    *   Examples:
        *   `tts_models/en/ljspeech/tacotron2-DDC` (Faster standard English)
        *   `tts_models/en/vctk/vits` (Higher quality standard English)
        *   `tts_models/multilingual/multi-dataset/xtts_v2` (High quality, multilingual, voice cloning)
    *   Default: `tts_models/en/ljspeech/tacotron2-DDC`
*   `COQUI_LANGUAGE`: Required **only** if using an XTTS model. Specifies the language code for synthesis (e.g., `en`, `de`, `fr`). Default: `en`.
*   `COQUI_SPEAKER_WAV`: Required **only** if using an XTTS model for voice cloning. Specifies the path *inside the container* to a `.wav` file used as the voice reference. This path typically points to a file mounted via a volume (e.g., `/app/speaker_files/your_speaker.wav`). Default: `""` (XTTS will use its default voice if empty or file not found).
*   `USE_CUDA`: Set to `true` (default) to enable GPU acceleration (requires NVIDIA GPU and nvidia-container-toolkit). Set to `false` to force CPU usage (will be very slow for complex models like XTTS).

## Model & Data Volumes

*   **Model Cache:** The service expects Coqui TTS models to be cached. The Dockerfile configures the cache location within the user's home directory (`/root/.local/share/tts` or `/home/user/.local/share/tts`). It's highly recommended to mount a local directory (e.g., `./coqui-models-data`) to this cache path using a Docker volume in `docker-compose.yml`. This persists downloaded models across container restarts and allows pre-populating the cache.
    ```yaml
    volumes:
      - ./coqui-models-data:/home/user/.local/share/tts # Or /root/.local/share/tts depending on final user in Dockerfile
    ```
*   **Speaker WAVs (for XTTS):** If using XTTS voice cloning, mount a local directory containing your speaker `.wav` file(s) into the container (e.g., to `/app/speaker_files`). Then set the `COQUI_SPEAKER_WAV` environment variable to the full path of the desired file *inside the container*.
    ```yaml
    volumes:
      - ./speaker-wavs:/app/speaker_files
    environment:
      - COQUI_SPEAKER_WAV=/app/speaker_files/your_voice.wav
    ```

## Running

The service is managed by `docker-compose`. It will be built and started along with other services. Ensure the necessary volumes and environment variables are correctly configured in `docker-compose.yml`. The first run might take longer as the specified `COQUI_MODEL` needs to be downloaded into the cache volume.

## API Endpoints

Details based on `coqui-tts-api/app.py`:

*   **`POST /api/tts`**: Synthesizes speech from text.
    *   **Request**:
        *   Method: `POST`
        *   Content-Type: `application/json`
        *   Body: A JSON object with the following fields:
            *   `text` (string, required): The text to synthesize.
            *   `language` (string, optional): The language code for synthesis (e.g., "en", "es", "fr"). Required if using an XTTS model and `COQUI_LANGUAGE` is not set. Defaults to the value of the `COQUI_LANGUAGE` environment variable, or "en" if not set.
            *   `speaker_wav` (string, optional): Path *inside the container* to a speaker `.wav` file for voice cloning with XTTS models. Overrides the `COQUI_SPEAKER_WAV` environment variable if provided.
        *   Example (using cURL):
            ```bash
            curl -X POST -H "Content-Type: application/json" \\
                 -d '{"text": "Hello world", "language": "en"}' \\
                 http://localhost:8080/api/tts --output output.wav
            ```
            For XTTS with a specific speaker WAV (assuming `speaker.wav` is in the mapped `speaker-wavs` directory):
            ```bash
            curl -X POST -H "Content-Type: application/json" \\
                 -d '{"text": "Hello with a custom voice.", "language": "en", "speaker_wav": "/app/speaker_files/speaker.wav"}' \\
                 http://localhost:8080/api/tts --output custom_voice_output.wav
            ```
    *   **Response**:
        *   Content-Type: `audio/wav`
        *   Body: The synthesized audio stream in WAV format.

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
