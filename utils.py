import os
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes

# Constants for conversation steps
CUSTOM_NAME, VCF_NAME, CUSTOM_NUMBER, RENAME_OLD_NAME, RENAME_NEW_NAME, RENAME_VCF_FILE, ASK_RENAME_FILE, GET_NEW_FILE_NAME, ASK_RESULT_FILE_NAME, GET_RESULT_FILE_NAME = range(10)

# Function to start the bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Selamat datang! Pilih fitur yang ingin Anda gunakan:\n"
        "/convert - Konversi file TXT ke VCF\n"
        "/custom_number - Tambah nomor kustom ke VCF\n"
        "/rename_contact - Ganti nama kontak di VCF\n"
        "Silakan ketikkan perintah di atas untuk memilih fitur."
    )
    return ConversationHandler.END

def convert_txt_to_vcard(input_file_path, contact_name):
    vcards = []
    try:
        with open(input_file_path, 'r', encoding='windows-1252') as file:
            for line in file:
                line = line.strip()  # Remove whitespace
                if not line:  # Skip empty lines
                    continue

                # Split by comma and remove whitespace
                contact_details = [detail.strip() for detail in line.split(',')]

                # Check if there are enough details for a valid contact
                if len(contact_details) < 2:
                    print(f"Skipping line due to insufficient details: {line}")
                    continue  # Skip if not enough details

                # Extract the phone number
                phone_number = contact_details[1]

                if not phone_number:  # Skip if phone number is empty
                    print(f"Skipping line due to empty phone number: {line}")
                    continue

                # Create VCard entry
                vcard = f"BEGIN:VCARD\nVERSION:3.0\nFN:{contact_name}\n"
                vcard += f"TEL:{phone_number}\n"
                vcard += "END:VCARD"
                vcards.append(vcard)

                # Debug output to check the generated VCard
                print(f"Generated VCard: {vcard}")

        # Debug: Check the number of VCards generated
        print(f"Number of VCards generated: {len(vcards)}")

    except Exception as e:
        print(f"Error reading file: {e}")
        return []

    return vcards

# Function to handle renaming contact
async def rename_contact_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Silakan unggah file VCF Anda.")
    return RENAME_VCF_FILE

# Function to handle uploading VCF for renaming
async def get_vcf_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    document = update.message.document
    if document:
        vcf_file = await document.get_file()
        file_path = os.path.join(os.getcwd(), document.file_name)
        await vcf_file.download_to_drive(file_path)

        context.user_data['vcf_file_path'] = file_path

        # Tanyakan apakah ingin mengganti nama file sebelum mengubah kontak
        await update.message.reply_text("Apakah Anda ingin mengganti nama file VCF sebelum mengubah kontak? (ketik 'ya' atau 'tidak')")
        return ASK_RENAME_FILE
    else:
        await update.message.reply_text("Harap unggah file VCF yang valid.")
        return ConversationHandler.END

# Function to handle renaming file confirmation before renaming contacts
async def ask_rename_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    response = update.message.text.strip().lower()
    if response == 'ya':
        await update.message.reply_text("Silakan masukkan nama file VCF baru (tanpa ekstensi '.vcf'):")
        return GET_NEW_FILE_NAME
    else:
        await update.message.reply_text("Silakan ketikkan nama kontak lama yang ingin diganti:")
        return RENAME_OLD_NAME

# Function to get new VCF file name and rename it before renaming contacts
async def get_new_file_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_file_name = update.message.text.strip()
    vcf_file_path = context.user_data.get('vcf_file_path')

    # Ganti nama file dengan yang baru
    new_vcf_full_path = os.path.join(os.getcwd(), f"{new_file_name}.vcf")
    os.rename(vcf_file_path, new_vcf_full_path)
    context.user_data['vcf_file_path'] = new_vcf_full_path  # Update file path setelah rename

    await update.message.reply_text("Nama file berhasil diubah. Sekarang, ketikkan nama kontak lama yang ingin diganti:")
    return RENAME_OLD_NAME

# Function to get old name for renaming contacts
async def get_old_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    old_name = update.message.text.strip()
    context.user_data['old_name'] = old_name
    await update.message.reply_text(f"Nama kontak lama yang Anda masukkan: {old_name}. Sekarang, ketikkan nama baru untuk kontak tersebut:")
    return RENAME_NEW_NAME

# Function to get new name and rename the contact in the VCF
async def get_new_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_name = update.message.text.strip()
    vcf_file_path = context.user_data.get('vcf_file_path')
    old_name = context.user_data.get('old_name')

    if not vcf_file_path:
        await update.message.reply_text("File VCF tidak ditemukan. Silakan unggah file terlebih dahulu.")
        return ConversationHandler.END

    new_lines = []
    contact_found = False

    # Membaca file VCF dan mengganti nama kontak yang sesuai
    with open(vcf_file_path, 'r', encoding='windows-1252') as file:  # Changed to Windows-1252
        for line in file:
            if line.startswith("FN:") and old_name in line:
                contact_found = True
                line = line.replace(old_name, new_name)
            new_lines.append(line)

    if contact_found:
        # Tanyakan nama file hasil VCF
        await update.message.reply_text("Silakan masukkan nama file VCF hasil yang diinginkan (tanpa ekstensi '.vcf'):")
        context.user_data['new_lines'] = new_lines  # Simpan new_lines untuk digunakan nanti
        return ASK_RESULT_FILE_NAME
    else:
        await update.message.reply_text(f"Kontak dengan nama '{old_name}' tidak ditemukan dalam file VCF.")
        return ConversationHandler.END

# Function to get result file name and save the renamed VCF file
async def get_result_file_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    result_file_name = update.message.text.strip()
    vcf_file_path = context.user_data.get('vcf_file_path')

    # Simpan nama file VCF dengan nama yang dimasukkan pengguna
    new_vcf_path = os.path.join(os.getcwd(), f"{result_file_name}.vcf")

    # Tulis file baru dengan nama kontak yang telah diubah
    with open(new_vcf_path, 'w', encoding='windows-1252') as file:  # Changed to Windows-1252
        file.writelines(context.user_data.get('new_lines', []))

    # Kirim file VCF hasil rename kontak ke pengguna
    with open(new_vcf_path, 'rb') as f:
        await context.bot.send_document(chat_id=update.message.chat.id, document=InputFile(f, filename=new_vcf_path))

    await update.message.reply_text("Kontak berhasil diganti dan file VCF telah dikirim.")
    return ConversationHandler.END

# Conversation handler setup for renaming contact
def rename_contact_handler_setup(application):
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('rename_contact', rename_contact_start)],
        states={
            RENAME_VCF_FILE: [MessageHandler(filters.Document.ALL, get_vcf_file)],
            ASK_RENAME_FILE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_rename_file)],
            GET_NEW_FILE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_new_file_name)],
            RENAME_OLD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_old_name)],
            RENAME_NEW_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_new_name)],
            ASK_RESULT_FILE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_result_file_name)]
        },
        fallbacks=[CommandHandler('cancel', lambda update, context: update.message.reply_text("Operasi dibatalkan."))],
    )

    application.add_handler(conv_handler)
