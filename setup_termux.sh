#!/data/data/com.termux/files/usr/bin/bash
# Setup Monitoring BA di Termux (Android)
# Pakai:  bash setup_termux.sh
set -e

echo "==> Update paket Termux..."
pkg update -y && pkg upgrade -y

echo "==> Install paket dasar..."
pkg install -y python git libjpeg-turbo libpng zlib freetype openssl rust binutils

echo "==> Upgrade pip..."
python -m pip install --upgrade pip wheel

echo "==> Install dependencies Python..."
# Pillow kadang gagal dibangun dari source; pakai --prefer-binary
pip install --prefer-binary -r requirements.txt

echo ""
echo "==> Selesai. Jalankan aplikasi:"
echo "    python app.py"
echo ""
echo "Buka di browser HP:        http://localhost:5000"
echo "Dari device lain di WiFi:  http://$(ifconfig 2>/dev/null | awk '/inet /{print $2}' | grep -v 127.0.0.1 | head -1):5000"
