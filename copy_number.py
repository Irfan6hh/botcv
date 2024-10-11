import os
import pandas as pd
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes

# Define states for the conversation
COLUMN_INPUT, FILE_UPLOAD, FINISH_OPTION = range(3)

async def start_copy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Masukkan nomor kolom dari mana Anda ingin mengambil data nomor (mulai dari 1):")
    return COLUMN_INPUT


# Receive the column number from the user
async def receive_column_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        column_number = int(update.message.text) - 1  # Adjust for 0-indexing
        context.user_data['column_number'] = column_number
        context.user_data['uploaded_files'] = []
        await update.message.reply_text("Silakan unggah file Excel (maksimal 100 file):")
        return FILE_UPLOAD
    except ValueError:
        await update.message.reply_text("Input tidak valid. Harap masukkan nomor kolom yang valid.")
        return COLUMN_INPUT


# Create directories for storing files
os.makedirs('tmp', exist_ok=True)
os.makedirs('extracted_files', exist_ok=True)


# Process uploaded Excel files
async def receive_files(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    column_number = context.user_data.get('column_number', None)
    if column_number is None:
        await update.message.reply_text("Proses tidak valid. Harap ulangi dari awal.")
        return ConversationHandler.END

    # Get the uploaded document
    document = update.message.document
    uploaded_file_name = document.file_name
    file_path = f'tmp/{uploaded_file_name}'

    # Download the uploaded file
    file = await document.get_file()
    await file.download_to_drive(file_path)

    # Process the file: extract numbers from the specified column
    extracted_lines = []

    # Read the Excel file
    try:
        df = pd.read_excel(file_path)

        # Check if the specified column exists
        if column_number >= len(df.columns):
            await update.message.reply_text("Kolom yang diminta tidak ada dalam file.")
            os.remove(file_path)  # Clean up the uploaded file
            return FILE_UPLOAD

        # Extract numbers from the specified column
        column_data = df.iloc[:, column_number].dropna()  # Drop NaN values
        for item in column_data:
            # Extract digits and format as needed
            cleaned_number = ''.join(filter(str.isdigit, str(item)))
            if cleaned_number:  # Ensure there's a number to process
                extracted_lines.append(f"+{cleaned_number}")

    except Exception as e:
        await update.message.reply_text(f"Terjadi kesalahan saat memproses file: {str(e)}")
        os.remove(file_path)  # Clean up the uploaded file
        return FILE_UPLOAD

    # Save extracted lines to a new TXT file
    extracted_file_path = f'extracted_files/extracted_{uploaded_file_name}.txt'
    with open(extracted_file_path, 'w', encoding='utf-8') as ef:
        ef.writelines('\n'.join(extracted_lines) + '\n')

    # Send the extracted file back to the user
    with open(extracted_file_path, 'rb') as ef:
        await context.bot.send_document(chat_id=update.effective_chat.id, document=ef)

    # Clean up temporary file
    os.remove(file_path)

    # Add the file to the user data for tracking
    context.user_data['uploaded_files'].append(uploaded_file_name)

    # Check if all files have been processed
    if len(context.user_data['uploaded_files']) >= 100:  # Maximum 100 files
        await finish_option(update, context)
        return FINISH_OPTION

    await finish_option(update, context)  # Prompt finish option after each file
    return FINISH_OPTION


# Finish the process after all files have been processed
async def finish_option(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Apakah Anda sudah selesai? Ketik 'selesai' atau 'belum'.")
    return FINISH_OPTION


# Handle user's response after processing files
async def handle_finish_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.lower()
    print(f"User input received: {user_input}")  # Debug log to check input

    if user_input == 'selesai':
        await update.message.reply_text("Terima kasih, proses selesai.")
        context.user_data.clear()  # Clear the user data after the process is finished
        return ConversationHandler.END  # End the conversation

    elif user_input == 'belum':
        await update.message.reply_text("Silakan unggah file lain.")
        return FILE_UPLOAD  # Return to file upload step

    else:
        await update.message.reply_text("Input tidak dikenal. Silakan ketik 'selesai' atau 'belum'.")
        return FINISH_OPTION


# Set up Telegram handlers and conversation flow
def copy_number_handler_setup(application: ApplicationBuilder) -> None:
    copy_handler = ConversationHandler(
        entry_points=[CommandHandler('copy_number', start_copy)],
        states={
            COLUMN_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_column_number)],
            FILE_UPLOAD: [MessageHandler(filters.Document.ALL, receive_files)],
            FINISH_OPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_finish_response)],
        },
        fallbacks=[],
    )
    application.add_handler(copy_handler)
