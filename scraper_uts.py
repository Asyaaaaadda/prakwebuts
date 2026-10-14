import os
import shutil
import subprocess
import glob
import time
import pandas as pd

# 1. Direktori penampung hasil prakutsweb
output_dir = "prakutsweb"
os.makedirs(output_dir, exist_ok=True)

# 2. Token autentikasi dan daftar kata kunci
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

# 3. Patch otomatis bug tweet-harvest jika diperlukan
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

# 4. Eksekusi crawling untuk setiap kata kunci
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

# 5. Pengumpulan dan penggabungan berkas CSV ke dalam folder prakutsweb
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
