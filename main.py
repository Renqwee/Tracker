import asyncio
import nest_asyncio
from telegram import BotCommand
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from Tools.commands import (
    start, button_handler, handle_message, add_product, my_products, delete_product
)
from Tools.price_tasks import check_all_prices
from config import TOKEN  

nest_asyncio.apply()

async def post_init(app):
    print("البوت شغّال ✅")

async def main():
    application = ApplicationBuilder().token(TOKEN).post_init(post_init).build()

    commands = [
        BotCommand("start", "بدء استخدام البوت"),
        BotCommand("add_product", "إضافة منتج للتتبع"),
        BotCommand("my_products", "عرض المنتجات المتعقبة"),
        BotCommand("delete_product", "حذف منتج من التتبع"),
    ]
    await application.bot.set_my_commands(commands)

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add_product", add_product))
    application.add_handler(CommandHandler("my_products", my_products))
    application.add_handler(CommandHandler("delete_product", delete_product))  
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)) 
    

    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_all_prices, "interval", minutes=1)
    scheduler.start()
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())