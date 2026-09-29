import os
import re
import sys
import hashlib
import requests
from bs4 import BeautifulSoup

TOKEN = os.environ.get("BALE_BOT_TOKEN")
CRON_SCHEDULE = os.environ.get("CRON_SCHEDULE", "")
HISTORY_FILE = "hadith_history.txt"

# افزایش حافظه به ۵۰ حدیث اخیر
MAX_HISTORY = 50

CHAT_IDS = [
    "5608057203", "5460021172", "5190191521", "5900602024", 
    "5220738339", "4967616984", "5867565511", "4568712387"
]

if not TOKEN:
    print("Error: BALE_BOT_TOKEN is not set.")
    sys.exit(1)

BALE_MESSAGE_URL = f"https://tapi.bale.ai/bot{TOKEN}/sendMessage"
BALE_PHOTO_URL = f"https://tapi.bale.ai/bot{TOKEN}/sendPhoto"

def format_respects(text):
    """جایگزینی حروف اختصاری، اصلاح نام معصومین و حذف واژگان نامناسب سازمانی"""
    replacements = {
        r'\s*\(ع\)\s*': ' علیه السلام ',
        r'\s*\(ص\)\s*': ' صلی الله علیه و آله ',
        r'\s*\(س\)\s*': ' سلام الله علیها ',
        r'\s*\(عج\)\s*': ' عجل الله تعالی فرجه الشریف ',
        r'\s*\(ره\)\s*': ' رحمة الله علیه ',
        r'امام\s+علی': 'امیرالمومنین',
        r'عشق': 'محبت',
        r'عاشقی': 'دلدادگی'
    }
    for abbr, full in replacements.items():
        text = re.sub(abbr, full, text)
    return text.strip()

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return f.read().splitlines()
    return []

def save_to_history(identifier):
    history = load_history()
    history.append(identifier)
    
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]
        
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        for item in history:
            f.write(item + "\n")

def extract_from_hadisgraph():
    """جستجو در ۵ صفحه اول سایت برای پیدا کردن احادیث متنوع و ایجاد استخر بزرگ"""
    valid_items = []
    
    for page in range(1, 6):
        try:
            url = f"https://hadisgraph.com/page/{page}/" if page > 1 else "https://hadisgraph.com/"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            res = requests.get(url, headers=headers, timeout=15)
            
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                # پیدا کردن تمام تصاویر آپلود شده در سایت
                for img in soup.find_all('img'):
                    src = img.get('src', '')
                    alt = img.get('alt', '')
                    
                    # فیلتر کردن تصاویر: فقط مواردی که مربوط به حدیث است (لوگو و آیکون نباشد)
                    if 'uploads' in src and len(alt) > 15:
                        valid_items.append((alt, src))
        except Exception as e:
            print(f"Error fetching page {page}: {e}")
            
    return valid_items

def get_new_hadith():
    items = extract_from_hadisgraph()
    if not items:
        raise ValueError("هیچ حدیث و تصویری در سایت یافت نشد.")
        
    # حذف موارد کاملا تکراری درون خود سایت
    items = list(dict.fromkeys(items))
    history = set(load_history())
    
    new_items = []
    for text, img_url in items:
        # ایجاد هش رمزنگاری شده بر اساس آدرس تصویر برای جلوگیری از تکرار
        identifier = hashlib.md5(img_url.encode('utf-8')).hexdigest()
        if identifier not in history:
            new_items.append((text, img_url, identifier))
    
    if not new_items:
        # اگر به احتمال یک در میلیون هر ۵ صفحه سایت در ۵۰ تای اخیر تکراری بود
        print("تمام احادیث ۵ صفحه اخیر قبلا ارسال شده‌اند. بازنشانی تاریخچه...")
        open(HISTORY_FILE, "w").close() 
        selected = (items[0][0], items[0][1], hashlib.md5(items[0][1].encode('utf-8')).hexdigest())
    else:
        # انتخاب اولین حدیثِ کاملاً جدید
        selected = new_items[0]
        
    save_to_history(selected[2])
    
    formatted_text = format_respects(selected[0])
    return formatted_text, selected[1]

def send_message(text):
    for chat_id in CHAT_IDS:
        try:
            payload = {"chat_id": chat_id, "text": text}
            res = requests.post(BALE_MESSAGE_URL, json=payload, timeout=10)
            res.raise_for_status()
            print(f"Message sent to {chat_id}")
        except Exception as e:
            print(f"Failed to send message to {chat_id}: {e}")

def send_photo(text, image_url):
    try:
        # دانلود تصویر اصلی با کیفیت بالا
        headers = {'User-Agent': 'Mozilla/5.0'}
        img_res = requests.get(image_url, headers=headers, timeout=15)
        img_res.raise_for_status()
    except Exception as e:
        print(f"Failed to download image: {e}")
        # اگر دانلود تصویر خطا داد، فقط متن را ارسال می‌کند تا گروه خالی نماند
        send_message(text)
        return

    for chat_id in CHAT_IDS:
        try:
            files = {'photo': ('image.jpg', img_res.content, 'image/jpeg')}
            data = {'chat_id': chat_id, 'caption': text}
            res = requests.post(BALE_PHOTO_URL, data=data, files=files, timeout=20)
            res.raise_for_status()
            print(f"Photo sent to {chat_id}")
        except Exception as e:
            print(f"Failed to send photo to {chat_id}: {e}")

def main():
    if CRON_SCHEDULE == '30 6 * * 3,6':
        # ارسال حدیث متنی به همراه عکس در شنبه و چهارشنبه
        try:
            text, img_url = get_new_hadith()
            msg = f"☀️ نقل است:\n\n✨ {text}"
            send_photo(msg, img_url)
        except Exception as e:
            print(f"Error fetching hadith: {e}")
            
    elif CRON_SCHEDULE == '30 8 * * 6':
        # ارسال یادآوری‌های کلاسی فقط در روز شنبه
        send_message("سلام یادآوری ثبت گزارش کلاس در سامانه تاک 📝💻")
        send_message("یادآوری ارسال گزارش متنی و تصویری از برگزاری کلاس در گروه 📸💬")
        
    else:
        # برای اجرای دستی تست در گیت‌هاب اکشنز
        try:
            text, img_url = get_new_hadith()
            send_photo(f"☀️ نقل است:\n\n✨ {text}", img_url)
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
