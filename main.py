async def run_tool_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Indica un objetivo. Ejemplo: /scan google.com")
        return
    
    objetivo = context.args[0]
    msg = await update.message.reply_text(f"⚙️ Escaneando {objetivo}...")

    try:
        # Forzamos la conexión directa al socket de Docker montado
        cliente_docker = docker.DockerClient(base_url='unix://var/run/docker.sock')
        
        resultado_raw = cliente_docker.containers.run(
            "alpine/nmap",
            f"-F {objetivo}",
            auto_remove=True
        )
        resultado_texto = resultado_raw.decode('utf-8')
        
        mensaje_final = "✅ Resultado del escaneo:\n```text\n" + resultado_texto + "\n```"
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=msg.message_id, text=mensaje_final, parse_mode='Markdown')
        
    except Exception as e:
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=msg.message_id, text=f"❌ Error real de Docker: {str(e)}")
