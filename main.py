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
    mensaje = (
        "¡Hola! Soy tu Orquestador IA.\n\n"
        "Comandos disponibles:\n"
        "🔍 /scan <dominio> - Auditoría rápida con Nmap + IA\n"
        "🛠️ /runrepo <url_github> <script.py> <args> - Ejecuta herramientas de GitHub\n\n"
        "O simplemente háblame para charlar con Qwen."
    )
    await update.message.reply_text(mensaje)

async def run_tool_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Indica un objetivo. Ejemplo: /scan google.com")
        return
    
    objetivo = context.args[0]
    msg = await update.message.reply_text(f"⚙️ 1/2: Ejecutando Nmap en contenedor efímero para {objetivo}...")

    try:
        comando = ["docker", "run", "--rm", "alpine", "sh", "-c", f"apk add --no-cache nmap > /dev/null && nmap -F {objetivo}"]
        resultado = subprocess.run(comando, capture_output=True, text=True, check=True)
        
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=msg.message_id, text=f"✅ Escaneo completado.\n🧠 2/2: Qwen está analizando los vectores de ataque...")
        
        prompt_experto = f"Eres un consultor experto en ciberseguridad. Analiza el siguiente resultado en crudo de un escaneo Nmap para el objetivo {objetivo}. Por favor, entrégame un reporte estructurado y en español que incluya:\n1. Resumen de puertos abiertos.\n2. Riesgos críticos detectados.\n3. Recomendaciones inmediatas.\n\nResultado crudo de Nmap:\n{resultado.stdout}"
        
        analisis_ia = await ask_ollama(prompt_experto)
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=msg.message_id, text=analisis_ia, parse_mode='Markdown')
        
    except Exception as e:
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=msg.message_id, text=f"❌ Error: {str(e)}")

# --- NUEVO: EJECUTOR DINÁMICO DE GITHUB ---
async def run_github_tool(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text("⚠️ Uso: /runrepo <url_github> <script_principal> <objetivo>\nEjemplo: `/runrepo https://github.com/usuario/repo main.py dominio.com`", parse_mode='Markdown')
        return
    
    repo_url = context.args[0]
    script_name = context.args[1]
    argumentos = " ".join(context.args[2:])
    
    msg = await update.message.reply_text(f"⚙️ Levantando entorno Python aislado...\n📦 Clonando: {repo_url}")

    try:
        # Script Bash que se ejecuta DENTRO del contenedor de Docker
        bash_script = (
            f"apk add --no-cache git > /dev/null && "
            f"git clone {repo_url} /app > /dev/null 2>&1 && "
            f"cd /app && "
            f"if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt > /dev/null 2>&1; fi && "
            f"python {script_name} {argumentos}"
        )
        
        # Usamos python:3.10-alpine por ser extremadamente ligero y rápido de descargar
        comando = ["docker", "run", "--rm", "python:3.10-alpine", "sh", "-c", bash_script]
        
        # Ejecutamos con un timeout de 3 minutos (180 segundos)
        resultado = subprocess.run(comando, capture_output=True, text=True, timeout=180)
        resultado_texto = resultado.stdout
        
        # Telegram tiene un límite de 4096 caracteres por mensaje. Truncamos si es muy largo.
        if len(resultado_texto) > 3500:
            resultado_texto = resultado_texto[:3500] + "\n\n... [RESULTADO TRUNCADO POR LONGITUD] ..."
            
        if not resultado_texto.strip():
            resultado_texto = f"Sin salida. Errores detectados:\n{resultado.stderr}"
            
        mensaje_final = f"✅ **Ejecución completada:**\n```text\n{resultado_texto}\n```"
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=msg.message_id, text=mensaje_final, parse_mode='Markdown')
        
    except subprocess.TimeoutExpired:
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=msg.message_id, text="⏳ La herramienta tardó más de 3 minutos y el contenedor fue destruido por seguridad.")
    except Exception as e:
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=msg.message_id, text=f"❌ Error ejecutando el repositorio: {str(e)}")

async def chat_libre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    processing_msg = await update.message.reply_text("🧠 Pensando...")
    respuesta_ia = await ask_ollama(user_message)
    await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=processing_msg.message_id, text=respuesta_ia)

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("scan", run_tool_scan))
    application.add_handler(CommandHandler("runrepo", run_github_tool))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_libre))
    
    print("Bot Orquestador iniciando...")
    application.run_polling()

if __name__ == "__main__":
    main()
