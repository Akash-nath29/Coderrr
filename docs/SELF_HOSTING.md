# Self-Hosting Coderrr Backend

Most users don't need this! The default hosted backend works great. But if you want to run your own backend for privacy, customization, or development, follow this guide.

## Why Self-Host?

- **Privacy**: Keep your code and AI interactions private
- **Customization**: Use different AI models or providers
- **Development**: Contribute to the backend or test changes
- **Cost Control**: Use your own API keys and control costs

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- An AI provider API key (GitHub Models, Mistral AI, etc.)

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/Akash-nath29/Coderrr.git
cd Coderrr
```

### 2. Set Up Python Virtual Environment

**Windows:**
```powershell
python -m venv env
.\env\Scripts\Activate.ps1
```

**Linux/Mac:**
```bash
python3 -m venv env
source env/bin/activate
```

### 3. Install Python Dependencies

```bash
pip install -r backend/requirements.txt
```

### 4. Configure Backend

Create `backend/.env` file:

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` with your API credentials:

```env
# Choose ONE authentication method:

# Option 1: GitHub Models (Free tier available)
GITHUB_TOKEN=ghp_your_github_token_here

# Option 2: Mistral AI Direct
# MISTRAL_API_KEY=your_mistral_api_key_here

# Model Configuration
MISTRAL_ENDPOINT=https://models.inference.ai.azure.com
MISTRAL_MODEL=mistral-large-2411

# Server Configuration
TIMEOUT_MS=120000
```

#### Getting API Keys

**GitHub Models (Recommended for Free Tier):**
1. Go to https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Select scopes: `read:user` (minimal)
4. Copy the token and paste in `GITHUB_TOKEN`

**Mistral AI:**
1. Go to https://console.mistral.ai/
2. Sign up and navigate to API Keys
3. Create a new API key
4. Copy and paste in `MISTRAL_API_KEY`

### 5. Start the Backend

**Development Mode (with auto-reload):**
```bash
cd backend
uvicorn main:app --reload --port 5000
```

**Production Mode:**
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 5000 --workers 4
```

The backend will be available at `http://localhost:8000`

### 6. Configure CLI to Use Local Backend

Create `~/.coderrr/.env`:

**Windows:**
```powershell
mkdir $HOME\.coderrr
echo CODERRR_BACKEND=http://localhost:8000 > $HOME\.coderrr\.env
```

**Linux/Mac:**
```bash
mkdir -p ~/.coderrr
echo "CODERRR_BACKEND=http://localhost:8000" > ~/.coderrr/.env
```

### 7. Test It

```bash
coderrr exec "Create a hello world script"
```

## Production Deployment

For production deployment, see our [Deployment Guide](./DEPLOYMENT.md) which covers:
- Docker deployment
- Cloud hosting (AWS, Azure, GCP)
- Vercel/Netlify deployment
- PM2 process management
- Nginx reverse proxy setup

## Troubleshooting

### Backend won't start

**Error: `ModuleNotFoundError: No module named 'fastapi'`**
- Solution: Make sure you activated the virtual environment and ran `pip install -r backend/requirements.txt`

**Error: `Address already in use`**
- Solution: Port 5000 is already taken. Either kill the process using port 5000 or use a different port:
  ```bash
  uvicorn main:app --port 5001
  ```
  Then update `CODERRR_BACKEND=http://localhost:5001`

### CLI can't connect to backend

**Error: `Failed to communicate with backend: ECONNREFUSED`**
- Check backend is running: `curl http://localhost:8000` should return a JSON response
- Check `~/.coderrr/.env` has correct `CODERRR_BACKEND` URL
- Check firewall isn't blocking port 5000

### API authentication errors

**Error: `401 Unauthorized`**
- Verify your API key is correct in `backend/.env`
- For GitHub token: check it has required permissions
- For Mistral: verify key is active on their console

## Advanced Configuration

### Using Different AI Models

Edit `backend/.env`:

```env
# Use GPT-4 via Azure
MISTRAL_ENDPOINT=https://your-azure-endpoint.openai.azure.com
MISTRAL_MODEL=gpt-4

# Use Claude via custom endpoint
MISTRAL_ENDPOINT=https://api.anthropic.com
MISTRAL_MODEL=claude-3-opus
```

Note: You may need to modify `backend/main.py` for providers other than Mistral/GitHub Models.

### Increasing Timeout

For large requests:

```env
TIMEOUT_MS=300000  # 5 minutes
```

### Rate Limiting

Add to `backend/main.py`:

```python
from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/chat")
@limiter.limit("10/minute")
async def chat(request: Request, body: ChatRequest):
    # ... existing code
```

## Security Considerations

- **Never commit** `.env` files to git
- **Use strong API keys** and rotate them regularly
- **Run backend on localhost** only unless you need remote access
- **Enable firewall** if exposing backend to internet
- **Use HTTPS** in production with reverse proxy
- **Monitor API usage** to prevent unexpected costs

## Need Help?

- [GitHub Discussions](https://github.com/Akash-nath29/Coderrr/discussions)
- [Open an Issue](https://github.com/Akash-nath29/Coderrr/issues)
- [Contributing Guide](../CONTRIBUTING.md)

---

**Remember:** Most users don't need to self-host! The default hosted backend at `https://coderrr-backend.vercel.app` works great for normal use.
