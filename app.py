import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from openai import OpenAI
from PIL import Image
from io import BytesIO
import base64

# === Настройки ===
TELEGRAM_TOKEN = "8026450624:AAFCN-efXeC1psLFRNsZN5uPwwgydOHPD00"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise Exception("Нужно задать OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)
app = Flask(__name__)

# === Telegram Application ===
bot_app = Application.builder().token(TELEGRAM_TOKEN).build()

# === Функция обработки изображений через GPT Vision ===
async def image_to_text(photo_file):
    try:
        image_bytes = BytesIO()
        await photo_file.download_to_memory(out=image_bytes)
        image_bytes.seek(0)
        image = Image.open(image_bytes)

        buffer = BytesIO()
        image.convert("RGB").save(buffer, format="JPEG")
        img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Реши задачу кратко. Ответ до 100 слов."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}}
                    ]
                }
            ],
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Ошибка GPT: {str(e)}"

# === Хендлер сообщений ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.message.photo:
            photo = update.message.photo[-1]
            photo_file = await context.bot.get_file(photo.file_id)
            answer = await image_to_text(photo_file)
            await update.message.reply_text(f"🖼 Ответ:\n{answer}")

        elif update.message.text:
            text = update.message.text
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": text}],
                max_tokens=150
            )
            answer = response.choices[0].message.content.strip()
            await update.message.reply_text(f"💬 Ответ:\n{answer}")

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

# === Подключаем хендлер ===
bot_app.add_handler(MessageHandler(filters.ALL, handle_message))

# === Инициализация бота при старте Flask ===
loop = asyncio.get_event_loop()
loop.run_until_complete(bot_app.initialize())
loop.run_until_complete(bot_app.start())

# === Webhook для Render ===
@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    # Thread-safe добавление в очередь
    future = asyncio.run_coroutine_threadsafe(bot_app.update_queue.put(update), bot_app._loop)
    future.result()
    return "ok"
