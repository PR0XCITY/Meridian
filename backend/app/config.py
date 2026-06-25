from dotenv import load_dotenv
from pathlib import Path
import os

# Resolve .env relative to this file (backend/.env)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LLM_MODEL = "llama-3.3-70b-versatile"
MAX_ITERATIONS = 15
SANDBOX_IMAGE = "python:3.11-alpine"
SANDBOX_TIMEOUT = 30  # seconds