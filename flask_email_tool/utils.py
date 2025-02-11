import requests
import imaplib
import email
from email.header import decode_header

def send_telegram_message(bot_token, chat_id, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print(f"Lỗi gửi Telegram: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"Lỗi khi gửi tin nhắn Telegram: {e}")
        return None

# Hàm kết nối Gmail
def connect_gmail(email_address, email_password):
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(email_address, email_password)
        return mail
    except Exception as e:
        print(f"Không thể kết nối tới tài khoản {email_address}: {e}")
        return None

# Hàm lấy thông tin email
def fetch_email_details(mail, email_id):
    try:
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
    except Exception as e:
        print(f"Lỗi khi lấy thông tin email: {e}")
    return None
