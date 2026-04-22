# Monitoring Berita Acara (BA) per Unit

Aplikasi web Flask untuk memantau proyek per unit, menandai penyelesaian proyek
lewat upload file bukti, dan **membuat Berita Acara otomatis langsung dari foto**.

## Fitur

- **Dashboard monitoring** per unit: jumlah proyek, progres, jumlah BA.
- **Manajemen unit & proyek** (CRUD dasar).
- **Selesaikan proyek via upload file** (PDF/DOC/XLS/foto). Proyek otomatis
  ditandai `COMPLETED` dan file bukti disimpan.
- **Buat BA otomatis dari foto langsung**:
    - Halaman `/projects/<id>/ba/capture` membuka kamera perangkat
      (`getUserMedia`, prefers rear camera) atau menerima upload gambar.
    - Backend menyimpan foto + meng-generate **PDF Berita Acara** berisi
      nomor BA, metadata proyek, catatan, foto, dan blok tanda tangan.
- Daftar dan unduh seluruh BA sebagai PDF.

## Stack

- Flask 3 (web), Jinja2 (templating)
- SQLite (stdlib `sqlite3`) - schema auto-init di boot
- ReportLab + Pillow (generator PDF dan penyimpanan foto)
- HTML/CSS/JS vanilla - `getUserMedia` untuk kamera

## Menjalankan

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Akses `http://localhost:5000`.

**Catatan kamera**: `getUserMedia` hanya jalan di `https://` atau `localhost`.
Untuk akses via IP/HP, gunakan reverse proxy HTTPS atau pakai tombol
"Upload Foto" (yang di HP akan membuka kamera native via `capture=environment`).

## Jalankan di GitHub Codespaces (dari iPad / browser apapun)

Repo ini punya `.devcontainer/devcontainer.json` yang otomatis setup Python +
forward port 5000 dengan URL HTTPS publik. **Tidak perlu install apapun di iPad**.

1. Buka `https://github.com/<user>/<repo>` di Safari iPad.
2. Klik tombol hijau **Code** → tab **Codespaces** → **Create codespace on
   `claude/news-monitoring-dashboard-hZfKK`**.
3. Tunggu ~1-2 menit. VS Code terbuka di browser dengan Python siap, deps
   ter-install, dan `python app.py` auto-jalan.
4. Panel **Ports** akan menampilkan URL seperti
   `https://<random>-5000.app.github.dev`. Klik ikon "Open in Browser" atau
   copy URL, buka di tab Safari baru.
5. Karena URL-nya HTTPS, tombol "Aktifkan Kamera" di `/ba/capture` langsung
   jalan di iPad.

Free tier: 60 jam core-hours/bulan (Codespace 2-core → 30 jam real-time / bulan).
Codespace otomatis stop setelah 30 menit idle (settingan default).

## Jalankan di Termux (Android)

1. Install **Termux** dari **F-Droid** (https://f-droid.org/packages/com.termux/) —
   JANGAN dari Play Store (versi Play Store sudah outdated).
2. Buka Termux, jalankan:
   ```bash
   termux-setup-storage            # izin akses storage (opsional)
   pkg update -y && pkg upgrade -y
   pkg install -y git
   git clone <URL-REPO-KAMU> && cd Monitoring-berita-acara
   bash setup_termux.sh
   python app.py
   ```
3. Buka di browser HP yang sama: **http://localhost:5000** → kamera aktif
   karena `localhost` dianggap secure context.
4. Akses dari HP/tablet lain di WiFi yang sama:
   ```bash
   ifconfig | grep "inet "   # cari IP misal 192.168.1.25
   ```
   Lalu buka `http://192.168.1.25:5000` di device lain. Kamera di device lain
   TIDAK akan aktif (HTTP non-localhost), tapi tombol "Upload Foto" tetap jalan.

### Supaya bisa diakses dari internet (opsional)
Pakai tunnel HTTPS dari Termux:
```bash
pkg install -y nodejs
npx localtunnel --port 5000
# atau cloudflared:
pkg install -y cloudflared
cloudflared tunnel --url http://localhost:5000
```
Dapat URL `https://...` yang bisa dibuka siapa saja, kamera pun aktif.

### Supaya tetap jalan di background
Termux kill proses saat di-background. Solusi:
- Aktifkan **Termux:Boot** (F-Droid) → auto-start saat HP boot.
- Gunakan `termux-wake-lock` sebelum menjalankan server, lalu
  jalankan dengan `nohup python app.py > server.log 2>&1 &`.

## Deploy Gratis ke Render.com

1. Buka https://render.com dan sign-in pakai akun GitHub kamu.
2. Push repo ini ke GitHub (kalau belum).
3. Di Render dashboard klik **New +** → **Blueprint** → pilih repo ini.
   Render otomatis membaca `render.yaml` dan membuat service Web.
4. Klik **Apply**. Tunggu ~2-3 menit sampai status **Live**.
5. Buka URL yang diberikan (contoh `https://monitoring-berita-acara.onrender.com`).
   Karena URL-nya `https://`, fitur kamera (`getUserMedia`) langsung jalan di iPad.

Alternatif manual (tanpa blueprint):
- **New + → Web Service** → connect repo.
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
- Plan: **Free**.

### Catatan Free Tier Render
- Service tidur setelah 15 menit idle; request pertama lambat ~30 detik.
- **Disk ephemeral**: SQLite (`data/monitoring.db`) dan file uploads **hilang
  setiap redeploy / restart**. Untuk demo tidak masalah; untuk produksi, pasang
  Persistent Disk (plan berbayar) atau pakai PostgreSQL + object storage.

### Alternatif hosting gratis
- **PythonAnywhere** (free tier persisten): upload file, set WSGI ke `app:app`.
- **Fly.io** (free allowance + volume persisten untuk SQLite): `fly launch`.
- **Railway** ($5 credit gratis/bulan): deploy langsung dari GitHub.

## Struktur

```
app.py              Flask app + routes
database.py         SQLite schema + seed data
ba_generator.py     Simpan foto & generate PDF BA
templates/          Jinja2 templates
static/css/         Styling
uploads/            Runtime: completion, photos, ba (PDF)
data/monitoring.db  Runtime: SQLite database
```

## Skema Data

- `units` - daftar unit.
- `projects` - proyek dibawah unit, punya `status` (`IN_PROGRESS`/`COMPLETED`)
  dan `completion_file` saat selesai.
- `berita_acara` - nomor BA, judul, catatan, referensi foto dan PDF.
