import os
import json
import urllib.request
import subprocess
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ==========================================
# AUTO-INSTALADOR DEL CLIENTE DOCKER
# ==========================================
try:
    subprocess.run(["docker", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print("Docker CLI ya está instalado.")
except FileNotFoundError:
    print("Docker CLI no encontrado. Instalando automáticamente...")
    codigo_salida = os.system("apt-get update && apt-get install -y docker.io")
    if codigo_salida != 0:
        print("Instalando binario estático como plan B...")
        os.system("curl -fsSLO https://download.docker.com/linux/static/stable/x86_64/docker-24.0.9.tgz")
        os.system("tar xzvf docker-24.0.9.tgz")
        os.system("mv docker/docker /usr/local/bin/")
        os.system("chmod +x /usr/local/bin/docker")
        os.system("rm -rf docker docker-24.0.9.tgz")
# ==========================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://187.77.206.103:11434/api/generate")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Soy tu Orquestador. Usa /scan <dominio> para ejecutar nmap en un contenedor efímero.")

async def run_tool_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Indica un objetivo. Ejemplo: /scan google.com")
        return
    
    objetivo = context.args[0]
    msg = await update.message.reply_text(f"⚙️ Levantando contenedor oficial para escanear {objetivo}...")

    try:
        # COMANDO A PRUEBA DE BALAS: Usamos la imagen oficial de alpine, instalamos nmap "al vuelo" y escaneamos
        comando = ["docker", "run", "--rm", "alpine", "sh", "-c", f"apk add --no-cache nmap > /dev/null && nmap -F {objetivo}"]
        
        resultado = subprocess.run(comando, capture_output=True, text=True, check=True)
        resultado_texto = resultado.stdout
        
        mensaje_final = "✅ **Resultado del escaneo:**\n```text\n" + resultado_texto + "\n```"
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=msg.message_id, text=mensaje_final, parse_mode='Markdown')
        
    except subprocess.CalledProcessError as e:
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=msg.message_id, text=f"❌ Error ejecutando Nmap:\n{e.stderr}\n\nSalida: {e.stdout}")
    except Exception as e:
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
    
    print("Bot iniciando con soporte de comandos nativos y Alpine oficial...")
    application.run_polling()

if __name__ == "__main__":
    main()
