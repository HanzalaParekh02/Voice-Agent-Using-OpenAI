# config.py
# Loads environment variables and exposes app-wide settings

import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
APP_ENV: str = os.getenv("APP_ENV", "development")

# In production we require OPENAI_API_KEY to be present.
if not OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY is not set. This service requires a valid OpenAI API key to start."
    )
