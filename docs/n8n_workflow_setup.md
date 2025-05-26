# n8n Workflow Setup Guide

*Last updated: May 27, 2025*

This guide provides detailed steps for setting up the n8n workflow that powers the intelligence of your local voice assistant.

## Overview

The n8n workflow acts as the "brain" of your voice assistant, processing text queries, interacting with your local LLM, and returning formatted responses. It's designed to be customizable while providing a solid foundation for voice interactions.

## Prerequisites

- n8n installed and running ([Installation Guide](https://docs.n8n.io/hosting/installation/))
- Local LLM service running (Ollama, LM Studio, or compatible API)
- Backend service configured with the correct n8n webhook URL

## Basic Workflow Setup

### 1. Create a new workflow in n8n

1. Open your n8n instance (default: http://localhost:5678)
2. Click "Create new workflow"
3. Name it "Voice Assistant Processor"

### 2. Add a Webhook Trigger

1. Add a new node: search for "Webhook"
2. Configure as follows:
   - **Authentication**: None (for local use) or Basic Auth (for added security)
   - **HTTP Method**: POST
   - **Path**: /voice-assistant/query
   - **Response Mode**: Last Node

3. Save the node and copy the generated webhook URL
4. Update your `.env` file with this URL:
   ```
   N8N_WEBHOOK_URL=http://YOUR_N8N_HOST:5678/webhook/voice-assistant/query
   ```

### 3. Add a Function Node to Parse Input

1. Add a new node: search for "Function"
2. Connect it to the Webhook node
3. Add this code to parse the incoming text query:

```javascript
// Extract the text query from the incoming data
const inputText = items[0].json.text || "";
const userId = items[0].json.userId || "default";

// Simple request logging
console.log(`Received query: "${inputText}" from user: ${userId}`);

// Return the processed data
return [{
  json: {
    query: inputText,
    userId: userId,
    timestamp: new Date().toISOString()
  }
}];
```

### 4. Add an AI Agent Node for LLM Integration

Instead of using generic HTTP Request nodes, use n8n's built-in AI (OpenAI) node configured for your local LLM endpoint. This provides schema validation, logging, and streaming support.

1. Add a new node: search for "OpenAI"
2. Select **Chat** or **Completion** operation
3. In **Credentials**, click "New OpenAI API"
   - **API Key**: Leave blank (no key required for local)
   - **Base URL**: Set to your local LLM API (e.g., `http://localhost:11434/api` for Ollama,
     `http://localhost:1234/v1` for LM Studio, or `http://localhost:8080/v1` for LocalAI)
4. Configure the node:
   - **Model**: Enter your model name (e.g., `mistral`, `llama3-7b-chat`, or `mixtral-v2`)
   - **Prompt/Message**: Use the query from the Function node:
     ```
     You are a helpful voice assistant. Answer the following query briefly and conversationally: {{$json.query}}
     ```
5. Connect this node to the Function node from step 3
6. (Optional) Enable **Stream** to play back audio as it generates

### 5. Add a Function Node to Process the LLM Response

1. Add a new node: search for "Function"
2. Connect it to the AI Agent node
3. Add this code to extract and format the LLM response:

```javascript
// Handle different LLM API response formats
let response;

if (items[0].json.response) {
  // Ollama format
  response = items[0].json.response;
} else if (items[0].json.choices && items[0].json.choices[0]) {
  // OpenAI-compatible format (LocalAI, LM Studio)
  const choice = items[0].json.choices[0];
  if (choice.message && choice.message.content) {
    response = choice.message.content;
  } else if (choice.text) {
    response = choice.text;
  }
}

// Clean up the response for voice output
response = response || "Sorry, I couldn't process that request.";
response = response.trim();

// Return the final response
return [{
  json: {
    response: response
  }
}];
```

### 6. Add a Respond to Webhook Node

1. Add a new node: search for "Respond to Webhook"
2. Connect it to the last Function node
3. Configure it to return the processed response:
   - **Response Body**: JSON
   - **Properties to Send**: response

### 7. Activate the Workflow

1. Click the "Active" toggle in the top-right corner
2. Save the workflow

## Advanced Configurations

### Adding Context Memory

To enable your assistant to remember conversation history:

1. Add a "Split In Batches" node after the initial Function node
2. Add an "n8n Memory" node to retrieve previous conversation context
3. Configure with:
   - **Operation**: Read from memory
   - **Memory Name**: `conversation:{{$json.userId}}`

4. Add a "Merge" node to combine the query with the memory
5. Modify your AI Agent node to include conversation history in the prompt

### Home Automation Integration (with Node-RED or Home Assistant)

1. Add an "IF" node after the Function that processes input
2. Configure it to detect home automation commands:
   - **Condition**: Contains a home control keyword
3. Add an HTTP Request node to your home automation system's API

### Custom Skill Integration

1. Create a Switch node after parsing the input
2. Add conditions for different skill domains (weather, calendar, etc.)
3. For each domain, create a specific AI Agent or Function node

## Testing Your Workflow

1. With the workflow active, send a test request:
```bash
curl -X POST http://YOUR_N8N_HOST:5678/webhook/voice-assistant/query \
  -H "Content-Type: application/json" \
  -d '{"text": "what time is it?", "userId": "test-user"}'
```

2. You should receive a response from your LLM

## Troubleshooting

- **Webhook Not Receiving Data**: Check that the backend's `.env` file has the correct webhook URL
- **LLM Connection Errors**: Ensure your local LLM service is running and accessible
- **Slow Responses**: Consider using a smaller/faster model or increasing resource allocation

## Next Steps

- Improve prompt engineering for better responses
- Add specialized handlers for different query types
- Implement authentication for public-facing deployments
- Create custom skills for frequently used functions

## References

- [n8n Documentation](https://docs.n8n.io/)
- [Ollama API Reference](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [LocalAI Documentation](https://localai.io/docs/)