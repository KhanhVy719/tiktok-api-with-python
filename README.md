# 🎵 TikTok 2-Node Data Collection & Streaming System

Hệ thống thu thập và phát nội dung TikTok với kiến trúc 2 node.

## 🏗️ Kiến trúc

```
┌─────────────────────┐     ┌─────────────────────────┐
│  Node 1 (API)       │     │  Node 2 (Worker)        │
│  - Flask web UI     │◄────│  - Scrape TikTok data   │
│  - Video streaming  │     │  - Download thumbnails  │
│  - Slideshow view   │     │  - Extract slideshow    │
│  - :8888            │     │  - Chạy mỗi 5 phút     │
└─────────────────────┘     └─────────────────────────┘
```

- **Node 1**: API Server — phát video qua `yt-dlp` pipe streaming (bypass 403), hiển thị ảnh slideshow
- **Node 2**: Worker — scrape metadata, tải thumbnails, dùng `undetected-chromedriver` + Xvfb lấy ảnh slideshow thật

## ⚡ Tính năng

- 🎬 **Video streaming** trực tiếp không cần tải file (yt-dlp pipe)
- 📷 **Photo slideshow** với nút prev/next chuyển ảnh thật
- 🔄 **Auto-refresh** mỗi 5 phút
- 🛡️ **Bypass anti-bot** bằng undetected-chromedriver
- 📺 **Xvfb support** cho Ubuntu/Linux (headless server)
- 🎨 **Dark theme UI** hiện đại

## 🚀 Cài đặt

### Ubuntu / Linux (Khuyến nghị)

```bash
git clone https://github.com/KhanhVy719/tiktok-api-with-python.git
cd tiktok-api-with-python

# Cài đặt tự động
chmod +x install.sh
./install.sh

# Hoặc cài thủ công:
sudo apt install -y xvfb chromium-browser python3-pip
pip install -r requirements.txt
```

### Windows

```bash
git clone https://github.com/KhanhVy719/tiktok-api-with-python.git
cd tiktok-api-with-python
pip install -r requirements.txt
```

> ⚠️ Windows cần có Chrome (Google Chrome) đã cài sẵn.

## ▶️ Chạy

```bash
# Terminal 1: Worker scraper (chạy nền, scrape mỗi 5 phút)
python node2_worker.py

# Terminal 2: API server
python node1_api.py
```

Truy cập: **http://localhost:8888**

## 📁 Cấu trúc

```
.
├── node1_api.py       # API Server + Web UI
├── node2_worker.py    # Worker scraper
├── install.sh         # Script cài đặt Ubuntu
├── requirements.txt   # Python dependencies
├── cache/             # (auto-created)
│   ├── videos_meta.json
│   ├── thumbnails/
│   └── slideshow/
└── data/
    └── tiktok_cookies.json
```

## 🔧 Cấu hình

Trong `node2_worker.py`:
```python
TARGET_USER = "The_sunflower71"  # Đổi username TikTok
SCRAPE_INTERVAL = 300            # Chu kỳ scrape (giây)
MAX_VIDEOS = 50                  # Số bài tối đa
```

## 📋 API Endpoints

| Endpoint | Mô tả |
|---|---|
| `GET /` | Web UI dashboard |
| `GET /api/videos` | Danh sách tất cả bài đăng |
| `GET /api/video/<id>` | Chi tiết 1 bài đăng |
| `GET /stream/<id>` | Stream video (yt-dlp pipe) |
| `GET /thumb/<id>` | Thumbnail ảnh |
| `GET /slideshow/<id>/<index>` | Ảnh slideshow theo index |
| `GET /api/status` | Trạng thái Node 2 |

## 🐧 Ghi chú Ubuntu

Trên Ubuntu server (không có GUI), hệ thống tự động dùng **Xvfb** (X Virtual Framebuffer) để chạy Chrome headless:

```bash
# Cài Xvfb
sudo apt install -y xvfb

# pip install
pip install pyvirtualdisplay
```

## 📜 License

MIT
