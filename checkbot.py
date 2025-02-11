import requests

TOKEN = "7760536676:AAE8HtLbXQSX-BUaT3Jvprtx9QKtkj5lSzs"
chatid = "5405720288"

message = "Xin chao, testbot ducvancoder"

# Sửa URL để không có khoảng trắng thừa
url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={chatid}&text={message}"

# Gửi yêu cầu GET
r = requests.get(url)

# In kết quả trả về
print(r.text)
