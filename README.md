# tg_vava_bot
Telegram chat bot created with Python 3.8.5. Communication implemented with a webhook. App implemented with Flask. Easy to deploy to Heroku.

App uses Telegram Bot API for communication with Telegram and Google Search API for the searches.

```
@bot_name *query* - Select and send an image from Google image search results with the given query

/img *query* - Post the first image from Google image search with the given query ("I'm Feeling Lucky")

/puppu *input* - Generate a "puppulause" from the given input (From http://puppulausegeneraattori.fi/)

/inspis - Generate a random inspirational image (From https://inspirobot.me/)

/ask - Ask questions or talk to VavaBot (Using GPT-3 https://openai.com/blog/openai-api/)

/subscribe - Subscribe chat to bargain alerts

/unsubscribe - Unsubscribe chat from bargain alerts

/help - Show this help message
```

You need to add ENV variables:

- TOKEN from Telegram Bot API and HOOK for the Telegram hook url.

- G_KEY and G_CX from Google Search API

- OPENAI_API_KEY from OpenAI API
