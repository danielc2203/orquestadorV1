import os
import json
import urllib.request
import docker
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://187.77.206.103:11434/api/generate")

# Inicializamos el cliente de Docker
try:
    docker_client = docker.from_env()
except Exception as e:
    print(f"Error conectando a Docker: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Soy tu Orquestador. Usa /scan <dominio> para ejecutar una herramienta en un contenedor aislado, o háblame normal para charlar con Qwen.")

async def run_tool_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Por favor, indica un objetivo. Ejemplo: /scan google.com")
        return
    
    objetivo = context.args[0]
    msg = await update.message.reply_text(f"⚙️ Levantando contenedor aislado para escanear {objetivo}...")

    try:
        # Aquí el bot levanta un contenedor nuevo, ejecuta Nmap, guarda el resultado y se destruye (auto_remove=True)
        resultado_raw = docker_client.containers.run(
            "alpine/nmap", # Imagen de Docker temporal
            f"-F {objetivo}", # Comando (Escaneo rápido)
            auto_remove=True
        )
        
        resultado_texto = resultado_raw.decode('utf-8')
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=msg.message_id, text=f"✅ **Resultado del escaneo:**\n```text\n{resultado_texto}\n
```", parse_mode='Markdown')
        
        # Opcional: Podríamos enviar este resultado a Qwen para que lo explique, ¡pero vamos paso a paso!
        
    except Exception as e:
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=msg.message_id, text=f"❌ Error ejecutando la herramienta: {str(e)}")


async def chat_with_ollama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
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
            await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=processing_msg.message_id, text=reply)
    except Exception as e:
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=processing_msg.message_id, text=f"⚠️ Error conectando a Ollama: {str(e)}")

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("scan", run_tool_scan)) # Nuevo comando
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_with_ollama))
    
    print("Bot iniciando...")
    application.run_polling()

if __name__ == "__main__":
    main()
