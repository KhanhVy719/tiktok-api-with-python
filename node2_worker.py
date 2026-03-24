"""
Node 2 - Worker (Scraper)
Chạy nền, mỗi 5 phút scrape TikTok metadata + thumbnails.
Video KHÔNG download - sẽ stream trực tiếp qua yt-dlp pipe ở Node 1.
Detect photo slideshow posts và download tất cả ảnh slideshow.
"""

import json
import os
import sys
import time
import subprocess
import re
from datetime import datetime

import requests

# ======================== CẤU HÌNH ========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, "cache")
THUMB_CACHE_DIR = os.path.join(CACHE_DIR, "thumbnails")
SLIDE_CACHE_DIR = os.path.join(CACHE_DIR, "slideshow")
META_FILE = os.path.join(CACHE_DIR, "videos_meta.json")
STATUS_FILE = os.path.join(CACHE_DIR, "worker_status.json")

TARGET_USER = "The_sunflower71"
TIKTOK_URL = f"https://www.tiktok.com/@{TARGET_USER}"
YTDLP_CMD = [sys.executable, "-m", "yt_dlp"]

SCRAPE_INTERVAL = 300  # 5 phút = 300 giây
MAX_VIDEOS = 50
# ===========================================================


def ensure_dirs():
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(THUMB_CACHE_DIR, exist_ok=True)
    os.makedirs(SLIDE_CACHE_DIR, exist_ok=True)


def update_status(status, message=""):
    data = {
        "status": status,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "next_run": None
    }
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def format_duration(seconds):
    if seconds is None:
        return "N/A"
    return f"{int(seconds) // 60}:{int(seconds) % 60:02d}"


def format_number(num):
    if num is None:
        return "N/A"
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return str(num)


def scrape_metadata():
    """Thu thập metadata từ TikTok."""
    cmd = YTDLP_CMD + [
        "--dump-json",
        "--no-download",
        "--no-warnings",
        TIKTOK_URL
    ]
    if MAX_VIDEOS > 0:
        cmd.extend(["--playlist-end", str(MAX_VIDEOS)])

    print(f"  📡 Đang scrape @{TARGET_USER}...")
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=300, encoding="utf-8"
        )
        videos = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                try:
                    videos.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return videos
    except Exception as e:
        print(f"  ❌ Lỗi scrape: {e}")
        return []


def is_photo_post(raw):
    """Nhận diện bài đăng ảnh (photo slideshow)."""
    # Cách 1: thumbnail URL chứa 'photomode'
    thumb = raw.get("thumbnail", "")
    if "photomode" in thumb.lower():
        return True
    # Cách 2: không có video format, chỉ có audio
    formats = raw.get("formats", [])
    has_video = any(f.get("vcodec", "none") != "none" for f in formats)
    if not has_video and formats:
        return True
    # Cách 3: width/height là None
    if raw.get("width") is None and raw.get("height") is None:
        return True
    return False


def download_image(url, output_path):
    """Download 1 ảnh."""
    if os.path.exists(output_path) and os.path.getsize(output_path) > 500:
        return True
    try:
        resp = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.tiktok.com/",
            },
            timeout=15
        )
        if resp.status_code == 200 and len(resp.content) > 500:
            with open(output_path, "wb") as f:
                f.write(resp.content)
            return True
    except Exception as e:
        print(f"    ⚠️ Lỗi download ảnh: {e}")
    return False


def scrape_slideshow_urls(video_id, username):
    """
    Dùng undetected-chromedriver để lấy URL ảnh slideshow thật từ TikTok.
    Bypass anti-bot detection.
    - Ubuntu/Linux: dùng Xvfb (virtual framebuffer) qua pyvirtualdisplay
    - Windows: dùng window-position off-screen
    """
    import platform

    try:
        import undetected_chromedriver as uc
        from selenium.webdriver.common.by import By
    except ImportError:
        print("    ⚠️ undetected-chromedriver chưa cài. Chạy: pip install undetected-chromedriver")
        return []

    url = f"https://www.tiktok.com/@{username}/photo/{video_id}"
    print(f"    🌐 Mở TikTok bằng undetected Chrome...")

    is_linux = platform.system() == "Linux"
    display = None

    # Linux/Ubuntu: khởi động Xvfb virtual display
    if is_linux:
        try:
            from pyvirtualdisplay import Display
            display = Display(visible=False, size=(1280, 720))
            display.start()
            print("    📺 Xvfb virtual display started")
        except ImportError:
            print("    ⚠️ pyvirtualdisplay chưa cài. Chạy: pip install pyvirtualdisplay")
            print("    ⚠️ Và cài Xvfb: sudo apt install -y xvfb")
            return []
        except Exception as e:
            print(f"    ⚠️ Xvfb error: {e}")
            print("    💡 Thử: sudo apt install -y xvfb chromium-browser")
            return []

    options = uc.ChromeOptions()
    options.add_argument("--window-size=1280,720")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    if not is_linux:
        # Windows: ẩn cửa sổ bằng vị trí off-screen
        options.add_argument("--window-position=-2000,-2000")

    image_urls = []
    driver = None
    try:
        driver = uc.Chrome(options=options, headless=False)
        driver.get(url)
        import time as _time
        _time.sleep(6)

        # Extract photomode images from DOM
        imgs = driver.find_elements(By.CSS_SELECTOR, 'img[src*="photomode"]')
        seen_bases = set()
        for img in imgs:
            src = img.get_attribute("src")
            if src:
                base = src.split("?")[0]
                if base not in seen_bases:
                    seen_bases.add(base)
                    image_urls.append(src)

        if image_urls:
            print(f"    ✅ Chrome lấy được {len(image_urls)} ảnh slideshow")
        else:
            print("    ❌ Không tìm thấy ảnh slideshow trong DOM")

    except Exception as e:
        print(f"    ⚠️ Chrome error: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass
        if display:
            try:
                display.stop()
            except:
                pass

    return image_urls


def download_slideshow_images(video_id, raw, username=TARGET_USER):
    """
    Download ảnh slideshow cho bài đăng ảnh.
    1. Thử dùng undetected-chromedriver lấy ảnh thật
    2. Fallback: dùng yt-dlp thumbnails
    Deduplicate bằng content hash.
    """
    import hashlib
    slide_dir = os.path.join(SLIDE_CACHE_DIR, video_id)
    os.makedirs(slide_dir, exist_ok=True)

    images = []
    seen_hashes = set()

    # Bước 1: Thử lấy ảnh thật bằng undetected Chrome
    chrome_urls = scrape_slideshow_urls(video_id, username)

    # Bước 2: Fallback yt-dlp thumbnails nếu Chrome fail
    if not chrome_urls:
        print("    📋 Fallback: dùng yt-dlp thumbnails")
        thumbnails = raw.get("thumbnails", [])
        chrome_urls = [t["url"] for t in thumbnails if t.get("url")]

    # Download từng ảnh với dedup
    for i, url in enumerate(chrome_urls):
        ext = "jpg"
        if ".png" in url.lower():
            ext = "png"
        elif ".webp" in url.lower():
            ext = "webp"

        try:
            resp = requests.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "https://www.tiktok.com/",
                },
                timeout=15
            )
            if resp.status_code != 200 or len(resp.content) < 500:
                continue

            content_hash = hashlib.md5(resp.content).hexdigest()
            if content_hash in seen_hashes:
                continue
            seen_hashes.add(content_hash)

            idx = len(images)
            filename = f"slide_{idx}.{ext}"
            filepath = os.path.join(slide_dir, filename)
            with open(filepath, "wb") as f:
                f.write(resp.content)

            images.append({
                "file": filename,
                "size": len(resp.content),
                "id": f"slide_{idx}",
            })
        except Exception as e:
            print(f"    ⚠️ Lỗi download slide {i}: {e}")

    return images


def extract_info(raw):
    """Trích xuất thông tin từ raw data."""
    upload_date = raw.get("upload_date", "")
    try:
        date_fmt = datetime.strptime(upload_date, "%Y%m%d").strftime("%d/%m/%Y")
    except:
        date_fmt = upload_date

    photo = is_photo_post(raw)

    info = {
        "id": raw.get("id", ""),
        "description": raw.get("description", ""),
        "url": raw.get("webpage_url", raw.get("url", "")),
        "duration": raw.get("duration"),
        "duration_str": format_duration(raw.get("duration")),
        "view_count": raw.get("view_count"),
        "like_count": raw.get("like_count"),
        "comment_count": raw.get("comment_count"),
        "share_count": raw.get("repost_count", raw.get("share_count")),
        "upload_date": upload_date,
        "upload_date_formatted": date_fmt,
        "thumbnail": raw.get("thumbnail", ""),
        "width": raw.get("width"),
        "height": raw.get("height"),
        "is_photo": photo,
        "post_type": "photo" if photo else "video",
    }

    if not photo:
        # Tìm best video URL cho stream
        best_url = raw.get("url", "")
        best_height = 0
        for fmt in raw.get("formats", []):
            h = fmt.get("height") or 0
            if fmt.get("vcodec", "none") != "none" and h > best_height:
                best_height = h
                best_url = fmt.get("url", best_url)
        info["video_cdn"] = raw.get("url", "")
        info["video_cdn_hd"] = best_url

    return info


def download_thumbnail(video_id, thumb_url):
    """Download ảnh thumbnail chính."""
    if not thumb_url or thumb_url == "N/A":
        return None
    ext = "jpg"
    if ".png" in thumb_url.lower():
        ext = "png"
    elif ".webp" in thumb_url.lower():
        ext = "webp"

    output_path = os.path.join(THUMB_CACHE_DIR, f"{video_id}.{ext}")
    if download_image(thumb_url, output_path):
        return os.path.basename(output_path)
    return None


def run_scrape_cycle():
    """1 chu kỳ scrape."""
    cycle_start = time.time()
    print(f"\n{'='*50}")
    print(f"🔄 [{datetime.now().strftime('%H:%M:%S')}] Bắt đầu chu kỳ scrape...")
    update_status("scraping", "Đang thu thập metadata...")

    raw_videos = scrape_metadata()
    if not raw_videos:
        print("  ❌ Không thu thập được video nào!")
        update_status("error", "Không thu thập được dữ liệu")
        return

    print(f"  ✅ Tìm thấy {len(raw_videos)} bài đăng")
    update_status("downloading", f"Đang xử lý {len(raw_videos)} bài đăng...")

    videos_info = []
    photo_count = 0
    video_count = 0

    for i, raw in enumerate(raw_videos, 1):
        info = extract_info(raw)
        video_id = info["id"]

        print(f"  [{i}/{len(raw_videos)}] {video_id} ", end="")

        # Download thumbnail
        thumb_file = download_thumbnail(video_id, info.get("thumbnail", ""))
        info["cached_thumb"] = thumb_file

        if info["is_photo"]:
            # Photo post - download slideshow images
            photo_count += 1
            slides = download_slideshow_images(video_id, raw)
            info["slideshow_images"] = slides
            info["slideshow_count"] = len(slides)
            print(f"📷 {len(slides)} ảnh")
        else:
            # Video post - chỉ lưu metadata, KHÔNG download video
            video_count += 1
            info["slideshow_images"] = []
            info["slideshow_count"] = 0
            print(f"🎬 video")

        videos_info.append(info)

    # Lưu metadata
    meta = {
        "target_user": TARGET_USER,
        "total_videos": len(videos_info),
        "video_count": video_count,
        "photo_count": photo_count,
        "last_update": datetime.now().isoformat(),
        "scrape_duration": round(time.time() - cycle_start, 1),
        "videos": videos_info
    }

    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    elapsed = round(time.time() - cycle_start, 1)
    msg = f"Hoàn tất: {video_count} video + {photo_count} ảnh, {elapsed}s"
    print(f"  💾 Metadata saved")
    print(f"  ✅ {msg}")
    update_status("idle", msg)


def main():
    print(f"""
╔══════════════════════════════════════════════════╗
║     ⚙️  Node 2 - Worker (Scraper)               ║
║     Metadata + Thumbnails mỗi {SCRAPE_INTERVAL}s            ║
╚══════════════════════════════════════════════════╝

👤 Target: @{TARGET_USER}
📂 Cache:  {CACHE_DIR}
🖼️ Thumbs: {THUMB_CACHE_DIR}
📷 Slides: {SLIDE_CACHE_DIR}
⏰ Interval: {SCRAPE_INTERVAL}s ({SCRAPE_INTERVAL // 60} phút)
    """)

    ensure_dirs()
    run_scrape_cycle()

    while True:
        next_run = datetime.now().timestamp() + SCRAPE_INTERVAL
        next_time = datetime.fromtimestamp(next_run).strftime('%H:%M:%S')
        print(f"\n⏳ Chu kỳ tiếp theo: {next_time} (sau {SCRAPE_INTERVAL}s)")

        status_data = {
            "status": "waiting",
            "message": f"Đợi chu kỳ tiếp theo",
            "timestamp": datetime.now().isoformat(),
            "next_run": next_time
        }
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(status_data, f, ensure_ascii=False, indent=2)

        time.sleep(SCRAPE_INTERVAL)
        run_scrape_cycle()


if __name__ == "__main__":
    main()
