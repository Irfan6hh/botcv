import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from flask import Flask
from threading import Thread

# Import handler setup functions from the feature modules
from split_vcf import split_vcf_handler_setup
from custom_number import custom_number_handler_setup
from txt_to_vcf import txt_to_vcf_handler_setup
from convert_any import any_file_handler_setup
from sisip import add_contact_handler_setup
from rename_contact import rename_contact_handler_setup
from extract import extract_handler_setup
from copy_number import copy_number_handler_setup

# Allowed user IDs who can access the bot
ALLOWED_USER_IDS = [1844552663, 6604912036]  # Replace with actual allowed user IDs

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Function to check user ID and display menu if allowed
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    logger.info(f"User ID {user_id} initiated /start command.")

    # Check if user_id is in the allowed users list
    if user_id not in ALLOWED_USER_IDS:
        await update.message.reply_text("Maaf, Anda tidak diizinkan untuk menggunakan bot ini. Hubungi @Bolu0907")
        logger.warning(f"Unauthorized access attempt by user ID {user_id}.")
        return

    # If the user is allowed, display the available features
    await update.message.reply_text(
        "Selamat datang di CV BOT LIGHTSPEED! Pilih fitur yang ingin Anda gunakan:\n"
        "/convert - Konversi file TXT ke VCF\n"
        "/extract - extract nomor perbaris\n"
        "/convert_any - Konversi semua format file ke VCF\n"
        "/custom_number - Tambah nomor kustom ke VCF\n"
        "/rename_contact - Ganti nama kontak di VCF\n"
        "/copy_number - ambil data per column excel\n"
        "/split_vcf - Pecah File\n"
        "/sisip - Sisipkan kontak admin ke VCF\n"
        "Silakan ketikkan perintah di atas untuk memilih fitur."
    )

# Flask app setup
app = Flask('')

@app.route('/')
def home():
    return "Bot is running"

def run():
    port = int(os.environ.get('PORT', 5000))  # Use dynamic port provided by Replit
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Main function to initialize the bot and set up feature handlers
def main() -> None:
    # Directly specify your bot token here (use environment variable in production)
    token = os.getenv('7805923237:AAHDCGSTwxMa_cmjSKCFH1Ap0uNzn45KbTM')  # Replace with your actual bot token

    # Create the bot application
    application = ApplicationBuilder().token("7805923237:AAHDCGSTwxMa_cmjSKCFH1Ap0uNzn45KbTM").build()

    # Set up feature handlers from imported modules
    custom_number_handler_setup(application)
    any_file_handler_setup(application)
    txt_to_vcf_handler_setup(application)
    rename_contact_handler_setup(application)
    extract_handler_setup(application)
    split_vcf_handler_setup(application)
    add_contact_handler_setup(application)
    copy_number_handler_setup(application)

    # Add the start command handler
    application.add_handler(CommandHandler('start', start))

    # Run the bot using polling
    logger.info("Bot started polling...")
    application.run_polling()

if __name__ == '__main__':
    keep_alive()  # Start Flask server in the background
    main()  # Start the bot