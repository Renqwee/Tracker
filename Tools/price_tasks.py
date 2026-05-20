from db import (
    get_all_tracked_products,
    update_product_price,
    get_tracking_condition,
    get_target_price,
)
from Tools.api_client import get_product_info  
from Tools.utils import send_telegram_alert

def parse_price(raw_price):
    try:
        return float(raw_price) if isinstance(raw_price, (int, float)) else float(str(raw_price).split()[0])
    except Exception as e:
        print(f"❌ خطأ في تحويل السعر: {e}")
        return None

async def check_all_prices():
    print("🔍 جاري فحص الأسعار...")

    products = await get_all_tracked_products()
    if not products:
        print("⚠️ لا يوجد منتجات لمتابعة أسعارها.")
        return

    updated_products = {}

    for product in products:
        telegram_id = product['telegram_id']
        url = product['url']
        last_price = product['last_price']
        current_price_db = product['current_price']
        product_name = product['product_name']
        condition = product['condition_type']
        target_price = product.get('target_price')
        site_name = product.get('site_name', 'unknown')

        try:
            if url in updated_products:
                new_price = updated_products[url]
            else:
                info = await get_product_info(url)  
                fetched_name = info['name']
                raw_price = info['price']
                site_name = info.get('site', 'unknown')

                new_price = parse_price(raw_price)
                if new_price is None:
                    continue

                updated_products[url] = new_price

            should_alert = False
            force_last_price = False

            if condition == "any_change":
                if last_price is None or new_price != last_price:
                    should_alert = True

            elif condition == "price_dropped":
                if last_price is not None and new_price < last_price:
                    should_alert = True

            elif condition == "target_reached":
                if target_price is not None:
                    try:
                        target = float(target_price)
                        if new_price <= target and new_price != last_price:
                            should_alert = True
                            force_last_price = True
                    except ValueError:
                        print(f"⚠️ لم أستطع تحويل السعر المستهدف إلى رقم: {target_price}")

            if should_alert:
                print(f"💡 تنبيه لمستخدم {telegram_id}: {product_name} | {last_price or '-'} ➡️ {new_price} | 🛍️ {site_name}")
                await send_telegram_alert(telegram_id, product_name, last_price or "-", new_price, url, site_name)

            if url not in updated_products or last_price is None or new_price != last_price:
                await update_product_price(telegram_id, url, new_price, force_update=True, force_last_price=force_last_price)

        except Exception as e:
            print(f"❌ فشل التحقق من الرابط: {url}\n📌 الخطأ: {e}")

    print("✅ تم فحص جميع المنتجات.\n")
