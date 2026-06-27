import os
import time
import threading
import requests
import telebot
from telebot.types import InputMediaPhoto
from flask import Flask

# Отключаем предупреждения об отключенной проверке SSL
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# === 1. НАСТРОЙКИ И КЛЮЧИ ===
TELEGRAM_BOT_TOKEN = "8873978933:AAEdC2M2698VW2m8HbT83o0dcgpB9FwbaJA"
ALLOWED_USERS = [5396240649, 5871786421] 
TELEGRAM_CHANNEL_ID = -1001809141014 

VK_API_VERSION = "5.131"
VK_GROUP_ID = "218321182"
VK_USER_TOKEN = "vk1.a.kHVN4iOlUZfKTopqB_bB83XbUE1qQefWbqeFciHe3y0NizfLGKbQEAEaLpkNkQLpJKdZOAM17N6R4oeFcYuLAvEDnQJsAHMgOfr-DE9UTfa98mBJkpEBVRdqNax1WafIfVg223GrOYPoXa7TiJNpxcBHyXzVZj199H6Ux-4LA4wW-fr0UpGgk1KRfGtHDWR3s9iKD7Gu8q-cV9oNh7jsgg"

MAX_ACCESS_TOKEN = "f9LHodD0cOJ7M2ZCCithS_gKv6HOMBiyGJTFTx1TPWP8L5H7EkVuaN0XaVMwFS8PLFpzaJRiYf1wbRCXbFZy"
MAX_CHANNEL_ID = -73892456761348

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
album_storage = {}
storage_lock = threading.Lock()

app = Flask(__name__)

@app.route('/')
def home():
    return "SMM Комбайн активен и работает!", 200

# === ШАБЛОНЫ ПОДПИСЕЙ С СЫЛКАМИ ===
TG_FOOTER = """\n\nЗаказать вещи 🛍\nможно в [боте](https://t.me/poizon_life_bot)🤖 через [менеджера](https://t.me/PoizonLifeRu) или в [МАКС](https://inlnk.ru/NDdGgP)👋\n \n[Наши отзывы](https://t.me/poizon_life_reviews) 😍\nАдрес: Толубеевский проезд 8к2, офис 1378 📍 всегда ждём в гости ❤️"""
VK_FOOTER = """\n\nЗаказать вещи 🛍\nможно в боте🤖 t.me/poizon_life_bot через менеджера t.me/PoizonLifeRu box или в МАКС👋 inlnk.ru/NDdGgP\n \nНаши отзывы t.me/poizon_life_reviews 😍\nАдрес: Толубеевский проезд 8к2, офис 1378 📍 всегда ждём в гости ❤️"""
MAX_FOOTER = """\n\nЗаказать вещи 🛍\nможно в [боте](https://t.me/poizon_life_bot)🤖 через менеджера в [МАКС](https://inlnk.ru/NDdGgP)👋\n \n[Наши отзывы](https://t.me/poizon_life_reviews) 😍\nАдрес: Толубеевский проезд 8к2, офис 1378 📍 всегда ждём в гости ❤️"""

def upload_photo_to_max(image_url):
    headers = {"Authorization": MAX_ACCESS_TOKEN}
    try:
        upload_init_url = "https://platform-api2.max.ru/uploads?type=image"
        res_init = requests.post(upload_init_url, headers=headers, timeout=15, verify=False).json()
        upload_url = res_init.get("url")
        if not upload_url: return None
        photo_data = requests.get(image_url, timeout=15).content
        files = {"data": ("photo.jpg", photo_data, "image/jpeg")}
        res_upload = requests.post(upload_url, files=files, timeout=30, verify=False).json()
        photos_dict = res_upload.get("photos", {})
        if photos_dict and isinstance(photos_dict, dict):
            for key, val in photos_dict.items():
                if isinstance(val, dict) and "token" in val: return val["token"]
        return None
    except Exception: return None

def post_to_max(text, tokens=None):
    url = f"https://platform-api2.max.ru/messages?chat_id={MAX_CHANNEL_ID}"
    headers = {"Authorization": MAX_ACCESS_TOKEN, "Content-Type": "application/json"}
    payload = {"text": text, "format": "markdown"}
    if tokens:
        payload["attachments"] = [{"type": "image", "payload": {"token": t}} for t in tokens]
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=15, verify=False).json()
        if "message" in res and "body" in res["message"] and "mid" in res["message"]["body"]: return True
        return False
    except Exception: return False

def upload_photo_to_vk_wall(image_url):
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            get_server_url = "https://api.vk.com/method/photos.getWallUploadServer"
            server_res = requests.get(get_server_url, params={"access_token": VK_USER_TOKEN, "v": VK_API_VERSION, "group_id": VK_GROUP_ID}, timeout=15).json()
            upload_url = server_res.get("response", {}).get("upload_url")
            if not upload_url: continue
            photo_data = requests.get(image_url, timeout=15).content
            upload_res = requests.post(upload_url, files={'photo': ('photo.jpg', photo_data)}, timeout=30).json()
            if not upload_res.get("photo"):
                time.sleep(2)
                continue
            save_res = requests.get("https://api.vk.com/method/photos.saveWallPhoto", params={"access_token": VK_USER_TOKEN, "v": VK_API_VERSION, "group_id": VK_GROUP_ID, "photo": upload_res.get("photo"), "server": upload_res.get("server"), "hash": upload_res.get("hash")}, timeout=15).json()
            photo_info = save_res.get("response", [{}])[0]
            if photo_info.get("owner_id") and photo_info.get("id"): return f"photo{photo_info['owner_id']}_{photo_info['id']}"
        except Exception:
            if attempt < max_retries: time.sleep(3)
    return None

def post_to_vk_wall(text, attachments=None):
    try:
        payload = {"access_token": VK_USER_TOKEN, "v": VK_API_VERSION, "owner_id": f"-{VK_GROUP_ID}", "from_group": 1, "signed": 0, "message": text, "primary_attachments_mode": "grid"}
        if attachments: payload["attachments"] = ",".join(attachments)
        res = requests.post("https://api.vk.com/method/wall.post", data=payload, timeout=15).json()
        return res.get('response', {}).get('post_id')
    except Exception: return None

def post_to_telegram_channel(text, file_ids):
    try:
        if len(file_ids) == 1:
            bot.send_photo(chat_id=TELEGRAM_CHANNEL_ID, photo=file_ids[0], caption=text, parse_mode="Markdown")
            return True
        media = [InputMediaPhoto(f_id, caption=text, parse_mode="Markdown") if i == 0 else InputMediaPhoto(f_id) for i, f_id in enumerate(file_ids)]
        bot.send_media_group(chat_id=TELEGRAM_CHANNEL_ID, media=media)
        return True
    except Exception as e:
        print(f"!!! Ошибка ТГ: {e}")
        return False

def process_album_and_post(chat_id, media_group_id):
    time.sleep(4.0)  
    with storage_lock:
        if media_group_id not in album_storage or album_storage[media_group_id].get("processed"): return
        data = album_storage[media_group_id]
        data["processed"] = True

    base_text, urls, tg_file_ids = data["text"], data["urls"], data["file_ids"]
    status_msg = bot.send_message(chat_id, "📦 Альбом принят. Запускаю кросспостинг...")

    vk_attachments = [upload_photo_to_vk_wall(u) for u in urls if upload_photo_to_vk_wall(u)]
    vk_post_id = post_to_vk_wall(base_text + VK_FOOTER, attachments=vk_attachments) if vk_attachments else None
    max_tokens = [upload_photo_to_max(u) for u in urls if upload_photo_to_max(u)]
    max_success = post_to_max(base_text + MAX_FOOTER, tokens=max_tokens) if max_tokens else False
    tg_success = post_to_telegram_channel(base_text + TG_FOOTER, tg_file_ids)

    report = f"📊 **Отчет SMM-Комбайна (3 в 1):**\n\n✅ ВК: {f'Опубликован (ID: {vk_post_id})' if vk_post_id else '❌ Ошибка'}\n✅ ТГ-Канал: {'Опубликован!' if tg_success else '❌ Ошибка'}\n✅ МАКС: {'Опубликован!' if max_success else '❌ Ошибка'}"
    bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text=report)
    
    with storage_lock:
        if media_group_id in album_storage: del album_storage[media_group_id]

@bot.message_handler(content_types=['photo'])
def handle_smm_post(message):
    if message.from_user.id not in ALLOWED_USERS: return
    text = message.caption if message.caption else ""
    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    telegram_image_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_info.file_path}"

    if message.media_group_id:
        mg_id = message.media_group_id
        with storage_lock:
            if mg_id not in album_storage: album_storage[mg_id] = {"text": text, "urls": [], "file_ids": [], "processed": False}
            album_storage[mg_id]["urls"].append(telegram_image_url)
            album_storage[mg_id]["file_ids"].append(file_id)
            if text and not album_storage[mg_id]["text"]: album_storage[mg_id]["text"] = text
            is_first = (len(album_storage[mg_id]["urls"]) == 1)
        if is_first: threading.Thread(target=process_album_and_post, args=(message.chat.id, mg_id)).start()
    else:
        status_msg = bot.reply_to(message, "⏳ Публикую одиночный пост...")
        vk_photo = upload_photo_to_vk_wall(telegram_image_url)
        vk_post_id = post_to_vk_wall(text + VK_FOOTER, attachments=[vk_photo] if vk_photo else None)
        max_token = upload_photo_to_max(telegram_image_url)
        max_success = post_to_max(text + MAX_FOOTER, tokens=[max_token] if max_token else None)
        tg_success = post_to_telegram_channel(text + TG_FOOTER, [file_id])
        
        report = f"📊 **Отчет:**\n✅ ВК: {'Опубликовано' if vk_post_id else '❌ Ошибка'}\n✅ ТГ: {'Опубликовано' if tg_success else '❌ Ошибка'}\n✅ МАКС: {'Опубликовано' if max_success else '❌ Ошибка'}"
        bot.edit_message_text(chat_id=message.chat.id, message_id=status_msg.message_id, text=report)

def run_bot_polling():
    try:
        print("[SMM Комбайн]: Сброс сессий и запуск ТГ пуллинга...")
        bot.delete_webhook(drop_pending_updates=True)
        time.sleep(1)
        bot.infinity_polling()
    except Exception as e:
        print(f"[Ошибка]: {e}")

if __name__ == "__main__":
    # Запускаем пуллинг Телеграма в фоне СТРОГО один раз, игнорируя системные дубли gunicorn
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        threading.Thread(target=run_bot_polling, daemon=True).start()
        
    port = int(os.environ.get("PORT", 10000))
    print(f"[Веб-Сервер]: Запуск Flask на порту {port}...")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
