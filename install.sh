#!/bin/bash
# ============================================
# Script cài đặt TikTok API trên Ubuntu/Debian
# ============================================

set -e

echo "🚀 Cài đặt TikTok 2-Node System..."

# === System dependencies ===
echo "📦 Cài đặt system dependencies..."
sudo apt update
sudo apt install -y \
    python3 python3-pip python3-venv \
    xvfb \
    chromium-browser \
    ffmpeg \
    wget curl

# === Python venv ===
echo "🐍 Tạo Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# === Python packages ===
echo "📚 Cài đặt Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# === Tạo thư mục cần thiết ===
echo "📁 Tạo thư mục cache..."
mkdir -p cache/thumbnails cache/slideshow data

# === Tạo empty cookie file nếu chưa có ===
if [ ! -f data/tiktok_cookies.json ]; then
    echo "[]" > data/tiktok_cookies.json
fi

echo ""
echo "✅ Cài đặt hoàn tất!"
echo ""
echo "📝 Cách chạy:"
echo "   Terminal 1:  python3 node2_worker.py    # Worker scraper"
echo "   Terminal 2:  python3 node1_api.py       # API server"
echo ""
echo "🌐 Truy cập: http://localhost:8888"
echo ""
