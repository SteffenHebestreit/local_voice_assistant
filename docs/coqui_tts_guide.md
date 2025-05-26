# Coqui TTS Information

This document provides information on configuring and using the Coqui TTS service within this project. Unlike Piper, training Coqui TTS models (especially high-quality ones like XTTS) is a complex process often requiring large datasets and significant compute resources, which is beyond the scope of this guide. This focuses on using pre-trained models provided by Coqui AI.

## Functionality

The `coqui-tts-api` service wraps the Coqui TTS library, providing a simple HTTP API for synthesizing speech from text. It supports various models, including the high-quality, multilingual XTTS v2 model capable of voice cloning.

## Configuration (via `docker-compose.yml`)

The behavior of the TTS service is controlled by environment variables set within the `coqui-tts-api` service definition in your `docker-compose.yml` file:

*   **`COQUI_MODEL`**: Specifies the Coqui TTS model to load.
    *   **Recommendation:** `tts_models/multilingual/multi-dataset/xtts_v2` (High quality, multilingual, voice cloning - **Requires GPU**).
    *   Faster, lower-quality alternatives (might work on CPU): `tts_models/en/ljspeech/tacotron2-DDC`, `tts_models/en/vctk/vits`.
    *   Find more models on the Coqui TTS GitHub repository or model zoo.
    *   Default: `tts_models/en/ljspeech/tacotron2-DDC`
*   **`COQUI_LANGUAGE`**: **Required only if using an XTTS model.** Specifies the language code for synthesis (e.g., `en`, `de`, `fr`, `es`, `pt`, `pl`, `it`, `ru`, `tr`, `ja`, `zh-cn`, `ko`).
    *   Default: `en`
*   **`COQUI_SPEAKER_WAV`**: **Required only if using an XTTS model for voice cloning.** Specifies the path *inside the container* to a `.wav` file used as the voice reference.
    *   Mount your local speaker `.wav` file(s) into the container using the `speaker-wavs` volume mount (e.g., mount `./coqui-tts-api/speaker-wavs` to `/app/speaker_files`).
    *   Set the variable like: `COQUI_SPEAKER_WAV=/app/speaker_files/your_voice.wav`.
    *   Ensure the `.wav` file is a clean, high-quality recording (e.g., 16-bit PCM, 22050Hz or 24000Hz depending on XTTS version).
    *   Default: `""` (XTTS will use its default voice if empty or the file is not found).
*   **`USE_CUDA`**: Set to `true` (default) to enable GPU acceleration. **Highly recommended for XTTS models.** Requires a compatible NVIDIA GPU on the host and the NVIDIA Container Toolkit installed for Docker. Set to `false` to force CPU usage (expect very slow synthesis for complex models).

## Model Management

*   **Model Cache:** Coqui TTS downloads models on first use. To persist these downloads and speed up subsequent starts, a local directory (`./coqui-tts-api/coqui-models-data`) is mounted to the container's cache directory (`/home/user/.local/share/tts`).
*   **Speaker WAVs:** Place your custom speaker `.wav` files (for XTTS cloning) in the local directory (`./coqui-tts-api/speaker-wavs`) which is mounted to `/app/speaker_files` in the container.

## Directory Structure

The current project uses the following directory structure for Coqui TTS:
```
coqui-tts-api/
  ├── app.py              # FastAPI application
  ├── Dockerfile          # Container definition
  ├── requirements.txt    # Python dependencies
  ├── README.md           # Service documentation
  ├── coqui-models-data/  # TTS model cache directory
  └── speaker-wavs/       # Speaker reference WAV files
```

## Resource Requirements

*   **GPU:** Using high-quality models like XTTS v2 effectively **requires** an NVIDIA GPU with sufficient VRAM (8GB+ recommended) and the NVIDIA Container Toolkit. CPU synthesis will be extremely slow.
*   **RAM:** Even with a GPU, the models can consume significant RAM. Monitor resource usage.
*   **Disk Space:** Models can be large (several gigabytes). Ensure the volume mounted for the model cache (`./coqui-tts-api/coqui-models-data`) has enough space.

## First Run

The first time you start the `coqui-tts-api` service (via `docker-compose up`), it will download the specified `COQUI_MODEL`. This can take a considerable amount of time depending on the model size and your internet connection. Monitor the service logs (`docker-compose logs -f coqui-tts-api`) to track progress.
