#!/usr/bin/env python3
"""
Patch script for Coqui TTS API to automatically accept the license agreement
This script modifies the TTS library to automatically accept the license agreement
"""
import os
import sys
import logging
import importlib.util
import inspect
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("patch_tts")

def find_tts_manage_module():
    """Find the TTS.utils.manage module path"""
    try:
        # Try to import the module to get its location
        import TTS.utils.manage as manage_module
        module_path = inspect.getfile(manage_module)
        logger.info(f"Found TTS.utils.manage module at: {module_path}")
        return module_path
    except ImportError:
        logger.error("Could not import TTS.utils.manage. Make sure TTS is installed.")
        return None

def patch_tts_module(module_path):
    """Patch the TTS.utils.manage module to auto-accept license agreements"""
    if not module_path or not os.path.exists(module_path):
        logger.error(f"Module path does not exist: {module_path}")
        return False
    
    try:
        # Read the module content
        with open(module_path, 'r') as f:
            content = f.read()
        
        # Check if we've already patched this file
        if "# AUTO-ACCEPT LICENSE PATCH APPLIED" in content:
            logger.info("Module already patched. Skipping.")
            return True
        
        # Find the ask_tos method
        if "def ask_tos(self, output_path):" not in content:
            logger.error("Could not find ask_tos method in the module.")
            return False
        
        # Create the patched method
        original_method = """    def ask_tos(self, output_path):
        """
        
        patched_method = """    def ask_tos(self, output_path):
        # AUTO-ACCEPT LICENSE PATCH APPLIED
        logger = logging.getLogger("TTS")
        logger.info("Auto-accepting license agreement for non-interactive environments")
        try:
            models_yaml = self.get_models_yaml_path()
            model_name = self.model_name_from_output_path(output_path)
            if not self.model_has_been_accepted(models_yaml, model_name):
                self.add_model_to_models_yaml(models_yaml, model_name)
                logger.info(f"License auto-accepted for {model_name}")
            return True
        except Exception as e:
            logger.warning(f"Error while auto-accepting license: {e}")
            # Continue anyway to avoid blocking in non-interactive environments
            return True
        """
        
        # Replace the method
        patched_content = content.replace(original_method, patched_method)
        
        # Write the patched module back
        with open(module_path, 'w') as f:
            f.write(patched_content)
        
        logger.info(f"Successfully patched {module_path} to auto-accept license agreements")
        return True
    
    except Exception as e:
        logger.error(f"Failed to patch module: {e}")
        return False

if __name__ == "__main__":
    logger.info("Running TTS library patch to auto-accept license agreements")
    
    # Find the TTS.utils.manage module
    module_path = find_tts_manage_module()
    if not module_path:
        sys.exit(1)
    
    # Patch the module
    if not patch_tts_module(module_path):
        logger.error("Failed to patch TTS module")
        sys.exit(1)
    
    logger.info("Patch completed successfully. TTS will now auto-accept license agreements.")
