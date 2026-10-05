# Settings come from environment variables (or a local .env file). Never put keys in this file.
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "3"))
