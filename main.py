import os
import json
import urllib.request
import subprocess
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://187.77.206.103:11434/api/generate")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Soy tu Orquestador. Usa /scan <dominio> para ejecutar nmap en un contenedor efímero.")

async def run_tool_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Indica un objetivo. Ejemplo: /scan google.com")
        return
    
    objetivo = context.args[0]
    msg = await update.message.reply_text(f"⚙️ Levantando contenedor para escanear {objetivo}...")

    try:
        # Usamos subprocess para ejecutar el comando docker nativo directamente
        # Esto equivale a escribir: docker run --rm alpine/nmap -F dominio.com
        comando = ["docker", "run", "--rm", "alpine/nmap", "-F", objetivo]
        
        # Ejecutamos el comando y capturamos la salida
        resultado = subprocess.run(comando, capture_output=True, text=True, check=True)
        
        # Si fue exitoso, tomamos la salida estándar (stdout)
        resultado_texto = resultado.stdout
        
        mensaje_final = "✅ Resultado del escaneo:\n```text\n" + resultado_texto + "\n```"
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=msg.message_id, text=mensaje_final, parse_mode='Markdown')
        
    except subprocess.CalledProcessError as e:
        # Si el comando de docker falla por alguna razón
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=msg.message_id, text=f"❌ Error ejecutando Nmap: {e.stderr}")
    except Exception as e:
        # Cualquier otro error de Python
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=msg.message_id, text=f"❌ Error inesperado: {str(e)}")

async def chat_with_ollama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    processing_msg = await update.message.reply_text("🧠 Pensando...")

    clean_url = OLLAMA_URL.replace("[", "").replace("]", "").replace("'", "").replace('"', "")

    data = {
        "model": "qwen2.5-coder:7b",
        "prompt": user_message,
        "stream": False
    }
    
    req = urllib.request.Request(clean_url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
    
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
    application.add_handler(CommandHandler("scan", run_tool_scan))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_with_ollama))
    
    print("Bot iniciando con soporte de comandos nativos...")
    application.run_polling()

if __name__ == "__main__":
    main()
