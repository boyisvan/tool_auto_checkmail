import os
import json
import smtplib
import time
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import requests

# Tải cấu hình từ tệp config.json
with open('config.json', 'r') as f:
    config = json.load(f)

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def send_email_notification(sender_email, recipient_email, subject, body):
    """Gửi thông báo qua email."""
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, config['accounts'][0]['password'])
            message = f"Subject: {subject}\n\n{body}"
            server.sendmail(sender_email, recipient_email, message)
    except Exception as e:
        print(f"Không thể gửi email: {e}")

def send_telegram_message(chat_id, message):
    """Gửi thông báo qua Telegram."""
    try:
        url = f"https://api.telegram.org/bot{config['telegram_bot_token']}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message
        }
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Không thể gửi tin nhắn Telegram: {e}")

def check_email(account):
    """Kiểm tra email chưa đọc và gửi thông báo nếu có nội dung phù hợp."""
    creds = Credentials.from_authorized_user_file(f"{account['email']}_token.json", SCOPES)
    service = build('gmail', 'v1', credentials=creds)
    results = service.users().messages().list(userId='me', q="is:unread").execute()
    messages = results.get('messages', [])

    for message in messages:
        msg = service.users().messages().get(userId='me', id=message['id']).execute()
        payload = msg['payload']
        headers = payload.get('headers', [])

        sender = next(h['value'] for h in headers if h['name'] == 'From')
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "(Không có tiêu đề)")
        snippet = msg.get('snippet', '')

        # Kiểm tra nội dung
        if "ABC" in snippet and "khan051002@gmail.com" in sender:
            notify_text = (
                f"📧 Email mới:\n"
                f"Người gửi: {sender}\n"
                f"Tiêu đề: {subject}\n"
                f"Nội dung: {snippet}"
            )

            # Gửi thông báo
            send_telegram_message(account['telegram_chat_id'], notify_text)
            send_telegram_message(config['telegram_admin_chat_id'], notify_text)
            send_email_notification(account['email'], config['admin_email'], "Email mới", notify_text)
            
            # Đánh dấu email đã đọc
            service.users().messages().modify(
                userId='me', id=message['id'], body={'removeLabelIds': ['UNREAD']}
            ).execute()

def main():
    while True:
        for account in config['accounts']:
            check_email(account)
        time.sleep(60) 
        
if __name__ == '__main__':
    main()
