import subprocess
import tempfile
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Token'i environment variable'dan al
TOKEN = os.environ.get("BOT_TOKEN")
ALLOWED_USERS = []  # Boş bırakırsanız herkes kullanabilir

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Merhaba! Bana .py dosyası gönder, çalıştırayım.")

async def handle_py_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Kullanıcı kontrolü
    if ALLOWED_USERS and update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("⛔ Yetkiniz yok!")
        return

    # Dosya kontrolü
    if not update.message.document or not update.message.document.file_name.endswith('.py'):
        return

    await update.message.reply_text("📥 Dosya alındı, işleniyor...")
    
    # Geçici dosya oluştur
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "code.py")
        
        # Dosyayı indir
        file = await update.message.document.get_file()
        await file.download_to_drive(file_path)
        
        # Paketleri kur ve çalıştır
        await install_requirements(file_path, update)
        await run_python_file(file_path, update)

async def install_requirements(file_path, update):
    try:
        # Dosyayı oku ve importları bul
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Sadece standart kütüphanede olmayan paketleri bul
        stdlib = ['os', 'sys', 'math', 'json', 'datetime', 're', 'random', 
                 'subprocess', 'tempfile', 'collections', 'itertools', 'functools']
        
        imports = []
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith(('import ', 'from ')):
                parts = line.split()
                if len(parts) > 1:
                    module = parts[1].split('.')[0]
                    if module not in stdlib and module not in imports and not module.startswith('_'):
                        imports.append(module)
        
        # Paketleri kur
        if imports:
            await update.message.reply_text(f"🔧 Kurulacak paketler: {', '.join(imports[:5])}")
            for package in imports:
                try:
                    subprocess.run(['pip', 'install', package], 
                                  capture_output=True, timeout=30)
                except:
                    continue
                    
    except Exception as e:
        print(f"Package install error: {e}")

async def run_python_file(file_path, update):
    try:
        await update.message.reply_text("🚀 Kod çalıştırılıyor...")
        
        # Kodu çalıştır
        result = subprocess.run(['python', file_path], 
                              capture_output=True, 
                              text=True, 
                              timeout=30,
                              encoding='utf-8',
                              errors='ignore')
        
        # Çıktıyı formatla
        output = ""
        if result.stdout:
            output += result.stdout[:2000]  # İlk 2000 karakter
        if result.stderr:
            output += "\n\nHatalar:\n" + result.stderr[:1000]
        
        if not output.strip():
            output = "✅ Kod başarıyla çalıştı, çıktı üretilmedi."
        
        # Çıktıyı gönder
        if len(output) > 4000:
            await update.message.reply_text(output[:4000])
        else:
            await update.message.reply_text(f"```\n{output}\n```", parse_mode='Markdown')
            
    except subprocess.TimeoutExpired:
        await update.message.reply_text("⏰ Zaman aşımı! Kod 30 saniyeden uzun sürdü.")
    except Exception as e:
        await update.message.reply_text(f"❌ Çalıştırma hatası: {str(e)[:500]}")

def main():
    if not TOKEN:
        print("❌ HATA: BOT_TOKEN environment variable ayarlanmamış!")
        print("Render'da: Settings > Environment Variables > BOT_TOKEN ekleyin")
        return
    
    # Botu başlat
    app = Application.builder().token(TOKEN).build()
    
    # Handler'ları ekle
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_py_file))
    
    print("🤖 Bot başlatılıyor...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
