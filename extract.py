import os
import traceback
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, ConversationHandler, MessageHandler, filters, ContextTypes

# Define states for the conversation
LINE_COUNT, FILE_UPLOAD, FINISH_OPTION = range(3)

# Start extraction process by requesting line count
async def start_extract(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Masukkan jumlah baris nomor yang ingin diambil:")
    return LINE_COUNT

# Receive the line count from the user
async def receive_line_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        line_count = int(update.message.text)
        context.user_data['line_count'] = line_count
        context.user_data['uploaded_files'] = []
        await update.message.reply_text("Silakan unggah file TXT (maksimal 100 file):")
        return FILE_UPLOAD
    except ValueError:
        await update.message.reply_text("Input tidak valid. Harap masukkan jumlah baris yang valid.")
        return LINE_COUNT

# Process uploaded TXT files
async def receive_files(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    line_count = context.user_data.get('line_count', 0)
    if not line_count:
        await update.message.reply_text("Proses tidak valid. Harap ulangi dari awal.")
        return ConversationHandler.END

    # Create necessary directories for extracted and remaining files
    os.makedirs('./extracted_files', exist_ok=True)
    os.makedirs('./remaining_files', exist_ok=True)
    os.makedirs('./tmp', exist_ok=True)

    # Get the uploaded document
    document = update.message.document
    uploaded_file_name = document.file_name
    file_path = f'tmp/{uploaded_file_name}'

    # Download the uploaded file
    file = await document.get_file()
    await file.download_to_drive(file_path)

    # Process the file: extract and clean numbers
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        # Extract lines and clean numbers
        extracted_lines = [
            ''.join(filter(str.isdigit, line.strip())) for line in lines[:line_count] if line.strip()
        ]
        remaining_lines = [
            ''.join(filter(str.isdigit, line.strip())) for line in lines[line_count:] if line.strip()
        ]

    # Add "+" to the start of each number for extracted and remaining lines
    formatted_extracted = [f"+{line}" for line in extracted_lines]
    formatted_remaining = [f"+{line}" for line in remaining_lines]

    # Save extracted lines to a new file
    extracted_file_path = f'./extracted_files/extracted_{uploaded_file_name}'
    with open(extracted_file_path, 'w', encoding='utf-8') as ef:
        ef.writelines('\n'.join(formatted_extracted) + '\n')

    # Save remaining lines to a new file
    remaining_file_path = f'./remaining_files/remaining_{uploaded_file_name}'
    with open(remaining_file_path, 'w', encoding='utf-8') as rf:
        rf.writelines('\n'.join(formatted_remaining) + '\n')

    # Send the extracted file back to the user
    with open(extracted_file_path, 'rb') as ef:
        await context.bot.send_document(chat_id=update.effective_chat.id, document=InputFile(ef, filename=os.path.basename(extracted_file_path)))

    # Send the remaining file to the user
    with open(remaining_file_path, 'rb') as rf:
        await context.bot.send_document(chat_id=update.effective_chat.id, document=InputFile(rf, filename=os.path.basename(remaining_file_path)))

    # Clean up temporary file
    os.remove(file_path)

    # Add the file to the user data for tracking
    context.user_data['uploaded_files'].append(uploaded_file_name)

    # Check if all files have been processed
    if len(context.user_data['uploaded_files']) >= 100:  # Maximum 100 files
        await finish_option(update, context)
        return FINISH_OPTION

    return FILE_UPLOAD

# Finish the process after all files have been processed and uploaded
async def finish_option(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Apakah Anda sudah selesai? Ketik 'selesai' atau 'belum'.")
    return FINISH_OPTION

# Handle user's response after processing files
async def handle_finish_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.lower()
    print(f"User input received: {user_input}")  # Debug log to check input

    if user_input == 'selesai':
        await update.message.reply_text("Terima kasih, proses selesai.")

        # Clear the user data after the process is finished
        print("Clearing user data...")
        context.user_data.clear()

        return ConversationHandler.END  # End the conversation

    elif user_input == 'belum':
        await update.message.reply_text("Silakan unggah file lain.")
        return FILE_UPLOAD  # Return to file upload step

    else:
        await update.message.reply_text("Input tidak dikenal. Silakan ketik 'selesai' atau 'belum'.")
        return FINISH_OPTION

# Error handling
async def handle_error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'Update {update} caused error {context.error}')
    traceback.print_exc()

# Set up Telegram handlers and conversation flow
def extract_handler_setup(application: ApplicationBuilder) -> None:
    extract_handler = ConversationHandler(
        entry_points=[CommandHandler('extract', start_extract)],
        states={
            LINE_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_line_count)],
            FILE_UPLOAD: [MessageHandler(filters.Document.ALL, receive_files)],
            FINISH_OPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_finish_response)],
        },
        fallbacks=[],
    )

    application.add_handler(extract_handler)
