from flask import Flask, render_template, request, redirect, flash, url_for
from models import db, Config, Account, EmailLog
from utils import send_telegram_message, connect_gmail, fetch_email_details
import os
import requests
import time
import html
import re
import threading

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///email_tool.db"
app.config["SECRET_KEY"] = "check_email_tool" 
db.init_app(app)


def send_telegram_message(chat_id, message):
    config = Config.query.first()
    if not config or not config.telegram_bot_token:
        print("Không tìm thấy Telegram Bot Token trong cấu hình.")
        return
    
    telegram_bot_token = config.telegram_bot_token
    url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
    clean_message = re.sub(r'<[^>]*>', '', message)
    escaped_message = html.escape(clean_message)
    
    payload = {"chat_id": chat_id, "text": escaped_message, "parse_mode": "HTML"}
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print(f"Lỗi gửi Telegram: {response.json()}")
    except Exception as e:
        print(f"Lỗi khi gửi tin nhắn Telegram: {e}")
        
@app.route("/", methods=["GET", "POST"])
def index():
    config = Config.query.first()

    if request.method == "POST":
        config.admin_email = request.form["admin_email"]
        config.telegram_bot_token = request.form["telegram_bot_token"]
        config.telegram_admin_chat_id = request.form["telegram_admin_chat_id"]
        config.check_from_emails = request.form["check_from_emails"]
        
        db.session.commit()
        flash("Cấu hình đã được lưu.", "success")
        
    return render_template("index.html", config=config)


@app.route("/accounts")
def accounts():
    accounts = Account.query.all()
    return render_template("accounts.html", accounts=accounts)

@app.route("/logs")
def logs():
    logs = EmailLog.query.order_by(EmailLog.id.desc()).all()
    return render_template("logs.html", logs=logs)

@app.route("/run_tool_page")
def run_tool_page():
    return render_template("run_tool.html")

@app.route("/run_tool", methods=["POST"])
def run_tool():
    config = Config.query.first()
    if not config:
        flash("Cấu hình chưa đầy đủ.", "danger")
        return redirect(url_for("index"))

    accounts = Account.query.all()
    if not accounts:
        flash("Không có tài khoản nào để kiểm tra.", "danger")
        return redirect(url_for("accounts"))

    for account in accounts:
        mail = connect_gmail(account.email, account.password)
        if not mail:
            flash(f"Không thể kết nối tài khoản {account.email}.", "danger")
            continue
        
        mail.select("inbox")
        status, messages = mail.search(None, f'FROM "{config.check_from_emails}"')
        email_ids = messages[0].split()
        
        if email_ids:
            latest_email_id = email_ids[-1]
            email_details = fetch_email_details(mail, latest_email_id)

            existing_log = EmailLog.query.filter_by(
                account_email=account.email,
                subject=email_details["subject"],
                sender=email_details["from"],
                date_received=email_details["date"]
            ).first()

            if existing_log:
                print(f"Đã tồn tại email từ {email_details['from']} với tiêu đề '{email_details['subject']}'.")
                continue
            
            log = EmailLog(
                account_email=account.email,
                subject=email_details["subject"],
                sender=email_details["from"],
                date_received=email_details["date"],
                body=email_details["body"]
            )
            db.session.add(log)
            db.session.commit()
            message = (
                f"<b>Có thư mới từ {config.check_from_emails}:</b>\n"
                f"<b>Đến :</b> {account.email}\n"
                f"<b>Người gửi:</b> {email_details['from']}\n"
                f"<b>Tiêu đề:</b> {email_details['subject']}\n"
                f"<b>Thời gian:</b> {email_details['date']}\n"
                f"<b>Nội dung:</b>\n{email_details['body']}"
            )
            send_telegram_message(account.telegram_chat_id, message)
        else:
            flash(f"Không có thư mới từ {config.check_from_emails}.", "info")

    flash("Đã hoàn thành kiểm tra email.", "success")
    return redirect(url_for("logs"))



@app.route("/save_config", methods=["POST"])
def save_config():
    config = Config.query.first()
    if not config:
        config = Config()

    config.admin_email = request.form.get("admin_email", "")
    config.telegram_bot_token = request.form.get("telegram_bot_token", "")
    config.telegram_admin_chat_id = request.form.get("telegram_admin_chat_id", "")
    config.check_from_emails = request.form.get("check_from_emails", "")
    db.session.add(config)
    db.session.commit()

    flash("Cấu hình đã được lưu.", "success")
    return redirect(url_for("index"))

@app.route("/add_account", methods=["POST"])
def add_account():
    email = request.form["email"]
    password = request.form["password"]
    telegram_chat_id = request.form["telegram_chat_id"]
    new_account = Account(email=email, password=password, telegram_chat_id=telegram_chat_id)
    db.session.add(new_account)
    db.session.commit()

    flash("Tài khoản đã được thêm thành công!", "success")
    return redirect(url_for("accounts"))

def get_check_from_email():
    config = Config.query.first()  
    if config:
        return config.check_from_emails
    else:
        return None  
def check_account_status(account):
    check_from_emails = get_check_from_email()
    if not check_from_emails:
        return "Không có email cần kiểm tra trong cấu hình."

    mail = connect_gmail(account.email, account.password)
    if not mail:
        return "Không thể kết nối"

    try:
        mail.select("inbox")
        status, messages = mail.search(None, f'FROM "{check_from_emails}"')  
        email_ids = messages[0].split()
        if email_ids:
            return "Hoạt động"
        else:
            return "Không hoạt động"
    except Exception as e:
        return "Lỗi khi quét thư: " + str(e)
    finally:
        mail.logout()

@app.route("/check_account_status/<int:account_id>")
def check_account_status_route(account_id):
    account = Account.query.get(account_id)
    if account:
        status = check_account_status(account)
        account.status = status 
        db.session.commit()  
        flash(f"Trạng thái tài khoản {account.email}: {status}", "info")
    return redirect(url_for("accounts"))

@app.route("/delete_account", methods=["POST"])
def delete_account():
    account_id = request.form.get("account_id")
    account = Account.query.get(account_id)
    if account:
        try:
            db.session.delete(account)
            db.session.commit()
            flash(f"Tài khoản {account.email} đã được xóa!", "success")
        except Exception as e:
            db.session.rollback()  
            flash(f"Không thể xóa tài khoản: {str(e)}", "danger")
    else:
        flash("Tài khoản không tồn tại!", "danger")

    return redirect(url_for("accounts"))

def periodic_email_check():
    """Hàm kiểm tra email định kỳ"""
    with app.app_context():
        while True:
            config = Config.query.first()
            if not config:
                print("Cấu hình chưa đầy đủ.")
                time.sleep(20)
                continue

            accounts = Account.query.all()
            configs = Config.query.all()
            if not accounts:
                print("Không có tài khoản nào để kiểm tra.")
                time.sleep(20)
                continue

            for account in accounts:
                mail = connect_gmail(account.email, account.password)
                if not mail:
                    print(f"Không thể kết nối tài khoản {account.email}.")
                    continue

                mail.select("inbox")
                status, messages = mail.search(None, f'FROM "{config.check_from_emails}"')
                email_ids = messages[0].split()

                if email_ids:
                    latest_email_id = email_ids[-1]
                    email_details = fetch_email_details(mail, latest_email_id)
                    existing_log = EmailLog.query.filter_by(
                        account_email=account.email,
                        subject=email_details["subject"],
                        sender=email_details["from"],
                        date_received=email_details["date"]
                    ).first()

                    if existing_log:
                        print(f"Email từ {email_details['from']} đã tồn tại, bỏ qua.")
                        continue

                    log = EmailLog(
                        account_email=account.email,
                        subject=email_details["subject"],
                        sender=email_details["from"],
                        date_received=email_details["date"],
                        body=email_details["body"]
                    )
                    db.session.add(log)
                    db.session.commit()
                    message = (
                        f"<b>Có thư mới từ {config.check_from_emails}:</b>\n"
                        f"<b>Người gửi:</b> {email_details['from']}\n"
                        f"<b>Tiêu đề:</b> {email_details['subject']}\n"
                        f"<b>Thời gian:</b> {email_details['date']}\n"
                        f"<b>Nội dung:</b>\n{email_details['body']}"
                    )
                    send_telegram_message(account.telegram_chat_id, message)
                    send_telegram_message(configs.telegram_admin_chat_id, message)
                else:
                    print(f"Không có thư mới từ {config.check_from_emails}.")
            time.sleep(20)


@app.route('/delete_log/<int:log_id>', methods=['POST'])
def delete_log(log_id):
    log = EmailLog.query.get_or_404(log_id)
    try:
        db.session.delete(log)
        db.session.commit()
        flash('Log đã được xóa thành công!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Có lỗi xảy ra khi xóa log.', 'danger')
        print(e)
    return redirect(url_for('logs'))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()  
        if not Config.query.first():
            config = Config(
                admin_email="admin@gmail.com",
                telegram_bot_token="",
                telegram_admin_chat_id="",
                check_from_emails=""
            )
            db.session.add(config)
            db.session.commit()

    email_check_thread = threading.Thread(target=periodic_email_check)
    email_check_thread.daemon = True
    email_check_thread.start()

    app.run(debug=True)
    
    
    
    