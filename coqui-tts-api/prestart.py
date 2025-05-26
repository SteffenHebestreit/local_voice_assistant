#!/usr/bin/env python3
"""
Pre-start script for Coqui TTS API
This script pre-accepts the license agreement for XTTS v2 models
"""
import os
import sys
import yaml
import json
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("prestart")

# Configuration
MODEL_NAME = os.environ.get("COQUI_MODEL", "tts_models/multilingual/multi-dataset/xtts_v2")
LICENSE_AGREED = True  # Set to True if you've agreed to the license terms

def get_license_file_paths():
    """Get potential license file paths based on user and environment"""
    # Get home directory - handles both root and non-root users
    home = Path.home()
    logger.info(f"Home directory: {home}")
    
    # Check environment variable for custom path
    custom_model_path = os.environ.get("TTS_MODEL_PATH")
    if custom_model_path:
        logger.info(f"Using custom model path from TTS_MODEL_PATH: {custom_model_path}")
        license_paths = [Path(custom_model_path) / ".models.yaml"]
    else:
        # Standard paths for both root and non-root users
        license_paths = [
            home / ".local" / "share" / "tts" / ".models.yaml",
            Path("/app") / ".models.yaml",
            Path("/root/.local/share/tts/.models.yaml"),
            Path("/home/user/.local/share/tts/.models.yaml"),
            Path("./.models.yaml")  # Current directory
        ]
    
    logger.info(f"Potential license file paths: {license_paths}")
    return license_paths

def create_license_file():
    """Create .models.yaml files with the license agreement pre-accepted in all potential locations"""
    paths = get_license_file_paths()
    created = False
    
    for license_file in paths:
        try:
            os.makedirs(os.path.dirname(license_file), exist_ok=True)
            
            # If the file already exists, load it first
            if os.path.exists(license_file):
                try:
                    with open(license_file, 'r') as f:
                        models_dict = yaml.safe_load(f) or {}
                except Exception as e:
                    logger.warning(f"Error reading existing file {license_file}: {e}")
                    models_dict = {}
            else:
                models_dict = {}
            
            # Add or update the license agreement for the model
            if "models" not in models_dict:
                models_dict["models"] = {}
            
            models_dict["models"][MODEL_NAME] = {
                "license_accepted": LICENSE_AGREED
            }
            
            # Write the updated file
            with open(license_file, 'w') as f:
                yaml.dump(models_dict, f)
            
            logger.info(f"Created/updated license file at {license_file}")
            created = True
        except Exception as e:
            logger.warning(f"Failed to create license file at {license_file}: {e}")
    
    if created:
        logger.info(f"License agreement for {MODEL_NAME} set to: {LICENSE_AGREED}")
    else:
        logger.error("Failed to create license file in any location")

def check_model_config():
    """Check if the model config exists and try to create directories for it"""
    # Extract the model folder name from the model path
    model_parts = MODEL_NAME.split('/')
    model_folder_name = '--'.join(model_parts)
    
    # Common paths for model configs
    home = Path.home()
    config_paths = [
        home / ".local" / "share" / "tts" / model_folder_name / "config.json",
        Path("/app/models") / model_folder_name / "config.json",
        Path("/root/.local/share/tts") / model_folder_name / "config.json"
    ]
    
    for config_path in config_paths:
        try:
            if not os.path.exists(os.path.dirname(config_path)):
                os.makedirs(os.path.dirname(config_path), exist_ok=True)
                logger.info(f"Created directory for model config: {os.path.dirname(config_path)}")
            
            if os.path.exists(config_path):
                logger.info(f"Model config already exists at {config_path}")
        except Exception as e:
            logger.warning(f"Failed to create directory for model config at {config_path}: {e}")

if __name__ == "__main__":
    logger.info("Running pre-start script for Coqui TTS API")
    try:
        logger.info(f"Current user: {os.getuid()}:{os.getgid()}")
    except:
        logger.info("Could not determine user ID (Windows environment)")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Model name: {MODEL_NAME}")
    
    create_license_file()
    check_model_config()
    
    logger.info("Pre-start script completed successfully")
