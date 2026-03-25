# 📋 TikTok API Documentation

> **Base URL**: `http://localhost:8888`  
> **CORS**: Enabled (`Access-Control-Allow-Origin: *`)

---

## Kiến trúc hệ thống

```
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  Node 1 — API    │◄───│  Node 2 — Worker │    │  Story Worker    │
│  (node1_api.py)  │    │  (node2_worker)  │    │  (diary_scraper) │
│  Port 8888       │    │  Mỗi 5 phút      │    │  Mỗi 10 phút    │
└──────────────────┘    └──────────────────┘    └──────────────────┘
        │                      │                        │
        │                cache/videos_meta.json    data/tiktok_diary_*.json
        │                cache/thumbnails/         data/stories/audio_*.mp3
        │                cache/slideshow/          data/tiktok_cookies.json
        ▼
    Clients (web, app, portfolio)
```

---

## Tổng hợp Endpoints

| Endpoint | Mô tả |
|----------|-------|
| `GET /api/all` | **Tổng hợp**: profile + posts + stories |
| `GET /api/videos` | Danh sách bài đăng |
| `GET /api/stories/<user>` | Danh sách stories 24h |
| `GET /api/status` | Trạng thái worker |
| `GET /stream/<id>` | Stream video (yt-dlp pipe) |
| `GET /hls/<id>/master.m3u8` | **HLS streaming** (nhanh hơn) |
| `GET /hls/<id>/<segment>` | HLS segment .ts |
| `GET /thumb/<id>` | Ảnh thumbnail đã cache |
| `GET /slideshow/<id>/<index>` | Ảnh slideshow |
| `GET /audio/<id>` | Audio nhạc nền slideshow |
| `GET /avatar` | Ảnh avatar đã cache |
| `GET /story/stream/<id>` | Stream story video |
| `GET /story/image?url=<cdn>` | Proxy ảnh story CDN |
| `GET /story/audio/<id>` | Audio story (local/proxy/yt-dlp) |

---

## 1. `GET /api/all` — API Tổng hợp

Trả về toàn bộ profile + bài đăng + stories 24h.

### Response

```json
{
  "profile": { ... },
  "posts": {
    "videos": [ ... ],
    "photos": [ ... ]
  },
  "stories": {
    "videos": [ ... ],
    "photos": [ ... ],
    "scrape_time": "2026-03-25T16:21:35"
  },
  "summary": { ... }
}
```

### 1.1 `profile`

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `username` | string | Tên đăng nhập |
| `nickname` | string | Tên hiển thị |
| `bio` | string | Tiểu sử |
| `verified` | boolean | Đã xác minh |
| `profile_url` | string | Link TikTok |
| `avatar.cdn` | string | Avatar CDN (có thể hết hạn) |
| `avatar.local` | string | Avatar cached (`/avatar`) |
| `stats.followers` | number | Người theo dõi |
| `stats.following` | number | Đang theo dõi |
| `stats.total_likes` | number | Tổng likes |
| `stats.total_videos` | number | Tổng bài đăng |

### 1.2 `posts.videos[]` — Bài đăng video

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `info.id` | string | ID bài đăng |
| `info.description` | string | Mô tả |
| `info.upload_date` | string | Ngày đăng |
| `info.tiktok_url` | string | Link gốc TikTok |
| `stats.views` | number | Lượt xem |
| `stats.likes` | number | Lượt thích |
| `stats.comments` | number | Bình luận |
| `stats.reposts` | number | Chia sẻ |
| `duration` | string | Thời lượng (`"0:24"`) |
| `urls.stream` | string | Stream trực tiếp (`/stream/<id>`) |
| `urls.hls` | string | **HLS stream** (`/hls/<id>/master.m3u8`) |
| `urls.thumbnail_cdn` | string | Ảnh bìa CDN |
| `urls.thumbnail_local` | string | Ảnh bìa cached (`/thumb/<id>`) |

### 1.3 `posts.photos[]` — Bài đăng ảnh slideshow

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `info.*` | | Giống `posts.videos[].info` |
| `stats.*` | | Giống `posts.videos[].stats` |
| `slideshow_count` | number | Số ảnh trong slideshow |
| `urls.slideshow` | string[] | Mảng URL ảnh (`/slideshow/<id>/0`, `/1`, ...) |
| `urls.thumbnail_cdn` | string | Ảnh bìa CDN |
| `urls.thumbnail_local` | string | Ảnh bìa cached |
| `music.title` | string | Tên bài nhạc |
| `music.author` | string | Tác giả |
| `music.audio_url` | string | Stream audio (`/audio/<id>`) |

### 1.4 `stories.videos[]` — Story video 24h

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `id` | string | Story ID |
| `url` | string | Link TikTok gốc |
| `title` | string | Tiêu đề |
| `timestamp` | string | Thời gian thu thập |
| `duration` | number | Thời lượng (giây) |
| `stream` | string | Stream video (`/story/stream/<id>`) |
| `hls` | string | **HLS stream** (`/hls/<id>/master.m3u8`) |
| `thumbnail` | string | Ảnh bìa CDN |
| `music.title` | string | Tên nhạc nền |
| `music.author` | string | Tác giả nhạc |

### 1.5 `stories.photos[]` — Story ảnh 24h

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `id` | string | Story ID |
| `url` | string | Link TikTok gốc |
| `image` | string | Proxy ảnh (`/story/image?url=...`) |
| `cdn_url` | string | CDN URL gốc |
| `music.title` | string | Tên nhạc |
| `music.audio_stream` | string | Stream audio (`/story/audio/<id>`) |

### 1.6 `summary`

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `total_posts` | number | Tổng bài đăng |
| `video_count` | number | Số video |
| `photo_count` | number | Số ảnh |
| `story_video_count` | number | Số story video |
| `story_photo_count` | number | Số story ảnh |
| `last_update` | string | Lần cập nhật cuối |

---

## 2. Streaming Endpoints

### `GET /stream/<id>` — Stream video trực tiếp

Pipe video từ TikTok qua yt-dlp. Trả toàn bộ file.

```html
<video controls src="http://localhost:8888/stream/7619881771651419413"></video>
```

### `GET /hls/<id>/master.m3u8` — HLS Streaming ⚡

Video được chia thành segments 2 giây → load nhanh hơn nhiều.
- Lần đầu: yt-dlp + ffmpeg tạo segments (mất vài giây)
- Lần sau: serve từ cache (instant)

```html
<!-- Native HLS (Safari) -->
<video src="http://localhost:8888/hls/7619881771651419413/master.m3u8"></video>

<!-- Với hls.js (Chrome, Firefox) -->
<script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
<script>
  const video = document.getElementById('video');
  if (Hls.isSupported()) {
    const hls = new Hls();
    hls.loadSource('http://localhost:8888/hls/7619881771651419413/master.m3u8');
    hls.attachMedia(video);
  }
</script>
```

### `GET /story/stream/<id>` — Stream story video

Tương tự `/stream/` nhưng cho story video.

### `GET /story/audio/<id>` — Audio story

Fallback 3 lớp:
1. ✅ File local (`data/stories/audio_<id>.mp3`)
2. 🍪 Cookie proxy CDN URL
3. 🎵 yt-dlp pipe (video stories)

### `GET /story/image?url=<cdn_url>` — Proxy ảnh story

Proxy CDN URL với cookies TikTok. Tránh CORS và 403.

---

## 3. Asset Endpoints

| Endpoint | Content-Type | Mô tả |
|----------|-------------|-------|
| `GET /thumb/<id>` | `image/jpeg` | Ảnh thumbnail đã cache |
| `GET /slideshow/<id>/<index>` | `image/*` | Ảnh slideshow (index từ 0) |
| `GET /audio/<id>` | `audio/mpeg` | Nhạc nền bài ảnh |
| `GET /avatar` | `image/jpeg` | Ảnh avatar đã cache |

---

## 4. Ví dụ sử dụng

### Python

```python
import requests

data = requests.get("http://localhost:8888/api/all").json()

# Profile
p = data["profile"]
print(f"{p['nickname']} — {p['stats']['followers']} followers")

# Video posts
for v in data["posts"]["videos"]:
    print(f"[Video] {v['info']['description'][:40]}")
    print(f"  Stream: {v['urls']['stream']}")
    print(f"  HLS:    {v['urls']['hls']}")

# Photo posts
for p in data["posts"]["photos"]:
    for url in p["urls"]["slideshow"]:
        print(f"  Ảnh: {url}")

# Stories 24h
for s in data["stories"]["videos"]:
    print(f"[Story] {s['title']} — {s['duration']}s")
    print(f"  HLS: {s['hls']}")

for s in data["stories"]["photos"]:
    print(f"[Story Photo] {s['image']}")
    if s.get("music"):
        print(f"  ♪ Audio: {s['music']['audio_stream']}")
```

### JavaScript

```javascript
const res = await fetch("http://localhost:8888/api/all");
const data = await res.json();

// Profile
console.log(`${data.profile.nickname} — ${data.profile.stats.followers} followers`);

// HLS Video Player
data.posts.videos.forEach(v => {
  const video = document.createElement('video');
  video.controls = true;
  if (Hls.isSupported()) {
    const hls = new Hls();
    hls.loadSource(v.urls.hls);
    hls.attachMedia(video);
  } else {
    video.src = v.urls.stream; // fallback
  }
});

// Stories
data.stories.videos.forEach(s => {
  console.log(`[Story] ${s.title} — HLS: ${s.hls}`);
});
```

---

## 5. Ghi chú kỹ thuật

| Chủ đề | Chi tiết |
|--------|---------|
| **CDN URLs** | Hết hạn sau vài phút. Luôn dùng API proxy (`/stream/`, `/hls/`, `/story/image`) |
| **Cookies** | Story worker lưu cookies browser → API dùng khi proxy CDN |
| **HLS Cache** | Segments cached `data/hls/<id>/`, tự xóa sau 2 giờ |
| **Audio Cache** | Photo story audio cached `data/stories/audio_<id>.mp3`, xóa khi story hết hạn |
| **Stories** | Hết hạn sau 24h. Worker quét mỗi 10 phút, tự dọn files cũ |
| **Video Stream** | yt-dlp pipe — CDN URL mới mỗi lần gọi, không cache |
| **CORS** | Tất cả endpoints đều có `Access-Control-Allow-Origin: *` |
