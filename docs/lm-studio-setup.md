# LM Studio Setup Guide

## Installation & Setup

### 1. Install LM Studio

If you haven't already, download LM Studio from: https://lmstudio.ai/

### 2. Download a Model

1. Open LM Studio
2. Go to the "Discover" tab
3. Search for and download one of these recommended models for SQL generation:
   - **Mistral 7B Instruct** (good balance of speed and quality)
   - **Llama 3.1 8B Instruct** (excellent for code/SQL)
   - **CodeLlama 7B** (specialized for code generation)
   - **Phi-3 Mini** (smaller, faster option)

### 3. Load the Model

1. Go to the "Models" tab
2. Select your downloaded model
3. Click "Load" 
4. Wait for the model to load into memory

### 4. Start the Local Server

1. Go to the "Local Server" tab
2. Configure settings:
   - **Port**: 1234 (default)
   - **CORS**: Enable (allows web apps to connect)
   - **Request Logging**: Enable (helpful for debugging)
3. Click "Start Server"
4. You should see "Server is running on http://localhost:1234"

### 5. Verify Connection

Run the test script:
```bash
python3 test_lm_studio.py
```

## Configuration for DuckDB Analytics App

### Environment Variables (.env file)

Create a `.env` file in the project root:
```env
# LM Studio Configuration
LM_STUDIO_URL=http://localhost:1234
LM_STUDIO_MODEL=auto  # Uses whatever model is loaded
LM_STUDIO_TIMEOUT=30

# Optional: Specific prompting for SQL
LM_STUDIO_SYSTEM_PROMPT="You are a SQL expert assistant. Convert natural language queries to DuckDB SQL. Only respond with valid SQL queries, no explanations."
```

### Python Configuration

In your code, use:
```python
import os
from dotenv import load_dotenv

load_dotenv()

LM_STUDIO_CONFIG = {
    "url": os.getenv("LM_STUDIO_URL", "http://localhost:1234"),
    "timeout": int(os.getenv("LM_STUDIO_TIMEOUT", "30")),
    "system_prompt": os.getenv("LM_STUDIO_SYSTEM_PROMPT", 
        "You are a SQL expert. Convert natural language to DuckDB SQL queries.")
}
```

## API Endpoints

LM Studio provides OpenAI-compatible endpoints:

### List Models
```
GET http://localhost:1234/v1/models
```

### Chat Completion
```
POST http://localhost:1234/v1/chat/completions
```

Example request:
```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are a SQL expert. Convert natural language to DuckDB SQL."
    },
    {
      "role": "user",
      "content": "Show me top 10 customers by revenue"
    }
  ],
  "temperature": 0.7,
  "max_tokens": 500,
  "stream": false
}
```

## Troubleshooting

### LM Studio Won't Start
- Check if port 1234 is already in use
- Try a different port (8080, 5000, etc.)
- Restart LM Studio application

### Model Won't Load
- Check available RAM (need ~4-8GB free for 7B models)
- Try a smaller model (Phi-3 Mini)
- Close other applications to free memory

### Slow Response Times
- Use a smaller model
- Reduce max_tokens in requests
- Enable GPU acceleration if available
- Lower the context window in LM Studio settings

### Connection Refused
1. Ensure LM Studio server is running
2. Check firewall settings
3. Verify the correct port
4. Try `127.0.0.1` instead of `localhost`

## Best Practices for SQL Generation

1. **Use Clear System Prompts**: Be specific about wanting DuckDB SQL
2. **Include Schema Context**: Pass table schemas in the system prompt
3. **Temperature Settings**: Use lower temperature (0.3-0.5) for more deterministic SQL
4. **Validation**: Always validate generated SQL before execution
5. **Error Handling**: Catch and handle malformed SQL responses

## Example Integration

```python
import requests
from typing import Optional

class LMStudioClient:
    def __init__(self, base_url: str = "http://localhost:1234"):
        self.base_url = base_url
        self.headers = {"Content-Type": "application/json"}
    
    def generate_sql(self, natural_language: str, schema_context: str = "") -> Optional[str]:
        """Convert natural language to SQL using LM Studio."""
        
        system_prompt = f"""You are a DuckDB SQL expert. Convert the user's natural language query to valid DuckDB SQL.
        {schema_context}
        Respond ONLY with the SQL query, no explanations or markdown."""
        
        try:
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": natural_language}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 500,
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
            else:
                print(f"Error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Connection error: {e}")
            return None

# Usage
client = LMStudioClient()
sql = client.generate_sql("Show me the top 10 customers by total sales")
print(sql)
```