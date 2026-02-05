import subprocess, tempfile, os, sys, time, asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Python Runner\n.py gönder, çalıştırayım!")

async def handle_py_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message.document or not update.message.document.file_name.endswith('.py'):
            return
        
        msg = await update.message.reply_text("⬇️ İndiriliyor...")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "code.py")
            
            # Dosya indir
            file = await update.message.document.get_file()
            await file.download_to_drive(file_path)
            await msg.edit_text("📦 Paketler kuruluyor...")
            
            # Tüm paketleri yükle
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                capture_output=True,
                text=True
            )
            
            await msg.edit_text("🚀 Çalıştırılıyor...")
            
            # Kodu çalıştır
            process = subprocess.run(
                [sys.executable, file_path],
                capture_output=True,
                text=True,
                timeout=30,
                encoding='utf-8'
            )
            
            # Sonuç
            output = ""
            if process.stdout:
                output += f"✅ Çıktı:\n{process.stdout[:1500]}"
            if process.stderr:
                output += f"\n\n⚠️ Hata:\n{process.stderr[:1000]}"
            
            if not output:
                output = "✅ Kod çalıştı, çıktı yok."
            
            await msg.edit_text(f"🎯 Tamamlandı!\n\n{output}")
            
    except subprocess.TimeoutExpired:
        await update.message.reply_text("⏰ Zaman aşımı! (30s)")
    except Exception as e:
        await update.message.reply_text(f"❌ Hata: {str(e)[:200]}")

def main():
    if not TOKEN:
        print("❌ BOT_TOKEN gerekli!")
        return
    
    # Tüm paketleri önceden yükle
    print("📦 Paketler yükleniyor...")
    subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_py_file))
    
    print("🤖 Bot başlatılıyor...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
