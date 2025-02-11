import json
import imaplib
import email
from email.header import decode_header
import requests
import time
import html
import re
# Đọc file cấu hình
with open("config.json", "r", encoding="utf-8") as file:
    config = json.load(file)

# Các thông tin từ file cấu hình
ADMIN_EMAIL = config["admin_email"]
TELEGRAM_BOT_TOKEN = config["telegram_bot_token"]
TELEGRAM_ADMIN_CHAT_ID = config["telegram_admin_chat_id"]
CHECK_FROM_EMAILS = config["check_from_emails"]
ACCOUNTS = config["accounts"]

# Hàm gửi tin nhắn đến Telegram
def send_telegram_message(chat_id, message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # Loại bỏ các thẻ HTML khỏi nội dung tin nhắn
    clean_message = re.sub(r'<[^>]*>', '', message)
    
    # Escape các ký tự đặc biệt trong nội dung tin nhắn
    escaped_message = html.escape(clean_message)
    
    payload = {"chat_id": chat_id, "text": escaped_message, "parse_mode": "HTML"}
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print(f"Lỗi gửi Telegram: {response.json()}")
    except Exception as e:
        print(f"Lỗi khi gửi tin nhắn Telegram: {e}")

# Kết nối đến Gmail
def connect_gmail(account):
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(account["email"], account["password"])
        return mail
    except Exception as e:
        print(f"Không thể kết nối tài khoản {account['email']}: {e}")
        return None

# Lấy thông tin email
def fetch_email_details(mail, email_id):
    res, msg = mail.fetch(email_id, "(RFC822)")
    for response in msg:
        if isinstance(response, tuple):
            msg = email.message_from_bytes(response[1])
            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding if encoding else "utf-8")
            from_ = msg.get("From")
            date = msg.get("Date")
            body = None
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode()
                        break
            else:
                body = msg.get_payload(decode=True).decode()
            return {
                "subject": subject,
                "from": from_,
                "date": date,
                "body": body,
            }
    return None

# Kiểm tra email mới
def check_latest_email(account):
    mail = connect_gmail(account)
    if not mail:
        return

    try:
        mail.select("inbox")
        status, messages = mail.search(None, f'FROM "{CHECK_FROM_EMAILS}"')
        email_ids = messages[0].split()
        if not email_ids:
            print(f"[{account['email']}] Không có thư mới từ {CHECK_FROM_EMAILS}.")
            return

        latest_email_id = email_ids[-1]
        email_details = fetch_email_details(mail, latest_email_id)

        if email_details:
            message = (
                f"<b>Có thư mới từ {CHECK_FROM_EMAILS}:</b>\n"
                f"<b>Người gửi:</b> {email_details['from']}\n"
                f"<b>Tiêu đề:</b> {email_details['subject']}\n"
                f"<b>Thời gian:</b> {email_details['date']}\n"
                f"<b>Nội dung:</b>\n{email_details['body']}"
            )
            send_telegram_message(account["telegram_chat_id"], message)
            print(f"Đã gửi thông báo Telegram cho {account['email']}.")
    except Exception as e:
        print(f"Lỗi khi kiểm tra email: {e}")
    finally:
        mail.logout()

# Kiểm tra thư tự động
def auto_check_inbox(interval=30):
    print("Bắt đầu quét thư... Nhấn Ctrl+C để dừng.")
    try:
        while True:
            for account in ACCOUNTS:
                check_latest_email(account)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nĐã dừng quét thư.")

if __name__ == "__main__":
    auto_check_inbox()
