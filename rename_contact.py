from telegram import Update
from telegram.ext import (
    MessageHandler,
    filters,
    ContextTypes,
    CommandHandler,
    ConversationHandler,
)
import aiohttp
import os

# State untuk percakapan
RENAME_VCF_NAME, RENAME_OLD_NAME, RENAME_NEW_NAME = range(3)

async def start_rename_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Memulai percakapan untuk mengganti nama kontak di file VCF."""
    await update.message.reply_text("Silakan unggah file VCF yang akan diproses.")
    return RENAME_VCF_NAME

async def get_vcf_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Mengambil file VCF yang diunggah oleh pengguna."""
    file = update.message.document
    
    # Memeriksa apakah file ada dan memiliki nama
    if file and file.file_name.endswith('.vcf'):
        file_path = f"./{file.file_name}"
        
        # Mendapatkan URL file dari Telegram
        new_file = await file.get_file()
        
        # Mengunduh file ke path yang ditentukan
        async with aiohttp.ClientSession() as session:
            async with session.get(new_file.file_path) as resp:
                if resp.status == 200:
                    with open(file_path, 'wb') as f:
                        f.write(await resp.read())
                else:
                    await update.message.reply_text("Gagal mengunduh file VCF.")
                    return RENAME_VCF_NAME
        
        context.user_data['vcf_file_path'] = file_path  # Simpan path file
        await update.message.reply_text("File VCF telah diunggah. Silakan masukkan nama kontak yang ingin diganti.")
        return RENAME_OLD_NAME
    else:
        await update.message.reply_text("Harap unggah file VCF yang valid.")
        return RENAME_VCF_NAME

async def get_old_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Mendapatkan nama lama kontak yang akan diganti."""
    context.user_data['old_name'] = update.message.text
    await update.message.reply_text("Silakan masukkan nama baru untuk kontak tersebut.")
    return RENAME_NEW_NAME

async def get_new_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Mendapatkan nama baru dan mengganti nama di file VCF serta mengirimkan file yang telah dimodifikasi."""
    old_name = context.user_data['old_name']
    new_name = update.message.text
    vcf_file_path = context.user_data['vcf_file_path']

    # Membaca file VCF, mengganti nama dan menyimpan kembali
    with open(vcf_file_path, 'r') as file:
        lines = file.readlines()

    with open(vcf_file_path, 'w') as file:
        for line in lines:
            if f"FN:{old_name}" in line:
                line = line.replace(old_name, new_name)
            file.write(line)

    await update.message.reply_text(f"Kontak '{old_name}' telah diganti menjadi '{new_name}' di file VCF.")

    # Mengirimkan file VCF yang telah dimodifikasi
    with open(vcf_file_path, 'rb') as file_to_send:
        await update.message.reply_document(document=file_to_send, filename=os.path.basename(vcf_file_path))

    return ConversationHandler.END

def rename_contact_handler_setup(application):
    """Mengatur handler untuk mengganti nama kontak."""
    rename_contact_conv = ConversationHandler(
        entry_points=[CommandHandler('rename_contact', start_rename_contact)],
        states={
            RENAME_VCF_NAME: [MessageHandler(filters.Document.ALL, get_vcf_file)],
            RENAME_OLD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_old_name)],
            RENAME_NEW_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_new_name)],
        },
        fallbacks=[],
    )
    application.add_handler(rename_contact_conv)