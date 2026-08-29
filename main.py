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

def get_daily_hadith():
    fallbacks = [
        "☀️ از امیرالمومنین علیه السلام نقل است:\n\n✨ زَكاةُ العِلمِ نَشرُهُ.\nزكات دانش، نشر آن است.\n\n📚 منبع: غررالحکم، ح ۵۴۵۴",
        "☀️ از پیامبر اکرم صلی الله علیه و آله نقل است:\n\n✨ اِنَّما بُعِثْتُ لِاُتَمِّمَ مَکارِمَ الاَخْلاقِ.\nمن تنها برانگیخته شده‌ام تا اخلاق بزرگوارانه را به کمال رسانم.\n\n📚 منبع: بحارالانوار، ج ۶۸، ص ۳۸۲",
        "☀️ از امیرالمومنین علیه السلام نقل است:\n\n✨ قَدرُ الرَّجُلِ عَلى قَدرِ هِمَّتِهِ.\nارزش هر انسان به اندازه همت اوست.\n\n📚 منبع: نهج البلاغه، حکمت ۴۷",
        "☀️ از امام رضا علیه السلام نقل است:\n\n✨ مَن لَم يَشكُرِ المُنعِمَ مِنَ المَخلوقينَ لَم يَشكُرِ اللّه َ عَزَّوَجَلَّ.\nكسى كه از انسان‌هاى نعمت‌دهنده تشكر نكند، شكر خداوند را به جا نياورده است.\n\n📚 منبع: عیون اخبار الرضا، ج ۲، ص ۲۴",
        "☀️ از امام حسین علیه السلام نقل است:\n\n✨ مَن حَاوَلَ اَمراً بِمَعصِيَةِ اللهِ كانَ اَفوَتَ لِما يَرجُو وَ اَسرَعَ لِمَجِيءِ مَا يَحذَرُ.\nكسى كه با نافرمانى خدا بخواهد به كارى برسد، آنچه را اميد دارد زودتر از دست مى‌دهد و آنچه را بيم دارد زودتر به سراغش مى‌آيد.\n\n📚 منبع: بحارالانوار، ج ۷۵، ص ۱۲۰",
        "☀️ از امیرالمومنین علیه السلام نقل است:\n\n✨ حُسنُ الخُلقِ يُوجِبُ المَحَبَّةَ وَ يُؤَكِّدُ المَوَدَّةَ.\nخوش‌خويى، محبّت مى‌آورد و دوستى را استوار مى‌سازد.\n\n📚 منبع: غررالحکم، ح ۴۸۶۴",
        "☀️ از امام صادق علیه السلام نقل است:\n\n✨ كَمالُ الاَدَبِ وَالمُروءَةِ سَبعُ خِصالٍ: اَلعَقلُ وَ الحِلمُ ، وَالصَّبرُ ، وَالرِّفقُ ، وَالصَّمتُ ، وَحُسنُ الخُلقِ ، وَ المُداراةُ.\nكمال ادب و مروّت در هفت چيز است: عقل، بردبارى، صبر، مدارا، سكوت، خوش‌خويى و سازش.\n\n📚 منبع: معدن الجواهر، ص ۵۹"
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
        
        if valid_hadiths:
            selected = valid_hadiths[0]
            formatted_text = format_respects(selected[0])
            source = selected[1]
            if ":" in formatted_text or "：" in formatted_text:
                parts = formatted_text.replace("：", ":").split(":", 1)
                speaker = parts[0].strip()
                body = parts[1].strip()
                return f"☀️ از {speaker} نقل است:\n\n✨ {body}\n\n📚 منبع: {source}"
            else:
                return f"☀️ نقل است:\n\n✨ {formatted_text}\n\n📚 منبع: {source}"
        
        raise ValueError("No standard structure found.")
            
    except Exception as e:
        print(f"Error scraping: {e}")
        # بر اساس شماره روز در سال می‌چرخد تا هرگز پیام تکراری نفرستد
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
    if CRON_SCHEDULE == '30 6 * * *':
        send_message(get_daily_hadith())
    elif CRON_SCHEDULE == '30 8 * * 2,5':
        send_message("سلام یادآوری برگزاری کلاس 📚🏫")
    elif CRON_SCHEDULE == '30 10 * * 2,5':
        send_message("سلام یادآوری ثبت گزارش کلاس در سامانه تاک 📝💻")
    elif CRON_SCHEDULE == '30 12 * * 2,5':
        send_message("یادآوری ارسال گزارش متنی و تصویری از برگزاری کلاس در گروه 📸💬")
    else:
        send_message(get_daily_hadith())

if __name__ == "__main__":
    main()
