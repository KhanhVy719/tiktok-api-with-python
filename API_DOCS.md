# 📋 TikTok API Documentation

> **Base URL**: `http://localhost:8888`  
> **CORS**: `Access-Control-Allow-Origin: *`

---

## Kiến trúc

```
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  Node 1 — API    │◄───│  Node 2 — Worker │    │  Story Worker    │
│  (node1_api.py)  │    │  (node2_worker)  │    │  (diary_scraper) │
│  Port 8888       │    │  Mỗi 5 phút      │    │  Mỗi 5 phút     │
└──────────────────┘    └──────────────────┘    └──────────────────┘
        │                 cache/                  data/
        ▼                 ├─ videos_meta.json     ├─ tiktok_diary_*.json
    Clients               ├─ thumbnails/          ├─ tiktok_cookies.json
                          └─ slideshow/           └─ stories/
                                                     ├─ img_*.jpg
                                                     └─ audio_*.mp3
```

---

## Endpoints

| Endpoint | Mô tả |
|----------|-------|
| **Tổng hợp** | |
| `GET /api/all` | Profile + posts + stories (tất cả) |
| `GET /api/videos` | Danh sách bài đăng |
| `GET /api/stories/<user>` | Stories 24h |
| `GET /api/status` | Trạng thái workers |
| **Video Streaming** | |
| `GET /stream/<id>` | Stream video (yt-dlp pipe) |
| `GET /hls/<id>/master.m3u8` | HLS streaming ⚡ (nhanh hơn) |
| `GET /hls/<id>/<segment>.ts` | HLS segment |
| **Story** | |
| `GET /story/stream/<id>` | Stream story video |
| `GET /story/image/<id>` | Ảnh story (local file) |
| `GET /story/audio/<id>` | Audio story (local/yt-dlp) |
| **Assets** | |
| `GET /thumb/<id>` | Thumbnail đã cache |
| `GET /slideshow/<id>/<index>` | Ảnh slideshow (index từ 0) |
| `GET /audio/<id>` | Audio slideshow |
| `GET /avatar` | Avatar đã cache |

---

## `GET /api/all`

### Response

```json
{
  "profile": { ... },
  "posts": { "videos": [...], "photos": [...] },
  "stories": { "videos": [...], "photos": [...], "scrape_time": "..." },
  "summary": { ... }
}
```

### `profile`

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `username` | string | Tên đăng nhập |
| `nickname` | string | Tên hiển thị |
| `bio` | string | Tiểu sử |
| `verified` | boolean | Đã xác minh |
| `avatar.cdn` | string | Avatar CDN |
| `avatar.local` | string | Avatar cached `/avatar` |
| `stats.followers` | number | Người theo dõi |
| `stats.following` | number | Đang theo dõi |
| `stats.total_likes` | number | Tổng likes |
| `stats.total_videos` | number | Tổng bài đăng |

### `posts.videos[]`

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `info.id` | string | ID bài đăng |
| `info.description` | string | Mô tả |
| `info.upload_date` | string | Ngày đăng |
| `info.tiktok_url` | string | Link TikTok |
| `stats.views` | number | Lượt xem |
| `stats.likes` | number | Lượt thích |
| `stats.comments` | number | Bình luận |
| `stats.reposts` | number | Chia sẻ |
| `duration` | string | Thời lượng `"0:24"` |
| `urls.stream` | string | `/stream/<id>` |
| `urls.hls` | string | `/hls/<id>/master.m3u8` |
| `urls.thumbnail_cdn` | string | Ảnh bìa CDN |
| `urls.thumbnail_local` | string | `/thumb/<id>` |

### `posts.photos[]`

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `info.*` / `stats.*` | | Giống videos |
| `slideshow_count` | number | Số ảnh |
| `urls.slideshow` | string[] | `/slideshow/<id>/0`, `/1`... |
| `music.title` | string | Tên nhạc |
| `music.author` | string | Tác giả |
| `music.audio_url` | string | `/audio/<id>` |

### `stories.videos[]`

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `id` | string | Story ID |
| `url` | string | Link TikTok |
| `stream` | string | `/story/stream/<id>` |
| `hls` | string | `/hls/<id>/master.m3u8` |
| `thumbnail` | string | Ảnh bìa |
| `music.title` | string | Tên nhạc |
| `music.author` | string | Tác giả |

### `stories.photos[]`

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `id` | string | Story ID |
| `url` | string | Link TikTok |
| `image` | string | `/story/image/<id>` |
| `cdn_url` | string | CDN gốc (tham khảo) |
| `music.title` | string | Tên nhạc |
| `music.audio_stream` | string | `/story/audio/<id>` |

### `summary`

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `total_posts` | number | Tổng bài đăng |
| `video_count` / `photo_count` | number | Số video / ảnh |
| `story_video_count` / `story_photo_count` | number | Số story video / ảnh |
| `last_update` | string | Lần cập nhật cuối |

---

## Streaming

### `/stream/<id>` — Direct pipe
Pipe toàn bộ video qua yt-dlp. Chờ lâu hơn trước khi phát.

### `/hls/<id>/master.m3u8` — HLS ⚡
Chia video thành segments 2s → phát ngay. Lần đầu: tạo segments (~5s). Lần sau: cache instant.

```html
<!-- Safari (native HLS) -->
<video src="/hls/VIDEO_ID/master.m3u8"></video>

<!-- Chrome/Firefox (cần hls.js) -->
<script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
<script>
  if (Hls.isSupported()) {
    const hls = new Hls();
    hls.loadSource('/hls/VIDEO_ID/master.m3u8');
    hls.attachMedia(document.getElementById('video'));
  }
</script>
```

### `/story/image/<id>` — Ảnh story
Serve từ file local `data/stories/img_<id>.jpg`. Fallback CDN proxy.

### `/story/audio/<id>` — Audio story
1. File local `audio_<id>.mp3`
2. Cookie proxy CDN
3. yt-dlp pipe (video)

---

## Ví dụ

### Python
```python
import requests

data = requests.get("http://localhost:8888/api/all").json()

# Profile
p = data["profile"]
print(f"{p['nickname']} — {p['stats']['followers']} followers")

# Video
for v in data["posts"]["videos"]:
    print(f"HLS: {v['urls']['hls']}")

# Story photos
for s in data["stories"]["photos"]:
    print(f"Image: {s['image']}")
    if s.get("music"):
        print(f"Audio: {s['music']['audio_stream']}")
```

### JavaScript
```javascript
const data = await fetch("/api/all").then(r => r.json());

// HLS player
data.posts.videos.forEach(v => {
  if (Hls.isSupported()) {
    const hls = new Hls();
    hls.loadSource(v.urls.hls);
    hls.attachMedia(videoElement);
  }
});
```

---

## Ghi chú

| Chủ đề | Chi tiết |
|--------|---------|
| **CDN** | Hết hạn nhanh → luôn dùng API endpoints |
| **Stories** | Ảnh + audio download local trong Phase 1, hết hạn sau 24h |
| **HLS** | Cache `data/hls/<id>/`, tự xóa sau 2h |
| **Cookies** | Browser cookies lưu `data/tiktok_cookies.json`, dùng cho CDN fallback |
| **Cleanup** | Story worker tự xóa `img_*.jpg` + `audio_*.mp3` khi story hết hạn |
