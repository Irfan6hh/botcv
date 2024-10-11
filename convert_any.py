import os
import re
from telegram import Update, InputFile
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, filters, ContextTypes
import openpyxl

# State for conversation
NAME, VCF_NAME, FILE_UPLOAD, FILE_COUNT, FINISH_OPTION = range(5)

async def convert_any_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()  # Clear previous user data for a fresh start
    await update.message.reply_text("Silakan masukkan nama kontak yang akan digunakan.")
    return NAME

# Function to handle name input
async def name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['contact_name'] = update.message.text.strip()
    await update.message.reply_text("Silakan masukkan nama file VCF yang diinginkan.")
    return VCF_NAME

# Function to handle VCF file name input
async def vcf_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['vcf_name'] = update.message.text.strip()
    await update.message.reply_text("Silakan masukkan jumlah file yang akan diunggah.")
    return FILE_COUNT

# Function to handle file count input
async def file_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['file_count'] = int(update.message.text.strip())
    context.user_data['uploaded_files'] = []  # Initialize uploaded files list
    await update.message.reply_text("Silakan unggah file yang akan dikonversi.")
    return FILE_UPLOAD

# Function to convert any file to VCF format
def convert_to_vcard(input_file_path, contact_name):
    vcards = []

    # Determine the file extension
    file_extension = os.path.splitext(input_file_path)[1].lower()

    try:
        if file_extension in ['.txt', '.csv']:
            # For TXT and CSV files
            with open(input_file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
                for index, line in enumerate(lines):
                    # Remove all characters except digits
                    line = re.sub(r'\D', '', line)  # Remove all non-numeric characters
                    if not line:
                        continue

                    # Add '+' at the beginning if it's not already there
                    if not line.startswith('+'):
                        line = '+' + line

                    # Create VCard entry with the contact name and sequence number
                    vcard = f"BEGIN:VCARD\nVERSION:3.0\nFN:{contact_name} {index + 1}\nTEL:{line}\nEND:VCARD"
                    vcards.append(vcard)

        elif file_extension in ['.xlsx', '.xls']:
            # For Excel files without using pandas
            wb = openpyxl.load_workbook(input_file_path)
            sheet = wb.active
            for index, row in enumerate(sheet.iter_rows(values_only=True)):
                for cell in row:
                    if cell:
                        line = str(cell)
                        # Remove all characters except digits
                        line = re.sub(r'\D', '', line)  # Remove all non-numeric characters
                        if not line:
                            continue

                        # Add '+' at the beginning if it's not already there
                        if not line.startswith('+'):
                            line = '+' + line

                        # Create VCard entry with the contact name and sequence number
                        vcard = f"BEGIN:VCARD\nVERSION:3.0\nFN:{contact_name} {index + 1}\nTEL:{line}\nEND:VCARD"
                        vcards.append(vcard)

        else:
            raise ValueError("Unsupported file type.")

    except Exception as e:
        print(f"Error reading file: {e}")
        return []

    return vcards

async def receive_files(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    expected_count = context.user_data.get('file_count', 0)

    if update.message.document:
        file = await update.message.document.get_file()
        input_file_path = f"{update.message.document.file_name}"
        await file.download_to_drive(custom_path=input_file_path)

        contact_name = context.user_data['contact_name']
        vcf_name = context.user_data['vcf_name']

        vcards = convert_to_vcard(input_file_path, contact_name)

        if not vcards:
            await update.message.reply_text("Tidak ada data yang ditemukan untuk diubah menjadi VCF.")
            return FILE_UPLOAD

        # Write all vcards to a single VCF file
        output_file_name = f"{vcf_name}.vcf"  # File name without sequence number
        output_file_path = os.path.join(os.getcwd(), output_file_name)

        with open(output_file_path, 'w') as f_out:
            f_out.write("\n".join(vcards) + "\n")

        # Send the created VCF file to the user
        with open(output_file_path, 'rb') as f:
            await context.bot.send_document(chat_id=update.message.chat.id, document=InputFile(f, filename=os.path.basename(output_file_path)))

        await update.message.reply_text(f"File '{input_file_path}' telah diproses dan dikonversi menjadi file VCF.")

        context.user_data['uploaded_files'].append(output_file_path)

        if len(context.user_data['uploaded_files']) >= expected_count:
            await update.message.reply_text("Semua file telah diproses dan dikirim.")
            await finish_option(update, context)
            return FINISH_OPTION

        return FILE_UPLOAD
    else:
        await update.message.reply_text("Tolong unggah file yang valid.")
        return FILE_UPLOAD

async def finish_option(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Apakah Anda sudah selesai? Ketik 'selesai' atau 'belum'.")
    return FINISH_OPTION

async def finish_process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    response = update.message.text.strip().lower()

    if response == 'selesai':
        await update.message.reply_text("Terima kasih! Anda telah menyelesaikan proses.")
    elif response == 'belum':
        await update.message.reply_text("Anda dapat melanjutkan dengan /convert_any untuk mengonversi file lainnya.")
    else:
        await update.message.reply_text("Tolong masukkan 'selesai' atau 'belum'.")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Proses dibatalkan.")
    return ConversationHandler.END

def any_file_handler_setup(application):
    convert_any_conv = ConversationHandler(
        entry_points=[CommandHandler('convert_any', convert_any_start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name)],
            VCF_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, vcf_name)],
            FILE_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, file_count)],
            FILE_UPLOAD: [MessageHandler(filters.Document.ALL, receive_files)],
            FINISH_OPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, finish_process)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    application.add_handler(convert_any_conv)
