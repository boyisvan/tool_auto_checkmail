import imaplib
import email
from email.header import decode_header
import time

EMAIL = "ducvan05102002@gmail.com"
PASSWORD = "qusoruyluwruzplm"

# Biến lưu trữ ID của thư mới nhất đã xử lý
last_email_id = None
last_email_info = None  # Lưu thông tin thư trước đó

def connect_gmail():
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL, PASSWORD)
        return mail
    except Exception as e:
        print(f"Không thể kết nối Gmail: {e}")
        return None

def fetch_email_details(mail, email_id):
    """Lấy thông tin chi tiết của một email theo ID."""
    res, msg = mail.fetch(email_id, "(RFC822)")
    for response in msg:
        if isinstance(response, tuple):
            msg = email.message_from_bytes(response[1])
            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding if encoding else "utf-8")
            from_ = msg.get("From")
            date = msg.get("Date")  # Thời gian nhận thư

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

def check_latest_email():
    global last_email_id, last_email_info

    mail = connect_gmail()
    if not mail:
        return

    mail.select("inbox")

    # Tìm kiếm thư từ địa chỉ "khan051002@gmail.com"
    status, messages = mail.search(None, 'FROM "khan051002@gmail.com"')
    email_ids = messages[0].split()

    if len(email_ids) == 0:
        print("Không có thư mới từ khan051002@gmail.com.")
        if last_email_info:
            print("\nThông tin thư trước đó:")
            print(f"Người gửi: {last_email_info['from']}")
            print(f"Tiêu đề: {last_email_info['subject']}")
            print(f"Thời gian nhận: {last_email_info['date']}")
            print(f"Nội dung:\n{last_email_info['body']}")
    else:
        latest_email_id = email_ids[-1]  # ID của email mới nhất

        if latest_email_id != last_email_id:
            # Có thư mới
            last_email_id = latest_email_id
            last_email_info = fetch_email_details(mail, latest_email_id)
            print("\n=== CÓ THƯ MỚI ===")
            print(f"Người gửi: {last_email_info['from']}")
            print(f"Tiêu đề: {last_email_info['subject']}")
            print(f"Thời gian nhận: {last_email_info['date']}")
            print(f"Nội dung:\n{last_email_info['body']}")
        else:
            # Không có thư mới
            print("\nChưa có thư mới.")
            if last_email_info:
                print("\nThông tin thư trước đó:")
                print(f"Người gửi: {last_email_info['from']}")
                print(f"Tiêu đề: {last_email_info['subject']}")
                print(f"Thời gian nhận: {last_email_info['date']}")
                print(f"Nội dung:\n{last_email_info['body']}")

    mail.logout()

def auto_check_inbox(interval=30):
    print("Bắt đầu quét thư... Nhấn Ctrl+C để dừng.")
    try:
        while True:
            check_latest_email()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nĐã dừng quét thư.")

if __name__ == "__main__":
    auto_check_inbox()
