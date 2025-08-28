# LM Studio Setup Instructions

## Prerequisites
- LM Studio installed from [https://lmstudio.ai/](https://lmstudio.ai/)
- At least 8GB RAM for running 7B quantized models

## Model Setup

### Recommended Model
Download the SQLCoder model for best SQL generation results:
- **Model**: `sqlcoder-7b-q4_K_M.gguf` 
- **Source**: HuggingFace or LM Studio's model browser
- **Size**: ~4GB
- **Requirements**: No GPU required (runs on CPU)

### Alternative SQL Models
- CodeLlama-7B-Instruct (Q4_K_M)
- Mistral-7B-Instruct (Q4_K_M)
- Any model with SQL training

## LM Studio Configuration

1. **Load the Model**
   - Open LM Studio
   - Go to the "Models" tab
   - Search for and download SQLCoder or your chosen model
   - Load the model with these settings:
     - Context Length: 4096
     - GPU Layers: 0 (for CPU-only) or adjust based on your GPU

2. **Start Local Server**
   - Navigate to the "Local Server" tab
   - Set port to `1234` (default)
   - Click "Start Server"
   - Verify server is running at `http://localhost:1234`

3. **Test the Connection**
   ```bash
   curl http://localhost:1234/v1/models
   ```
   Should return a JSON response with available models.

## Running with DuckDB Analytics

1. Ensure LM Studio server is running on port 1234
2. Start the DuckDB Analytics application:
   ```bash
   streamlit run app.py
   ```
3. The chat interface will automatically connect to LM Studio

## Troubleshooting

- **Connection Failed**: Ensure LM Studio server is running and accessible at `http://localhost:1234`
- **Slow Response**: Consider using a smaller quantized model (Q3_K_S or Q2_K)
- **Out of Memory**: Reduce context length or use a smaller model
- **No SQL Generated**: Verify you're using a SQL-capable model like SQLCoder