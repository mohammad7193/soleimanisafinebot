import os
import re
import sys
import datetime
import requests
from bs4 import BeautifulSoup

TOKEN = os.environ.get("BALE_BOT_TOKEN")
CRON_SCHEDULE = os.environ.get("CRON_SCHEDULE", "")

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
    print("Error: BALE_BOT_TOKEN is not set.")
    sys.exit(1)

BALE_API_URL = f"https://tapi.bale.ai/bot{TOKEN}/sendMessage"

def format_respects(text):
    """جایگزینی حروف اختصاری با عبارات احترام کامل"""
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
    """استخراج تمام احادیث صفحه و انتخاب چرخشی بر اساس تقویم"""
    valid_hadiths = []
    
    # جستجو در تمام تگ‌های پاراگراف و دایو صفحه برای پیدا کردن هر محتوایی که شبیه حدیث است
    containers = soup.find_all(['p', 'div'])
    
    for c in containers:
        text = c.get_text(separator="\n", strip=True)
        # اگر کلمات کلیدی حدیث را داشت
        if any(keyword in text for keyword in ["علیه السلام", "صلی الله", "نقل است", "قال"]):
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            # معمولاً خط آخر منبع است و خطوط قبلی متن حدیث
            if len(lines) >= 2:
                source = lines[-1]
                body = " ".join(lines[:-1])
                
                # یک اعتبارسنجی منطقی: طول منبع خیلی طولانی نباشد و متن اصلی هم خیلی کوتاه نباشد
                if len(source) < 150 and len(body) > 20:
                    valid_hadiths.append((body, source))
    
    if not valid_hadiths:
        raise ValueError("هیچ ساختار استانداردی برای حدیث در صفحه یافت نشد.")
        
    # حذف موارد کاملاً تکراری از لیستی که جمع‌آوری کردیم
    valid_hadiths = list(dict.fromkeys(valid_hadiths))
    
    # ترفند ضد تکرار: استفاده از شماره روز در سال برای گردش در لیست احادیث
    # به این ترتیب هر روز یک ایندکس جدید خوانده می‌شود، حتی اگر سایت آپدیت نشده باشد
    day_of_year = datetime.datetime.now().timetuple().tm_yday
    selected_index = day_of_year % len(valid_hadiths)
    
    return valid_hadiths[selected_index]

def get_daily_hadith():
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        # تایم‌اوت را کمی بالاتر می‌بریم تا سایت‌های ایرانی بهتر لود شوند
        response = requests.get("https://www.hadithlib.com/", headers=headers, timeout=20)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        raw_text, source = extract_hadith_and_source(soup)
        formatted_text = format_respects(raw_text)
        
        # فرمت‌بندی نهایی خروجی
        if ":" in formatted_text or "：" in formatted_text:
            parts = formatted_text.replace("：", ":").split(":", 1)
            speaker = parts[0].strip()
            body = parts[1].strip()
            return f"☀️ از {speaker} نقل است:\n\n✨ {body}\n\n📚 منبع: {source}"
        else:
            return f"☀️ نقل است:\n\n✨ {formatted_text}\n\n📚 منبع: {source}"
            
    except Exception as e:
        print(f"Error scraping hadith: {e}")
        # در صورتی که کلاً سایت قطع باشد، این حدیث خوانده می‌شود
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
        # حالت تست دستی
        send_message(get_daily_hadith())

if __name__ == "__main__":
    main()
