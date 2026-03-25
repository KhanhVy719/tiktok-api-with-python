"""
TikTok Story Scraper (Nhật ký video 24h) - yt-dlp Edition
Thu thập video/ảnh từ phần "Nhật ký video" (Story) của TikTok.

Flow:
Phase 1: Mở Story viewer → chuyển qua tất cả story → thu thập URL
         (dạng tiktok.com/@user/photo/ID hoặc /video/ID)
Phase 2: Dùng yt-dlp extract_info() cho mỗi URL → download video/ảnh
"""

import json
import os
import sys
import time
import hashlib
import platform
from datetime import datetime

import requests

try:
    import yt_dlp
    YTDLP_AVAILABLE = True
except ImportError:
    YTDLP_AVAILABLE = False

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# ======================== CẤU HÌNH ========================
TARGET_USER = "the_sunflower71"
TIKTOK_URL = f"https://www.tiktok.com/@{TARGET_USER}"
OUTPUT_DIR = "data"
STORY_DIR = os.path.join(OUTPUT_DIR, "stories")
# ===========================================================


def ensure_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(STORY_DIR, exist_ok=True)


def format_filesize(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def setup_chrome():
    try:
        import undetected_chromedriver as uc
    except ImportError:
        print("❌ Chưa cài undetected-chromedriver!")
        sys.exit(1)

    is_linux = platform.system() == "Linux"
    display = None
    use_headless = False

    if is_linux:
        # Thử Xvfb trước (tốt hơn headless cho DOM)
        try:
            from pyvirtualdisplay import Display
            display = Display(visible=False, size=(1280, 720))
            display.start()
            print("  ✅ Xvfb virtual display started")
        except Exception as e:
            print(f"  ⚠️ Xvfb không có, dùng headless mode: {e}")
            use_headless = True

    options = uc.ChromeOptions()
    options.add_argument("--window-size=1280,900")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--lang=vi-VN")

    if is_linux:
        options.add_argument("--disable-setuid-sandbox")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--remote-debugging-port=0")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-infobars")
        # Tăng shared memory
        options.add_argument("--shm-size=2g")

    if use_headless:
        options.add_argument("--headless=new")

    driver = uc.Chrome(options=options, headless=use_headless)
    return driver, display




def is_story_viewer_open(driver):
    try:
        el = driver.find_element("id", "stories-player")
        return el.is_displayed()
    except:
        return False


def click_next_story(driver):
    """Click nút next nhanh (không cần chờ lâu)."""
    try:
        clicked = driver.execute_script("""
            const player = document.getElementById('stories-player');
            if (!player) return 'no_player';

            // DOM: div[2] > div[3] > button
            let containers = player.children;
            for (let container of containers) {
                let divs = container.children;
                if (divs.length >= 3) {
                    let nextDiv = divs[2];
                    let btn = nextDiv.querySelector('button');
                    if (btn) { btn.click(); return 'ok'; }
                    let inner = nextDiv.querySelector('div');
                    if (inner) { inner.click(); return 'ok'; }
                }
            }

            // Position fallback
            let buttons = player.querySelectorAll('button');
            let viewH = window.innerHeight;
            let viewW = window.innerWidth;
            for (let btn of buttons) {
                let rect = btn.getBoundingClientRect();
                let cY = rect.top + rect.height / 2;
                let cX = rect.left + rect.width / 2;
                if (cX > viewW * 0.6 && cY > viewH * 0.25 && cY < viewH * 0.75 &&
                    rect.width > 15 && rect.width < 100) {
                    btn.click();
                    return 'ok';
                }
            }
            return 'not_found';
        """)
        return clicked == 'ok'
    except:
        pass

    # Arrow key fallback
    try:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ARROW_RIGHT)
        return True
    except:
        return False


# ============================================================
#  PHASE 1: Thu thập tất cả story URLs từ browser
# ============================================================
def get_image_cdn_from_dom(driver):
    """Lấy image CDN URL trực tiếp từ DOM #stories-player."""
    try:
        return driver.execute_script("""
            const player = document.getElementById('stories-player');
            if (!player) return null;
            
            let imgs = player.querySelectorAll('img');
            for (let img of imgs) {
                let src = img.src || '';
                if (src && src.startsWith('http') &&
                    !src.includes('avatar') && !src.includes('emoji') &&
                    !src.includes('profile') && !src.includes('icon') &&
                    (src.includes('photomode') || src.includes('tiktokcdn') ||
                     src.includes('story') || src.includes('muscdn') ||
                     img.naturalWidth > 200 || img.width > 200)) {
                    return src;
                }
            }
            return null;
        """)
    except:
        return None


def get_music_from_dom(driver):
    """Lấy thông tin music từ DOM #stories-player."""
    try:
        return driver.execute_script("""
            const player = document.getElementById('stories-player');
            if (!player) return null;
            
            let result = {};
            
            // Tìm music title/author từ các element text
            let allText = player.querySelectorAll('*');
            for (let el of allText) {
                let cls = (el.className || '').toString().toLowerCase();
                let attr = el.getAttribute('data-e2e') || '';
                
                // Music icon hoặc music section
                if (cls.includes('music') || attr.includes('music')) {
                    let text = el.textContent.trim();
                    if (text && text.length > 1 && text.length < 200) {
                        result.music_text = text;
                    }
                }
            }
            
            // Tìm audio element
            let audios = player.querySelectorAll('audio');
            for (let audio of audios) {
                if (audio.src) {
                    result.audio_src = audio.src;
                }
            }
            
            // Tìm từ meta hoặc data attributes
            let metaMusic = document.querySelector('meta[property="og:music"]');
            if (metaMusic) result.music_meta = metaMusic.content;
            
            return Object.keys(result).length > 0 ? result : null;
        """)
    except:
        return None


def collect_story_urls(driver):
    """Chạy qua tất cả story nhanh, thu thập URLs + image CDN."""
    print("\n" + "=" * 50)
    print("📋 PHASE 1: Thu thập Story URLs...")
    print("=" * 50 + "\n")

    stories = []  # List of {url, type, image_cdn}
    seen = set()
    max_stories = 50
    no_new = 0

    for i in range(max_stories):
        if not is_story_viewer_open(driver):
            print("  ⚠️ Story viewer đóng!")
            break

        # Chờ URL thay đổi + content load
        time.sleep(2)

        # Lấy URL hiện tại
        current_url = driver.current_url
        print(f"  [{i+1}] {current_url}")

        if current_url in seen:
            no_new += 1
            print(f"       ⏭ Trùng ({no_new})")
        elif "/photo/" in current_url or "/video/" in current_url:
            seen.add(current_url)
            no_new = 0

            story_type = "photo" if "/photo/" in current_url else "video"
            entry = {"url": current_url, "type": story_type}

            # Nếu là photo → bắt CDN URL + music từ DOM ngay!
            if story_type == "photo":
                cdn = get_image_cdn_from_dom(driver)
                music = get_music_from_dom(driver)
                if cdn:
                    entry["image_cdn"] = cdn
                if music:
                    entry["music"] = music
                    # Download audio ngay (CDN hết hạn nhanh!)
                    audio_src = music.get("audio_src", "")
                    if audio_src and audio_src.startswith("http"):
                        story_id = current_url.rstrip("/").split("/")[-1]
                        audio_path = os.path.join(STORY_DIR, f"audio_{story_id}.mp3")
                        # Skip nếu đã có file
                        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 500:
                            entry["audio_file"] = audio_path
                            print(f"       ♪ Audio đã có (skip)")
                        else:
                            try:
                                resp = requests.get(
                                    audio_src,
                                    headers={
                                        "User-Agent": "Mozilla/5.0",
                                        "Referer": "https://www.tiktok.com/",
                                    },
                                    timeout=30
                                )
                                if resp.status_code == 200 and len(resp.content) > 500:
                                    with open(audio_path, "wb") as f:
                                        f.write(resp.content)
                                    entry["audio_file"] = audio_path
                                    print(f"       ♪ Audio saved ({format_filesize(len(resp.content))})")
                                else:
                                    print(f"       ♪ Audio download failed ({resp.status_code})")
                            except Exception as e:
                                print(f"       ♪ Audio error: {e}")
                print(f"       ✅ Photo" + (" [CDN]" if cdn else "") + (" [♪]" if music else ""))
            else:
                print(f"       ✅ Video")

            stories.append(entry)
        elif "tiktok.com" in current_url and current_url not in seen:
            seen.add(current_url)
            no_new = 0
            # Thử bắt image CDN cho trường hợp URL không rõ
            cdn = get_image_cdn_from_dom(driver)
            entry = {"url": current_url, "type": "unknown"}
            if cdn:
                entry["image_cdn"] = cdn
                entry["type"] = "photo"
            stories.append(entry)
            print(f"       ✅ {entry['type']}")
        else:
            no_new += 1
            print(f"       ⚠️ URL lạ ({no_new})")

        if no_new >= 3:
            print("  ℹ️ 3 lần trùng/lạ → dừng.")
            break

        # Chuyển story tiếp
        if not click_next_story(driver):
            print("  ℹ️ Không chuyển tiếp → dừng.")
            break

    print(f"\n  📊 Tổng stories thu thập: {len(stories)}")
    for s in stories:
        tag = "📷" if s["type"] == "photo" else "🎬"
        cdn_tag = " [CDN ✅]" if s.get("image_cdn") else ""
        print(f"    {tag} {s['url']}{cdn_tag}")
    return stories


# ============================================================
#  PHASE 2: Dùng yt-dlp xử lý từng URL
# ============================================================
def process_stories(collected):
    """Phase 2: Lấy CDN URLs. Photo từ Phase 1, Video từ yt-dlp. KHÔNG download."""
    print("\n" + "=" * 50)
    print("📥 PHASE 2: Lấy CDN URLs (stream mode)...")
    print("=" * 50 + "\n")

    stories_data = []

    for i, entry in enumerate(collected, 1):
        url = entry["url"]
        stype = entry.get("type", "unknown")
        print(f"  [{i}/{len(collected)}] {stype.upper()} | {url}")

        story = {
            "url": url,
            "type": stype,
            "index": i - 1,
            "timestamp": datetime.now().isoformat(),
        }

        # Extract ID
        parts = url.rstrip("/").split("/")
        story["story_id"] = parts[-1] if parts else ""

        # === PHOTO: CDN + music từ Phase 1 ===
        if stype == "photo":
            cdn = entry.get("image_cdn", "")
            if cdn:
                story["cdn_url"] = cdn
                print(f"       ✅ CDN: {cdn[:65]}...")
            else:
                print(f"       ⚠️ Không có CDN cho photo")

            # Music từ DOM
            music = entry.get("music")
            if music:
                story["music"] = music
                print(f"       ♪ Music: {music.get('music_text', '')[:50]}")
            # Audio file đã download
            if entry.get("audio_file"):
                story["audio_file"] = entry["audio_file"]

        # === VIDEO: yt-dlp extract CDN ===
        elif stype == "video":
            if not YTDLP_AVAILABLE:
                print(f"       ❌ yt-dlp chưa cài!")
                stories_data.append(story)
                print()
                continue

            try:
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'nocheckcertificate': True,
                    'skip_download': True,
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)

                if info:
                    cdn_url = info.get("url", "")
                    if not cdn_url:
                        formats = info.get("formats", [])
                        if formats:
                            cdn_url = formats[-1].get("url", "")

                    story["cdn_url"] = cdn_url
                    story["title"] = info.get("title", "")
                    story["duration"] = info.get("duration", 0)
                    story["thumbnail"] = info.get("thumbnail", "")

                    # Music info
                    track = info.get("track", "") or info.get("music", "")
                    artist = info.get("artist", "") or info.get("creator", "")
                    if track or artist:
                        story["music"] = {
                            "title": track,
                            "author": artist,
                        }
                        print(f"       ♪ Music: {track} - {artist}")

                    if cdn_url:
                        print(f"       ✅ CDN: {cdn_url[:65]}...")
                    else:
                        print(f"       ⚠️ yt-dlp: không tìm thấy CDN")
            except Exception as e:
                print(f"       ⚠️ yt-dlp error: {e}")
        else:
            print(f"       ⚠️ Unknown type")

        stories_data.append(story)
        print()

    return stories_data



def scrape_stories():
    """Main: Phase 1 (collect URLs) + Phase 2 (extract CDN URLs). Không download."""
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import ElementClickInterceptedException

    print(f"""
╔══════════════════════════════════════════════════╗
║  📖 TikTok Story Scraper - yt-dlp Edition       ║
║  Thu thập Stories từ profile TikTok              ║
╚══════════════════════════════════════════════════╝

👤 Target: @{TARGET_USER}
🔗 URL:    {TIKTOK_URL}
📂 Output: {STORY_DIR}
🔧 yt-dlp: {"✅ " + yt_dlp.version.__version__ if YTDLP_AVAILABLE else "❌ Not installed"}
    """)

    ensure_dirs()

    # ============================
    # PHASE 1: Thu thập URLs
    # ============================
    print("🚀 Khởi động Chrome...")
    driver, display = setup_chrome()
    story_urls = []

    try:
        print(f"\n📡 Mở profile @{TARGET_USER}...")
        driver.get(TIKTOK_URL)
        time.sleep(6)

        # Đóng popup
        for sel in [
            'button[data-e2e="modal-close-inner-button"]',
            'div[class*="DivCloseIcon"]',
        ]:
            try:
                btn = driver.find_element(By.CSS_SELECTOR, sel)
                if btn.is_displayed():
                    btn.click()
                    time.sleep(0.5)
                    print("  ✅ Đóng popup")
            except:
                continue



        # Click avatar mở Story
        print("\n🔍 Click avatar mở Story...")
        avatar_clicked = False
        for sel in [
            'div[data-e2e="user-avatar"] img',
            'span[data-e2e="user-avatar"] img',
            'div[data-e2e="user-avatar"]',
        ]:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                if el.is_displayed():
                    try:
                        el.click()
                    except ElementClickInterceptedException:
                        driver.execute_script("arguments[0].click();", el)
                    avatar_clicked = True
                    print(f"  ✅ Click avatar ({sel})")
                    break
            except:
                continue

        if not avatar_clicked:
            print("  ❌ Không click được avatar!")
            return []

        # Chờ story viewer
        print("\n⏳ Chờ #stories-player...")
        time.sleep(5)

        for _ in range(5):
            if is_story_viewer_open(driver):
                print("  ✅ Story viewer mở!")
                break
            time.sleep(1)
        else:
            print("  ❌ Story viewer không mở!")

            return []



        # Thu thập URLs
        story_urls = collect_story_urls(driver)

        # Lưu cookies cho API proxy CDN
        try:
            cookies = driver.get_cookies()
            cookie_path = os.path.join(OUTPUT_DIR, "tiktok_cookies.json")
            with open(cookie_path, "w", encoding="utf-8") as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            print(f"\n🍪 Saved {len(cookies)} cookies → {cookie_path}")
        except Exception as e:
            print(f"\n⚠️ Cookie save error: {e}")

    except Exception as e:
        print(f"\n❌ Lỗi Phase 1: {e}")
        import traceback
        traceback.print_exc()
    finally:

        try:
            driver.quit()
        except OSError:
            pass
        except:
            pass
        if display:
            try:
                display.stop()
            except:
                pass

    if not story_urls:
        print("\n😔 Không thu thập được URL nào.")
        return []

    # ============================
    # PHASE 2: yt-dlp download
    # ============================
    stories_data = process_stories(story_urls)
    return stories_data


def display_results(stories_data):
    if not stories_data:
        print("\n⚠️ Không thu thập được story nào!")
        return

    if RICH_AVAILABLE:
        console = Console()
        console.print(Panel(
            f"[bold cyan]📖 TikTok Story Scraper (yt-dlp)[/bold cyan]\n"
            f"[white]@{TARGET_USER}[/white]\n"
            f"[green]Tổng: {len(stories_data)} stories[/green]",
            box=box.DOUBLE, border_style="cyan"
        ))

        table = Table(title="📹 Stories", box=box.ROUNDED, show_lines=True,
                      header_style="bold magenta")
        table.add_column("#", width=4, justify="center")
        table.add_column("Loại", width=8)
        table.add_column("CDN", width=4)
        table.add_column("ID", width=22)
        table.add_column("CDN URL", max_width=50, overflow="ellipsis")

        for idx, s in enumerate(stories_data, 1):
            stype = s.get("type", "?")
            has_cdn = "✅" if s.get("cdn_url") else "❌"
            sid = s.get("story_id", "")[:20]
            cdn_display = s.get("cdn_url", "")[:50]
            table.add_row(str(idx), stype, has_cdn, sid, cdn_display)
        console.print(table)

        videos = sum(1 for s in stories_data if s.get("type") == "video")
        photos = sum(1 for s in stories_data if s.get("type") == "photo")
        has_cdn = sum(1 for s in stories_data if s.get("cdn_url"))
        console.print(f"\n📊 Video: {videos} | Photo: {photos} | "
                       f"CDN URLs: {has_cdn}/{len(stories_data)}")


def save_to_json(stories_data):
    """Lưu vào file JSON cố định (overwrite mỗi cycle)."""
    filename = os.path.join(OUTPUT_DIR, f"tiktok_diary_{TARGET_USER}.json")

    with open(filename, "w", encoding="utf-8") as f:
        json.dump({
            "scrape_info": {
                "target_user": TARGET_USER,
                "scrape_time": datetime.now().isoformat(),
                "total_stories": len(stories_data),
                "method": "browser_collect_urls_then_ytdlp",
            },
            "stories": stories_data
        }, f, ensure_ascii=False, indent=2)

    print(f"\n💾 JSON: {filename}")

    # Dọn audio hết hạn
    cleanup_expired_audio(stories_data)

    return filename


def cleanup_expired_audio(stories_data):
    """Xóa audio files của stories đã hết hạn (không còn trong viewer)."""
    import glob as g

    # Lấy danh sách story_id hiện tại
    current_ids = set(s.get("story_id", "") for s in stories_data)

    # Quét tất cả audio files
    audio_files = g.glob(os.path.join(STORY_DIR, "audio_*.mp3"))
    removed = 0
    for f in audio_files:
        # Tách story_id từ filename: audio_7620824822469250325.mp3
        basename = os.path.basename(f)
        file_id = basename.replace("audio_", "").replace(".mp3", "")

        if file_id not in current_ids:
            try:
                os.remove(f)
                removed += 1
                print(f"  🗑️ Xóa audio hết hạn: {basename}")
            except:
                pass

    if removed:
        print(f"  🧹 Đã xóa {removed} audio files hết hạn")
    else:
        print(f"  ✅ Không có audio hết hạn")


STATUS_FILE = os.path.join(OUTPUT_DIR, "story_worker_status.json")
SCRAPE_INTERVAL = 600  # 10 phút


def update_status(status, message="", next_run=None):
    data = {
        "status": status,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "next_run": next_run,
    }
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def run_scrape_cycle():
    """Chạy 1 chu kỳ scrape."""
    update_status("running", "Đang scrape stories...")

    start = time.time()
    stories = scrape_stories()
    elapsed = time.time() - start

    print(f"\n⏱ {elapsed:.1f}s")
    display_results(stories)

    if stories:
        save_to_json(stories)
        update_status("done", f"{len(stories)} stories | {elapsed:.1f}s")
        print(f"\n🎉 Xong! {len(stories)} stories")
    else:
        update_status("done", "Không có story mới")
        print("\n😔 Không có story.")


def main():
    print(f"""
╔══════════════════════════════════════════════════╗
║  ⚙️  Story Worker - Thu thập nhật ký 24h         ║
║  Chạy nền, mỗi {SCRAPE_INTERVAL}s scrape stories           ║
╚══════════════════════════════════════════════════╝

👤 Target:    @{TARGET_USER}
🔗 URL:       {TIKTOK_URL}
📂 Output:    {OUTPUT_DIR}
⏰ Interval:  {SCRAPE_INTERVAL}s ({SCRAPE_INTERVAL // 60} phút)
🔧 yt-dlp:    {"✅ " + yt_dlp.version.__version__ if YTDLP_AVAILABLE else "❌"}
    """)

    ensure_dirs()

    # Chạy ngay lần đầu
    run_scrape_cycle()

    # Loop
    while True:
        next_run = datetime.now().timestamp() + SCRAPE_INTERVAL
        next_time = datetime.fromtimestamp(next_run).strftime('%H:%M:%S')
        print(f"\n⏳ Chu kỳ tiếp theo: {next_time} (sau {SCRAPE_INTERVAL}s)")

        update_status("waiting", f"Đợi chu kỳ tiếp theo", next_time)

        time.sleep(SCRAPE_INTERVAL)
        run_scrape_cycle()


if __name__ == "__main__":
    main()
