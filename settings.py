import os

from environs import Env

env = Env()

if os.path.exists(".env"):
    env.read_env()  # read .env file, if it exists


REQUEST_TIMEOUT = 30

# Environment variables
PORT = env("PORT", 5002)

DATABASE_URL = env("DATABASE_URL", "sqlite:///app.db")

TARJOUSHAUKKA_URL = env("TARJOUSHAUKKA_URL", "http://192.168.1.16:5000")

TELEGRAM_TOKEN = env("TOKEN", "test")

TELEGRAM_HOOK = env("HOOK", "test")

GOOGLE_SEARCH_KEY = env("G_KEY", "test")

GOOGLE_SEARCH_CX = env("G_CX", "test")

EXTERNAL_ENDPOINT_KEY = env("EXTERNAL_ENDPOINT_KEY", "test")

SENTRY_DSN = env("SENTRY_DSN", "")

OPENAI_API_KEY = env("OPENAI_API_KEY", "")

OPENAI_CHAT_IDS = env.list("OPENAI_CHAT_IDS", [], subcast=str)

RAPIDAPI_KEY = env("RAPIDAPI_KEY", "")

RIOT_API_KEY = env("RIOT_API_KEY", "")
