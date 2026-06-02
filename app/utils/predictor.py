"""
ML Predictor Service
Load model saat startup dan sediakan fungsi prediksi.
"""

import json
import numpy as np
import joblib
from pathlib import Path
from datetime import date, datetime

BASE_DIR = Path(__file__).parent.parent / "models"

# ── Load all artifacts on import ─────────────────────────────────
_model      = joblib.load(BASE_DIR / "rf_model.pkl")
_scaler     = joblib.load(BASE_DIR / "scaler.pkl")
_le         = joblib.load(BASE_DIR / "label_encoder.pkl")
_le_stasiun = joblib.load(BASE_DIR / "station_encoder.pkl")

with open(BASE_DIR / "metadata.json", encoding="utf-8") as f:
    _meta = json.load(f)

FEATURE_COLS     = _meta["feature_cols"]
STATION_MAPPING  = {int(k): v for k, v in _meta["station_mapping"].items()}
CATEGORY_MAPPING = {int(k): v for k, v in _meta["category_mapping"].items()}
HISTORICAL_STATS = _meta["historical_stats"]
CATEGORIES       = _meta["categories"]
STATIONS         = _meta["stations"]
BOBOT            = _meta["feature_importances"]

# Category metadata: warna, saran, level severity
CATEGORY_META = {
    "BAIK": {
        "color_hex":   "#27AE60",
        "color_name":  "green",
        "severity":    1,
        "emoji":       "😊",
        "short_desc":  "Kualitas udara baik",
        "advice":      "Aktivitas luar ruangan aman untuk semua kalangan.",
        "advice_kids": "Aman untuk anak-anak bermain di luar.",
        "aqi_range":   "0–50",
    },
    "SEDANG": {
        "color_hex":   "#F39C12",
        "color_name":  "yellow",
        "severity":    2,
        "emoji":       "😐",
        "short_desc":  "Kualitas udara sedang",
        "advice":      "Kelompok sensitif sebaiknya mengurangi aktivitas berat berkepanjangan di luar.",
        "advice_kids": "Anak-anak asma atau alergi perlu ekstra hati-hati.",
        "aqi_range":   "51–100",
    },
    "TIDAK SEHAT": {
        "color_hex":   "#E74C3C",
        "color_name":  "red",
        "severity":    3,
        "emoji":       "😷",
        "short_desc":  "Tidak sehat",
        "advice":      "Kurangi atau hindari aktivitas luar ruangan berkepanjangan. Gunakan masker.",
        "advice_kids": "Anak-anak sebaiknya bermain di dalam ruangan.",
        "aqi_range":   "101–199",
    },
    "SANGAT TIDAK SEHAT": {
        "color_hex":   "#8E44AD",
        "color_name":  "purple",
        "severity":    4,
        "emoji":       "⚠️",
        "short_desc":  "Sangat tidak sehat",
        "advice":      "Semua kelompok sebaiknya menghindari aktivitas di luar ruangan.",
        "advice_kids": "Anak-anak harus tetap di dalam ruangan dengan jendela tertutup.",
        "aqi_range":   "≥200",
    },
}


def _build_features(pm10: float, so2: float, co: float, o3: float,
                    no2: float, bulan: int, stasiun_encoded: int) -> np.ndarray:
    polutan_score = (
        pm10 * float(BOBOT["pm10"]) +
        o3   * float(BOBOT["o3"])   +
        no2  * float(BOBOT["no2"])  +
        co   * float(BOBOT["co"])   +
        so2  * float(BOBOT["so2"])
    )
    musim_kemarau = 1 if bulan in [5, 6, 7, 8, 9, 10] else 0
    features = [pm10, so2, co, o3, no2, polutan_score, bulan, musim_kemarau, stasiun_encoded]
    return np.array([features])


def predict_single(pm10: float, so2: float, co: float, o3: float,
                   no2: float, bulan: int, stasiun_name: str) -> dict:
    """
    Prediksi kategori kualitas udara dari nilai polutan.
    """
    stasiun_encoded = int(_le_stasiun.transform([stasiun_name])[0])
    X = _build_features(pm10, so2, co, o3, no2, bulan, stasiun_encoded)
    import warnings; warnings.filterwarnings("ignore", category=UserWarning); X_scaled = _scaler.transform(X)

    pred_label = int(_model.predict(X_scaled)[0])
    pred_proba = _model.predict_proba(X_scaled)[0]
    category   = CATEGORY_MAPPING[pred_label]
    confidence = float(pred_proba[pred_label]) * 100

    probabilities = {
        CATEGORY_MAPPING[i]: round(float(p) * 100, 1)
        for i, p in enumerate(pred_proba)
    }

    return {
        "category":      category,
        "confidence":    round(confidence, 1),
        "probabilities": probabilities,
        "category_meta": CATEGORY_META.get(category, {}),
        "dominant_pollutant": _get_dominant_pollutant(pm10, so2, co, o3, no2),
        "input_summary": {
            "pm10": pm10, "so2": so2, "co": co, "o3": o3, "no2": no2,
            "bulan": bulan, "stasiun": stasiun_name,
        },
    }


def predict_forecast(stasiun_name: str, days: int = 30) -> list[dict]:
    """
    Generate prediksi harian untuk N hari ke depan
    berdasarkan pola historis (median per bulan+stasiun).
    """
    from app.utils.calendar_engine import get_combined_factor, get_natural_language_note

    stasiun_encoded = int(_le_stasiun.transform([stasiun_name])[0])
    today   = date.today()
    results = []

    for i in range(days):
        target_date = today + timedelta(days=i)
        bulan       = target_date.month

        # Ambil nilai historis median untuk bulan ini
        hist_key = f"{stasiun_encoded}_{bulan}"
        hist     = HISTORICAL_STATS.get(hist_key, {
            "pm10": 60.0, "so2": 10.0, "co": 20.0, "o3": 40.0, "no2": 15.0
        })

        # Apply calendar factor
        factor, events = get_combined_factor(target_date)
        pm10 = round(hist["pm10"] * factor, 1)
        so2  = round(hist["so2"]  * factor, 1)
        co   = round(hist["co"]   * factor, 1)
        o3   = round(hist["o3"]   * factor, 1)
        no2  = round(hist["no2"]  * factor, 1)

        prediction = predict_single(pm10, so2, co, o3, no2, bulan, stasiun_name)
        note       = get_natural_language_note(factor, events)

        results.append({
            "date":               target_date.isoformat(),
            "day_label":          _get_day_label(target_date, i),
            "category":           prediction["category"],
            "confidence":         prediction["confidence"],
            "category_meta":      prediction["category_meta"],
            "calendar_factor":    factor,
            "calendar_events":    events,
            "natural_language":   note,
            "pollutants":         {"pm10": pm10, "so2": so2, "co": co, "o3": o3, "no2": no2},
            "dominant_pollutant": prediction["dominant_pollutant"],
        })

    return results


def get_station_stats(stasiun_name: str) -> dict:
    """
    Return statistik historis ringkasan untuk satu stasiun.
    """
    from app.utils.calendar_engine import get_combined_factor, get_natural_language_note

    stasiun_encoded = int(_le_stasiun.transform([stasiun_name])[0])

    monthly_forecast = []
    for bulan in range(1, 13):
        hist_key = f"{stasiun_encoded}_{bulan}"
        hist     = HISTORICAL_STATS.get(hist_key, {})
        if not hist:
            continue
        pm10, so2, co, o3, no2 = (hist["pm10"], hist["so2"],
                                   hist["co"], hist["o3"], hist["no2"])
        pred = predict_single(pm10, so2, co, o3, no2, bulan, stasiun_name)
        monthly_forecast.append({
            "bulan":      bulan,
            "bulan_name": _month_name(bulan),
            "category":   pred["category"],
            "color_hex":  pred["category_meta"].get("color_hex", "#888"),
            "pm10_avg":   pm10,
            "o3_avg":     o3,
        })

    return {
        "station_name":     stasiun_name,
        "monthly_forecast": monthly_forecast,
        "model_accuracy":   _meta["model_accuracy"],
        "data_range":       "2010–2025",
        "total_records":    int(23456 / 5),
    }


def get_all_stations_today() -> list[dict]:
    """
    Return prediksi hari ini untuk semua 5 stasiun berdasarkan historis bulan ini.
    """
    today = date.today()
    bulan = today.month
    results = []

    for station in STATIONS:
        stasiun_encoded = int(_le_stasiun.transform([station])[0])
        hist_key = f"{stasiun_encoded}_{bulan}"
        hist = HISTORICAL_STATS.get(hist_key, {
            "pm10": 60.0, "so2": 10.0, "co": 20.0, "o3": 40.0, "no2": 15.0
        })
        pred = predict_single(
            hist["pm10"], hist["so2"], hist["co"],
            hist["o3"], hist["no2"], bulan, station
        )
        results.append({
            "station":    station,
            "category":   pred["category"],
            "confidence": pred["confidence"],
            "color_hex":  pred["category_meta"].get("color_hex", "#888"),
            "emoji":      pred["category_meta"].get("emoji", ""),
            "pollutants": {k: hist[k] for k in ["pm10", "so2", "co", "o3", "no2"]},
        })

    return results


def _get_dominant_pollutant(pm10, so2, co, o3, no2) -> str:
    pollutants = {"PM10": pm10, "SO2": so2, "CO": co, "O3": o3, "NO2": no2}
    weights    = {"PM10": BOBOT["pm10"], "SO2": BOBOT["so2"],
                  "CO": BOBOT["co"],   "O3": BOBOT["o3"], "NO2": BOBOT["no2"]}
    scores = {k: v * weights[k] for k, v in pollutants.items()}
    return max(scores, key=scores.get)


def _get_day_label(d: date, offset: int) -> str:
    if offset == 0: return "Hari ini"
    if offset == 1: return "Besok"
    days = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    return days[d.weekday()]


def _month_name(m: int) -> str:
    names = ["Jan","Feb","Mar","Apr","Mei","Jun","Jul","Agu","Sep","Okt","Nov","Des"]
    return names[m - 1]


# Fix missing import
from datetime import timedelta
