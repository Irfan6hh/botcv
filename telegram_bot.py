from telegram import Update

from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes  # Ensure ContextTypes is imported

from custom_number import custom_number_handler_setup  # type: ignore # Import the custom number handler setup

from txt_to_vcf import txt_to_vcf_handler_setup  # Import the txt to vcf handler setup



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    await update.message.reply_text(

        "Selamat datang! Pilih fitur yang ingin Anda gunakan:\n"

        "/convert - Konversi file TXT ke VCF\n"

        "/custom_number - Tambah nomor kustom ke VCF\n"

        "Silakan ketikkan perintah di atas untuk memilih fitur."

    )



def main() -> None:

    application = ApplicationBuilder().token("8041257494:AAHGUBiqwPKEoOWX-NwUcbH8W-djm3Z-FO8").build()



    # Set up custom number handler

    custom_number_handler_setup(application)  # Use the application directly



    # Set up txt to vcf handler

    txt_to_vcf_handler_setup(application)  # Setup the txt to vcf handler



    # Set up command handler for start

    application.add_handler(CommandHandler('start', start))



    application.run_polling()



if __name__ == '__main__':

    main()

