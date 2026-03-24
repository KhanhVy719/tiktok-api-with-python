#!/bin/bash
# ============================================
# Script cài đặt TikTok API trên Ubuntu/Debian
# ============================================

set -e

echo "🚀 Cài đặt TikTok 2-Node System..."
echo ""

# === System dependencies ===
echo "📦 Cài đặt system dependencies..."
sudo apt update -y
sudo apt install -y \
    python3 python3-pip python3-venv python3-full \
    xvfb \
    chromium-browser \
    ffmpeg \
    wget curl

# === Python venv (bắt buộc trên Ubuntu 24.04+) ===
echo ""
echo "🐍 Tạo Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# === Python packages ===
echo "📚 Cài đặt Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# === Tạo thư mục cần thiết ===
echo ""
echo "📁 Tạo thư mục cache..."
mkdir -p cache/thumbnails cache/slideshow data

# === Tạo empty cookie file nếu chưa có ===
if [ ! -f data/tiktok_cookies.json ]; then
    echo "[]" > data/tiktok_cookies.json
fi

# === Tạo script chạy nhanh ===
cat > start.sh << 'EOF'
#!/bin/bash
source venv/bin/activate

echo "🚀 Khởi động TikTok 2-Node System..."
echo ""

# Chạy Node 2 (Worker) trong background
echo "⚙️  Khởi động Node 2 (Worker)..."
nohup python3 node2_worker.py > logs_worker.log 2>&1 &
WORKER_PID=$!
echo "   PID: $WORKER_PID"

# Đợi 2s rồi chạy Node 1
sleep 2
echo "📡 Khởi động Node 1 (API Server)..."
python3 node1_api.py
EOF
chmod +x start.sh

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  ✅ Cài đặt hoàn tất!                       ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "📝 Cách chạy:"
echo ""
echo "   Cách 1 (nhanh):"
echo "     ./start.sh"
echo ""
echo "   Cách 2 (thủ công):"
echo "     source venv/bin/activate"
echo "     python3 node2_worker.py &"
echo "     python3 node1_api.py"
echo ""
echo "🌐 Truy cập: http://<IP>:8888"
echo ""
