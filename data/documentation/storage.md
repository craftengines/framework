# Storage & Cloud Object Disks

Craft Engine provides a unified, expressive filesystem abstraction for local disks, public assets, and S3-compatible cloud storage (AWS S3, MinIO, Cloudflare R2, Google Cloud Storage).

## 🚀 Basic Usage

```python
from craft.facades import Storage

# 1. Store contents
Storage.put("documents/report.pdf", pdf_bytes)

# 2. Check existence & read
if Storage.exists("documents/report.pdf"):
    content = Storage.get("documents/report.pdf")
    size = Storage.size("documents/report.pdf")
    mime = Storage.mime_type("documents/report.pdf")

# 3. Public or S3 URL
url = Storage.url("documents/report.pdf")

# 4. Signed Temporary URL (for private files)
temp_url = Storage.temporary_url("documents/report.pdf", minutes=15)

# 5. Delete file
Storage.delete("documents/report.pdf")
```

---

## ☁️ Multi-Disk Switching (`local`, `public`, `s3`)

Configured in `config/storage.py`:

```python
# Upload directly to S3 disk
Storage.disk("s3").put("backups/database.sql", backup_content)

# Read from public disk
avatar_url = Storage.disk("public").url("avatars/user_1.jpg")
```
