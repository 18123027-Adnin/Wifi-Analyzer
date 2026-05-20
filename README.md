# 📡 WiFi Analyzer dengan Firebase (GCP)

**ET3204 Layanan Tersambung dan Komputasi Awan — Kelompok 10**

> Aplikasi analisis jaringan WiFi berbasis Python dengan dashboard Streamlit dan penyimpanan cloud Firebase Firestore (GCP).

---

## Struktur Project

```
wifi-analyzer/
├── app.py                  # Dashboard Streamlit (jalankan ini)
├── scanner.py              # Scanning WiFi menggunakan pywifi
├── firebase_config.py      # Koneksi & operasi Firebase Firestore
├── analyzer.py             # Analisis interferensi & rekomendasi channel
├── requirements.txt        # Dependensi Python
├── serviceAccountKey.json  # ⚠️ TIDAK di-push ke repo (buat sendiri)
└── README.md
```

---

## Setup & Instalasi

### 1. Clone repository
```bash
git clone <url-repository>
cd wifi-analyzer
```

### 2. Install dependensi
```bash
pip install -r requirements.txt
```

### 3. Konfigurasi Firebase Firestore

1. Buka [Firebase Console](https://console.firebase.google.com)
2. Buat project baru (atau gunakan yang sudah ada)
3. Aktifkan **Firestore Database** → pilih mode **Production**
4. Buka **Project Settings** → **Service Accounts** → klik **Generate new private key**
5. Rename file yang didownload menjadi `serviceAccountKey.json`
6. Letakkan file di **root folder project** (sejajar dengan `app.py`)

> ⚠️ **Jangan upload `serviceAccountKey.json` ke GitHub!** Sudah ditambahkan ke `.gitignore`.

### 4. Jalankan scanner (opsional, untuk upload data awal)
```bash
python scanner.py
```

### 5. Jalankan dashboard
```bash
streamlit run app.py
```

Browser akan otomatis membuka `http://localhost:8501`

---

## Cara Penggunaan Dashboard

| Fitur | Cara Akses |
|---|---|
| Scan WiFi | Klik tombol **🔍 Scan Sekarang** di sidebar |
| Auto Refresh | Centang **Auto Refresh** di sidebar, atur interval |
| Filter Band/Kualitas | Gunakan multiselect di sidebar |
| Lihat histori cloud | Centang **Tampilkan Histori Cloud** |

---

## Catatan Teknis

- `pywifi` memerlukan **adapter WiFi yang aktif** dan akses administrator di Windows
- Di Linux, mungkin perlu menjalankan dengan `sudo` agar pywifi dapat mengakses interface WiFi
- Jika `pywifi` tidak tersedia, aplikasi otomatis menggunakan **data dummy** untuk demo/testing
- Firebase Free Tier: 1 GB storage, 50.000 baca/hari — cukup untuk penggunaan normal

---

## Tech Stack

- **Backend**: Python 3.10+
- **WiFi Scanning**: `pywifi`
- **Cloud**: Firebase Firestore (Google Cloud Platform)
- **Dashboard**: Streamlit
- **Visualisasi**: Plotly, Matplotlib
- **Data Processing**: Pandas
