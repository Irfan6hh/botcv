import os
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, ConversationHandler, CommandHandler, MessageHandler, filters, ContextTypes

# States for adding contacts conversation
CONTACT_NAME, VCF_NAME, CONTACT_NUMBERS, VCF_FILE_COUNT, FILE_UPLOAD = range(5)

# Function to start the adding contacts process
async def add_contact_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Silakan masukkan nama kontak yang akan ditambahkan.")
    return CONTACT_NAME

# Get the contact name and automatically add a sequence number
async def get_contact_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    contact_name = update.message.text
    context.user_data['contact_name_base'] = contact_name  # Store the base name
    await update.message.reply_text(
        f"Nama kontak '{contact_name}' telah dipilih. Silakan masukkan nama file VCF yang akan digunakan."
    )
    return VCF_NAME

# Get the VCF file name
async def get_vcf_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    vcf_name = update.message.text
    context.user_data['vcf_name'] = vcf_name
    await update.message.reply_text(
        "Silakan masukkan nomor kontak (format: satu nomor per baris). Kirim 'SELESAI' jika sudah selesai."
    )
    return CONTACT_NUMBERS

# Get the contact numbers
async def get_contact_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    contact_numbers = context.user_data.get('contact_numbers', [])

    # Check for "SELESAI" command
    if update.message.text.strip().upper() == "SELESAI":
        if not contact_numbers:
            await update.message.reply_text("Tidak ada nomor kontak yang dimasukkan. Silakan masukkan nomor kontak terlebih dahulu.")
            return CONTACT_NUMBERS
        else:
            await update.message.reply_text("Silakan masukkan jumlah file VCF yang akan Anda unggah.")
            return VCF_FILE_COUNT

    # Split numbers by line and validate
    numbers = update.message.text.strip().splitlines()
    for number in numbers:
        if number.startswith('+') and len(number) > 1 and number[1:].isdigit():
            contact_numbers.append(number.strip())
        else:
            await update.message.reply_text("Harap masukkan nomor kontak yang valid dengan format yang benar.")
            return CONTACT_NUMBERS

    context.user_data['contact_numbers'] = contact_numbers
    await update.message.reply_text("Nomor kontak telah ditambahkan. Kirim nomor lain atau 'SELESAI' jika sudah selesai.")
    return CONTACT_NUMBERS

# Get the number of VCF files to upload
async def get_vcf_file_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        file_count = int(update.message.text)
        if file_count <= 0:
            raise ValueError
        context.user_data['vcf_file_count'] = file_count
        await update.message.reply_text(f"Anda akan mengunggah {file_count} file VCF. Silakan unggah file VCF Anda satu per satu.")
        return FILE_UPLOAD
    except ValueError:
        await update.message.reply_text("Harap masukkan angka yang valid untuk jumlah file VCF.")
        return VCF_FILE_COUNT

# Handle the file upload and add contacts to each VCF
async def upload_vcf_files(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    document = update.message.document
    contact_numbers = context.user_data['contact_numbers']
    contact_name_base = context.user_data['contact_name_base']
    vcf_file_count = context.user_data['vcf_file_count']
    contact_name_counter = context.user_data.get('contact_name_counter', 1)  # Fetch the counter, or default to 1

    if document and document.file_name.endswith('.vcf'):
        # Process the file one at a time
        file = await document.get_file()
        input_file_path = os.path.join(os.getcwd(), document.file_name)
        await file.download_to_drive(custom_path=input_file_path)

        # Reset the contact name counter for each new VCF file
        contact_name_counter = 1

        # Add the new contacts to the VCF file
        with open(input_file_path, 'a') as f:
            for number in contact_numbers:
                contact_name = f"{contact_name_base} {contact_name_counter}"
                f.write(f"BEGIN:VCARD\n")
                f.write(f"VERSION:3.0\n")
                f.write(f"N:{contact_name}\n")
                f.write(f"TEL;TYPE=CELL:{number}\n")
                f.write(f"END:VCARD\n")
                contact_name_counter += 1  # Increment the counter for each contact

        # Send the modified VCF file back to the user without changing its name
        with open(input_file_path, 'rb') as f:
            await context.bot.send_document(chat_id=update.message.chat.id, document=InputFile(f, filename=document.file_name))

        await update.message.reply_text(f"File '{document.file_name}' telah diproses dan dikirim.")

        # Update the contact name counter in case we upload another file
        context.user_data['contact_name_counter'] = contact_name_counter

        # Decrement the VCF file count and check if more uploads are needed
        context.user_data['vcf_file_count'] -= 1
        if context.user_data['vcf_file_count'] > 0:
            await update.message.reply_text(f"Silakan unggah {context.user_data['vcf_file_count']} file VCF lagi.")
            return FILE_UPLOAD
        else:
            await update.message.reply_text("Semua file VCF telah diproses.")
            return ConversationHandler.END

    else:
        await update.message.reply_text("Harap unggah file VCF yang valid.")
        return FILE_UPLOAD

# Conversation handler setup for adding contacts
def add_contact_handler_setup(application):
    add_contact_conv = ConversationHandler(
        entry_points=[CommandHandler('sisip', add_contact_start)],
        states={
            CONTACT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_contact_name)],
            VCF_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_vcf_name)],
            CONTACT_NUMBERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_contact_numbers)],
            VCF_FILE_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_vcf_file_count)],
            FILE_UPLOAD: [MessageHandler(filters.Document.ALL, upload_vcf_files)],
        },
        fallbacks=[CommandHandler('cancel', add_contact_start)]
    )
    application.add_handler(add_contact_conv)