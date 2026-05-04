import os
import json
import urllib.request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Tomamos el Token de Telegram desde las variables de entorno de Coolify
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Usamos la IP de tu VPS donde instalamos Ollama (que ya escucha en 0.0.0.0)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://187.77.206.103:11434/api/generate")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Soy tu agente orquestador en el VPS. ¿Qué orden ejecutamos hoy?")

async def chat_with_ollama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    # Mensaje temporal mientras la IA procesa
    processing_msg = await update.message.reply_text("🧠 Qwen está pensando...")

    data = {
        "model": "qwen2.5-coder:7b",
        "prompt": user_message,
        "stream": False
    }
    
    req = urllib.request.Request(OLLAMA_URL, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            reply = result.get("response", "Sin respuesta.")
            # Editamos el mensaje temporal con la respuesta real
            await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=processing_msg.message_id, text=reply)
    except Exception as e:
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=processing_msg.message_id, text=f"⚠️ Error conectando a Ollama: {str(e)}")

def main():
    if not TELEGRAM_TOKEN:
        print("Error: No se encontró TELEGRAM_TOKEN")
        return
        
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_with_ollama))
    
    print("Bot iniciando y esperando mensajes...")
    application.run_polling()

if __name__ == "__main__":
    main()
