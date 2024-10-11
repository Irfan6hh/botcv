import os
import re
from telegram import Update, InputFile
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, filters, ContextTypes

# Status untuk percakapan
NAME, VCF_NAME, SEND_OPTION, TARGET_ID, FILE_UPLOAD, FILE_COUNT, FILE_SEQ_START, FINISH_OPTION = range(8)

async def convert_txt_to_vcard(input_file_path, contact_name_prefix):
    vcards = []

    try:
        with open(input_file_path, 'r', encoding='utf-8') as file:  # Specifying UTF-8 encoding for reading
            for idx, line in enumerate(file, start=1):
                line = re.sub(r'[^\d+]', '', line.strip())
                if line:
                    if not line.startswith('+'):
                        line = '+' + line
                    vcard = f"BEGIN:VCARD\nVERSION:3.0\nFN:{contact_name_prefix} - {idx:02d}\nTEL:{line}\nEND:VCARD"
                    vcards.append(vcard)

    except Exception as e:
        print(f"Kesalahan saat membaca file: {e}")
        return []

    return vcards

async def convert_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()  # Menghapus data pengguna sebelumnya untuk memulai dari awal
    await update.message.reply_text("Silakan masukkan nama kontak yang akan digunakan.")
    return NAME

async def name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_name = update.message.text
    context.user_data['contact_name'] = user_name
    await update.message.reply_text(
        f"Anda telah memilih nama kontak '{user_name}'. Silakan masukkan nama kustom untuk file VCF."
    )
    return VCF_NAME

async def vcf_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    vcf_name = update.message.text
    context.user_data['vcf_name'] = vcf_name
    await update.message.reply_text("Apakah Anda ingin file VCF dikirim langsung ke ID Telegram lain? (ketik 'ya' atau 'tidak')")
    return SEND_OPTION

async def send_option(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    response = update.message.text.strip().lower()
    if response == 'ya':
        await update.message.reply_text("Silakan masukkan ID tujuan untuk mengirim dokumen (contoh: 123456789).")
        return TARGET_ID
    elif response == 'tidak':
        context.user_data['target_id'] = None  # Tidak ada ID tujuan, akan dikirim ke pengguna saat ini
        await update.message.reply_text("Berapa jumlah file .txt yang akan Anda unggah? (Silakan masukkan angka)")
        return FILE_COUNT
    else:
        await update.message.reply_text("Tolong ketik 'ya' atau 'tidak'.")
        return SEND_OPTION

async def target_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    target_id = update.message.text
    context.user_data['target_id'] = target_id  # Simpan ID tujuan
    await update.message.reply_text("Berapa jumlah file .txt yang akan Anda unggah? (Silakan masukkan angka)")
    return FILE_COUNT

async def file_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        count = int(update.message.text)
        if count <= 0:
            raise ValueError("Jumlah harus positif.")
        context.user_data['file_count'] = count
        context.user_data['uploaded_files'] = []
        await update.message.reply_text("Silakan masukkan nomor urut awal untuk file VCF.")
        return FILE_SEQ_START
    except ValueError:
        await update.message.reply_text("Tolong masukkan angka yang valid untuk jumlah file.")
        return FILE_COUNT

async def file_seq_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        seq_start = int(update.message.text)
        if seq_start <= 0:
            raise ValueError("Nomor urut harus positif.")
        context.user_data['seq_start'] = seq_start
        await update.message.reply_text("Silakan unggah file .txt Anda untuk dikonversi ke VCF.")
        return FILE_UPLOAD
    except ValueError:
        await update.message.reply_text("Tolong masukkan angka yang valid untuk nomor urut.")
        return FILE_SEQ_START

async def receive_files(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    expected_count = context.user_data.get('file_count', 0)

    if update.message.document and update.message.document.file_name.endswith('.txt'):
        file = await update.message.document.get_file()
        input_file_path = f"{update.message.document.file_name}"
        await file.download_to_drive(custom_path=input_file_path)

        contact_name_prefix = context.user_data['contact_name']
        vcf_name = context.user_data['vcf_name']
        target_id = context.user_data.get('target_id')  # Ambil target_id

        # Gunakan ID pengguna jika tidak ada target ID
        if target_id is None:
            target_id = update.message.chat.id  # Dapatkan chat ID pengguna saat ini

        seq_start = context.user_data['seq_start'] + len(context.user_data['uploaded_files'])

        vcards = await convert_txt_to_vcard(input_file_path, contact_name_prefix)

        # Menulis semua vcard ke satu file VCF
        output_file_name = f"{vcf_name}-{seq_start:02d}.vcf"
        output_file_path = os.path.join(os.getcwd(), output_file_name)

        with open(output_file_path, 'w', buffering=8192, encoding='utf-8') as f_out:  # Specifying UTF-8 encoding for writing
            f_out.write("\n".join(vcards) + "\n")

        context.user_data['uploaded_files'].append(output_file_path)

        # Mengirim file VCF yang dibuat
        with open(output_file_path, 'rb') as f:
            await context.bot.send_document(chat_id=target_id, document=InputFile(f, filename=os.path.basename(output_file_path)))

        

        if len(context.user_data['uploaded_files']) >= expected_count:
            await update.message.reply_text("Semua file telah diproses dan dikirim.")
            await finish_option(update, context)
            return FINISH_OPTION

        return FILE_UPLOAD
    else:
        await update.message.reply_text("Tolong unggah file .txt yang valid.")
        return FILE_UPLOAD

async def finish_option(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Apakah Anda sudah selesai? Ketik 'selesai' atau 'belum'.")
    return FINISH_OPTION

async def finish_process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    response = update.message.text.strip().lower()
    if response == 'selesai':
        await update.message.reply_text("Terima kasih! Anda telah menyelesaikan proses.")
    elif response == 'belum':
        await update.message.reply_text("Anda dapat melanjutkan dengan /convert untuk mengonversi file lainnya.")
    else:
        await update.message.reply_text("Tolong masukkan 'selesai' atau 'belum'.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Proses dibatalkan.")
    return ConversationHandler.END

def txt_to_vcf_handler_setup(application):
    txt_to_vcf_conv = ConversationHandler(
        entry_points=[CommandHandler('convert', convert_start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name)],
            VCF_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, vcf_name)],
            SEND_OPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_option)],
            TARGET_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, target_id)],
            FILE_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, file_count)],
            FILE_SEQ_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, file_seq_start)],
            FILE_UPLOAD: [MessageHandler(filters.Document.ALL, receive_files)],
            FINISH_OPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, finish_process)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    application.add_handler(txt_to_vcf_conv)
