# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Install ffmpeg and build dependencies (required by openai-whisper)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        build-essential \
        gcc \
        git && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install whisper first as it might have specific dependencies
RUN pip install --no-cache-dir openai-whisper

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

# Make port 9000 available to the world outside this container (matches docker-compose)
EXPOSE 9000

# Run app.py when the container launches
CMD ["python", "app.py"]