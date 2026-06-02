# Metropolitan Air Quality — Backend API

Backend Python FastAPI untuk aplikasi mobile prediksi kualitas udara DKI Jakarta.  
Model: Random Forest | Accuracy: 96.97% | Dataset: 23.456 baris, 5 stasiun, 2010–2025

---

## Cara Deploy ke Railway (gratis, ~5 menit)

### Langkah 1 — Persiapan GitHub

1. Buat akun GitHub di https://github.com jika belum punya
2. Buat repository baru bernama `metropolitan-air-quality-backend`
3. Upload **seluruh isi folder ini** ke repository tersebut

### Langkah 2 — Deploy ke Railway

1. Buka https://railway.app dan login dengan akun GitHub
2. Klik **New Project** → **Deploy from GitHub repo**
3. Pilih repository `metropolitan-air-quality-backend`
4. Railway otomatis mendeteksi `Procfile` dan mulai deploy
5. Tunggu sekitar 2–3 menit hingga status menjadi **Active**

### Langkah 3 — Dapatkan URL API

1. Di dashboard Railway, klik project kamu
2. Klik tab **Settings** → **Domains**
3. Klik **Generate Domain** → kamu akan mendapat URL seperti:
   ```
   https://metropolitan-air-quality-backend-production.up.railway.app
   ```
4. **Simpan URL ini** — ini adalah BASE_URL yang dimasukkan ke Flutter

### Langkah 4 — Test API

Buka browser, akses:
```
https://YOUR-RAILWAY-URL/docs
```
Kamu akan melihat dokumentasi interaktif (Swagger UI). Coba endpoint `/today` untuk memastikan API berjalan.

---

## Endpoint API

| Method | Path | Deskripsi |
|--------|------|-----------|
| GET | `/` | Info API |
| GET | `/health` | Status server |
| GET | `/stations` | Daftar 5 stasiun + koordinat |
| GET | `/today` | Prediksi semua stasiun hari ini |
| POST | `/predict` | Prediksi dari input manual polutan |
| GET | `/forecast/{station}?days=30` | Prediksi 30 hari ke depan |
| GET | `/calendar/YYYY-MM-DD` | Event kalender + factor untuk 1 tanggal |
| GET | `/station-stats/{station}` | Statistik bulanan 1 stasiun |
| GET | `/categories` | Metadata kategori ISPU |

### Contoh Request `/predict`

```json
POST /predict
{
  "station": "DKI1 (Bunderan HI)",
  "pm10": 80.0,
  "so2": 10.0,
  "co": 25.0,
  "o3": 40.0,
  "no2": 15.0,
  "month": 7
}
```

### Contoh Response

```json
{
  "category": "SEDANG",
  "confidence": 97.0,
  "probabilities": {
    "BAIK": 2.5,
    "SEDANG": 97.0,
    "TIDAK SEHAT": 0.5,
    "SANGAT TIDAK SEHAT": 0.0
  },
  "category_meta": {
    "color_hex": "#F39C12",
    "emoji": "😐",
    "advice": "Kelompok sensitif sebaiknya mengurangi aktivitas berat di luar."
  },
  "dominant_pollutant": "O3"
}
```

---

## Struktur Folder

```
metropolitan-air-quality-backend/
├── app/
│   ├── main.py                  ← FastAPI endpoints
│   ├── models/
│   │   ├── rf_model.pkl         ← Model Random Forest (trained)
│   │   ├── scaler.pkl           ← StandardScaler
│   │   ├── label_encoder.pkl    ← LabelEncoder kategori
│   │   ├── station_encoder.pkl  ← LabelEncoder stasiun
│   │   └── metadata.json        ← Feature cols, station/category mapping, historical stats
│   └── utils/
│       ├── predictor.py         ← ML prediction logic
│       └── calendar_engine.py   ← Calendar events & AQI factor
├── requirements.txt
├── Procfile                     ← Railway start command
├── runtime.txt                  ← Python version
└── README.md
```

---

## Catatan Penting

- File `.pkl` dan `metadata.json` di folder `app/models/` **wajib ikut diupload** ke GitHub
- Jangan hapus file-file tersebut karena itu adalah model yang sudah ditraining
- Jika ingin retrain model dengan data baru, jalankan `train_and_save.py` secara lokal lalu upload ulang file `.pkl`
- Railway free tier mati setelah tidak ada traffic selama 15 menit (cold start ~3 detik)
- Untuk production, upgrade ke Railway Hobby Plan ($5/bulan) agar selalu aktif
