import os
import time
import threading
import requests
import telebot
from telebot.types import InputMediaPhoto

# Отключаем предупреждения об отключенной проверке SSL в консоли
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# === 1. НАСТРОЙКИ И КЛЮЧИ ===
TELEGRAM_BOT_TOKEN = "8873978933:AAEdC2M2698VW2m8HbT83o0dcgpB9FwbaJA"
ALLOWED_USERS = [5396240649, 5871786421] 
TELEGRAM_CHANNEL_ID = -1001808345159 

VK_API_VERSION = "5.131"
VK_GROUP_ID = "218321182"
VK_USER_TOKEN = "vk1.a.kHVN4iOlUZfKTopqB_bB83XbUE1qQefWbqeFciHe3y0NizfLGKbQEAEaLpkNkQLpJKdZOAM17N6R4oeFcYuLAvEDnQJsAHMgOfr-DE9UTfa98mBJkpEBVRdqNax1WafIfVg223GrOYPoXa7TiJNpxcBHyXzVZj199H6Ux-4LA4wW-fr0UpGgk1KRfGtHDWR3s9iKD7Gu8q-cV9oNh7jsgg"

# --- НАСТРОЙКИ ДЛЯ ПЛАТФОРМЫ МАКС ---
MAX_ACCESS_TOKEN = "f9LHodD0cOJ7M2ZCCithS_gKv6HOMBiyGJTFTx1TPWP8L5H7EkVuaN0XaVMwFS8PLFpzaJRiYf1wbRCXbFZy"
# Железный верифицированный ID твоего канала
MAX_CHANNEL_ID = -73892456761348

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
album_storage = {}
storage_lock = threading.Lock()

# === ШАБЛОНЫ ПОДПИСЕЙ С СЫЛКАМИ ===

TG_FOOTER = """

Заказать вещи 🛍
можно в [боте](https://t.me/poizon_life_bot)🤖 через [менеджера](https://t.me/PoizonLifeRu) или в [МАКС](https://inlnk.ru/NDdGgP)👋
 
[Наши отзывы](https://t.me/poizon_life_reviews) 😍
Адрес: Толубеевский проезд 8к2, офис 1378 📍 всегда ждём в гости ❤️"""

VK_FOOTER = """

Заказать вещи 🛍
можно в боте🤖 t.me/poizon_life_bot через менеджера t.me/PoizonLifeRu box или в МАКС👋 inlnk.ru/NDdGgP
 
Наши отзывы t.me/poizon_life_reviews 😍
Адрес: Толубеевский проезд 8к2, офис 1378 📍 всегда ждём в гости ❤️"""

MAX_FOOTER = """

Заказать вещи 🛍
можно в [боте](https://t.me/poizon_life_bot)🤖 через менеджера в [МАКС](https://inlnk.ru/NDdGgP)👋
 
[Наши отзывы](https://t.me/poizon_life_reviews) 😍
Адрес: Толубеевский проезд 8к2, офис 1378 📍 всегда ждём в гости ❤️"""


# === МЕТОДЫ ДЛЯ РАБОТЫ С МАКС API ===

def upload_photo_to_max(image_url):
    """Загрузка медиафайла на сервера МАКС по официальной схеме"""
    headers = {"Authorization": MAX_ACCESS_TOKEN}
    try:
        upload_init_url = "https://platform-api2.max.ru/uploads?type=image"
        res_init = requests.post(upload_init_url, headers=headers, timeout=15, verify=False).json()
        upload_url = res_init.get("url")
        if not upload_url:
            return None

        photo_data = requests.get(image_url, timeout=15).content
        files = {"data": ("photo.jpg", photo_data, "image/jpeg")}
        res_upload = requests.post(upload_url, files=files, timeout=30, verify=False).json()
        
        token = None
        photos_dict = res_upload.get("photos", {})
        if photos_dict and isinstance(photos_dict, dict):
            for key, val in photos_dict.items():
                if isinstance(val, dict) and "token" in val:
                    token = val["token"]
                    break
        return token
    except Exception:
        return None


def post_to_max(text, tokens=None):
    """Отправка сообщения с вложениями в канал МАКС через Query-параметры URL"""
    url = f"https://platform-api2.max.ru/messages?chat_id={MAX_CHANNEL_ID}"
    headers = {"Authorization": MAX_ACCESS_TOKEN, "Content-Type": "application/json"}
    
    payload = {
        "text": text,
        "format": "markdown"
    }
    
    if tokens:
        attachments = []
        for token in tokens:
            attachments.append({"type": "image", "payload": {"token": token}})
        payload["attachments"] = attachments

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=15, verify=False).json()
        if "message" in res and "body" in res["message"] and "mid" in res["message"]["body"]:
            return True
        print("[МАКС Ошибка публикации]:", res)
        return False
    except Exception:
        return False


# === СТАНДАРТНЫЕ МЕТОДЫ ВК И ТГ ===

def upload_photo_to_vk_wall(image_url):
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            get_server_url = "https://api.vk.com/method/photos.getWallUploadServer"
            params = {"access_token": VK_USER_TOKEN, "v": VK_API_VERSION, "group_id": VK_GROUP_ID}
            server_res = requests.get(get_server_url, params=params, timeout=15).json()
            upload_url = server_res.get("response", {}).get("upload_url")
            if not upload_url:
                continue

            photo_data = requests.get(image_url, timeout=15).content
            files = {'photo': ('photo.jpg', photo_data)}
            upload_res = requests.post(upload_url, files=files, timeout=30).json()
            if not upload_res.get("photo") or upload_res.get("photo") == "[]" or upload_res.get("photo") == "":
                time.sleep(2)
                continue

            save_url = "https://api.vk.com/method/photos.saveWallPhoto"
            save_params = {
                "access_token": VK_USER_TOKEN, "v": VK_API_VERSION, "group_id": VK_GROUP_ID,
                "photo": upload_res.get("photo"), "server": upload_res.get("server"), "hash": upload_res.get("hash")
            }
            save_res = requests.get(save_url, params=save_params, timeout=15).json()
            photo_info = save_res.get("response", [{}])[0]
            owner_id = photo_info.get("owner_id")
            media_id = photo_info.get("id")
            if owner_id and media_id:
                return f"photo{owner_id}_{media_id}"
        except Exception:
            if attempt < max_retries:
                time.sleep(3)
    return None


def post_to_vk_wall(text, attachments=None):
    try:
        url = "https://api.vk.com/method/wall.post"
        payload = {
            "access_token": VK_USER_TOKEN, "v": VK_API_VERSION, "owner_id": f"-{VK_GROUP_ID}",
            "from_group": 1, "signed": 0, "message": text, "primary_attachments_mode": "grid"
        }
        if attachments:
            payload["attachments"] = ",".join(attachments)
        res = requests.post(url, data=payload, timeout=15).json()
        return res.get('response', {}).get('post_id')
    except Exception:
        return None


def post_to_telegram_channel(text, file_ids):
    try:
        if len(file_ids) == 1:
            bot.send_photo(chat_id=TELEGRAM_CHANNEL_ID, photo=file_ids[0], caption=text, parse_mode="Markdown")
            return True
        else:
            media = []
            for i, f_id in enumerate(file_ids):
                if i == 0:
                    media.append(InputMediaPhoto(f_id, caption=text, parse_mode="Markdown"))
                else:
                    media.append(InputMediaPhoto(f_id))
            bot.send_media_group(chat_id=TELEGRAM_CHANNEL_ID, media=media)
            return True
    except Exception:
        return False


# === ОСНОВНАЯ ЛОГИКА СИНХРОНИЗАЦИИ ===

def process_album_and_post(chat_id, media_group_id):
    time.sleep(4.0)  
    with storage_lock:
        if media_group_id not in album_storage:
            return
        data = album_storage[media_group_id]
        if data.get("processed"):
            return
        data["processed"] = True

    base_text = data["text"]
    urls = data["urls"]
    tg_file_ids = data["file_ids"]

    status_msg = bot.send_message(chat_id, "📦 Альбом принят. Запускаю кросспостинг...")

    vk_text = base_text + VK_FOOTER
    tg_text = base_text + TG_FOOTER
    max_text = base_text + MAX_FOOTER

    vk_attachments = []
    for url in urls:
        vk_photo = upload_photo_to_vk_wall(url)
        if vk_photo:
            vk_attachments.append(vk_photo)
        time.sleep(0.6)

    vk_success = False
    vk_post_id = None
    if vk_attachments:
        vk_post_id = post_to_vk_wall(vk_text, attachments=vk_attachments)
        if vk_post_id:
            vk_success = True

    max_tokens = []
    for url in urls:
        max_token = upload_photo_to_max(url)
        if max_token:
            max_tokens.append(max_token)
        time.sleep(0.5)

    if max_tokens:
        time.sleep(2.0)
    max_success = post_to_max(max_text, tokens=max_tokens) if max_tokens else False

    tg_success = post_to_telegram_channel(tg_text, tg_file_ids)

    report = "📊 **Отчет SMM-Комбайна (3 в 1):**\n\n"
    report += f"✅ **ВК:** Опубликован (ID: {vk_post_id})\n" if vk_success else "❌ **ВК:** Ошибка сети.\n"
    report += "✅ **ТГ-Канал:** Опубликован!\n" if tg_success else "❌ **ТГ-Канал:** Ошибка.\n"
    report += "✅ **МАКС:** Опубликован!\n" if max_success else "❌ **МАКС:** Ошибка.\n"

    bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text=report)
    
    with storage_lock:
        if media_group_id in album_storage:
            del album_storage[media_group_id]


@bot.message_handler(content_types=['photo'])
def handle_smm_post(message):
    if message.from_user.id not in ALLOWED_USERS:
        print("[Внимание]: Блокировка доступа")
        return

    text = message.caption if message.caption else ""
    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    telegram_image_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_info.file_path}"

    if message.media_group_id:
        mg_id = message.media_group_id
        with storage_lock:
            if mg_id not in album_storage:
                album_storage[mg_id] = {"text": text, "urls": [], "file_ids": [], "processed": False}
            album_storage[mg_id]["urls"].append(telegram_image_url)
            album_storage[mg_id]["file_ids"].append(file_id)
            if text and not album_storage[mg_id]["text"]:
                album_storage[mg_id]["text"] = text
            is_first = (len(album_storage[mg_id]["urls"]) == 1)
        if is_first:
            threading.Thread(target=process_album_and_post, args=(message.chat.id, mg_id)).start()
    else:
        status_msg = bot.reply_to(message, "⏳ Публикую одиночный пост...")
        vk_text = text + VK_FOOTER
        tg_text = text + TG_FOOTER
        max_text = text + MAX_FOOTER
        
        photo_str = upload_photo_to_vk_wall(telegram_image_url)
        vk_post_id = post_to_vk_wall(vk_text, attachments=[photo_str] if photo_str else None)
        
        max_token = upload_photo_to_max(telegram_image_url)
        if max_token:
            time.sleep(1.5)
        max_success = post_to_max(max_text, tokens=[max_token] if max_token else None)
        
        tg_success = post_to_telegram_channel(tg_text, [file_id])
        
        report = "📊 **Отчет:**\n"
        report += f"✅ ВК: Опубликовано (ID: {vk_post_id})\n" if vk_post_id else "❌ ВК: Ошибка\n"
        report += "✅ ТГ: Опубликовано\n" if tg_success else "❌ ТГ: Ошибка\n"
        report += "✅ МАКС: Опубликовано\n" if max_success else "❌ МАКС: Ошибка\n"
        bot.edit_message_text(chat_id=message.chat.id, message_id=status_msg.message_id, text=report)


if __name__ == "__main__":
    print("[SMM Комбайн]: Полный кросспостинг ВК + ТГ + МАКС запущен...")
    bot.infinity_polling()