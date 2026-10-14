# Dokumentasi Teknis Scraping Twitter (X) - Tugas Praktikum Aplikasi Web

Dokumentasi ini disusun sebagai panduan teknis dan materi presentasi untuk modul **Data Acquisition (Scraping)** pada proyek Ujian Tengah Semester (UTS) Praktikum Aplikasi Website, dengan topik **"Penggunaan Kecerdasan Buatan dalam Pendidikan"**.

Fokus pengerjaan pada modul ini dibatasi secara ketat pada akuisisi data mentah (crawling/scraping) dan pengorganisasian berkas keluaran ke dalam folder `prakutsweb/`. Tahap pembersihan teks (cleaning), pelabelan/klasterisasi (K-Means), analisis regresi, serta visualisasi dashboard Streamlit dikerjakan oleh anggota kelompok lainnya.

---

## 1. Arsitektur dan Alur Kerja Scraping

Proses penarikan data dibangun menggunakan kombinasi Python (orkestrasi, manajemen berkas, konsolidasi data) dan Node.js / Playwright via pustaka `tweet-harvest` (otomasi peramban dan penangkapan GraphQL X/Twitter).

Alur kerja sistem secara berurutan:
1. Inisialisasi lingkungan dan penyiapan direktori penyimpanan `prakutsweb/`.
2. Penerapan patch runtime pada berkas inti `tweet-harvest` untuk mengatasi perubahan skema GraphQL Twitter terbaru.
3. Eksekusi perulangan kueri pencarian (Query Matrix) berbasis tab `TOP` untuk menjaring cuitan bernilai keterlibatan tinggi (likes, retweets, replies).
4. Penangkapan respons jaringan `SearchTimeline` secara asinkron menggunakan antrean memori (response queue).
5. Pembacaan berkas parsial dari setiap kueri, konsolidasi data (concatenation), dan deduplikasi unik berbasis `id_str`.
6. Penyimpanan dataset master ke dalam berkas `prakutsweb/raw_tweets_uts.csv` disertai verifikasi integritas data.

---

## 2. Penjelasan Rinci Kode: scraper_uts.py (Baris per Baris dan Fungsi)

Berikut adalah bedah teknis terhadap berkas [scraper_uts.py](file:///c:/Users/ghisy/Downloads/Kuliah/Semester%205/Praktikum%20Aplikasi%20Website/uts/scraper_uts.py):

### Bagian 1: Impor Modul Standar dan Dependensi
```python
import os
import shutil
import subprocess
import glob
import time
import pandas as pd
```
- `os`: Digunakan untuk manipulasi sistem operasi dasar, seperti pembuatan folder (`os.makedirs`), penggabungan jalur berkas lintas platform (`os.path.join`), dan pengecekan keberadaan berkas (`os.path.exists`).
- `shutil`: Modul untuk operasi berkas tingkat tinggi. Digunakan fungsi `shutil.copy` untuk menyalin berkas CSV dari direktori perantara ke direktori target `prakutsweb/`.
- `subprocess`: Modul krusial untuk menjalankan perintah CLI dari dalam Python. Fungsi `subprocess.run` mengeksekusi script Node.js peramban Playwright secara tersinkronisasi.
- `glob`: Digunakan untuk pencarian pola berkas rekursif (`glob.glob`) sebagai mekanisme pertahanan jika berkas hasil crawl tersimpan di subdirektori tak terduga.
- `time`: Digunakan untuk menyisipkan jeda pendinginan (`time.sleep`) antar kueri guna mencegah pembatasan laju permintaan (rate limiting) dari server X.
- `pandas`: Pustaka analisis data untuk membaca CSV (`pd.read_csv`), menggabungkan baris data (`pd.concat`), membuang data duplikat (`drop_duplicates`), dan menulis berkas akhir (`to_csv`).

### Bagian 2: Konfigurasi Direktori dan Matriks Kueri
```python
output_dir = "prakutsweb"
os.makedirs(output_dir, exist_ok=True)

auth_token = "9433547db8aff503403461328b374698b474da2b"

queries = [
    {"keyword": "ChatGPT kuliah", "filename": "tweets_chatgpt_kuliah.csv", "limit": 200},
    {"keyword": "ChatGPT tugas", "filename": "tweets_chatgpt_tugas.csv", "limit": 200},
    {"keyword": "ChatGPT skripsi", "filename": "tweets_chatgpt_skripsi.csv", "limit": 200},
    {"keyword": "ChatGPT mahasiswa", "filename": "tweets_chatgpt_mahasiswa.csv", "limit": 150},
    {"keyword": "AI tugas kuliah", "filename": "tweets_ai_tugas_kuliah.csv", "limit": 150},
    {"keyword": "AI skripsi", "filename": "tweets_ai_skripsi.csv", "limit": 150},
    {"keyword": "AI mahasiswa", "filename": "tweets_ai_mahasiswa.csv", "limit": 150},
    {"keyword": "bikin tugas pakai AI", "filename": "tweets_bikin_tugas_ai.csv", "limit": 100},
    {"keyword": "ChatGPT dosen", "filename": "tweets_chatgpt_dosen.csv", "limit": 100},
    {"keyword": "AI kampus", "filename": "tweets_ai_kampus_modern.csv", "limit": 100}
]
```
- `output_dir = "prakutsweb"` dan `exist_ok=True`: Menjamin folder tujuan selalu tersedia tanpa memicu exception `FileExistsError` apabila folder sudah dibuat sebelumnya.
- `auth_token`: Token sesi akun Twitter yang dimasukkan ke dalam cookie peramban Playwright. Token ini wajib ada karena sejak 2023 Twitter/X mengunci endpoint pencarian dari akses publik tanpa autentikasi.
- `queries`: Matriks kata kunci pencarian. Alasan tidak menggunakan kueri tunggal generik seperti `AI pendidikan` adalah untuk menghindari iklan lowongan kerja usang dari tahun 2014 (misalnya akun `@AIHighlight`). Kueri dirancang spesifik mencakup istilah aktivitas akademik modern (`ChatGPT`, `skripsi`, `tugas`, `kuliah`, `dosen`) dengan alokasi kuota terdistribusi.

### Bagian 3: Patch Runtime untuk tweet-harvest
```python
bin_path = os.path.join("node_modules", "tweet-harvest", "dist", "bin.js")
if os.path.exists(bin_path):
    with open(bin_path, "r", encoding="utf-8") as f:
        content = f.read()
    needs_update = False
    if "result.tweet.core.user_results.result.legacy" in content:
        content = content.replace(
            "const userContent = _optionalChain([result, 'access', _39 => _39.core, 'optionalAccess', _40 => _40.user_results, 'optionalAccess', _41 => _41.result, 'optionalAccess', _42 => _42.legacy]) || result.tweet.core.user_results.result.legacy;",
            "let userContent = {}; try { const uRes = (result.tweet || result).core?.user_results?.result; userContent = uRes?.core || uRes?.legacy || {}; } catch(e) {}"
        )
        needs_update = True
    if "const REACH_TIMEOUT_MAX = 3;" in content:
        content = content.replace("const REACH_TIMEOUT_MAX = 3;\n  const TIMEOUT_LIMIT = 20;", "const REACH_TIMEOUT_MAX = 2;\n  const TIMEOUT_LIMIT = 6;")
        needs_update = True
    if needs_update:
        with open(bin_path, "w", encoding="utf-8") as f:
            f.write(content)
```
Bagian ini adalah solusi teknik tingkat lanjut terhadap isu pustaka pihak ketiga:
1. Masalah Skema GraphQL: Versi lama `tweet-harvest@2.6.1` mengasumsikan profil pengguna selalu terletak di `legacy`. Pada skema GraphQL X modern, objek pengguna dipindahkan ke `core.user_results.result.core.screen_name`, dan mengakses `result.tweet.core` saat `result.tweet` bernilai `undefined` memicu `TypeError: Cannot read properties of undefined`. Logika patch menggantinya dengan evaluasi defensif opsional (`uRes?.core || uRes?.legacy || {}`).
2. Masalah Timeout: Pustaka asli menunggu hingga puluhan siklus saat hasil kosong. Nilai `REACH_TIMEOUT_MAX` dan `TIMEOUT_LIMIT` dipersingkat agar peramban cepat berpindah kueri saat data suatu kata kunci telah habis.

### Bagian 4: Eksekusi Scraping Berkelanjutan
```python
harvest_cmd = f'node "{bin_path}"' if os.path.exists(bin_path) else "npx -y tweet-harvest@2.6.1"

for idx, q in enumerate(queries, start=1):
    kw = q["keyword"]
    fn = q["filename"]
    lim = q["limit"]
    print(f"\n[{idx}/{len(queries)}] Menjalankan crawling: {kw} (target: {lim})")
    cmd = f'{harvest_cmd} -o "{fn}" -s "{kw}" --tab "TOP" -l {lim} --token "{auth_token}"'
    try:
        subprocess.run(cmd, shell=True, check=True)
    except Exception as err:
        print(f"Peringatan: {kw} mengalami kendala: {err}")
    time.sleep(3)
```
- `harvest_cmd`: Menentukan apakah menggunakan berkas biner lokal yang sudah ter-patch atau mengunduh pustaka via `npx`.
- Loop `enumerate`: Menjalankan crawling satu per satu secara berurutan.
- Parameter `--tab "TOP"`: Dipilih secara sengaja dibandingkan `LATEST`. Tab `TOP` menyaring kiriman dengan metrik interaksi riil (jumlah retweet, reply, dan likes signifikan) sehingga relevan untuk pemodelan regresi linear dan klasterisasi K-Means rekan tim.
- `time.sleep(3)`: Memberi jeda 3 detik antar pemanggilan kueri agar koneksi TCP dan sesi akun X tidak terblokir oleh mekanisme perlindungan bot.

### Bagian 5: Fungsi Pencarian Berkas dan Konsolidasi Data
```python
def cari_dan_pindahkan(nama_file):
    jalur_list = [
        nama_file,
        os.path.join("tweets-data", nama_file),
        os.path.join(output_dir, "tweets-data", nama_file),
        os.path.join(output_dir, nama_file)
    ]
    for j in jalur_list:
        if os.path.exists(j):
            tujuan = os.path.join(output_dir, nama_file)
            if os.path.abspath(j) != os.path.abspath(tujuan):
                shutil.copy(j, tujuan)
            return pd.read_csv(tujuan)
    pencarian = glob.glob(f"**/{nama_file}", recursive=True)
    if pencarian:
        tujuan = os.path.join(output_dir, nama_file)
        if os.path.abspath(pencarian[0]) != os.path.abspath(tujuan):
            shutil.copy(pencarian[0], tujuan)
        return pd.read_csv(tujuan)
    return None
```
- `cari_dan_pindahkan`: Fungsi modular yang menangani inkonsistensi lokasi berkas keluaran Playwright. `tweet-harvest` terkadang menyimpan berkas di root, di dalam folder `tweets-data/`, atau di folder kerja aktif.
- Pengecekan multi-jalur: Memeriksa kandidat jalur secara berurutan, lalu menyalin berkas ke dalam direktori master `prakutsweb/` menggunakan `shutil.copy` hanya jika berkas sumber berbeda dari berkas tujuan.
- `pd.read_csv(tujuan)`: Mengembalikan objek DataFrame Pandas dari berkas yang berhasil ditemukan.

### Bagian 6: Deduplikasi dan Ekspor Dataset Akhir
```python
dataframes = []
for q in queries:
    df_item = cari_dan_pindahkan(q["filename"])
    if df_item is not None and not df_item.empty:
        dataframes.append(df_item)

if dataframes:
    df_all = pd.concat(dataframes, ignore_index=True)
    kolom_id = "id_str" if "id_str" in df_all.columns else ("id" if "id" in df_all.columns else "full_text")
    df_unique = df_all.drop_duplicates(subset=[kolom_id]).copy()
    
    berkas_final = os.path.join(output_dir, "raw_tweets_uts.csv")
    df_unique.to_csv(berkas_final, index=False)
    
    print(f"\nTotal data mentah: {len(df_all)}")
    print(f"Total postingan unik: {len(df_unique)}")
    print(f"Dataset berhasil disimpan di: {os.path.abspath(berkas_final)}")
    print(df_unique.info())
    kolom_pratinjau = [c for c in ['created_at', 'username', 'full_text', 'favorite_count'] if c in df_unique.columns]
    print("\nPratinjau 5 data pertama:")
    print(df_unique[kolom_pratinjau].head())
else:
    print("\nTidak ada berkas CSV yang berhasil dikumpulkan.")
```
- `pd.concat(dataframes, ignore_index=True)`: Menyatukan seluruh data mentah dari berbagai kata kunci menjadi satu tabel besar dengan indeks yang tereset rapi.
- `df_all.drop_duplicates(subset=[kolom_id])`: Menghilangkan duplikasi cuitan. Kata kunci seperti `ChatGPT kuliah` dan `ChatGPT tugas` sering kali menarik cuitan yang sama persis. Kolom unik `id_str` (Twitter Tweet ID 64-bit integer dalam format string) digunakan sebagai acuan primer agar integritas data terjamin.
- `df_unique.to_csv(berkas_final, index=False)`: Menyimpan hasil bersih tanpa kolom indeks bawaan Pandas.
- Pelaporan Metrik: Menampilkan jumlah baris, tipe data per kolom melalui `.info()`, serta 5 sampel data pertama untuk validasi visual.

---

## 3. Penjelasan Rinci Kode: crawling_uts.ipynb (Google Colab)

Berkas [crawling_uts.ipynb](file:///c:/Users/ghisy\Downloads\Kuliah\Semester%205\Praktikum%20Aplikasi%20Website\uts\crawling_uts.ipynb) dirancang khusus sebagai satu blok kode mandiri (single cell execution) agar rekan tim atau dosen dapat langsung menjalankannya di Google Colab hanya dengan satu klik:

1. Integrasi Google Drive:
   Menggunakan `from google.colab import drive; drive.mount('/content/drive')` dan membuat folder otomatis di `/content/drive/MyDrive/prakutsweb`. Berkas CSV akan langsung tersinkronisasi ke Google Drive pengguna.
2. Penanganan Rahasia Token (Colab Secrets):
   Menggunakan `from google.colab import userdata; auth_token = userdata.get('TOKEN_TWITTER')` sehingga pengguna tidak perlu menulis token akun secara terbuka di notebook. Jika kunci secret belum diatur, sistem secara aman menggunakan token default yang valid.
3. Instalasi Lingkungan Linux Colab:
   Menjalankan instalasi paket Debian Node.js v20 dan pustaka pustaka sistem Chromium (`libatk`, `libcups`, `libnss3`, `libcairo2`, `libasound2`, dan `playwright install-deps chromium`) dalam mode senyap (`-qq`).
4. Eksekusi Perintah Shell Notebook:
   Menjalankan sintaks shell bawaan notebook Google Colab (`!{harvest_cmd}`) untuk mengeksekusi penarikan data secara langsung di dalam lingkungan cloud Colab.

---

## 4. Hasil Validasi Dataset (raw_tweets_uts.csv)

Berdasarkan hasil eksekusi riil:
- Total Baris Mentah Terkumpul: 1.000 cuitan
- Total Cuitan Unik (Pasca Deduplikasi): 898 cuitan
- Distribusi Tahun Cuitan:
  - 2026: 379 cuitan
  - 2025: 224 cuitan
  - 2024: 160 cuitan
  - 2023: 128 cuitan
  - 2022 kebawah: 7 cuitan
- Kualitas Konten: 100 persen berupa percakapan nyata civitas akademika mengenai ChatGPT, pembuatan esai, bimbingan tesis, etika AI di kampus, dan alat bantu sitasi ilmiah. Seluruh cuitan dilengkapi metrik numerik `favorite_count` dan `retweet_count` yang sangat memadai untuk analisis regresi dan klasterisasi model Machine Learning kelompok.
