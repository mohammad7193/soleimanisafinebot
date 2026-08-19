import os
import re
import sys
import requests
from bs4 import BeautifulSoup

# پیکربندی پایه‌ای
TOKEN = os.environ.get("BALE_BOT_TOKEN")
CRON_SCHEDULE = os.environ.get("CRON_SCHEDULE", "")
CHAT_IDS = ["5608057203", "5460021172"]

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

def get_daily_hadith():
    """استخراج حدیث از سایت و فرمت‌بندی آن"""
    try:
        # درخواست به سایت با تایم‌اوت مشخص تا سیستم کرش نکند
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get("https://www.hadithlib.com/", headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # نکته: سلکتورهای HTML بستگی به قالب سایت دارند.
        # در اینجا فرض بر ساختار معمول نمایش احادیث است.
        hadith_box = soup.find('div', class_='hadith-text') or soup.find('p') 
        
        if not hadith_box:
            raise ValueError("محتوای حدیث در صفحه یافت نشد.")
            
        raw_text = hadith_box.get_text(separator=" ", strip=True)
        formatted_text = format_respects(raw_text)
        
        # تلاش برای جداسازی نام معصوم از متن حدیث (در صورتی که با دو نقطه جدا شده باشد)
        if ":" in formatted_text or "：" in formatted_text:
            parts = formatted_text.replace("：", ":").split(":", 1)
            speaker = parts[0].strip()
            hadith_body = parts[1].strip()
            return f"از {speaker} نقل است:\n\n{hadith_body}"
        else:
            # در صورتی که ساختار دو نقطه‌ای نداشت
            return f"نقل است:\n\n{formatted_text}"
            
    except Exception as e:
        print(f"Error in scraping hadith: {e}")
        # دیتای بازگشتی جایگزین برای جلوگیری از توقف سیستم در صورت قطعی سایت مبدأ
        return "از پیامبر اکرم صلی الله علیه و آله نقل است:\n\nاِنَّما بُعِثْتُ لِاُتَمِّمَ مَکارِمَ الاَخْلاقِ.\nمن تنها برانگیخته شده‌ام تا اخلاق بزرگوارانه را به کمال رسانم."

def send_message(text):
    """ارسال پیام به گروه‌های مشخص شده در بله"""
    if not text:
        return

    for chat_id in CHAT_IDS:
        try:
            payload = {
                "chat_id": chat_id,
                "text": text
            }
            res = requests.post(BALE_API_URL, json=payload, timeout=10)
            res.raise_for_status()
            print(f"Successfully sent message to group: {chat_id}")
        except requests.exceptions.RequestException as e:
            print(f"Failed to send message to {chat_id}. Error: {e}")

def main():
    # مسیریابی بر اساس کرون‌جاب گیت‌هاب (زمان‌بندی‌ها)
    if CRON_SCHEDULE == '30 6 * * *':
        # ساعت ۱۰:۰۰ صبح ایران -> ارسال حدیث
        print("Action: Sending Daily Hadith")
        msg = get_daily_hadith()
        send_message(msg)
        
    elif CRON_SCHEDULE == '30 8 * * 2,5':
        # ساعت ۱۲:۰۰ سه‌شنبه و جمعه
        print("Action: Sending Reminder 1")
        send_message("سلام یادآوری برگزاری کلاس")
        
    elif CRON_SCHEDULE == '30 10 * * 2,5':
        # ساعت ۱۴:۰۰ سه‌شنبه و جمعه
        print("Action: Sending Reminder 2")
        send_message("سلام یادآوری ثبت گزارش کلاس در سامانه تاک")
        
    elif CRON_SCHEDULE == '30 12 * * 2,5':
        # ساعت ۱۶:۰۰ سه‌شنبه و جمعه
        print("Action: Sending Reminder 3")
        send_message("یادآوری ارسال گزارش متنی و تصویری از برگزاری کلاس در گروه")
        
    else:
        # برای اجرای دستی (تست)
        print("Manual Run Detected. Executing default daily task (Hadith)...")
        msg = get_daily_hadith()
        send_message(msg)

if __name__ == "__main__":
    main()
