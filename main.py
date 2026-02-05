import subprocess, tempfile, os, sys, time, logging, atexit, signal
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Logging ayarla
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN")
ALLOWED_USERS = []

# Çalışan işlemler
running_processes = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 7/24 Python Runner\n.py gönder, hemen çalıştırayım!")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"✅ Bot Aktif\n📊 Çalışan işlem: {len(running_processes)}")

async def handle_py_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message.document or not update.message.document.file_name.endswith('.py'):
            return
        
        msg = await update.message.reply_text("⬇️ İndiriliyor...")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "bot_code.py")
            
            # Dosya indir
            file = await update.message.document.get_file()
            await file.download_to_drive(file_path)
            await msg.edit_text("⚡ Çalıştırılıyor...")
            
            # Hemen çalıştır
            process = subprocess.Popen(
                [sys.executable, file_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            
            # PID kaydet
            pid = str(process.pid)
            running_processes[pid] = process
            await msg.edit_text(f"🚀 Başlatıldı! PID: {pid}")
            
            # Arka planda çalıştır, çıktıyı kontrol et
            asyncio.create_task(check_process_output(process, pid, update))
            
    except Exception as e:
        await update.message.reply_text(f"❌ {str(e)[:200]}")

async def check_process_output(process, pid, update):
    """İşlem çıktısını kontrol et"""
    try:
        stdout, stderr = process.communicate(timeout=300)  # 5 dakika
        
        if stdout:
            await update.message.reply_text(f"📤 Çıktı (PID:{pid}):\n{stdout[:2000]}")
        if stderr:
            await update.message.reply_text(f"⚠️ Hata (PID:{pid}):\n{stderr[:1000]}")
            
    except subprocess.TimeoutExpired:
        await update.message.reply_text(f"⏳ PID:{pid} hala çalışıyor...")
    finally:
        # İşlem listeden çıkar
        if pid in running_processes:
            del running_processes[pid]

async def list_processes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if running_processes:
        await update.message.reply_text(f"📋 Çalışan işlemler: {', '.join(running_processes.keys())}")
    else:
        await update.message.reply_text("📭 Çalışan işlem yok.")

async def kill_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        pid = context.args[0]
        if pid in running_processes:
            running_processes[pid].kill()
            del running_processes[pid]
            await update.message.reply_text(f"✅ {pid} durduruldu.")
        else:
            await update.message.reply_text("❌ İşlem bulunamadı.")
    else:
        await update.message.reply_text("⚠️ Kullanım: /kill PID")

def cleanup():
    """Bot kapanırken tüm işlemleri durdur"""
    for pid, p in running_processes.items():
        try:
            p.kill()
            logger.info(f"İşlem durduruldu: {pid}")
        except:
            pass

def main():
    if not TOKEN:
        logger.error("❌ BOT_TOKEN gerekli!")
        return
    
    # Çıkışta temizlik
    atexit.register(cleanup)
    signal.signal(signal.SIGTERM, lambda s, f: cleanup())
    
    # Botu başlat
    app = Application.builder().token(TOKEN).build()
    
    # Handler'lar
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("list", list_processes))
    app.add_handler(CommandHandler("kill", kill_process))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_py_file))
    
    logger.info("🤖 7/24 Python Runner başlatılıyor...")
    
    try:
        # Sürekli çalış
        app.run_polling(
            drop_pending_updates=True,
            close_loop=False,
            stop_signals=None  # Sinyalleri ignore et
        )
    except KeyboardInterrupt:
        cleanup()
    except Exception as e:
        logger.error(f"Bot hatası: {e}")
        cleanup()

if __name__ == "__main__":
    main()
