import os
import re
import sys
import hashlib
import datetime
import requests
from bs4 import BeautifulSoup

TOKEN = os.environ.get("BALE_BOT_TOKEN")
CRON_SCHEDULE = os.environ.get("CRON_SCHEDULE", "")
HISTORY_FILE = "hadith_history.txt"
MAX_HISTORY = 30

CHAT_IDS = [
    "5608057203", "5460021172", "5190191521", "5900602024", 
    "5220738339", "4967616984", "5867565511", "4568712387"
]

if not TOKEN:
    print("Error: BALE_BOT_TOKEN is not set.")
    sys.exit(1)

BALE_API_URL = f"https://tapi.bale.ai/bot{TOKEN}/sendMessage"

def format_respects(text):
    replacements = {
        r'\s*\(ع\)\s*': ' علیه السلام ',
        r'\s*\(ص\)\s*': ' صلی الله علیه و آله ',
        r'\s*\(س\)\s*': ' سلام الله علیها ',
        r'\s*\(عج\)\s*': ' عجل الله تعالی فرجه الشریف ',
        r'\s*\(ره\)\s*': ' رحمة الله علیه ',
        r'امام\s+علی': 'امیرالمومنین'
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
    
    # نگه داشتن فقط ۳۰ شناسه آخر
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]
        
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        for item in history:
            f.write(item + "\n")

def get_daily_hadith():
    fallbacks = [
        "☀️ از امیرالمومنین علیه السلام نقل است:\n\n✨ زَكاةُ العِلمِ نَشرُهُ.\nزكات دانش، نشر آن است.\n\n📚 منبع: غررالحکم، ح ۵۴۵۴",
        "☀️ از پیامبر اکرم صلی الله علیه و آله نقل است:\n\n✨ اِنَّما بُعِثْتُ لِاُتَمِّمَ مَکارِمَ الاَخْلاقِ.\nمن تنها برانگیخته شده‌ام تا اخلاق بزرگوارانه را به کمال رسانم.\n\n📚 منبع: بحارالانوار، ج ۶۸، ص ۳۸۲",
        "☀️ از امیرالمومنین علیه السلام نقل است:\n\n✨ قَدرُ الرَّجُلِ عَلى قَدرِ هِمَّتِهِ.\nارزش هر انسان به اندازه همت اوست.\n\n📚 منبع: نهج البلاغه، حکمت ۴۷",
        "☀️ از امام رضا علیه السلام نقل است:\n\n✨ مَن لَم يَشكُرِ المُنعِمَ مِنَ المَخلوقينَ لَم يَشكُرِ اللّه َ عَزَّوَجَلَّ.\nكسى كه از انسان‌هاى نعمت‌دهنده تشكر نكند، شكر خداوند را به جا نياورده است.\n\n📚 منبع: عیون اخبار الرضا، ج ۲، ص ۲۴",
        "☀️ از امام حسین علیه السلام نقل است:\n\n✨ مَن حَاوَلَ اَمراً بِمَعصِيَةِ اللهِ كانَ اَفوَتَ لِما يَرجُو وَ اَسرَعَ لِمَجِيءِ مَا يَحذَرُ.\nكسى كه با نافرمانى خدا بخواهد به كارى برسد، آنچه را اميد دارد زودتر از دست مى‌دهد.\n\n📚 منبع: بحارالانوار، ج ۷۵، ص ۱۲۰",
        "☀️ از امیرالمومنین علیه السلام نقل است:\n\n✨ حُسنُ الخُلقِ يُوجِبُ المَحَبَّةَ وَ يُؤَكِّدُ المَوَدَّةَ.\nخوش‌خويى، محبّت مى‌آورد و دوستى را استوار مى‌سازد.\n\n📚 منبع: غررالحکم، ح ۴۸۶۴",
        "☀️ از امیرالمومنین علیه السلام نقل است:\n\n✨ اَلتَّفَكُّرُ يَدعُو إلَى البِرِّ وَ العَمَلِ بِهِ.\nانديشيدن، به نيكى و عمل به آن فرا مى‌خواند.\n\n📚 منبع: کافی، ج ۲، ص ۵۵"
    ]
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get("https://www.hadithlib.com/", headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        valid_hadiths = []
        containers = soup.find_all(['p', 'div'])
        for c in containers:
            text = c.get_text(separator="\n", strip=True)
            if any(keyword in text for keyword in ["علیه السلام", "صلی الله", "نقل است", "قال"]):
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                if len(lines) >= 2:
                    source = lines[-1]
                    body = " ".join(lines[:-1])
                    if len(source) < 150 and len(body) > 20:
                        valid_hadiths.append((body, source))
        
        # حذف موارد تکراری از لیست استخراج‌شده
        valid_hadiths = list(dict.fromkeys(valid_hadiths))
        history = set(load_history())
        
        new_hadiths = []
        for body, source in valid_hadiths:
            identifier = hashlib.md5(body.encode('utf-8')).hexdigest()
            if identifier not in history:
                new_hadiths.append((body, source, identifier))
        
        # اگر تمام احادیث سایت در 30 روز گذشته ارسال شده باشند، ارور می‌دهد تا از لیست جایگزین استفاده شود
        if not new_hadiths:
            raise ValueError("تمام احادیث این صفحه در تاریخچه ۳۰ تایی وجود دارند.")
            
        selected = new_hadiths[0]
        save_to_history(selected[2])
        
        formatted_text = format_respects(selected[0])
        source = selected[1]
        
        if ":" in formatted_text or "：" in formatted_text:
            parts = formatted_text.replace("：", ":").split(":", 1)
            speaker = parts[0].strip()
            body = parts[1].strip()
            return f"☀️ از {speaker} نقل است:\n\n✨ {body}\n\n📚 منبع: {source}"
        else:
            return f"☀️ نقل است:\n\n✨ {formatted_text}\n\n📚 منبع: {source}"
            
    except Exception as e:
        print(f"Fallback triggered due to: {e}")
        day_of_year = datetime.datetime.now().timetuple().tm_yday
        return fallbacks[day_of_year % len(fallbacks)]

def send_message(text):
    if not text: return
    for chat_id in CHAT_IDS:
        try:
            payload = {"chat_id": chat_id, "text": text}
            res = requests.post(BALE_API_URL, json=payload, timeout=10)
            res.raise_for_status()
            print(f"Sent successfully to {chat_id}")
        except Exception as e:
            print(f"Failed to send to {chat_id}: {e}")

def main():
    if CRON_SCHEDULE == '30 6 * * 3,6':
        send_message(get_daily_hadith())
    elif CRON_SCHEDULE == '30 8 * * 6':
        # ارسال دو پیام یادآوری پشت سر هم
        send_message("سلام یادآوری ثبت گزارش کلاس در سامانه تاک 📝💻")
        send_message("یادآوری ارسال گزارش متنی و تصویری از برگزاری کلاس در گروه 📸💬")
    else:
        # برای اجرای دستی تست
        send_message(get_daily_hadith())

if __name__ == "__main__":
    main()
