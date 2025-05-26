# Use an official NVIDIA CUDA runtime image with Python
# Adjust CUDA/Python versions as needed for Coqui TTS and PyTorch compatibility
FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC
# Python version (ensure compatibility with Coqui TTS)
ENV PYTHON_VERSION=3.10

# Install system dependencies, Python, pip, git, and audio tools
# Coqui TTS might need additional libraries like libsndfile1
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    wget \
    libsndfile1 \
    ffmpeg \
    espeak-ng \
    python${PYTHON_VERSION} \
    python${PYTHON_VERSION}-venv \
    python3-pip \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Make python3 point to the desired version - only if not already pointing to the right version
# Use conditional so it doesn't fail if links already exist
RUN if [ ! -f /usr/bin/python3 ] || [ "$(readlink -f /usr/bin/python3)" != "/usr/bin/python${PYTHON_VERSION}" ]; then \
        rm -f /usr/bin/python3 || true; \
        ln -s /usr/bin/python${PYTHON_VERSION} /usr/bin/python3; \
    fi && \
    if [ ! -f /usr/bin/pip ] || [ "$(readlink -f /usr/bin/pip)" != "/usr/bin/pip3" ]; then \
        rm -f /usr/bin/pip || true; \
        ln -s /usr/bin/pip3 /usr/bin/pip; \
    fi

# Verify Python and pip versions
RUN python3 --version && pip --version

WORKDIR /app

# Install PyTorch matching the CUDA version
# ** IMPORTANT: Verify the correct command on pytorch.org for CUDA 11.8 **
RUN pip install --no-cache-dir torch==2.0.1+cu118 torchvision==0.15.2+cu118 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Coqui TTS and other Python dependencies
# Using --no-deps for TTS initially, then installing full requirements might avoid conflicts
# Or install TTS directly: pip install --no-cache-dir TTS
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Create directory for models and potentially speaker wavs
# Models might be downloaded here by TTS library or mounted
RUN mkdir -p /app/models /app/speaker_files && chown 1000:1000 /app/models /app/speaker_files
# Coqui TTS often downloads models to /root/.local/share/tts or user's home .local
# Ensure this path is writable or mount a volume there if needed
RUN mkdir -p /root/.local/share/tts && chown -R 1000:1000 /root/.local

# Install PyYAML for the license agreement script
RUN pip install --no-cache-dir pyyaml

# Create the .models.yaml in root's directory as well for redundancy
RUN mkdir -p /root/.local/share/tts && \
    echo "models:" > /root/.local/share/tts/.models.yaml && \
    echo "  tts_models/multilingual/multi-dataset/xtts_v2:" >> /root/.local/share/tts/.models.yaml && \
    echo "    license_accepted: true" >> /root/.local/share/tts/.models.yaml && \
    cp /root/.local/share/tts/.models.yaml /app/.models.yaml && \
    chmod 777 /app/.models.yaml /root/.local/share/tts/.models.yaml

# Create a non-root user and group
RUN groupadd -r user && useradd --no-log-init -r -g user -u 1000 user
RUN mkdir /home/user && chown user:user /home/user

# Switch to non-root user
USER user
WORKDIR /home/user

# Expose the port the app runs on
EXPOSE 5002

# Set environment variables for model configuration (can be overridden in docker-compose)
ENV COQUI_MODEL="tts_models/en/ljspeech/tacotron2-DDC"
ENV COQUI_SPEAKER_WAV=""
ENV COQUI_LANGUAGE="en"
ENV USE_CUDA="true"
# Set environment variable to accept the license agreement automatically
ENV COQUI_TOS_AGREED="1"
# Ensure Python path includes local site-packages if needed
ENV PYTHONPATH="${PYTHONPATH}:/home/user/.local/lib/python${PYTHON_VERSION}/site-packages"
# Set home for the user for local cache directories
ENV HOME=/home/user
# Set workdir back to /app where code resides
WORKDIR /app

# Command to run the application using Uvicorn
# Run prestart script as a redundant measure, run conversion script, then start the API
CMD ["sh", "-c", "python3 prestart.py && python3 convert_mp3.py && uvicorn app:app --host 0.0.0.0 --port 5002"]
