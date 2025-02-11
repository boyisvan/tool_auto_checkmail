from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Config(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_email = db.Column(db.String(120), nullable=False)
    telegram_bot_token = db.Column(db.String(200), nullable=False)
    telegram_admin_chat_id = db.Column(db.String(50), nullable=False)
    check_from_emails = db.Column(db.String(120), nullable=False)

class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    telegram_chat_id = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(50), default="Chưa kiểm tra")  

    def __repr__(self):
        return f'<Account {self.email}>'


class EmailLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    sender = db.Column(db.String(255), nullable=False)
    date_received = db.Column(db.String(50), nullable=False)
    body = db.Column(db.Text, nullable=False)
