import os
import sys
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()


# Mistral client — try import, with fallback to the repo virtualenv site-packages
def _import_mistralai_with_fallback():
    try:
        from mistralai import Mistral, UserMessage, SystemMessage
        return Mistral, UserMessage, SystemMessage
    except Exception as orig_err:
        # Try common local venv paths relative to the project root
        base = os.path.dirname(__file__)
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        candidates = [
            os.path.join(base, "env", "Lib", "site-packages"),
            os.path.join(base, "env", "lib", py_ver, "site-packages"),
            os.path.join(base, ".venv", "Lib", "site-packages"),
            os.path.join(base, ".venv", "lib", py_ver, "site-packages"),
        ]

        for p in candidates:
            if os.path.isdir(p) and p not in sys.path:
                sys.path.insert(0, p)
                try:
                    from mistralai import Mistral, UserMessage, SystemMessage
                    return Mistral, UserMessage, SystemMessage
                except Exception:
                    # continue trying other candidate paths
                    pass

        # If we reach here, we couldn't import even after trying local venv paths
        raise RuntimeError(
            "mistralai import failed. Install the SDK in the active environment or activate the project's virtualenv. "
            "On Windows PowerShell run: `env\\Scripts\\Activate.ps1` then `pip install mistralai`. "
            f"Original error: {orig_err}"
        )


Mistral, UserMessage, SystemMessage = _import_mistralai_with_fallback()

app = FastAPI(title="Coderrr Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TOKEN = os.getenv("GITHUB_TOKEN") or os.getenv("MISTRAL_API_KEY")
ENDPOINT = os.getenv("MISTRAL_ENDPOINT", "https://models.github.ai/inference")
MODEL_NAME = os.getenv("MISTRAL_MODEL", "mistral-ai/Mistral-Large-2411")

client = Mistral(api_key=TOKEN, server_url=ENDPOINT)


SYSTEM_INSTRUCTIONS = """
You are Coderrr, a coding assistant that MUST respond with a JSON object for execution plans.
When the user asks for code changes or tasks, produce a JSON object with this EXACT schema:

{
  "explanation": "Brief plain English explanation of what you will do and why",
  "plan": [
    {
      "action": "create_file" | "update_file" | "patch_file" | "delete_file" | "read_file" | "run_command",
      "path": "relative/path/to/file",
      "content": "complete file content for create_file or update_file",
      "oldContent": "content to find (for patch_file)",
      "newContent": "content to replace with (for patch_file)",
      "command": "shell command (for run_command)",
      "summary": "one-line description for this step"
    }
  ]
}

CRITICAL RULES:
1. Return ONLY valid JSON. Wrap it in ```json ``` if you want, but the JSON must be valid.
2. The "explanation" field is required and should be a clear, concise summary.
3. Each item in "plan" must have "action" and "summary".
4. For file operations, include "path".
5. For create_file/update_file, include "content" with the COMPLETE file content.
6. For patch_file, include "oldContent" and "newContent".
7. For run_command, include "command".
8. Use relative paths from the project root.
9. Be explicit and conservative - small, clear steps are better than large complex ones.
10. For test execution, use run_command with the appropriate test command (npm test, pytest, etc).

Example response:
```json
{
  "explanation": "I will create a new user authentication module with JWT support",
  "plan": [
    {
      "action": "create_file",
      "path": "src/auth.py",
      "content": "# Authentication module\\nimport jwt\\n\\ndef authenticate(user, password):\\n    # TODO: implement\\n    pass",
      "summary": "Create authentication module"
    },
    {
      "action": "run_command",
      "command": "pytest tests/test_auth.py",
      "summary": "Run authentication tests"
    }
  ]
}
```

Now respond to the user's request with a valid JSON plan.
"""

@app.get("/")
def root():
    return {"message": "Coderrr backend is running 🚀", "model": MODEL_NAME}

@app.post("/chat")
async def chat(req: Request):
    body = await req.json()
    user_prompt = body.get("prompt", "")
    if not user_prompt:
        return {"error": "prompt required"}, 400

    system_prompt = SYSTEM_INSTRUCTIONS
    # Append user request asking for a plan in JSON
    user_message = f"User request: {user_prompt}\n\nPlease output a JSON object with explanation and plan as described."

    try:
        response = client.chat.complete(
            model=MODEL_NAME,
            messages=[
                SystemMessage(content=system_prompt),
                UserMessage(content=user_message)
            ],
            temperature=float(body.get("temperature", 0.2)),
            max_tokens=int(body.get("max_tokens", 1500)),
            top_p=float(body.get("top_p", 1.0))
        )
        # Extract model text
        text = ""
        try:
            text = response.choices[0].message.content
        except Exception:
            text = str(response)

        # Return raw text and let CLI try to parse JSON
        return {"response": text}
    except Exception as e:
        return {"error": "model request failed", "details": str(e)}, 500
