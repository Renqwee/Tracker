from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db import (
    is_user_new,
    set_user_not_new,
    save_tracking_to_db,
    get_user_products,
    is_product_tracked,
    get_product_by_url,
    delete_tracking_by_id,
)
from Tools.api_client import get_product_info
import requests
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id

    if await is_user_new(telegram_id):
        keyboard = [
            [InlineKeyboardButton("Start", callback_data="start_bot")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "أهلاً وسهلاً في بوت تتبع الأسعار!\nاضغط على زر Start عشان نبدأ.",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text("حياك الله من جديد! استخدم القائمة الجانبية لاختيار أمر.")

async def add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['adding_product'] = True

    keyboard = [
        [InlineKeyboardButton("هونت", callback_data="cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "أرسل لي رابط المنتج اللي تبي تتابعه:",
        reply_markup=reply_markup
    )

async def delete_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    products = await get_user_products(telegram_id)

    if not products:
        await update.message.reply_text("ما عندك منتجات تتابعها حالياً.")
        return

    keyboard = []
    for row in products:
        name = row["product_name"]
        product_id = row["id"]  # تأكد أن get_user_products ترجع product_id
        keyboard.append([InlineKeyboardButton(name, callback_data=f"confirm_delete:{product_id}")])

    keyboard.append([InlineKeyboardButton("هونت", callback_data="cancel")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "اختر المنتج اللي تبي تحذفه من التتبع:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    telegram_id = query.from_user.id
    data = query.data

    if data == "start_bot":
        await set_user_not_new(telegram_id)
        await query.edit_message_text(
            "🎉 مرحباً في بوت تتبّع الأسعار!\n\n"
            "🔹 تقدر تتابع تغيّر أسعار المنتجات بسهولة.\n"
            "🔹 المواقع المدعومة حالياً:\n"
            "   - Amazon\n"
            "   - Noon\n"
            "   - Extra\n"
            "   - Carrefour\n\n"
            "🔹 أنواع التتبع المتاحة:\n"
            "   - 📈 أي تغيير في السعر\n"
            "   - 📉 إذا انخفض السعر\n"
            "   - 🎯 إذا وصل لسعر مستهدف تحدده\n\n"
            "📦 تقدر تشوف منتجاتك الحالية أو تحذفها متى ما بغيت.\n\n"
            "✅ اضغط على زر Add من القائمة لإضافة أول منتج.\n"
            "🗂️ باقي الأوامر تلقاها في قائمة البوت.\n\n"
            "📩 للاستفسار أو المساعدة تواصل معي: ",
            parse_mode="Markdown"
        )
    elif data == "cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ تم إلغاء العملية.")

    elif data == "target_reached":
        context.user_data['condition_type'] = data
        context.user_data['awaiting_target_price'] = True

        keyboard = [[InlineKeyboardButton("هونت", callback_data="cancel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "أرسل لي السعر المستهدف اللي تبي توصله:",
            reply_markup=reply_markup
        )

    elif data in ["any_change", "price_dropped"]:
        context.user_data['condition_type'] = data

        if 'product_url' not in context.user_data:
            await query.edit_message_text("⚠️ الرابط غير موجود. يرجى إعادة إرسال الرابط.")
            return

        if 'product_name' not in context.user_data:
            product_info = await get_product_by_url(telegram_id, context.user_data['product_url'])
            if not product_info:
                await query.edit_message_text("❌ ما قدرنا نجيب بيانات المنتج. حاول تضيفه من جديد.")
                return

            context.user_data['product_name'] = product_info['product_name']
            context.user_data['current_price'] = product_info['current_price']
            context.user_data['site_name'] = product_info.get('site_name', 'unknown')
            context.user_data['target_price'] = product_info.get('target_price')

        await save_tracking_to_db(telegram_id, context.user_data)
        await query.edit_message_text("✅ تم إضافة المنتج وتتبع السعر بنجاح.")
        context.user_data.clear()

    elif data == "change_tracking":
        url = context.user_data.get("product_url")
        if not url:
            await query.edit_message_text("❌ الرابط غير معروف. أرسل الرابط من جديد.")
            return

        keyboard = [
            [
                InlineKeyboardButton("أي تغيير بالسعر", callback_data="any_change"),
                InlineKeyboardButton("سعر مستهدف", callback_data="target_reached"),
            ],
            [
                InlineKeyboardButton("انخفاض السعر", callback_data="price_dropped"),
                InlineKeyboardButton("هونت", callback_data="cancel"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "اختر نوع التتبع الجديد لهذا الرابط:",
            reply_markup=reply_markup
        )

    elif data == "my_products":
        products = await get_user_products(telegram_id)
        if not products:
            await query.edit_message_text("ما عندك منتجات قاعد تتابعها حالياً.")
            return

        msg = "📦 المنتجات اللي تتابعها:\n\n"
        for i, row in enumerate(products, 1):
            name = row.get("product_name", "بدون اسم")
            price = row.get("current_price", "-")
            last = row.get("last_price", "-")
            url = row.get("url", "-")
            cond = row.get("condition_type", "unknown")
            target = row.get("target_price", "-")
            site = row.get("site_name", "غير معروف")

            cond_text = {
                "any_change": "📈 أي تغيير بالسعر",
                "price_dropped": "📉 عند انخفاض السعر",
                "target_reached": f"🎯 عند الوصول إلى {target} ريال"
            }.get(cond, "🔔 تتبع غير معروف")

            msg += (
                f"{i}. {name}\n"
                f"🛒 الموقع: {site}\n"
                f"💰 السعر الحالي: {price} ريال\n"
                f"🔁 السعر السابق: {last} ريال\n"
                f"🔎 نوع التتبع: {cond_text}\n"
                f"🔗 [رابط المنتج]({url})\n\n"
            )

        await query.edit_message_text(msg, parse_mode="Markdown")
    elif data == "delete_product":
        products = await get_user_products(telegram_id)
        if not products:
            await query.edit_message_text("ما عندك منتجات تتابعها حالياً.")
            return

        keyboard = []
        for row in products:
            name = row["product_name"]
            product_id = row["product_id"]  # لازم تتأكد أن get_user_products ترجع هذا الحقل
            keyboard.append([InlineKeyboardButton(name, callback_data=f"confirm_delete:{product_id}")])
        keyboard.append([InlineKeyboardButton("هونت", callback_data="cancel")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text("اختر المنتج اللي تبي تحذفه من التتبع:", reply_markup=reply_markup)

    elif data.startswith("confirm_delete:"):
        product_id = data.split("confirm_delete:")[1]
        context.user_data['product_id_to_delete'] = int(product_id)

        keyboard = [
            [InlineKeyboardButton("🗑️ متأكد", callback_data="delete_confirmed")],
            [InlineKeyboardButton("هونت", callback_data="cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"هل أنت متأكد أنك تبي تحذف هذا المنتج من التتبع؟",
            reply_markup=reply_markup
        )

    elif data == "delete_confirmed":
        product_id = context.user_data.get("product_id_to_delete")
        if not product_id:
            await query.edit_message_text("❌ ما قدرنا نحدد المنتج. حاول مرة ثانية.")
            return

        await delete_tracking_by_id(telegram_id, product_id)
        context.user_data.clear()
        await query.edit_message_text("✅ تم حذف المنتج من التتبع بنجاح.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    text = update.message.text.strip()

    if text.lower() in ["هونت", "cancel"]:
        context.user_data.clear()
        await update.message.reply_text("✅ تم إلغاء العملية.")
        return

    if context.user_data.get('awaiting_target_price'):
        if text.lower() in ["هونت", "cancel"]:
            context.user_data.clear()
            await update.message.reply_text("❌ تم إلغاء العملية.")
            return
        try:
            target_price = float(text)
        except ValueError:
            await update.message.reply_text("رجاءً أرسل رقم صالح للسعر المستهدف أو أرسل 'هونت' لإلغاء.")
            return

        context.user_data['target_price'] = target_price
        context.user_data['awaiting_target_price'] = False

        if 'product_name' not in context.user_data:
            product_info = await get_product_by_url(telegram_id, context.user_data.get('product_url'))
            if not product_info:
                await update.message.reply_text("❌ ما قدرنا نجيب بيانات المنتج. حاول تضيفه من جديد.")
                return
            context.user_data['product_name'] = product_info['product_name']
            context.user_data['current_price'] = product_info['current_price']
            context.user_data['site_name'] = product_info.get('site_name', 'unknown')

        await save_tracking_to_db(telegram_id, context.user_data)
        await update.message.reply_text(
            f"✅ تم تتبع المنتج بنجاح.\n"
            f"اسم المنتج: {context.user_data['product_name']}\n"
            f"السعر المستهدف: {target_price} ريال"
        )
        context.user_data.clear()
        return

    if context.user_data.get('adding_product'):
        url = text

        if not url.startswith("http"):
            await update.message.reply_text("رجاءً أرسل رابط صحيح أو أرسل 'هونت' لإلغاء.")
            return

        if "aliexpress.com" in url:
            await update.message.reply_text("❌ حالياً ما ندعم تتبع منتجات من موقع AliExpress.")
            context.user_data.clear()
            return

        # تحقق إذا الرابط مكرر للمستخدم الحالي
        if await is_product_tracked(telegram_id, url):
            keyboard = [
                [InlineKeyboardButton("تغيير نوع التتبع", callback_data="change_tracking")],
                [InlineKeyboardButton("هونت", callback_data="cancel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "⚠️ هذا الرابط سبق وتابعته. تقدر تغير نوع التتبع أو تضيف رابط جديد.",
                reply_markup=reply_markup
            )
            context.user_data.clear()
            context.user_data['product_url'] = url  # نخزن الرابط عشان نستخدمه لاحقًا في زر التغيير
            return

        await update.message.reply_text("ثواني... جاري جلب معلومات المنتج.")

        try:
            info = await get_product_info(url)
            product_name = info['name']
            raw_price = info['price']
            site_name = info.get('site') or "unknown"

            try:
                current_price = float(raw_price) if isinstance(raw_price, (int, float)) else float(str(raw_price).split()[0])
            except Exception as e:
                await update.message.reply_text("❌ السعر ما كان بصيغة صحيحة.")
                print(f"خطأ في تحويل السعر: {e}")
                return

        except Exception as e:
            print(f"❌ خطأ أثناء جلب معلومات المنتج: {e}")
            await update.message.reply_text("❌ فشل في جلب معلومات المنتج. تأكد من الرابط أو أرسل 'هونت' لإلغاء.")
            return

        context.user_data['product_url'] = url
        context.user_data['product_name'] = product_name
        context.user_data['current_price'] = current_price
        context.user_data['site_name'] = site_name

        keyboard = [
            [
                InlineKeyboardButton("أي تغيير بالسعر", callback_data="any_change"),
                InlineKeyboardButton("عند وصول السعر المستهدف", callback_data="target_reached"),
            ],
            [
                InlineKeyboardButton("عند انخفاض السعر فقط", callback_data="price_dropped"),
                InlineKeyboardButton("هونت", callback_data="cancel"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"اسم المنتج: {product_name}\n"
            f"السعر الحالي: {current_price} ريال\n"
            "وش نوع التتبع اللي تبيه؟",
            reply_markup=reply_markup
        )
        context.user_data['adding_product'] = False

async def my_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    products = await get_user_products(telegram_id)

    if not products:
        await update.message.reply_text("ما عندك منتجات قاعد تتابعها حالياً.")
        return

    msg = "📦 المنتجات اللي تتابعها:\n\n"
    for i, row in enumerate(products, 1):
        name = row.get("product_name", "بدون اسم")
        price = row.get("current_price", "-")
        last = row.get("last_price", "-")
        url = row.get("url", "-")
        cond = row.get("condition_type", "unknown")
        target = row.get("target_price", "-")
        site = row.get("site_name", "غير معروف")

        cond_text = {
            "any_change": "📈 أي تغيير بالسعر",
            "price_dropped": "📉 عند انخفاض السعر",
            "target_reached": f"🎯 عند الوصول إلى {target} ريال"
        }.get(cond, "🔔 تتبع غير معروف")

        msg += (
            f"{i}. {name}\n"
            f"🛒 الموقع: {site}\n"
            f"💰 السعر الحالي: {price} ريال\n"
            f"🔁 السعر السابق: {last} ريال\n"
            f"🔎 نوع التتبع: {cond_text}\n"
            f"🔗 [رابط المنتج]({url})\n\n"
        )

    await update.message.reply_text(msg, parse_mode="Markdown")