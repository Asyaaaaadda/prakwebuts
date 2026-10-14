# Scraping Data Twitter (X) - UTS Praktikum Aplikasi Web

Repository ini berisi skrip crawling data Twitter (X) untuk tugas UTS Praktikum Aplikasi Website dengan topik **Penggunaan AI dalam Pendidikan**.

Data hasil scraping otomatis dikumpulkan, digabung, dan di-deduplikasi ke dalam berkas `prakutsweb/raw_tweets_uts.csv`.

---

## Prasyarat

Pastikan komputer sudah terinstall:
- **Python 3.9+**
- **Node.js (v18+) & npm**
- Akun Twitter (X) untuk mengambil token autentikasi

---

## Cara Menjalankan

### 1. Clone Repository & Masuk Direktori
```bash
git clone https://github.com/Asyaaaaadda/prakwebuts.git
cd prakwebuts
```

### 2. Install Dependensi

**Python:**
```bash
pip install pandas
```

**Node.js / Playwright:**
```bash
npm install
npx playwright install-deps chromium
```

### 3. Masukkan Auth Token Twitter
1. Buka [x.com](https://x.com) di browser dan pastikan sudah login.
2. Buka DevTools (`F12` atau klik kanan > **Inspect**).
3. Buka tab **Application** (Chrome/Edge) atau **Storage** (Firefox) > **Cookies** > `https://x.com`.
4. Cari cookie bernama `auth_token`, lalu salin isinya.
5. Buka `scraper_uts.py`, lalu masukkan token tersebut ke variabel `auth_token`:
   ```python
   auth_token = "PASTE_AUTH_TOKEN_DISINI"
   ```

### 4. Eksekusi Script
```bash
python scraper_uts.py
```

Skrip akan menjalankan crawling secara berurutan sesuai daftar kata kunci, menerapkan patch otomatis, lalu menyatukan hasilnya.

---

## Output

Hasil scraping tersimpan di folder `prakutsweb/`:
- `prakutsweb/raw_tweets_uts.csv` : Dataset master (gabungan seluruh query tanpa duplikasi berdasarkan `id_str`).
- `prakutsweb/tweets_*.csv` : Data mentah per kata kunci pencarian.
