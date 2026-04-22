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
