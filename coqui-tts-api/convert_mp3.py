#!/usr/bin/env python3
"""
Automatic MP3 to WAV conversion script for Coqui TTS API
This script runs at container startup to ensure any MP3 files in the speaker_files directory
are properly converted to WAV format for XTTS voice cloning
"""
import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mp3_converter")

def convert_mp3_to_wav():
    """
    Scans the /app/speaker_files directory for MP3 files and converts them to WAV
    """
    try:
        from pydub import AudioSegment
    except ImportError:
        logger.error("pydub not installed. Cannot convert MP3 files.")
        return

    speaker_dir = Path("/app/speaker_files")
    if not speaker_dir.exists():
        logger.warning(f"Speaker directory {speaker_dir} does not exist.")
        return

    mp3_files = list(speaker_dir.glob("*.mp3"))
    
    if not mp3_files:
        logger.info("No MP3 files found in speaker directory.")
        return
    
    logger.info(f"Found {len(mp3_files)} MP3 files to convert.")
    
    for mp3_file in mp3_files:
        wav_file = mp3_file.with_suffix(".wav")
        
        # Skip if WAV already exists and is newer than MP3
        if wav_file.exists() and wav_file.stat().st_mtime > mp3_file.stat().st_mtime:
            logger.info(f"WAV file {wav_file.name} already exists and is up to date.")
            continue
            
        logger.info(f"Converting {mp3_file.name} to {wav_file.name}")
        try:
            audio = AudioSegment.from_mp3(mp3_file)
            audio.export(wav_file, format="wav")
            logger.info(f"Successfully converted {mp3_file.name} to {wav_file.name}")
        except Exception as e:
            logger.error(f"Error converting {mp3_file.name}: {e}")

if __name__ == "__main__":
    logger.info("Starting MP3 to WAV conversion...")
    convert_mp3_to_wav()
    logger.info("MP3 to WAV conversion completed.")
