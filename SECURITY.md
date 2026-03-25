# 🔒 Hướng dẫn bảo mật API

## API Key Authentication

### Cách hoạt động
- API key tự tạo ngẫu nhiên khi chạy lần đầu
- Lưu tại `data/api_key.txt` trên server
- **Mọi request** phải kèm key, không có → **403 Unauthorized**

### Gửi API Key

**Header (khuyên dùng):**
```bash
curl -H "X-API-Key: YOUR_KEY" http://79.108.225.33:8888/api/all
```

**Query param (nhanh, ít bảo mật hơn):**
```
http://79.108.225.33:8888/api/all?key=YOUR_KEY
```

**JavaScript:**
```javascript
fetch("http://79.108.225.33:8888/api/all", {
  headers: { "X-API-Key": "YOUR_KEY" }
})
```

**Python:**
```python
import requests
r = requests.get("http://79.108.225.33:8888/api/all",
    headers={"X-API-Key": "YOUR_KEY"})
```

---

## CORS Whitelist

Chỉ các domain sau được gọi API từ browser:

| Domain | Mô tả |
|--------|-------|
| `https://khanhwiee.site` | Website chính |
| `https://khanh-vy-portfolio-production.up.railway.app` | Railway deploy |
| `https://khanhvy719.github.io` | GitHub Pages |
| `http://localhost:3000` | Dev local |
| `http://localhost:5173` | Vite dev |
| `http://127.0.0.1:5500` | Live Server |

### Thêm domain mới
Sửa `ALLOWED_ORIGINS` trong `node1_api.py`:
```python
ALLOWED_ORIGINS = [
    "https://khanhwiee.site",
    "https://your-new-domain.com",  # ← thêm ở đây
]
```

---

## Quản lý API Key

```bash
# Xem key hiện tại
cat data/api_key.txt

# Tạo key mới (xóa file cũ → restart)
rm data/api_key.txt
pm2 restart node1-api
cat data/api_key.txt  # Key mới

# Đặt key tùy chọn
echo "my_custom_secret_key_123" > data/api_key.txt
pm2 restart node1-api
```

---

## Lưu ý bảo mật

| ⚠️ | Lưu ý |
|----|-------|
| 🔑 | **Không commit** `data/api_key.txt` lên GitHub (đã có `.gitignore`) |
| 🌐 | Dùng **header** thay vì query param — param lộ trong log/URL bar |
| 🔄 | Đổi key định kỳ bằng cách xóa file + restart |
| 🚫 | Không chia sẻ key qua kênh không mã hóa |
| 🛡️ | Nên dùng **HTTPS** (reverse proxy Nginx + Let's Encrypt) |

---

## Setup HTTPS (khuyến nghị)

```bash
# Cài Nginx + Certbot
apt install -y nginx certbot python3-certbot-nginx

# Cấu hình reverse proxy
cat > /etc/nginx/sites-available/tiktok-api << 'EOF'
server {
    server_name 79.108.225.33;  # hoặc domain

    location / {
        proxy_pass http://127.0.0.1:8888;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_buffering off;
    }
}
EOF

ln -s /etc/nginx/sites-available/tiktok-api /etc/nginx/sites-enabled/
nginx -t && systemctl restart nginx

# SSL (nếu có domain)
certbot --nginx -d your-domain.com
```
