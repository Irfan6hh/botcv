import os
from telegram import Update, InputFile
from telegram.ext import ConversationHandler, MessageHandler, CommandHandler, filters, ContextTypes

# States for splitting VCF conversation
SPLIT_NAME, SPLIT_VCF_NAME, SPLIT_COUNT, SEND_OPTION, TARGET_ID, FILE_UPLOAD = range(6)

# Handle the start of the splitting process and ask for contact name first
async def split_vcf_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Silakan masukkan nama kontak yang akan digunakan.")
    return SPLIT_NAME

# Get the contact name
async def split_vcf_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    contact_name = update.message.text
    context.user_data['contact_name'] = contact_name
    await update.message.reply_text(f"Nama kontak '{contact_name}' telah dipilih. Sekarang, masukkan nama file VCF.")
    return SPLIT_VCF_NAME

# Get the VCF file name
async def split_vcf_file_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    vcf_name = update.message.text
    context.user_data['vcf_name'] = vcf_name
    await update.message.reply_text(f"Nama file VCF '{vcf_name}' diterima. Berapa jumlah pecahan yang Anda inginkan?")
    return SPLIT_COUNT

# Get the number of parts to split into
async def split_vcf_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        split_count = int(update.message.text)
        if split_count <= 0:
            raise ValueError("Jumlah pecahan harus lebih dari 0.")
        context.user_data['split_count'] = split_count
        await update.message.reply_text("Apakah Anda ingin file VCF dikirim langsung ke ID Telegram lain? (ketik 'ya' atau 'tidak')")
        return SEND_OPTION
    except ValueError:
        await update.message.reply_text("Harap masukkan angka yang valid.")
        return SPLIT_COUNT

# Handle the send option (whether to send to another ID)
async def send_option(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    response = update.message.text.strip().lower()
    if response == 'ya':
        await update.message.reply_text("Silakan masukkan ID tujuan untuk mengirim dokumen (contoh: 123456789).")
        return TARGET_ID
    elif response == 'tidak':
        # Jika pengguna memilih tidak, gunakan ID pengguna untuk pengiriman
        context.user_data['target_id'] = update.message.chat_id  # ID pengguna
        await update.message.reply_text("Silakan unggah file VCF Anda.")
        return FILE_UPLOAD
    else:
        await update.message.reply_text("Tolong ketik 'ya' atau 'tidak'.")
        return SEND_OPTION

# Get the target ID if user chooses to send the file
async def target_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    target_id = update.message.text.strip()

    # Validasi apakah ID tujuan adalah angka
    if not target_id.isdigit():
        await update.message.reply_text("ID tujuan harus berupa angka. Silakan masukkan ID yang valid.")
        return TARGET_ID
    
    context.user_data['target_id'] = int(target_id)
    await update.message.reply_text("Silakan unggah file VCF Anda.")
    return FILE_UPLOAD

# Handle the file upload and split it
async def split_vcf_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    document = update.message.document
    if document and document.file_name.endswith('.vcf'):
        file = await document.get_file()
        input_file_path = os.path.join(os.getcwd(), document.file_name)
        await file.download_to_drive(custom_path=input_file_path)

        split_count = context.user_data['split_count']
        contact_name = context.user_data['contact_name']  # Nama kontak dari input pengguna
        vcf_name = context.user_data['vcf_name']
        
        # Gunakan chat_id dari pengguna jika target_id tidak disediakan
        target_id = context.user_data.get('target_id', update.message.chat_id)

        # Validasi apakah chat_id valid sebelum melanjutkan
        if not target_id:
            await update.message.reply_text("ID tujuan tidak valid atau kosong. Pengiriman dibatalkan.")
            return FILE_UPLOAD

        # Baca file VCF dan simpan nomor dengan "TEL;"
        with open(input_file_path, 'r') as f:
            lines = f.readlines()

        # Hanya ambil baris yang berisi nomor telepon (dimulai dengan 'TEL;')
        contacts = [line for line in lines if line.startswith('TEL;')]

        # Hitung jumlah kontak per file pecahan
        contacts_per_file = len(contacts) // split_count
        split_files = []
        for i in range(split_count):
            start_idx = i * contacts_per_file
            end_idx = (i + 1) * contacts_per_file if i < split_count - 1 else len(contacts)
            split_contacts = contacts[start_idx:end_idx]
            split_file_name = f"{vcf_name}_part_{i+1}.vcf"
            split_file_path = os.path.join(os.getcwd(), split_file_name)

            with open(split_file_path, 'w') as f_out:
                # Tambahkan kontak satu per satu dengan struktur vCard yang benar
                for idx, contact in enumerate(split_contacts, start=1):
                    f_out.write("BEGIN:VCARD\n")
                    f_out.write("VERSION:3.0\n")
                    f_out.write(f"FN:{contact_name} - {idx:02d}\n")  # Nama kontak pada FN dengan nomor urut
                    f_out.write(contact)  # Menulis kontak (baris TEL)
                    f_out.write("END:VCARD\n\n")  # Footer vCard

            split_files.append(split_file_path)

        # Kirim file VCF yang dipecah ke pengguna atau ID tujuan
        for file_path in split_files:
            with open(file_path, 'rb') as f:
                await context.bot.send_document(chat_id=target_id, document=InputFile(f, filename=os.path.basename(file_path)))

        await update.message.reply_text("Semua file VCF telah dipecah dan dikirim.")
        return ConversationHandler.END
    else:
        await update.message.reply_text("Harap unggah file VCF yang valid.")
        return FILE_UPLOAD

# Conversation handler setup for splitting VCF files
def split_vcf_handler_setup(application):
    split_conv = ConversationHandler(
        entry_points=[CommandHandler('split_vcf', split_vcf_start)],
        states={
            SPLIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, split_vcf_name)],
            SPLIT_VCF_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, split_vcf_file_name)],
            SPLIT_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, split_vcf_count)],
            SEND_OPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_option)],
            TARGET_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, target_id)],
            FILE_UPLOAD: [MessageHandler(filters.Document.ALL, split_vcf_file)],
        },
        fallbacks=[CommandHandler('cancel', split_vcf_start)]
    )
    application.add_handler(split_conv)
    