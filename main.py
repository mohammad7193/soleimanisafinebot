import os
import re
import sys
import hashlib
import requests
from bs4 import BeautifulSoup

# دریافت توکن به صورت ایمن
TOKEN = os.environ.get("BALE_BOT_TOKEN")
CRON_SCHEDULE = os.environ.get("CRON_SCHEDULE", "")
HISTORY_FILE = "hadith_history.txt"

# لیست کامل ۸ گروه
CHAT_IDS = [
    "5608057203", # مربیان سفینه النجاه قشم
    "5460021172", # مربیان غرب هرمزگان
    "5190191521", # هماهنگی طرح برهان
    "5900602024", # مربيان دوره دوم قشم ( سفینة النجاة )
    "5220738339", # سفینه النجات خمیر دوره دو(طرح برهان)
    "4967616984", # ناظمان غرب
    "5867565511", # ناظمان قشم
    "4568712387"  # گروه سفینة النجاه برهان قشم
]

if not TOKEN:
    print("Error: BALE_BOT_TOKEN is not set in GitHub Secrets.")
    sys.exit(1)

BALE_API_URL = f"https://tapi.bale.ai/bot{TOKEN}/sendMessage"

def format_respects(text):
    replacements = {
        r'\s*\(ع\)\s*': ' علیه السلام ',
        r'\s*\(ص\)\s*': ' صلی الله علیه و آله ',
        r'\s*\(س\)\s*': ' سلام الله علیها ',
        r'\s*\(عج\)\s*': ' عجل الله تعالی فرجه الشریف ',
        r'\s*\(ره\)\s*': ' رحمة الله علیه '
    }
    for abbr, full in replacements.items():
        text = re.sub(abbr, full, text)
    return text.strip()

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return set(f.read().splitlines())
    return set()

def save_to_history(identifier):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(identifier + "\n")

def clear_history():
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        f.write("")

def extract_hadith_and_source(soup):
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
    
    if not valid_hadiths:
        raise ValueError("No standard structure found.")
        
    valid_hadiths = list(dict.fromkeys(valid_hadiths))
    history = load_history()
    
    new_hadiths = []
    for body, source in valid_hadiths:
        # ایجاد هش رمزنگاری شده از کل متن حدیث برای دقت 100 درصدی
        identifier = hashlib.md5(body.encode('utf-8')).hexdigest()
        if identifier not in history:
            new_hadiths.append((body, source, identifier))
            
    if not new_hadiths:
        print("All scraped hadiths were used. Clearing history to restart cycle.")
        clear_history()
        selected = valid_hadiths[0]
        identifier = hashlib.md5(selected[0].encode('utf-8')).hexdigest()
        save_to_history(identifier)
        return selected[0], selected[1]
        
    selected = new_hadiths[0]
    save_to_history(selected[2])
    return selected[0], selected[1]

def get_daily_hadith():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get("https://www.hadithlib.com/", headers=headers, timeout=20)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        raw_text, source = extract_hadith_and_source(soup)
        formatted_text = format_respects(raw_text)
        
        if ":" in formatted_text or "：" in formatted_text:
            parts = formatted_text.replace("：", ":").split(":", 1)
            speaker = parts[0].strip()
            body = parts[1].strip()
            return f"☀️ از {speaker} نقل است:\n\n✨ {body}\n\n📚 منبع: {source}"
        else:
            return f"☀️ نقل است:\n\n✨ {formatted_text}\n\n📚 منبع: {source}"
            
    except Exception as e:
        print(f"Error scraping hadith: {e}")
        return "☀️ از امام علی علیه السلام نقل است:\n\n✨ حُسنُ الصُّحبَةِ يَزيدُ في مَحَبَّةِ القُلوبِ.\nخوش‌رفتاری و هم‌نشینی نيکو، محبّت دل‌ها را می‌افزايد.\n\n📚 منبع: غررالحکم، ج ۴، ص ۳۹۵"

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
