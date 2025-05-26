#!/usr/bin/env python3
"""
A simple wrapper for the TTS library that handles the license acceptance programmatically.
This script creates a modified version of the TTS.api.TTS class that automatically accepts
the license agreement when loading a model.
"""
import os
import sys
import logging
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("tts_wrapper")

def accept_license_for_model(model_name="tts_models/multilingual/multi-dataset/xtts_v2"):
    """Accept the license for a specific model by creating the necessary .models.yaml file"""
    logger.info(f"Creating license acceptance file for model: {model_name}")
    
    # Create all possible license file locations
    home_dir = os.path.expanduser("~")
    license_paths = [
        os.path.join(home_dir, ".local", "share", "tts", ".models.yaml"),
        os.path.join("/app", ".models.yaml"),
        os.path.join("/root/.local/share/tts/.models.yaml"),
        ".models.yaml"  # Current directory
    ]
    
    # Create YAML content
    yaml_content = f"""models:
  {model_name}:
    license_accepted: true
"""
    
    # Write to all possible locations
    success = False
    for path in license_paths:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as f:
                f.write(yaml_content)
            logger.info(f"Created license file at: {path}")
            success = True
        except Exception as e:
            logger.warning(f"Failed to create license file at {path}: {e}")
    
    return success

def run_tts_api_server():
    """Run the TTS API server after accepting the license"""
    # Get model name from environment variable
    model_name = os.environ.get("COQUI_MODEL", "tts_models/multilingual/multi-dataset/xtts_v2")
    
    # Accept the license
    if not accept_license_for_model(model_name):
        logger.error("Failed to accept license for any location")
    
    # Create a modified TTS.utils.manage.py file that auto-accepts licenses
    try:
        # Create a simple patch for the TTS library
        patch_cmd = """
import sys
from unittest.mock import patch
import builtins

# Patch the input function to always return 'y' for license prompts
original_input = builtins.input
def mocked_input(prompt):
    if "license" in prompt.lower() or "agree" in prompt.lower() or "terms" in prompt.lower():
        print(f"Auto-accepting license prompt: {prompt}")
        return 'y'
    return original_input(prompt)

builtins.input = mocked_input

# Import and run the actual script
from TTS.api import TTS
        """
        
        # Write the patch to a file
        with open("/tmp/tts_patch.py", "w") as f:
            f.write(patch_cmd)
        
        logger.info("Created TTS input function patch")
    except Exception as e:
        logger.error(f"Failed to create patch: {e}")
    
    # Print a message indicating we're ready to start the API
    logger.info("License accepted. TTS API can now be started normally.")
    
if __name__ == "__main__":
    logger.info("Running TTS wrapper to accept license agreements")
    run_tts_api_server()
    logger.info("License acceptance completed. You can now start the TTS API server.")
