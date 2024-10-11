import os
import re
from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

# State untuk percakapan
CUSTOM_NAME, VCF_NAME, CUSTOM_NUMBER = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Memulai percakapan dan memberikan pilihan fitur kepada pengguna."""
    await update.message.reply_text(
        "Selamat datang! Pilih fitur yang ingin Anda gunakan:\n"
        "/convert - Konversi file TXT ke VCF\n"
        "/custom_number - Tambah nomor kustom ke VCF\n"
        "Silakan ketikkan perintah di atas untuk memilih fitur."
    )

async def custom_number_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Memulai percakapan dan meminta nama kontak."""
    await update.message.reply_text("Silakan masukkan nama kontak untuk VCF.")
    return CUSTOM_NAME

async def set_custom_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menyimpan nama kontak yang dimasukkan oleh pengguna."""
    context.user_data['custom_name'] = update.message.text
    context.user_data['numbers'] = []  # Initialize the list to hold phone numbers
    await update.message.reply_text(
        f"Nama kontak '{update.message.text}' telah disimpan. "
        "Silakan masukkan nama file VCF yang diinginkan (tanpa ekstensi)."
    )
    return VCF_NAME

async def set_vcf_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menyimpan nama file VCF yang dimasukkan oleh pengguna."""
    context.user_data['vcf_file_name'] = update.message.text
    await update.message.reply_text(
        f"Nama file VCF '{update.message.text}' telah disimpan. "
        "Silakan masukkan nomor telepon (satu per baris, ketik 'selesai' untuk menyelesaikan)."
    )
    return CUSTOM_NUMBER

async def add_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menambahkan nomor telepon yang dimasukkan ke dalam daftar."""
    numbers_input = update.message.text.strip().splitlines()  # Membagi input menjadi beberapa baris

    # Mengubah logika untuk menambahkan nomor
    for number in numbers_input:
        cleaned_number = re.sub(r'\D', '', number.strip())  # Hapus semua karakter non-numerik

        if cleaned_number:  # Pastikan nomor yang bersih tidak kosong
            context.user_data['numbers'].append(cleaned_number)
            await update.message.reply_text(f"Nomor '{number}' telah ditambahkan.")

    # Periksa apakah pengguna mengetik 'selesai'
    if 'selesai' in [num.lower() for num in numbers_input]:  # Memeriksa semua baris untuk 'selesai'
        return await finish_custom_number(update, context)

    # Hanya satu pesan untuk menginstruksikan pengguna
    await update.message.reply_text("Silakan masukkan nomor telepon lain atau ketik 'selesai' untuk mengakhiri.")
    return CUSTOM_NUMBER  # Tetap di state CUSTOM_NUMBER

async def finish_custom_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menyelesaikan proses dan mengirimkan file VCF kepada pengguna."""
    contact_name = context.user_data.get('custom_name', 'Kontak Tanpa Nama')
    vcf_file_name = context.user_data.get('vcf_file_name', 'Kontak').strip()
    numbers = context.user_data.get('numbers', [])

    if numbers:  # Periksa apakah ada nomor yang valid untuk disimpan
        output_file_path = os.path.join(os.getcwd(), f"{vcf_file_name}.vcf")

        # Membuat file VCF
        with open(output_file_path, 'w') as f_out:
            for count, number in enumerate(numbers, start=1):
                vcard = (
                    f"BEGIN:VCARD\n"
                    f"VERSION:3.0\n"
                    f"FN:{contact_name} - {count:02d}\n"
                    f"TEL:{number}\n"
                    f"END:VCARD\n"
                )
                f_out.write(vcard)

        # Mengirim file VCF ke pengguna
        try:
            with open(output_file_path, 'rb') as f:
                await context.bot.send_document(chat_id=update.message.chat.id, document=InputFile(f, filename=f"{vcf_file_name}.vcf"))
            await update.message.reply_text(f"Proses selesai. VCF '{vcf_file_name}.vcf' telah dibuat dengan {len(numbers)} kontak.")
        except Exception as e:
            await update.message.reply_text(f"Gagal mengirim file VCF: {str(e)}")
        finally:
            # Hapus file setelah dikirim
            if os.path.exists(output_file_path):
                os.remove(output_file_path)

    else:
        await update.message.reply_text("Tidak ada nomor yang valid untuk disimpan.")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menghentikan percakapan dan membersihkan data pengguna."""
    await update.message.reply_text("Proses dibatalkan.")
    return ConversationHandler.END

def custom_number_handler_setup(application):
    """Menyusun handler untuk percakapan custom number."""
    custom_number_conv = ConversationHandler(
        entry_points=[CommandHandler('custom_number', custom_number_start)],
        states={
            CUSTOM_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_custom_name)],
            VCF_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_vcf_name)],
            CUSTOM_NUMBER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_numbers),  # Update ke add_numbers
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    application.add_handler(custom_number_conv)

def main() -> None:
    """Menjalankan bot Telegram."""
    application = ApplicationBuilder().token("YOUR_BOT_TOKEN").build()

    # Set up custom number handler
    custom_number_handler_setup(application)  # Use the application directly

    # Set up command handler for start
    application.add_handler(CommandHandler('start', start))

    application.run_polling()

if __name__ == '__main__':
    main()
