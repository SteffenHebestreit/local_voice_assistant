# LLM Setup Guide

*Last updated: May 27, 2025*

This guide provides detailed instructions for setting up and configuring various Local Large Language Model (LLM) providers to work with your voice assistant.

## Overview

The LLM is the intelligence behind your voice assistant, processing queries and generating responses. This guide covers setup for popular local LLM solutions that can run efficiently on consumer hardware.

## Choosing an LLM Provider

| Provider | Ease of Setup | GPU Requirements | CPU-Only Performance | Best For |
|----------|---------------|------------------|----------------------|----------|
| Ollama   | Very Easy     | Minimal          | Good                 | Beginners, quick setup |
| LM Studio| Easy          | Flexible         | Very Good            | Testing different models |
| LocalAI  | Moderate      | Customizable     | Good                 | Advanced users, extensibility |

## 1. Ollama Setup

### Installation

#### Windows
1. Download the installer from [Ollama.com](https://ollama.com)
2. Run the installer and follow the prompts
3. Ollama will run as a service in the background

#### Linux
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

#### macOS
```bash
brew install ollama
```

### Configuration

1. Start Ollama (should run automatically after installation)
2. Pull a model:
   ```bash
   ollama pull mixtral-v2       # ~7.6GB, top mixture-of-experts model
   # OR for balanced performance
   ollama pull mistral-7b       # ~4GB, efficient and versatile model
   # OR for light hardware
   ollama pull tinyllama        # ~3GB, compact Llama variant
   # OR edge-optimized
   ollama pull phi2             # ~1.7GB, Microsoft Phi-2 model
   ```

3. Test the model:
   ```bash
   ollama run mistral-7b "Hello, are you working properly?"
   ```

4. For custom parameters, create a Modelfile:
   ```
   # Create a file named 'Modelfile'
   FROM mistral-7b
   PARAMETER temperature 0.7
   PARAMETER top_p 0.9
   PARAMETER system "You are a helpful voice assistant that gives concise spoken responses."
   
   # Build the custom model
   ollama create assistant-mistral -f Modelfile
   ```

### Integration with the Voice Assistant

1. Update your n8n workflow to use the Ollama API:
   - API Endpoint: `http://localhost:11434/api/generate`
   - Set the model name to match your pulled model

2. No API key required for local Ollama instance

## 2. LM Studio Setup

### Installation

1. Download LM Studio from [lmstudio.ai](https://lmstudio.ai/) 
2. Install and launch the application

### Configuration

1. In LM Studio, go to the "Models" tab
2. Download a model:
   - Recommended starter: `mixtral-v2` (Mixture-of-Experts, best overall)
   - For balanced performance: `llama3-7b-chat`
   - For lower-end systems: `tinyllama` or `phi2`

3. Once downloaded, click "Chat" in the sidebar
4. Select your model from the dropdown
5. Click on "Local Inference Server" in the sidebar
6. Click "Start Server" - this exposes an OpenAI-compatible API

### Integration with the Voice Assistant

1. Update your n8n workflow to use the LM Studio API:
   - API Endpoint: `http://localhost:1234/v1/chat/completions`
   - No need to specify model name in the request

2. No API key required for local LM Studio instance

## 3. LocalAI Setup

### Installation with Docker

```bash
docker run -p 8080:8080 -v ~/.local/share/localai:/root/.local/share/localai -e CUDA_VISIBLE_DEVICES=0 --gpus all localai/localai:v2.7.0-cublas-cuda12
```

For CPU-only:
```bash
docker run -p 8080:8080 -v ~/.local/share/localai:/root/.local/share/localai localai/localai:latest
```

### Configuration

1. Download a model through the API:
```bash
curl -X POST http://localhost:8080/models/apply -H "Content-Type: application/json" -d '{
  "name": "mistral-7b-instruct",
  "url": "github:go-skynet/model-gallery/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
}'
```

2. Test the model:
```bash
curl http://localhost:8080/v1/chat/completions -H "Content-Type: application/json" -d '{
  "model": "mistral-7b-instruct",
  "messages": [{"role": "user", "content": "Hello, are you working?"}]
}'
```

### Integration with the Voice Assistant

1. Update your n8n workflow to use the LocalAI API:
   - API Endpoint: `http://localhost:8080/v1/chat/completions`
   - Specify the model name in the request

## Model Recommendations

### For Low-End Systems (≤4GB RAM)
- **phi2**: 1.7GB model suitable for very constrained hardware
- **tinyllama**: ~3GB, compact Llama variant with modest performance
- **mistral-7b-instruct**: ~4GB quantized model for balanced performance

### For Mid-Range Systems (8–16GB RAM)
- **mixtral-v2**: ~7.6GB mixture-of-experts, best overall performance
- **llama3-7b-chat**: ~7GB Chat-optimized LLaMA 3 model
- **mistral-7b-instruct**: Standard instruct-tuned model

### For High-End Systems (16GB+ RAM or GPU)
- **mixtral-v3**: Latest mixture-of-experts with improved capabilities
- **llama3-13b-chat**: High-capacity chat model
- **mixtral-v2 (Q5_K_M)**: Higher quantized variant for quality

## Prompt Engineering

### Prompt Engineering
For voice assistant responses, keep prompts simple and speech-friendly:
- Keep responses concise (1–2 sentences).
- Use plain language without markdown or technical symbols.
- Set a friendly, conversational tone.

**Example prompt**:
```
You are a voice assistant. Answer briefly and conversationally in plain language.
```

## Troubleshooting

### Common Issues

1. **Out of Memory Errors**:
   - Try a smaller model or higher quantization level (Q4 vs Q5)
   - Close other applications to free RAM
   - Enable swap space/virtual memory

2. **Slow Response Times**:
   - Use a more heavily quantized model (Q4_K_M instead of Q8_0)
   - Set a lower max_tokens value in your API requests
   - If using CPU, try enabling more threads with environment variables:
     ```
     OLLAMA_NUM_THREAD=4 ollama serve
     ```

3. **API Connection Errors**:
   - Verify the service is running with correct ports exposed
   - Check for firewall blocking the connection
   - Verify Docker network configurations if using containers

## Performance Optimization

### CPU Optimization
- Enable hardware acceleration if available (AVX2, AVX-512)
- Set appropriate thread counts based on your CPU
- Lower context length for faster responses

### GPU Optimization
- For NVIDIA GPUs, ensure CUDA is properly installed
- For AMD GPUs, check ROCm compatibility
- Adjust batch size based on available VRAM

## References
- [Ollama Documentation](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [LM Studio Documentation](https://lmstudio.ai/docs)
- [LocalAI Documentation](https://localai.io/docs/)
- [GGUF Model Format](https://github.com/ggerganov/ggml/blob/master/docs/gguf.md)