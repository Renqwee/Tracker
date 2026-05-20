import asyncpg
from datetime import datetime
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

async def get_connection():
    return await asyncpg.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

async def ensure_user_exists(telegram_id, is_new=False):
    conn = await get_connection()
    try:
        await conn.execute("""
            INSERT INTO users (telegram_id, is_new)
            VALUES ($1, $2)
            ON CONFLICT (telegram_id) DO NOTHING
        """, telegram_id, is_new)
    except Exception as e:
        print("❌ خطأ في ensure_user_exists:", e)
    finally:
        await conn.close()

async def get_user_id(telegram_id):
    conn = await get_connection()
    try:
        row = await conn.fetchrow("SELECT id FROM users WHERE telegram_id = $1", telegram_id)
        return row["id"] if row else None
    except Exception as e:
        print("❌ خطأ في get_user_id:", e)
        return None
    finally:
        await conn.close()

async def is_user_new(telegram_id):
    await ensure_user_exists(telegram_id, is_new=True)
    conn = await get_connection()
    try:
        row = await conn.fetchrow("SELECT is_new FROM users WHERE telegram_id = $1", telegram_id)
        return row["is_new"] if row else True
    except Exception as e:
        print("❌ خطأ في is_user_new:", e)
        return False
    finally:
        await conn.close()

async def set_user_not_new(telegram_id):
    conn = await get_connection()
    try:
        await conn.execute("UPDATE users SET is_new = FALSE WHERE telegram_id = $1", telegram_id)
    except Exception as e:
        print("❌ خطأ في set_user_not_new:", e)
    finally:
        await conn.close()

async def get_all_tracked_products():
    conn = await get_connection()
    try:
        return await conn.fetch("""
            SELECT
                u.telegram_id,
                p.url,
                p.product_name,
                p.current_price,
                p.last_price,
                p.site_name,
                t.condition_type,
                t.target_price
            FROM tracking t
            JOIN products p ON p.id = t.product_id
            JOIN users u ON u.id = t.user_id
        """)
    except Exception as e:
        print("❌ خطأ في get_all_tracked_products:", e)
        return []
    finally:
        await conn.close()

async def save_tracking_to_db(telegram_id, user_data):
    await ensure_user_exists(telegram_id)
    user_id = await get_user_id(telegram_id)
    if user_id is None:
        print("❌ فشل في إيجاد user_id.")
        return

    conn = await get_connection()
    try:
        url = user_data.get('product_url')
        name = user_data.get('product_name')
        current_price = user_data.get('current_price')
        condition_type = user_data.get('condition_type')
        target_price = user_data.get('target_price', None)
        site_name = user_data.get('site_name', 'unknown')
        track_type = user_data.get('track_type')

        if not all([url, name, current_price, condition_type]):
            print("❌ بيانات ناقصة ما قدرنا نحفظ المنتج.")
            return

        row = await conn.fetchrow("SELECT id FROM products WHERE url = $1", url)
        if row:
            product_id = row['id']
            await conn.execute("""
                UPDATE products SET
                    current_price = $1,
                    product_name = $2,
                    site_name = $3,
                    last_price = $4,
                    last_checked = NOW()
                WHERE id = $5
            """, current_price, name, site_name, current_price, product_id)
        else:
            row = await conn.fetchrow("""
                INSERT INTO products (url, product_name, current_price, last_price, site_name, last_checked)
                VALUES ($1, $2, $3, $4, $5, NOW())
                RETURNING id
            """, url, name, current_price, current_price, site_name)
            product_id = row['id']

        await conn.execute("""
            INSERT INTO tracking (user_id, product_id, condition_type, target_price, track_type)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (user_id, product_id) DO UPDATE
            SET condition_type = EXCLUDED.condition_type,
                target_price = EXCLUDED.target_price,
                track_type = EXCLUDED.track_type
        """, user_id, product_id, condition_type, target_price, track_type)

    except Exception as e:
        print("❌ خطأ في save_tracking_to_db:", e)
    finally:
        await conn.close()

async def update_product_price(telegram_id, url, new_price, force_update=False, force_last_price=False):
    conn = await get_connection()
    try:
        row = await conn.fetchrow("SELECT id, current_price FROM products WHERE url = $1", url)
        if row is None:
            print("❌ المنتج غير موجود للتحديث.")
            return False

        product_id = row['id']
        old_price = row['current_price']

        if not force_update and old_price == new_price:
            print("ℹ️ السعر ما تغير، ما راح نحدث last_price.")
            return False

        last_price_to_set = new_price if force_last_price else old_price

        await conn.execute("""
            UPDATE products
            SET current_price = $1,
                last_price = $2,
                last_checked = NOW()
            WHERE id = $3
        """, new_price, last_price_to_set, product_id)

        return True

    except Exception as e:
        print("❌ خطأ في update_product_price:", e)
        return False

    finally:
        await conn.close()

async def get_tracking_condition(telegram_id, url):
    user_id = await get_user_id(telegram_id)
    if user_id is None:
        return None

    conn = await get_connection()
    try:
        row = await conn.fetchrow("""
            SELECT t.condition_type FROM tracking t
            JOIN products p ON p.id = t.product_id
            WHERE t.user_id = $1 AND p.url = $2
        """, user_id, url)
        return row["condition_type"] if row else None
    except Exception as e:
        print("❌ خطأ في get_tracking_condition:", e)
        return None
    finally:
        await conn.close()

async def get_target_price(telegram_id, url):
    user_id = await get_user_id(telegram_id)
    if user_id is None:
        return None

    conn = await get_connection()
    try:
        row = await conn.fetchrow("""
            SELECT t.target_price FROM tracking t
            JOIN products p ON p.id = t.product_id
            WHERE t.user_id = $1 AND p.url = $2
        """, user_id, url)
        return row["target_price"] if row else None
    except Exception as e:
        print("❌ خطأ في get_target_price:", e)
        return None
    finally:
        await conn.close()

async def get_user_products(telegram_id):
    user_id = await get_user_id(telegram_id)
    if user_id is None:
        return []

    conn = await get_connection()
    try:
        query = """
            SELECT p.id AS id, p.product_name, p.current_price, p.last_price, p.url,
                   t.condition_type, t.target_price, p.site_name, t.track_type
            FROM products p
            JOIN tracking t ON p.id = t.product_id
            WHERE t.user_id = $1
        """
        rows = await conn.fetch(query, user_id)
        return rows
    except Exception as e:
        print("❌ خطأ في get_user_products:", e)
        return []
    finally:
        await conn.close()

async def is_product_tracked(telegram_id, url):
    user_id = await get_user_id(telegram_id)
    if user_id is None:
        return False

    conn = await get_connection()
    try:
        row = await conn.fetchrow("""
            SELECT 1 FROM tracking t
            JOIN products p ON p.id = t.product_id
            WHERE t.user_id = $1 AND p.url = $2
        """, user_id, url)
        return row is not None
    except Exception as e:
        print("❌ خطأ في is_product_tracked:", e)
        return False
    finally:
        await conn.close()

async def get_product_by_url(telegram_id, url):
    user_id = await get_user_id(telegram_id)
    if user_id is None:
        return None

    conn = await get_connection()
    try:
        row = await conn.fetchrow("""
            SELECT p.product_name, p.current_price, p.site_name, t.target_price
            FROM products p
            JOIN tracking t ON p.id = t.product_id
            WHERE t.user_id = $1 AND p.url = $2
        """, user_id, url)
        return dict(row) if row else None
    except Exception as e:
        print("❌ خطأ في get_product_by_url:", e)
        return None
    finally:
        await conn.close()

async def delete_tracking_by_id(telegram_id, product_id):
    user_id = await get_user_id(telegram_id)
    if user_id is None:
        return False

    conn = await get_connection()
    try:
        result = await conn.execute("""
            DELETE FROM tracking
            WHERE user_id = $1 AND product_id = $2
        """, user_id, product_id)
        return result  
    except Exception as e:
        print("❌ خطأ في delete_tracking_by_id:", e)
        return False
    finally:
        await conn.close()