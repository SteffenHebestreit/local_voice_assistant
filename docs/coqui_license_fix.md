# Coqui TTS License Fix Implementation

## Problem Statement
The Coqui TTS API container was failing because it required interactive license acceptance in a non-interactive Docker environment. This was particularly problematic for the XTTS v2 model which has a license agreement that must be accepted before use.

## Solution Approach
We implemented the recommended `COQUI_TOS_AGREED` environment variable approach based on Coqui TTS developers' recommendations. This approach:

1. Sets an environment variable that tells Coqui TTS to automatically accept the license agreement
2. Eliminates the need for interactive prompts in a Docker environment
3. Is much simpler than previous workarounds involving monkey-patching and custom stdin overrides

## Implementation Details

### 1. Dockerfile Changes
We added the environment variable to the Dockerfile:

```dockerfile
# Set environment variables for model configuration (can be overridden in docker-compose)
ENV COQUI_MODEL="tts_models/en/ljspeech/tacotron2-DDC"
ENV COQUI_SPEAKER_WAV=""
ENV COQUI_LANGUAGE="en"
ENV USE_CUDA="true"
# Set environment variable to accept the license agreement automatically
ENV COQUI_TOS_AGREED="1"
```

### 2. app.py Changes
We set the environment variable in app.py before importing the TTS module:

```python
# Set environment variable to accept license agreement
os.environ["COQUI_TOS_AGREED"] = "1"

# Now import TTS after setting the environment variable
from TTS.api import TTS
```

### 3. rebuild_coqui.ps1 Changes
We updated the script to explain the new approach:

```powershell
# Explain the environment variable approach
Write-Host "Setting up automatic license acceptance in app.py and Dockerfile..." -ForegroundColor Yellow
Write-Host "The app.py file and Dockerfile have been updated to use the COQUI_TOS_AGREED environment variable." -ForegroundColor Yellow
Write-Host "This is the recommended approach by Coqui TTS developers and solves the issue with interactive license prompts in Docker containers." -ForegroundColor Yellow
```

### 4. troubleshooting.md Changes
We updated the troubleshooting documentation:

```markdown
1. **XTTS License Agreement Issue**
   - If you see an error about accepting the XTTS model license agreement
   - The system now uses the `COQUI_TOS_AGREED=1` environment variable in the Dockerfile to automatically accept the license
   - If you still encounter issues, run the `accept_license.cmd` script which will automatically accept the license
```

### 5. accept_license.ps1 Changes
We updated the script to inform users about the new approach while keeping backward compatibility:

```powershell
Write-Host "NOTE: This project now uses the COQUI_TOS_AGREED environment variable approach." -ForegroundColor Yellow
Write-Host "This is the recommended method by Coqui TTS developers and simplifies license acceptance." -ForegroundColor Yellow
Write-Host "The environment variable is already set in the Dockerfile and app.py." -ForegroundColor Yellow
Write-Host "This script is kept for backward compatibility and as a fallback method." -ForegroundColor Yellow
```

## Verification
1. Built the container using `docker-compose build coqui-tts-api`
2. Started the container using `docker-compose up -d coqui-tts-api`
3. Checked the logs to confirm:
   - No license acceptance prompts interrupting the process
   - Model downloading without interactive prompts
   - Container running successfully

## Benefits
- **Simplicity**: Much cleaner solution than previous approaches
- **Reliability**: Follows Coqui TTS developers' recommendations
- **Maintainability**: Easier to understand and maintain
- **Future-proof**: Will work with future versions of Coqui TTS

## References
- Coqui TTS GitHub repository discussions on license acceptance
- Docker best practices for environment variables
- FastAPI documentation on environment variable configuration
