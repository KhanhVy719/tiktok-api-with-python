"""
Node 1 - API Server (Storage)
Serve dữ liệu từ cache Node 2.
- Video: stream trực tiếp qua yt-dlp pipe (không download)
- Ảnh: serve từ cache + slideshow navigation
"""

import json
import os
import sys
import time
import subprocess
from datetime import datetime

from flask import Flask, Response, request, jsonify, send_file, render_template_string

# ======================== CẤU HÌNH ========================
TARGET_USER = "The_sunflower71"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, "cache")
THUMB_CACHE_DIR = os.path.join(CACHE_DIR, "thumbnails")
SLIDE_CACHE_DIR = os.path.join(CACHE_DIR, "slideshow")
META_FILE = os.path.join(CACHE_DIR, "videos_meta.json")
STATUS_FILE = os.path.join(CACHE_DIR, "worker_status.json")

TARGET_USER = "The_sunflower71"
YTDLP_CMD = [sys.executable, "-m", "yt_dlp"]
HOST = "0.0.0.0"
PORT = 8888
# ===========================================================

app = Flask(__name__)

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


def load_meta():
    if os.path.exists(META_FILE):
        with open(META_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"videos": [], "total_videos": 0, "last_update": None}


def load_worker_status():
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"status": "offline", "message": "Node 2 chưa chạy"}


# =================== HTML TEMPLATE =========================

PLAYER_HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TikTok CDN - Node 1 API</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #16213e 100%);
            color: #e0e0e0;
            min-height: 100vh;
        }

        .header {
            background: rgba(255,255,255,0.03);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid rgba(255,255,255,0.06);
            padding: 16px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .header h1 {
            font-size: 20px;
            background: linear-gradient(90deg, #fe2c55, #25f4ee);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .header .user-tag { color: #aaa; font-size: 13px; }

        .node-status { display: flex; gap: 8px; align-items: center; }

        .node-badge {
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
        }

        .node-badge.n1 { background: rgba(37, 244, 238, 0.15); color: #25f4ee; }
        .node-badge.n2 { background: rgba(254, 44, 85, 0.15); color: #fe2c55; }
        .node-badge.online { border: 1px solid rgba(76,175,80,0.4); }
        .node-badge.offline { border: 1px solid rgba(244,67,54,0.4); opacity: 0.6; }

        .container { max-width: 1400px; margin: 0 auto; padding: 24px; }

        .stats-bar {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 12px;
            margin-bottom: 24px;
        }

        .stat-card {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 12px 16px;
        }

        .stat-card .label { font-size: 10px; color: #888; text-transform: uppercase; letter-spacing: 1px; }
        .stat-card .value { font-size: 20px; font-weight: 700; color: #fff; margin-top: 4px; }
        .stat-card .value.green { color: #4caf50; }
        .stat-card .value.cyan { color: #25f4ee; }
        .stat-card .value.pink { color: #fe2c55; }
        .stat-card .sub { font-size: 11px; color: #666; margin-top: 2px; }

        .video-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 16px;
        }

        .video-card {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 14px;
            overflow: hidden;
            transition: all 0.3s;
        }

        .video-card:hover {
            transform: translateY(-2px);
            border-color: rgba(254, 44, 85, 0.3);
            box-shadow: 0 8px 25px rgba(0,0,0,0.3);
        }

        .media-container {
            position: relative;
            background: #000;
            aspect-ratio: 9/16;
            max-height: 420px;
            overflow: hidden;
        }

        .media-container img.thumb,
        .media-container img.slide-img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            position: absolute;
            inset: 0;
        }

        .media-container video {
            width: 100%;
            height: 100%;
            object-fit: contain;
        }

        .play-overlay {
            position: absolute;
            inset: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            background: rgba(0,0,0,0.45);
            cursor: pointer;
            transition: all 0.3s;
            gap: 8px;
            z-index: 5;
        }

        .play-overlay:hover { background: rgba(0,0,0,0.25); }
        .play-overlay .play-icon { font-size: 42px; }

        .type-badge {
            position: absolute;
            top: 10px;
            left: 10px;
            padding: 3px 10px;
            border-radius: 8px;
            font-size: 10px;
            font-weight: 600;
            z-index: 10;
        }

        .type-badge.video { background: rgba(37,244,238,0.3); color: #25f4ee; }
        .type-badge.photo { background: rgba(255,152,0,0.3); color: #ff9800; }

        .cache-tag {
            font-size: 10px;
            padding: 3px 10px;
            border-radius: 10px;
            background: rgba(76,175,80,0.3);
            color: #4caf50;
        }

        /* Slideshow navigation */
        .slide-nav {
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: rgba(0,0,0,0.6);
            color: #fff;
            border: 1px solid rgba(255,255,255,0.2);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            z-index: 15;
            transition: all 0.2s;
        }

        .slide-nav:hover { background: rgba(255,255,255,0.2); }
        .slide-nav.prev { left: 8px; }
        .slide-nav.next { right: 8px; }

        .slide-counter {
            position: absolute;
            bottom: 10px;
            left: 50%;
            transform: translateX(-50%);
            padding: 3px 12px;
            border-radius: 10px;
            background: rgba(0,0,0,0.6);
            color: #fff;
            font-size: 11px;
            z-index: 15;
        }

        .slide-dots {
            position: absolute;
            bottom: 32px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            gap: 5px;
            z-index: 15;
        }

        .slide-dots .dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: rgba(255,255,255,0.4);
            transition: all 0.2s;
        }

        .slide-dots .dot.active {
            background: #fff;
            width: 16px;
            border-radius: 3px;
        }

        .video-info { padding: 12px 14px; }

        .video-info .desc {
            font-size: 13px;
            line-height: 1.5;
            color: #ccc;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
            margin-bottom: 8px;
        }

        .video-meta {
            display: flex;
            gap: 12px;
            font-size: 11px;
            color: #888;
            flex-wrap: wrap;
        }

        .video-meta span { display: flex; align-items: center; gap: 3px; }

        .action-links {
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px solid rgba(255,255,255,0.06);
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
        }

        .action-links a {
            font-size: 11px;
            color: #25f4ee;
            text-decoration: none;
            padding: 3px 10px;
            background: rgba(37, 244, 238, 0.08);
            border-radius: 6px;
            transition: all 0.2s;
        }

        .action-links a:hover { background: rgba(37, 244, 238, 0.2); }

        .toast {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: rgba(30,30,30,0.95);
            color: #fff;
            padding: 10px 18px;
            border-radius: 8px;
            display: none;
            z-index: 1000;
            font-size: 13px;
            border: 1px solid rgba(255,255,255,0.1);
        }

        .loading-spinner {
            width: 32px;
            height: 32px;
            border: 3px solid rgba(255,255,255,0.2);
            border-top-color: #25f4ee;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin { to { transform: rotate(360deg); } }

        /* Modal for TikTok photo posts */
        .modal-overlay {
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.85);
            z-index: 1000;
            display: none;
            align-items: center;
            justify-content: center;
        }

        .modal-overlay.active { display: flex; }

        .modal-content {
            width: 90%;
            max-width: 480px;
            height: 85vh;
            border-radius: 14px;
            overflow: hidden;
            position: relative;
            background: #111;
        }

        .modal-content iframe {
            width: 100%;
            height: 100%;
            border: none;
        }

        .modal-close {
            position: absolute;
            top: 10px;
            right: 10px;
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: rgba(0,0,0,0.7);
            color: #fff;
            border: 1px solid rgba(255,255,255,0.2);
            font-size: 18px;
            cursor: pointer;
            z-index: 10;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .modal-close:hover { background: rgba(255,255,255,0.2); }

        .photo-view-btn {
            position: absolute;
            inset: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            background: rgba(0,0,0,0.4);
            cursor: pointer;
            transition: all 0.3s;
            gap: 8px;
            z-index: 5;
        }

        .photo-view-btn:hover { background: rgba(0,0,0,0.2); }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>🎬 TikTok Node 1 - API Server</h1>
            <span class="user-tag">@{{ username }} • Stream trực tiếp • :{{ port }}</span>
        </div>
        <div class="node-status">
            <span class="node-badge n1 online">Node 1 ● API</span>
            <span class="node-badge n2" id="node2Badge">Node 2 ...</span>
        </div>
    </div>

    <div class="container">
        <div class="stats-bar">
            <div class="stat-card">
                <div class="label">Tổng bài đăng</div>
                <div class="value" id="totalPosts">-</div>
            </div>
            <div class="stat-card">
                <div class="label">🎬 Video</div>
                <div class="value cyan" id="videoCount">-</div>
            </div>
            <div class="stat-card">
                <div class="label">📷 Ảnh</div>
                <div class="value pink" id="photoCount">-</div>
            </div>
            <div class="stat-card">
                <div class="label">Tổng lượt xem</div>
                <div class="value" id="totalViews">-</div>
            </div>
            <div class="stat-card">
                <div class="label">Node 2</div>
                <div class="value" id="workerStatus" style="font-size:13px;">-</div>
                <div class="sub" id="workerNext"></div>
            </div>
        </div>

        <div class="video-grid" id="videoGrid">
            <div style="text-align:center;padding:40px;color:#888;">⏳ Đang tải...</div>
        </div>
    </div>

    <div class="toast" id="toast"></div>

    <script>
        function fmtNum(n) {
            if (n == null) return 'N/A';
            if (n >= 1e6) return (n/1e6).toFixed(1) + 'M';
            if (n >= 1e3) return (n/1e3).toFixed(1) + 'K';
            return n.toString();
        }

        function showToast(msg) {
            const t = document.getElementById('toast');
            t.textContent = msg;
            t.style.display = 'block';
            setTimeout(() => t.style.display = 'none', 3000);
        }

        // Slideshow state per video
        const slideState = {};

        function slideGo(id, dir) {
            const state = slideState[id];
            if (!state) return;
            state.current += dir;
            if (state.current < 0) state.current = state.total - 1;
            if (state.current >= state.total) state.current = 0;

            const container = document.getElementById('p-' + id);
            const img = container.querySelector('.slide-img');
            if (img) {
                img.src = '/slideshow/' + id + '/' + state.current;
            }

            // Update counter
            const counter = container.querySelector('.slide-counter');
            if (counter) counter.textContent = (state.current + 1) + ' / ' + state.total;

            // Update dots
            container.querySelectorAll('.dot').forEach((d, i) => {
                d.className = 'dot' + (i === state.current ? ' active' : '');
            });
        }

        async function loadData() {
            try {
                const [vRes, sRes] = await Promise.all([
                    fetch('/api/videos'),
                    fetch('/api/status')
                ]);
                const vData = await vRes.json();
                const sData = await sRes.json();
                const videos = vData.videos || [];

                // Stats
                document.getElementById('totalPosts').textContent = videos.length;
                document.getElementById('videoCount').textContent =
                    videos.filter(v => !v.is_photo).length;
                document.getElementById('photoCount').textContent =
                    videos.filter(v => v.is_photo).length;
                document.getElementById('totalViews').textContent = fmtNum(
                    videos.reduce((s, v) => s + (v.view_count || 0), 0)
                );

                // Worker status
                const ws = sData.worker;
                const badge = document.getElementById('node2Badge');
                const statusEl = document.getElementById('workerStatus');
                const nextEl = document.getElementById('workerNext');

                if (ws.status === 'waiting' || ws.status === 'idle') {
                    badge.className = 'node-badge n2 online';
                    badge.textContent = 'Node 2 ● Worker';
                    statusEl.textContent = '● Online';
                    statusEl.className = 'value green';
                } else if (ws.status === 'scraping' || ws.status === 'downloading') {
                    badge.className = 'node-badge n2 online';
                    badge.textContent = 'Node 2 ⟳ Working';
                    statusEl.textContent = '⟳ ' + ws.message;
                    statusEl.className = 'value cyan';
                } else {
                    badge.className = 'node-badge n2 offline';
                    badge.textContent = 'Node 2 ○ Offline';
                    statusEl.textContent = '○ Offline';
                    statusEl.className = 'value';
                    statusEl.style.color = '#f44336';
                }
                nextEl.textContent = ws.next_run ? 'Next: ' + ws.next_run : ws.message || '';

                // Render
                const grid = document.getElementById('videoGrid');
                if (videos.length === 0) {
                    grid.innerHTML = '<div style="text-align:center;padding:40px;color:#888;">⏳ Đợi Node 2 scrape xong...</div>';
                    return;
                }

                grid.innerHTML = videos.map(v => {
                    if (v.is_photo) {
                        return renderPhotoCard(v);
                    } else {
                        return renderVideoCard(v);
                    }
                }).join('');
            } catch(e) {
                document.getElementById('videoGrid').innerHTML =
                    '<div style="text-align:center;padding:40px;color:#f44336;">❌ ' + e.message + '</div>';
            }
        }

        function renderVideoCard(v) {
            return `
            <div class="video-card">
                <div class="media-container" id="p-${v.id}">
                    <span class="type-badge video">🎬 Video</span>
                    ${v.cached_thumb ? '<img class="thumb" src="/thumb/' + v.id + '">' : ''}
                    <div class="play-overlay" onclick="playVideo('${v.id}')">
                        <span class="play-icon">▶️</span>
                        <span class="cache-tag">Stream trực tiếp</span>
                    </div>
                </div>
                <div class="video-info">
                    <div class="desc">${v.description || 'Không có mô tả'}</div>
                    <div class="video-meta">
                        <span>📅 ${v.upload_date_formatted}</span>
                        <span>⏱ ${v.duration_str}</span>
                        <span>👁 ${fmtNum(v.view_count)}</span>
                        <span>❤️ ${fmtNum(v.like_count)}</span>
                        <span>💬 ${fmtNum(v.comment_count)}</span>
                    </div>
                    <div class="action-links">
                        <a href="/stream/${v.id}" target="_blank">▶ Stream</a>
                        <a href="${v.url}" target="_blank">🔗 TikTok</a>
                        <a href="/api/video/${v.id}" target="_blank">📋 JSON</a>
                    </div>
                </div>
            </div>`;
        }

        function renderPhotoCard(v) {
            const tiktokUrl = v.url.replace('/video/', '/photo/');
            const slideCount = v.slideshow_count || 0;
            const hasSlides = slideCount > 1;

            if (hasSlides) {
                slideState[v.id] = { current: 0, total: slideCount };
            }

            const dotsHtml = hasSlides ? '<div class="slide-dots">' +
                Array.from({length: slideCount}, (_, i) =>
                    '<span class="dot' + (i === 0 ? ' active' : '') + '"></span>'
                ).join('') + '</div>' : '';

            return `
            <div class="video-card">
                <div class="media-container" id="p-${v.id}">
                    <span class="type-badge photo">📷 ${slideCount > 1 ? slideCount + ' ảnh' : 'Ảnh'}</span>
                    ${v.cached_thumb
                        ? '<img class="slide-img" src="' + (hasSlides ? '/slideshow/' + v.id + '/0' : '/thumb/' + v.id) + '">'
                        : ''}
                    ${hasSlides ? '<button class="slide-nav prev" onclick="slideGo(\\'' + v.id + '\\', -1)">‹</button>' : ''}
                    ${hasSlides ? '<button class="slide-nav next" onclick="slideGo(\\'' + v.id + '\\', 1)">›</button>' : ''}
                    ${hasSlides ? '<span class="slide-counter">1 / ' + slideCount + '</span>' : ''}
                    ${dotsHtml}
                    ${!hasSlides ? '<div class="photo-view-btn" onclick="window.open(\\'' + tiktokUrl + '\\', \\'_blank\\')"><span class="play-icon">📷</span><span class="cache-tag">Mở trên TikTok</span></div>' : ''}
                </div>
                <div class="video-info">
                    <div class="desc">${v.description || 'Không có mô tả'}</div>
                    <div class="video-meta">
                        <span>📅 ${v.upload_date_formatted}</span>
                        <span>📷 ${slideCount > 1 ? slideCount + ' ảnh' : 'Ảnh'}</span>
                        <span>👁 ${fmtNum(v.view_count)}</span>
                        <span>❤️ ${fmtNum(v.like_count)}</span>
                        <span>💬 ${fmtNum(v.comment_count)}</span>
                    </div>
                    <div class="action-links">
                        <a href="${tiktokUrl}" target="_blank">🔗 TikTok</a>
                        <a href="/api/video/${v.id}" target="_blank">📋 JSON</a>
                    </div>
                </div>
            </div>`;
        }

        function playVideo(id) {
            const player = document.getElementById('p-' + id);
            const badge = player.querySelector('.type-badge');
            player.innerHTML = '';
            if (badge) player.appendChild(badge);

            // Loading spinner
            const spinner = document.createElement('div');
            spinner.className = 'play-overlay';
            spinner.innerHTML = '<div class="loading-spinner"></div><span class="cache-tag">Đang tải stream...</span>';
            player.appendChild(spinner);

            const video = document.createElement('video');
            video.controls = true;
            video.autoplay = true;
            video.src = '/stream/' + id;
            video.style.cssText = 'width:100%;height:100%;object-fit:contain;position:relative;z-index:2;';
            video.onloadeddata = () => { if (spinner.parentNode) spinner.remove(); };
            video.onerror = () => {
                spinner.innerHTML = '<span style="color:#ff9800;">❌ Không stream được</span>';
            };
            player.appendChild(video);
        }

        loadData();
        setInterval(loadData, 30000);

        function openPhotoModal(tiktokUrl) {
            const modal = document.getElementById('photoModal');
            const iframe = document.getElementById('photoIframe');
            iframe.src = tiktokUrl;
            modal.classList.add('active');
        }

        function closePhotoModal() {
            const modal = document.getElementById('photoModal');
            const iframe = document.getElementById('photoIframe');
            modal.classList.remove('active');
            iframe.src = '';
        }

        // Close on Escape
        document.addEventListener('keydown', e => {
            if (e.key === 'Escape') closePhotoModal();
        });
    </script>

    <!-- Photo modal -->
    <div class="modal-overlay" id="photoModal" onclick="if(event.target===this)closePhotoModal()">
        <div class="modal-content">
            <button class="modal-close" onclick="closePhotoModal()">✕</button>
            <iframe id="photoIframe" src="" allow="autoplay; encrypted-media"></iframe>
        </div>
    </div>
</body>
</html>
"""


# =================== API ROUTES ============================

@app.route("/")
def index():
    return render_template_string(PLAYER_HTML, username=TARGET_USER, port=PORT)


@app.route("/api/videos")
def api_videos():
    meta = load_meta()
    return jsonify({
        "videos": meta.get("videos", []),
        "total": meta.get("total_videos", 0),
        "last_update": meta.get("last_update"),
    })


@app.route("/api/video/<video_id>")
def api_video_detail(video_id):
    meta = load_meta()
    for v in meta.get("videos", []):
        if v["id"] == video_id:
            return jsonify(v)
    return jsonify({"error": "Video not found"}), 404


@app.route("/api/status")
def api_status():
    meta = load_meta()
    worker = load_worker_status()
    return jsonify({
        "node1": "online",
        "worker": worker,
        "total_videos": meta.get("total_videos", 0),
        "video_count": meta.get("video_count", 0),
        "photo_count": meta.get("photo_count", 0),
        "last_update": meta.get("last_update"),
    })


@app.route("/thumb/<video_id>")
def serve_thumbnail(video_id):
    """Serve ảnh thumbnail."""
    meta = load_meta()
    for v in meta.get("videos", []):
        if v["id"] == video_id and v.get("cached_thumb"):
            thumb_path = os.path.join(THUMB_CACHE_DIR, v["cached_thumb"])
            if os.path.exists(thumb_path):
                ext = v["cached_thumb"].rsplit(".", 1)[-1].lower()
                mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                        "png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")
                return send_file(thumb_path, mimetype=mime)
    return jsonify({"error": "Not found"}), 404


@app.route("/api/all")
def api_all():
    """
    API tổng hợp: profile (avatar, bio, followers, likes) + tất cả bài đăng.
    """
    meta = load_meta()
    videos = meta.get("videos", [])

    # Load profile
    profile = {}
    profile_path = os.path.join(CACHE_DIR, "user_profile.json")
    if os.path.exists(profile_path):
        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                profile = json.load(f)
        except:
            pass

    # Build response
    base_url = request.host_url.rstrip("/")

    # Tách video vs photo
    video_posts = []
    photo_posts = []

    for v in videos:
        info = {
            "id": v["id"],
            "description": v.get("description", ""),
            "upload_date": v.get("upload_date_formatted", ""),
            "tiktok_url": v.get("url", ""),
        }
        stats = {
            "views": v.get("view_count", 0),
            "likes": v.get("like_count", 0),
            "comments": v.get("comment_count", 0),
            "reposts": v.get("repost_count", 0),
        }

        if v.get("is_photo"):
            slide_urls = []
            if v.get("slideshow_images"):
                slide_urls = [
                    f"{base_url}/slideshow/{v['id']}/{i}"
                    for i in range(len(v["slideshow_images"]))
                ]
            photo_posts.append({
                "info": info,
                "stats": stats,
                "music": {
                    "title": v.get("music_title", ""),
                    "author": v.get("music_author", ""),
                    "audio_url": f"{base_url}/audio/{v['id']}" if v.get("audio_file") else None,
                },
                "urls": {
                    "thumbnail_cdn": v.get("thumbnail", ""),
                    "thumbnail_local": f"{base_url}/thumb/{v['id']}" if v.get("cached_thumb") else None,
                    "slideshow": slide_urls,
                },
                "slideshow_count": len(slide_urls),
            })
        else:
            video_posts.append({
                "info": info,
                "stats": stats,
                "duration": v.get("duration_str", ""),
                "urls": {
                    "stream": f"{base_url}/stream/{v['id']}",
                    "thumbnail_cdn": v.get("thumbnail", ""),
                    "thumbnail_local": f"{base_url}/thumb/{v['id']}" if v.get("cached_thumb") else None,
                },
            })

    return jsonify({
        "profile": {
            "username": profile.get("username", TARGET_USER),
            "nickname": profile.get("nickname", ""),
            "bio": profile.get("bio", ""),
            "verified": profile.get("verified", False),
            "profile_url": profile.get("profile_url", f"https://www.tiktok.com/@{TARGET_USER}"),
            "avatar": {
                "cdn": profile.get("avatar_cdn", ""),
                "local": f"{base_url}/avatar",
            },
            "stats": {
                "followers": profile.get("followers", 0),
                "following": profile.get("following", 0),
                "total_likes": profile.get("likes", 0),
                "total_videos": profile.get("total_videos", 0),
            },
        },
        "videos": video_posts,
        "photos": photo_posts,
        "summary": {
            "total_posts": len(videos),
            "video_count": len(video_posts),
            "photo_count": len(photo_posts),
            "last_update": meta.get("last_update"),
        },
    })


@app.route("/audio/<video_id>")
def serve_audio(video_id):
    """Serve audio mp3 cho bài ảnh slideshow."""
    audio_path = os.path.join(CACHE_DIR, "audio", f"{video_id}.mp3")
    if os.path.exists(audio_path):
        return send_file(audio_path, mimetype="audio/mpeg")
    return jsonify({"error": "Audio not found"}), 404


@app.route("/avatar")
def serve_avatar():
    """Serve ảnh avatar đã cache."""
    avatar_path = os.path.join(CACHE_DIR, "avatar.jpg")
    if os.path.exists(avatar_path):
        return send_file(avatar_path, mimetype="image/jpeg")
    return jsonify({"error": "Avatar not found"}), 404


@app.route("/slideshow/<video_id>/<int:index>")
def serve_slideshow_image(video_id, index):
    """Serve 1 ảnh slideshow theo index."""
    meta = load_meta()
    for v in meta.get("videos", []):
        if v["id"] == video_id and v.get("slideshow_images"):
            images = v["slideshow_images"]
            if 0 <= index < len(images):
                img = images[index]
                img_path = os.path.join(SLIDE_CACHE_DIR, video_id, img["file"])
                if os.path.exists(img_path):
                    ext = img["file"].rsplit(".", 1)[-1].lower()
                    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                            "png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")
                    return send_file(img_path, mimetype=mime)
    return jsonify({"error": "Image not found"}), 404


@app.route("/stream/<video_id>")
def stream_video(video_id):
    """
    Stream video qua yt-dlp pipe.
    Không download file - pipe trực tiếp từ TikTok CDN qua yt-dlp.
    """
    meta = load_meta()
    tiktok_url = None
    for v in meta.get("videos", []):
        if v["id"] == video_id:
            tiktok_url = v.get("url", "")
            break

    if not tiktok_url:
        return jsonify({"error": "Video not found"}), 404

    cmd = YTDLP_CMD + [
        "-f", "best[vcodec^=h264][acodec!=none]/best[vcodec!=none][acodec!=none]/best",
        "-o", "-",
        "--no-warnings",
        "--quiet",
        "--no-playlist",
        tiktok_url
    ]

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        def generate():
            try:
                while True:
                    chunk = process.stdout.read(65536)
                    if not chunk:
                        break
                    yield chunk
            finally:
                process.stdout.close()
                process.wait()

        return Response(
            generate(),
            mimetype="video/mp4",
            headers={
                "Content-Type": "video/mp4",
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "public, max-age=3600",
            }
        )
    except Exception as e:
        return jsonify({"error": f"Stream error: {str(e)}"}), 500


# =================== MAIN ==================================

if __name__ == "__main__":
    print(f"""
╔══════════════════════════════════════════════════╗
║     📡 Node 1 - API Server                      ║
║     Stream video + Slideshow ảnh                 ║
╚══════════════════════════════════════════════════╝

📡 Server:     http://localhost:{PORT}
🎮 Player:     http://localhost:{PORT}
📋 API:        http://localhost:{PORT}/api/videos
▶️  Stream:     http://localhost:{PORT}/stream/<id>
🖼️  Thumbnail:  http://localhost:{PORT}/thumb/<id>
📷 Slideshow:  http://localhost:{PORT}/slideshow/<id>/<index>
📊 Status:     http://localhost:{PORT}/api/status

📂 Cache: {CACHE_DIR}
    """)

    if os.path.exists(META_FILE):
        meta = load_meta()
        print(f"✅ Loaded {meta.get('total_videos', 0)} posts ({meta.get('video_count',0)} video, {meta.get('photo_count',0)} photo)")
    else:
        print("⚠️ Chưa có cache. Chạy python node2_worker.py trước!")

    app.run(host=HOST, port=PORT, debug=False, threaded=True)
