import os
import telegram
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from openai import OpenAI
from PIL import Image
import requests
from io import BytesIO

# === ТВОИ НАСТРОЙКИ ===
TELEGRAM_TOKEN = "8026450624:AAFCN-efXeC1psLFRNsZN5uPwwgydOHPD00"
CHAT_ID = 1570500473
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    print("❌ OPENAI_API_KEY не задан!")
    exit(1)

client = OpenAI(api_key=OPENAI_API_KEY)

async def image_to_text(photo_file):
    try:
        image_bytes = BytesIO()
        await photo_file.download_to_memory(out=image_bytes)
        image_bytes.seek(0)
        image = Image.open(image_bytes)

        buffer = BytesIO()
        image.convert("RGB").save(buffer, format="JPEG")
        img_base64 = buffer.getvalue().encode('base64').decode().replace('\n', '')

        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Реши задачу кратко. Ответ до 100 слов."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"image/jpeg;base64,{img_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Ошибка GPT: {str(e)}"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID:
        return

    try:
        if update.message.photo:
            photo = update.message.photo[-1]
            photo_file = await context.bot.get_file(photo.file_id)
            answer = await image_to_text(photo_file)
            await update.message.reply_text(f"🧠 Ответ:\n{answer}")

        elif update.message.text:
            text = update.message.text
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": f"Кратко реши: {text}"}],
                max_tokens=150
            )
            answer = response.choices[0].message.content.strip()
            await update.message.reply_text(f"🧠 Ответ:\n{answer}")

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

if __name__ == "__main__":
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(MessageHandler(filters.PHOTO, handle_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Бот запущен и ждёт сообщения...")
    app.run_polling()
