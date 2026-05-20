from telegram import Bot
from config import TOKEN

bot = Bot(token=TOKEN)

async def send_telegram_alert(telegram_id, product_name, old_price, new_price, url, site_name="غير معروف"):
    message = (
        f"📢 <b>تنبيه بتغير السعر</b>\n\n"
        f"🔖 <b>المنتج:</b> {product_name}\n"
        f"🛍️ <b>الموقع:</b> {site_name}\n"
        f"💰 <b>السعر القديم:</b> {old_price} ريال\n"
        f"💸 <b>السعر الجديد:</b> {new_price} ريال\n"
        f"🔗 <b>الرابط:</b> <a href=\"{url}\">اضغط هنا</a>"
    )

    try:
        await bot.send_message(
            chat_id=telegram_id,
            text=message,
            parse_mode="HTML",
            disable_web_page_preview=False
        )
        print(f"✅ تم إرسال التنبيه للمستخدم {telegram_id}")
    except Exception as e:
        print(f"❌ فشل إرسال التنبيه للمستخدم {telegram_id}: {e}")
