import os

# Environment variables
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///app.db")

TELEGRAM_TOKEN = os.getenv("TOKEN", "test")

TELEGRAM_HOOK = os.getenv("HOOK", "test")

GOOGLE_SEARCH_KEY = os.getenv("G_KEY", "test")

GOOGLE_SEARCH_CX = os.getenv("G_CX", "test")

EXTERNAL_ENDPOINT_KEY = os.getenv("EXTERNAL_ENDPOINT_KEY", "test")

SENTRY_DSN = os.getenv("SENTRY_DSN", "")
