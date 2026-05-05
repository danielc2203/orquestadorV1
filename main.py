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
    print("Docker CLI listo.")
except FileNotFoundError:
    print("Instalando Docker CLI...")
    codigo_salida = os.system("apt-get update && apt-get install -y docker.io")
    if codigo_salida != 0:
        os.system("curl -fsSLO https://download.docker.com/linux/static/stable/x86_64/docker-24.0.9.tgz")
        os.system("tar xzvf docker-24.0.9.tgz")
        os.system("mv docker/docker /usr/local/bin/")
        os.system("chmod +x /usr/local/bin/docker")
        os.system("rm -rf docker docker-24.0.9.tgz")
# ==========================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://187.77.206.103:11434/api/generate")

# --- FUNCIÓN CENTRAL DE IA ---
async def ask_ollama(prompt_text):
    """Envía un prompt a Ollama y devuelve la respuesta limpia."""
    clean_url = OLLAMA_URL.replace("[", "").replace("]", "").replace("'", "").replace('"', "")
    data = {
        "model": "qwen2.5-coder:7b",
        "prompt": prompt_text,
        "stream": False
    }
    req = urllib.request.Request(clean_url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get("response", "Sin respuesta de la IA.")
    except Exception as e:
        return f"⚠️ Error de conexión con Ollama: {str(e)}"

# --- COMANDOS DEL BOT ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Soy tu Orquestador IA. Háblame normal para charlar, o usa /scan <dominio> para una auditoría de puertos.")

async def run_tool_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Indica un objetivo. Ejemplo: /scan google.com")
        return
    
    objetivo = context.args[0]
    msg = await update.message.reply_text(f"⚙️ 1/2: Ejecutando Nmap en contenedor efímero para {objetivo}...")

    try:
        # 1. Ejecución del escaneo
        comando = ["docker", "run", "--rm", "alpine", "sh", "-c", f"apk add --no-cache nmap > /dev/null && nmap -F {objetivo}"]
        resultado = subprocess.run(comando, capture_output=True, text=True, check=True)
        resultado_texto = resultado.stdout
        
        # 2. Transición visual en Telegram
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=msg.message_id, text=f"✅ Escaneo completado.\n🧠 2/2: Qwen está analizando los vectores de ataque...")
        
        # 3. Prompt de sistema (El rol del Analista)
        prompt_experto = f"""Eres un consultor experto en ciberseguridad. Analiza el siguiente resultado en crudo de un escaneo Nmap para el objetivo {objetivo}. 
Por favor, entrégame un reporte estructurado y en español que incluya:
1. Resumen de puertos abiertos.
2. Riesgos críticos detectados (ej. si hay bases de datos, FTP o paneles de admin expuestos).
3. Recomendaciones inmediatas para asegurar el servidor.

Resultado crudo de Nmap:
{resultado_texto}
"""
        # 4. Enviamos a la IA y obtenemos el análisis
        analisis_ia = await ask_ollama(prompt_experto)
        
        # 5. Entregamos el reporte final
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=msg.message_id, text=analisis_ia, parse_mode='Markdown')
        
    except subprocess.CalledProcessError as e:
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=msg.message_id, text=f"❌ Error ejecutando Nmap:\n{e.stderr}")
    except Exception as e:
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=msg.message_id, text=f"❌ Error inesperado: {str(e)}")

async def chat_libre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Atiende cualquier mensaje de texto normal usándolo como charla con Qwen."""
    user_message = update.message.text
    processing_msg = await update.message.reply_text("🧠 Pensando...")
    
    respuesta_ia = await ask_ollama(user_message)
    
    await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=processing_msg.message_id, text=respuesta_ia)

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("scan", run_tool_scan))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_libre))
    
    print("Bot Orquestador + Analista IA iniciando...")
    application.run_polling()

if __name__ == "__main__":
    main()
