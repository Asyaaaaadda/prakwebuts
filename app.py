import re
import joblib
import numpy as np
import pandas as pd
import streamlit as st
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

CSV_DEFAULT, MODEL_PATH, RS = "tweets_cleaned_preprocessed.csv", "model_lr.joblib", 42
REQ = ["text", "created_at", "like_count", "cleaned_text", "word_count", "hashtag_count"]
STOP = set("yang dan di ke dari ini itu untuk dengan atau pada juga sudah udah aja saja ada adalah ya nya "
           "aku kamu kalian saya gue gw lu kita mereka dia jadi bisa kalau kalo sama kok sih deh dong lah "
           "the a to of and in is it for on with you i that this are be as at by".split())
NEG = {"tidak", "tak", "bukan", "ga", "gak", "nggak", "ngga", "enggak", "belum", "jangan", "no", "not", "never"}
POS = set("bagus baik suka keren mantap membantu bantu terbantu mudah senang hebat berguna manfaat cepat pintar canggih "
          "efisien produktif seru puas makasih thanks good great love helpful best amazing nice useful recommended".split())
NGT = set("buruk jelek benci bahaya takut khawatir malas bodoh bohong salah rugi parah curang plagiat cheating sulit susah "
          "lemot error bingung kecewa sedih masalah hoax ketergantungan ngeri gagal merusak mengancam bad hate worse "
          "worst problem wrong stress".split())


def sentiment(t):
    """Lexicon + negasi (kata negasi dipertahankan, membalik polaritas 2 kata berikutnya)."""
    w, s = str(t).split(), 0
    for i, x in enumerate(w):
        p = (x in POS) - (x in NGT)
        if p and any(v in NEG for v in w[max(0, i - 2):i]):
            p = -p
        s += p
    return "Positif" if s > 0 else "Negatif" if s < 0 else "Netral"


@st.cache_data
def load(src):
    return pd.read_csv(src)


@st.cache_resource
def load_model():
    return joblib.load(MODEL_PATH)


@st.cache_data
def run_cluster(texts, k=3):
    v = TfidfVectorizer(stop_words=list(STOP), min_df=3, max_df=0.7)
    X = v.fit_transform(texts)
    km = KMeans(k, n_init=10, random_state=RS).fit(X)
    terms = np.array(v.get_feature_names_out())
    top = [terms[np.argsort(km.cluster_centers_[i])[::-1][:5]].tolist() for i in range(k)]
    return km.labels_, top


st.set_page_config("Dashboard Analisis X", layout="wide")
st.title("📊 Dashboard Analisis Postingan X")
tabs = st.tabs(["Data", "Sentimen", "Clustering", "Regresi"])

# ---------------- Data ----------------
with tabs[0]:
    up = st.file_uploader("Unggah CSV (kosongkan untuk memakai dataset bawaan)", type="csv")
    try:
        raw = load(up if up else CSV_DEFAULT)
    except Exception as e:
        st.error(f"Data tidak dapat dibaca: {e}")
        st.stop()
    miss = [c for c in REQ if c not in raw.columns]
    st.write("Pemeriksaan kolom wajib:", {c: c in raw.columns for c in REQ})
    if miss:
        st.error(f"Kolom wajib tidak tersedia: {miss}. Analisis dihentikan.")
        st.stop()
    df = raw.drop_duplicates("text").copy()
    df["cleaned_text"] = df["cleaned_text"].fillna("").astype(str)
    df["like_count"] = pd.to_numeric(df["like_count"], errors="coerce")
    c1, c2, c3 = st.columns(3)
    c1.metric("Jumlah postingan", len(raw))
    c2.metric("Duplikat dibuang", len(raw) - len(df))
    c3.metric("Teks bersih kosong", int((df.cleaned_text.str.strip() == "").sum()))
    st.dataframe(raw.head(20), use_container_width=True)
    if len(df) < 150:
        st.warning("Jumlah postingan unik kurang dari 150 (syarat minimal tugas).")

ok = df[df.cleaned_text.str.strip() != ""].copy()  # dipakai untuk sentimen & clustering
ok["sentimen"] = ok.cleaned_text.map(sentiment)
excl = len(df) - len(ok)

# ---------------- Sentimen ----------------
with tabs[1]:
    st.caption(f"{len(ok)} postingan dianalisis; {excl} dikeluarkan karena teks bersih kosong (hanya tautan/simbol). "
               "Metode: lexicon sederhana dengan penanganan negasi.")
    cnt = ok.sentimen.value_counts().reindex(["Positif", "Netral", "Negatif"], fill_value=0)
    a, b = st.columns(2)
    a.dataframe(pd.DataFrame({"Jumlah": cnt, "Persen (%)": (cnt / cnt.sum() * 100).round(1)}))
    b.bar_chart(cnt)
    st.dataframe(ok[["text", "sentimen"]], use_container_width=True)

    st.subheader("Pemeriksaan manual (20 postingan acak)")
    st.caption("Isi label manual SEBELUM melihat prediksi sistem. Prediksi baru tampil setelah tombol ditekan.")
    smp = ok.sample(min(20, len(ok)), random_state=RS)[["text"]].reset_index(drop=True)
    smp["label_manual"] = None
    ed = st.data_editor(smp, disabled=["text"], use_container_width=True, key="manual",
                        column_config={"label_manual": st.column_config.SelectboxColumn(
                            options=["Positif", "Netral", "Negatif"])})
    if st.button("Bandingkan dengan prediksi sistem"):
        if ed.label_manual.isna().any():
            st.error("Semua 20 label manual harus diisi terlebih dahulu.")
        else:
            ed["prediksi_sistem"] = ed.text.map(lambda t: sentiment(ok.set_index("text").cleaned_text[t]))
            ed["sesuai"] = ed.label_manual == ed.prediksi_sistem
            n = int(ed.sesuai.sum())
            st.success(f"Sesuai: {n}/{len(ed)} ({n / len(ed) * 100:.1f}%) — evaluasi terbatas, bukan akurasi keseluruhan.")
            st.dataframe(ed[~ed.sesuai], use_container_width=True)
            st.download_button("Unduh evaluasi_sentimen.csv", ed.to_csv(index=False), "evaluasi_sentimen.csv")

# ---------------- Clustering ----------------
with tabs[2]:
    lab, top = run_cluster(tuple(ok.cleaned_text), 3)
    ok["cluster"] = lab
    st.caption("TF-IDF + K-Means (k=3). Beri nama tema setelah membaca kata dominan & contoh.")
    for i in range(3):
        sub = ok[ok.cluster == i]
        name = st.text_input(f"Tema cluster {i}", f"Cluster {i}", key=f"n{i}")
        st.markdown(f"**{name}** — {len(sub)} postingan ({len(sub) / len(ok) * 100:.1f}%)  \n"
                    f"Kata dominan: `{', '.join(top[i])}`")
        for t in sub.text.sample(min(3, len(sub)), random_state=RS):
            st.markdown(f"- {t}")
        st.divider()

# ---------------- Regresi ----------------
with tabs[3]:
    reg = df.dropna(subset=["like_count", "word_count", "hashtag_count"])
    reg = reg[reg.like_count >= 0]
    st.caption(f"{len(reg)} postingan dipakai; {len(df) - len(reg)} dikeluarkan (likes tidak valid). "
               f"Split 80/20, random_state={RS}. Model dimuat dari {MODEL_PATH}.")
    F = ["word_count", "hashtag_count"]
    _, Xte, _, yte = train_test_split(reg[F], reg.like_count, test_size=0.2, random_state=RS)
    try:
        model = load_model()
        pred = model.predict(Xte)
    except Exception as e:
        st.error(f"Model tidak dapat dimuat/dipakai: {e}")
        st.stop()
    m1, m2 = st.columns(2)
    m1.metric("MAE (data uji)", f"{mean_absolute_error(yte, pred):,.1f}")
    m2.metric("R² (data uji)", f"{r2_score(yte, pred):.3f}")
    st.scatter_chart(pd.DataFrame({"Likes aktual": yte.values, "Likes prediksi": pred}),
                     x="Likes aktual", y="Likes prediksi")
    st.caption("MAE = rata-rata selisih absolut prediksi dan likes aktual (satuan: likes). R² mengukur proporsi variasi "
               "likes yang dijelaskan model; R² < 0 berarti model lebih buruk daripada menebak rata-rata.")
    with st.form("est"):
        w = st.number_input("Jumlah kata", 0, 500, 20)
        h = st.number_input("Jumlah hashtag", 0, 50, 0)
        if st.form_submit_button("Estimasi likes"):
            p = float(model.predict(pd.DataFrame([[w, h]], columns=F))[0])
            st.metric("Estimasi likes", f"{p:,.0f}")
            if p < 0:
                st.warning("Estimasi negatif tidak bermakna sebagai jumlah likes — keterbatasan model linear.")

# ---------------- Ringkasan ----------------
st.divider()
st.header("Temuan Utama & Keterbatasan")
mx = cnt.idxmax()
st.markdown(f"""**Temuan** (otomatis dari hasil di atas; sesuaikan narasinya):
1. Sentimen terbanyak adalah **{mx}** ({cnt.max()} dari {cnt.sum()} postingan, {cnt.max() / cnt.sum() * 100:.1f}%).
2. Ukuran cluster: {', '.join(f'C{i}={int((ok.cluster == i).sum())}' for i in range(3))}; kata dominan C0: {', '.join(top[0])}.
3. Model regresi: MAE {mean_absolute_error(yte, pred):,.1f} likes dan R² {r2_score(yte, pred):.3f} pada data uji.

**Keterbatasan**
1. Sentimen memakai lexicon sederhana dan hanya divalidasi pada 20 sampel; hasil tidak mewakili seluruh opini di X.
2. Likes juga dipengaruhi usia postingan, jangkauan akun, dan isi pesan, sehingga jumlah kata & hashtag saja kurang memadai.""")
