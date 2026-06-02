"""
Calendar Intelligence Engine
Menyimpan daftar event yang mempengaruhi kualitas udara Jakarta,
dan memberikan adjustment factor + deskripsi untuk setiap tanggal.
"""

from datetime import date, timedelta
from typing import Optional
import json

# ─── AQI Adjustment Factor ────────────────────────────────────────────────────
# Nilai positif = polusi naik, negatif = polusi turun
# Skala: 1.0 = normal, 0.7 = turun 30%, 1.3 = naik 30%
# ─────────────────────────────────────────────────────────────────────────────

CALENDAR_EVENTS = {
    # ── Recurring: Musim ───────────────────────────────────────────
    "kemarau": {
        "months": [5, 6, 7, 8, 9, 10],
        "factor": 1.25,
        "icon": "☀️",
        "label": "Musim kemarau",
        "description": "Polusi cenderung lebih tinggi. Minim hujan membuat partikel polutan menumpuk di udara.",
        "tip": "Gunakan masker saat beraktivitas di luar pada siang hari.",
    },
    "hujan": {
        "months": [11, 12, 1, 2, 3, 4],
        "factor": 0.85,
        "icon": "🌧️",
        "label": "Musim hujan",
        "description": "Hujan membantu membersihkan partikel polutan dari udara.",
        "tip": "Kualitas udara relatif lebih baik di musim hujan.",
    },

    # ── Hari Libur Nasional (recurring setiap tahun) ───────────────
    # Format: "MM-DD"
    "tahun_baru": {
        "dates_md": ["01-01"],
        "factor": 1.35,
        "icon": "🎆",
        "label": "Tahun Baru Masehi",
        "description": "Kembang api dan aktivitas malam menyebabkan lonjakan PM2.5 dan PM10.",
        "tip": "Hindari aktivitas luar ruangan dini hari.",
    },
    "kemerdekaan": {
        "dates_md": ["08-17"],
        "factor": 0.80,
        "icon": "🇮🇩",
        "label": "HUT Kemerdekaan RI",
        "description": "Hari libur nasional. Aktivitas kendaraan berkurang signifikan.",
        "tip": "Udara cenderung lebih bersih dari biasanya.",
    },
    "natal": {
        "dates_md": ["12-25"],
        "factor": 0.75,
        "icon": "🎄",
        "label": "Hari Natal",
        "description": "Libur panjang, banyak warga meninggalkan Jakarta.",
        "tip": "Kualitas udara membaik karena volume kendaraan berkurang.",
    },
    "malam_natal": {
        "dates_md": ["12-24"],
        "factor": 1.15,
        "icon": "✨",
        "label": "Malam Natal",
        "description": "Kepadatan lalu lintas meningkat menjelang libur Natal.",
        "tip": "Hindari perjalanan di jam padat malam ini.",
    },
    "tahun_baru_imlek": {
        "dates_md": ["02-10"],  # update tiap tahun
        "factor": 1.30,
        "icon": "🧧",
        "label": "Tahun Baru Imlek",
        "description": "Tradisi kembang api dan petasan meningkatkan partikel polutan.",
        "tip": "PM10 dan PM2.5 cenderung tinggi sekitar perayaan.",
    },
    "hari_buruh": {
        "dates_md": ["05-01"],
        "factor": 0.80,
        "icon": "✊",
        "label": "Hari Buruh Internasional",
        "description": "Hari libur nasional, volume kendaraan berkurang.",
        "tip": "Momen yang baik untuk beraktivitas di luar.",
    },
    "waisak": {
        "dates_md": ["05-23"],
        "factor": 0.82,
        "icon": "☸️",
        "label": "Hari Raya Waisak",
        "description": "Libur nasional, aktivitas industri dan kendaraan berkurang.",
        "tip": "Udara cenderung lebih bersih.",
    },
    "kenaikan_yesus": {
        "dates_md": ["05-29"],
        "factor": 0.83,
        "icon": "✝️",
        "label": "Kenaikan Yesus Kristus",
        "description": "Libur nasional, lalu lintas berkurang.",
        "tip": "Kualitas udara sedikit lebih baik dari hari biasa.",
    },

    # ── Lebaran (tanggal berubah setiap tahun — Islamic calendar) ──
    # Data 2024–2027 (perkiraan)
    "lebaran_2024": {
        "dates": ["2024-04-10", "2024-04-11", "2024-04-12",
                  "2024-04-13", "2024-04-14", "2024-04-15"],
        "factor": 0.45,
        "icon": "🌙",
        "label": "Idul Fitri 1445 H",
        "description": "Ribuan warga Jakarta mudik. Volume kendaraan turun drastis hingga 60–70%.",
        "tip": "Momen terbaik untuk beraktivitas di luar. Udara Jakarta paling bersih.",
    },
    "lebaran_2025": {
        "dates": ["2025-03-30", "2025-03-31", "2025-04-01",
                  "2025-04-02", "2025-04-03", "2025-04-04"],
        "factor": 0.45,
        "icon": "🌙",
        "label": "Idul Fitri 1446 H",
        "description": "Ribuan warga Jakarta mudik. Volume kendaraan turun drastis hingga 60–70%.",
        "tip": "Momen terbaik untuk beraktivitas di luar. Udara Jakarta paling bersih.",
    },
    "lebaran_2026": {
        "dates": ["2026-03-19", "2026-03-20", "2026-03-21",
                  "2026-03-22", "2026-03-23", "2026-03-24"],
        "factor": 0.45,
        "icon": "🌙",
        "label": "Idul Fitri 1447 H",
        "description": "Ribuan warga Jakarta mudik. Volume kendaraan turun drastis hingga 60–70%.",
        "tip": "Momen terbaik untuk beraktivitas di luar. Udara Jakarta paling bersih.",
    },
    "iduladha_2025": {
        "dates": ["2025-06-06", "2025-06-07"],
        "factor": 0.78,
        "icon": "🐑",
        "label": "Idul Adha 1446 H",
        "description": "Libur nasional, aktivitas kendaraan berkurang. Namun pembakaran sampah kurban bisa meningkatkan partikel lokal.",
        "tip": "Secara keseluruhan kualitas udara masih lebih baik dari hari biasa.",
    },
    "iduladha_2026": {
        "dates": ["2026-05-27", "2026-05-28"],
        "factor": 0.78,
        "icon": "🐑",
        "label": "Idul Adha 1447 H",
        "description": "Libur nasional, aktivitas kendaraan berkurang.",
        "tip": "Secara keseluruhan kualitas udara masih lebih baik dari hari biasa.",
    },

    # ── Event Khusus ───────────────────────────────────────────────
    "car_free_day": {
        "day_of_week": 6,  # Sunday
        "hours": "06:00–11:00",
        "factor": 0.88,
        "icon": "🚴",
        "label": "Car Free Day",
        "description": "Setiap Minggu pagi, Jl. MH Thamrin dan Sudirman bebas kendaraan.",
        "tip": "Waktu terbaik untuk jogging atau bersepeda di sekitar Bundaran HI.",
    },
    "kebakaran_hutan_season": {
        "months": [8, 9, 10],
        "factor": 1.40,
        "icon": "🔥",
        "label": "Potensi kiriman asap kebakaran hutan",
        "description": "Periode puncak kebakaran hutan di Kalimantan/Sumatera. Asap dapat terbawa angin ke Jakarta.",
        "tip": "Pantau ISPU harian dan siapkan masker N95.",
    },
    "asian_games": {
        "dates": ["2018-08-18", "2018-09-02"],
        "factor": 0.70,
        "icon": "🏅",
        "label": "Asian Games 2018",
        "description": "Kebijakan rekayasa lalu lintas dan pengurangan kendaraan selama event.",
        "tip": "Contoh sukses perbaikan kualitas udara melalui kebijakan transportasi.",
    },
    "covid_lockdown": {
        "dates_range": [("2020-03-20", "2020-06-30")],
        "factor": 0.50,
        "icon": "😷",
        "label": "Pembatasan COVID-19 (PSBB)",
        "description": "Aktivitas kendaraan turun drastis selama pembatasan sosial.",
        "tip": "Data historis menunjukkan perbaikan kualitas udara signifikan.",
    },
}


def get_events_for_date(target_date: date) -> list[dict]:
    """
    Return list of calendar events yang aktif pada tanggal tertentu.
    """
    events = []
    month = target_date.month
    day   = target_date.day
    dow   = target_date.weekday()  # 0=Mon, 6=Sun
    date_str = target_date.strftime("%Y-%m-%d")
    md_str   = target_date.strftime("%m-%d")

    for key, ev in CALENDAR_EVENTS.items():
        matched = False

        # Exact date match (YYYY-MM-DD list)
        if "dates" in ev and date_str in ev["dates"]:
            matched = True

        # Monthly pattern (MM-DD list)
        if "dates_md" in ev and md_str in ev["dates_md"]:
            matched = True

        # Month range (e.g. musim kemarau/hujan)
        if "months" in ev and month in ev["months"]:
            matched = True

        # Day of week (e.g. Car Free Day = Sunday)
        if "day_of_week" in ev and dow == ev["day_of_week"]:
            matched = True

        # Date range
        if "dates_range" in ev:
            for (start_str, end_str) in ev["dates_range"]:
                start = date.fromisoformat(start_str)
                end   = date.fromisoformat(end_str)
                if start <= target_date <= end:
                    matched = True

        if matched:
            events.append({
                "key":         key,
                "label":       ev.get("label", key),
                "icon":        ev.get("icon", "📅"),
                "description": ev.get("description", ""),
                "tip":         ev.get("tip", ""),
                "factor":      ev.get("factor", 1.0),
            })

    return events


def get_combined_factor(target_date: date) -> tuple[float, list[dict]]:
    """
    Hitung combined AQI factor dan return events untuk suatu tanggal.
    Multiple events: faktornya dikalikan (bukan dijumlah).
    """
    events  = get_events_for_date(target_date)
    factor  = 1.0
    for ev in events:
        factor *= ev["factor"]

    # Clamp factor ke range reasonable
    factor = max(0.3, min(2.0, factor))
    return round(factor, 3), events


def get_natural_language_note(factor: float, events: list[dict]) -> str:
    """
    Generate kalimat natural language untuk ditampilkan di app.
    Contoh output: 'Udara lebih bersih dari biasanya — kemungkinan karena Idul Fitri.'
    """
    if not events:
        if factor < 0.9:
            return "Kualitas udara diprediksi sedikit lebih baik dari rata-rata."
        elif factor > 1.1:
            return "Kualitas udara diprediksi sedikit di atas rata-rata."
        return "Kualitas udara diprediksi normal sesuai pola historis."

    primary_event = max(events, key=lambda e: abs(e["factor"] - 1.0))
    label = primary_event["label"]

    if factor < 0.6:
        return f"Udara diprediksi jauh lebih bersih dari biasanya — karena {label}."
    elif factor < 0.85:
        return f"Udara diprediksi lebih bersih dari biasanya — kemungkinan karena {label}."
    elif factor < 0.95:
        return f"Udara sedikit lebih bersih — pengaruh {label}."
    elif factor > 1.4:
        return f"Waspadai penurunan kualitas udara signifikan — periode {label}."
    elif factor > 1.15:
        return f"Kualitas udara diprediksi lebih buruk dari biasanya — periode {label}."
    elif factor > 1.05:
        return f"Kualitas udara sedikit di atas rata-rata — pengaruh {label}."
    return f"Kualitas udara normal — {label}."
