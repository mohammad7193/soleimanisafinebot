import os
import re
import sys
import requests
from bs4 import BeautifulSoup

TOKEN = os.environ.get("BALE_BOT_TOKEN")
CRON_SCHEDULE = os.environ.get("CRON_SCHEDULE", "")
CHAT_IDS = ["5608057203", "5460021172"]

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
        r'\s*\(ره\)\s*': ' رحمة الله علیه '
    }
    for abbr, full in replacements.items():
        text = re.sub(abbr, full, text)
    return text.strip()

def extract_hadith_and_source(soup):
    elements = soup.find_all(string=re.compile("حدیث روز"))
    for el in elements:
        parent = el.find_parent("div") or el.find_parent("p")
        if parent:
            text = parent.get_text(separator="\n", strip=True)
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            if len(lines) >= 3:
                source = lines[-1]
                body = " ".join(lines[1:-1])
                if re.search(r'(ج\s*\d+|ص\s*\d+|بحار|کافی|وسایل|میزان)', source):
                    return body, source
    
    paras = soup.find_all('p')
    for p in paras:
        text = p.get_text(separator="\n", strip=True)
        if "علیه السلام" in text or "صلی الله" in text or ":" in text:
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            if len(lines) > 1:
                source = lines[-1]
                body = " ".join(lines[:-1])
                if len(source) < 100: 
                    return body, source
    raise ValueError("Could not find standard structure.")

def get_daily_hadith():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get("https://www.hadithlib.com/", headers=headers, timeout=15)
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
        return "☀️ از پیامبر اکرم صلی الله علیه و آله نقل است:\n\n✨ اِنَّما بُعِثْتُ لِاُتَمِّمَ مَکارِمَ الاَخْلاقِ.\nمن تنها برانگیخته شده‌ام تا اخلاق بزرگوارانه را به کمال رسانم.\n\n📚 منبع: بحارالانوار، ج ۶۸، ص ۳۸۲"

def send_message(text):
    if not text: return
    for chat_id in CHAT_IDS:
        try:
            payload = {"chat_id": chat_id, "text": text}
            res = requests.post(BALE_API_URL, json=payload, timeout=10)
            res.raise_for_status()
            print(f"Sent to {chat_id}")
        except Exception as e:
            print(f"Failed {chat_id}: {e}")

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
