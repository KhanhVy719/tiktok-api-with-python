# 📋 API Documentation — `/api/all`

> **Endpoint**: `GET /api/all`  
> **Mô tả**: Trả về toàn bộ thông tin profile + tất cả bài đăng (video & ảnh) với đầy đủ CDN URLs.

---

## Cấu trúc JSON

```
{
  "profile": { ... },
  "videos": [ ... ],
  "photos": [ ... ],
  "summary": { ... }
}
```

---

## 1. `profile` — Thông tin người dùng

| Trường | Kiểu | Mô tả |
|---|---|---|
| `username` | string | Tên đăng nhập TikTok |
| `nickname` | string | Tên hiển thị |
| `bio` | string | Tiểu sử |
| `verified` | boolean | Tài khoản đã xác minh |
| `profile_url` | string | Link trang TikTok |

### 1.1 `profile.avatar` — Ảnh đại diện

| Trường | Kiểu | Mô tả |
|---|---|---|
| `cdn` | string | URL gốc trên TikTok CDN (có thể hết hạn) |
| `local` | string | URL ảnh đã cache trên server (`/avatar`) |

### 1.2 `profile.stats` — Thống kê tài khoản

| Trường | Kiểu | Mô tả |
|---|---|---|
| `followers` | number | Số người theo dõi |
| `following` | number | Số người đang theo dõi |
| `total_likes` | number | Tổng lượt thích tất cả bài đăng |
| `total_videos` | number | Tổng số bài đăng |

---

## 2. `videos` — Danh sách bài video

Mảng JSON, mỗi phần tử là 1 bài video.

### 2.1 `videos[].info` — Thông tin cơ bản

| Trường | Kiểu | Mô tả |
|---|---|---|
| `id` | string | ID bài đăng (dùng để gọi API khác) |
| `description` | string | Chú thích / mô tả bài đăng |
| `upload_date` | string | Ngày đăng (dd/mm/yyyy) |
| `tiktok_url` | string | Link gốc trên TikTok |

### 2.2 `videos[].stats` — Lượt tương tác

| Trường | Kiểu | Mô tả |
|---|---|---|
| `views` | number | Lượt xem |
| `likes` | number | Lượt thích |
| `comments` | number | Lượt bình luận |
| `reposts` | number | Lượt chia sẻ |

### 2.3 `videos[].duration`

| Kiểu | Mô tả |
|---|---|
| string | Thời lượng video (vd: `"0:24"`) |

### 2.4 `videos[].urls` — Các đường dẫn

| Trường | Kiểu | Mô tả |
|---|---|---|
| `stream` | string | **URL stream video** — dùng để phát trực tiếp, embed vào `<video>` |
| `thumbnail_cdn` | string | URL ảnh bìa trên TikTok CDN |
| `thumbnail_local` | string | URL ảnh bìa đã cache (`/thumb/<id>`) |

**Ví dụ stream video**:
```html
<video controls src="http://79.108.225.33:8888/stream/7619881771651419413"></video>
```

---

## 3. `photos` — Danh sách bài ảnh (slideshow)

Mảng JSON, mỗi phần tử là 1 bài ảnh.

### 3.1 `photos[].info` — Thông tin cơ bản

_(Giống `videos[].info`)_

| Trường | Kiểu | Mô tả |
|---|---|---|
| `id` | string | ID bài đăng |
| `description` | string | Chú thích |
| `upload_date` | string | Ngày đăng |
| `tiktok_url` | string | Link gốc TikTok |

### 3.2 `photos[].stats` — Lượt tương tác

_(Giống `videos[].stats`)_

### 3.3 `photos[].slideshow_count`

| Kiểu | Mô tả |
|---|---|
| number | Số lượng ảnh trong slideshow |

### 3.4 `photos[].urls` — Các đường dẫn

| Trường | Kiểu | Mô tả |
|---|---|---|
| `slideshow` | string[] | Mảng URL từng ảnh slideshow (`/slideshow/<id>/0`, `.../1`, ...) |
| `thumbnail_cdn` | string | URL ảnh bìa trên TikTok CDN |
| `thumbnail_local` | string | URL ảnh bìa đã cache |

**Ví dụ hiển thị slideshow**:
```html
<img src="http://79.108.225.33:8888/slideshow/7536905686702148880/0">
<img src="http://79.108.225.33:8888/slideshow/7536905686702148880/1">
```

---

## 4. `summary` — Tổng kết

| Trường | Kiểu | Mô tả |
|---|---|---|
| `total_posts` | number | Tổng số bài đăng |
| `video_count` | number | Số bài video |
| `photo_count` | number | Số bài ảnh |
| `last_update` | string | Thời gian cập nhật cuối (ISO 8601) |

---

## Ví dụ gọi API

### Python
```python
import requests

data = requests.get("http://79.108.225.33:8888/api/all").json()

# Profile
p = data["profile"]
print(f"{p['nickname']} — {p['stats']['followers']} followers, {p['stats']['total_likes']} likes")

# Video nhiều view nhất
top = max(data["videos"], key=lambda v: v["stats"]["views"])
print(f"Top video: {top['info']['description'][:40]} — {top['stats']['views']} views")
print(f"Stream: {top['urls']['stream']}")

# Slideshow ảnh
for photo in data["photos"]:
    for i, url in enumerate(photo["urls"]["slideshow"]):
        print(f"Ảnh {i}: {url}")
```

### JavaScript
```javascript
fetch("http://79.108.225.33:8888/api/all")
  .then(r => r.json())
  .then(data => {
    console.log(`${data.profile.nickname} — ${data.profile.stats.followers} followers`);
    data.videos.forEach(v => {
      console.log(`[Video] ${v.info.description} — ${v.stats.views} views`);
    });
  });
```
