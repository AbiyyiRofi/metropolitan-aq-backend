"""
Metropolitan Air Quality — FastAPI Application
All endpoints for the Flutter mobile app.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import date
from typing import Optional

from app.utils.predictor import (
    predict_single,
    predict_forecast,
    get_station_stats,
    get_all_stations_today,
    STATIONS,
    CATEGORIES,
    CATEGORY_META,
    BOBOT,
)
from app.utils.calendar_engine import get_events_for_date, get_combined_factor

# ── App Init ──────────────────────────────────────────────────────
app = FastAPI(
    title="Metropolitan Air Quality API",
    description="Backend API untuk aplikasi prediksi kualitas udara DKI Jakarta. "
                "Powered by Random Forest ML model trained on 23,456 data points from 5 stations.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request/Response Models ───────────────────────────────────────

class PredictRequest(BaseModel):
    station:  str   = Field(..., example="DKI1 (Bunderan HI)")
    pm10:     float = Field(..., ge=0, le=1000, example=80.0)
    so2:      float = Field(..., ge=0, le=1000, example=10.0)
    co:       float = Field(..., ge=0, le=1000, example=25.0)
    o3:       float = Field(..., ge=0, le=1000, example=40.0)
    no2:      float = Field(..., ge=0, le=1000, example=15.0)
    month:    int   = Field(..., ge=1, le=12, example=7)


class ForecastRequest(BaseModel):
    station: str = Field(..., example="DKI1 (Bunderan HI)")
    days:    int = Field(30, ge=1, le=60)


# ── Endpoints ─────────────────────────────────────────────────────

@app.get("/", tags=["Info"])
def root():
    return {
        "app":     "Metropolitan Air Quality API",
        "version": "1.0.0",
        "status":  "online",
        "endpoints": [
            "GET  /health",
            "GET  /stations",
            "GET  /today",
            "POST /predict",
            "GET  /forecast/{station}",
            "GET  /calendar/{date}",
            "GET  /station-stats/{station}",
            "GET  /categories",
        ],
    }


@app.get("/health", tags=["Info"])
def health():
    return {"status": "ok", "model": "RandomForest", "accuracy": 0.9697}


@app.get("/stations", tags=["Stations"])
def get_stations():
    """Return daftar semua stasiun pemantauan udara DKI Jakarta."""
    station_info = {
        "DKI1 (Bunderan HI)":    {"area": "Jakarta Pusat", "lat": -6.1944, "lng": 106.8229},
        "DKI2 (Kelapa Gading)":  {"area": "Jakarta Utara", "lat": -6.1575, "lng": 106.9056},
        "DKI3 (Jagakarsa)":      {"area": "Jakarta Selatan", "lat": -6.3350, "lng": 106.8371},
        "DKI4 (Lubang Buaya)":   {"area": "Jakarta Timur", "lat": -6.2856, "lng": 106.9122},
        "DKI5 (Kebon Jeruk)":    {"area": "Jakarta Barat", "lat": -6.1895, "lng": 106.7641},
    }
    return {
        "stations": [
            {"name": s, **info}
            for s, info in station_info.items()
            if s in STATIONS
        ]
    }


@app.get("/today", tags=["Prediction"])
def get_today_all_stations():
    """
    Return prediksi kualitas udara hari ini untuk semua 5 stasiun.
    Digunakan untuk tampilan peta/overview di home screen app.
    """
    results = get_all_stations_today()
    today   = date.today()
    factor, events = get_combined_factor(today)
    return {
        "date":           today.isoformat(),
        "predictions":    results,
        "calendar_events": events,
        "calendar_factor": factor,
    }


@app.post("/predict", tags=["Prediction"])
def predict(req: PredictRequest):
    """
    Prediksi kategori kualitas udara dari input nilai polutan manual.
    Sama persis dengan fungsi Gradio di UAS — digunakan di tab 'Input Manual' Flutter.
    """
    if req.station not in STATIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Stasiun tidak valid. Pilih dari: {STATIONS}"
        )

    result = predict_single(
        pm10=req.pm10, so2=req.so2, co=req.co,
        o3=req.o3, no2=req.no2,
        bulan=req.month, stasiun_name=req.station
    )

    # Tambahkan calendar context untuk bulan ini
    from datetime import date
    today = date.today().replace(day=15, month=req.month)
    factor, events = get_combined_factor(today)

    return {
        **result,
        "calendar_context": {
            "month_factor": factor,
            "events": events,
        }
    }


@app.get("/forecast/{station}", tags=["Forecast"])
def get_forecast(station: str, days: int = 30):
    """
    Return prediksi harian untuk N hari ke depan (default 30).
    Menggabungkan pola historis + calendar intelligence.
    Digunakan di tab 'Forecast' Flutter.
    """
    # Decode URL-encoded station name
    from urllib.parse import unquote
    station = unquote(station)

    if station not in STATIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Stasiun tidak valid. Pilih dari: {STATIONS}"
        )

    if days < 1 or days > 60:
        raise HTTPException(status_code=422, detail="Days harus antara 1–60.")

    forecast = predict_forecast(station, days)
    return {
        "station":  station,
        "days":     days,
        "forecast": forecast,
    }


@app.get("/calendar/{target_date}", tags=["Calendar"])
def get_calendar_events(target_date: str):
    """
    Return event kalender dan adjustment factor untuk tanggal tertentu.
    Format date: YYYY-MM-DD
    """
    try:
        d = date.fromisoformat(target_date)
    except ValueError:
        raise HTTPException(status_code=422, detail="Format tanggal harus YYYY-MM-DD.")

    factor, events = get_combined_factor(d)
    return {
        "date":    target_date,
        "factor":  factor,
        "events":  events,
        "has_special_event": len(events) > 1,
    }


@app.get("/station-stats/{station}", tags=["Stations"])
def get_station_statistics(station: str):
    """
    Return statistik ringkasan dan forecast bulanan untuk satu stasiun.
    Digunakan di tab 'Statistik' Flutter.
    """
    from urllib.parse import unquote
    station = unquote(station)

    if station not in STATIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Stasiun tidak valid. Pilih dari: {STATIONS}"
        )

    return get_station_stats(station)


@app.get("/categories", tags=["Info"])
def get_categories():
    """Return metadata semua kategori kualitas udara (warna, saran, dll)."""
    return {
        "categories": [
            {"name": name, **meta}
            for name, meta in CATEGORY_META.items()
        ],
        "feature_importances": BOBOT,
    }
