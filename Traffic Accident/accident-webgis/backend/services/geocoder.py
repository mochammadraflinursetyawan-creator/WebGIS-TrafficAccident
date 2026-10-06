import re
import json
import urllib.request
import urllib.parse
from typing import Optional, Tuple, Dict, Any

from backend.services.landmarks import DIY_LOCATIONS, DIY_LOCATION_ACCURACY

# Backward-compatible alias used throughout this module.
YOGYA_LOCATIONS = DIY_LOCATIONS
GENERAL_LOCATION_NAMES = {
    "yogyakarta", "kota yogyakarta", "sleman", "bantul", "kulon progo",
    "gunung kidul", "depok", "mlati", "gamping", "kalasan", "prambanan",
    "piyungan", "ngaglik", "banguntapan", "kasihan", "wates", "sentolo",
    "nanggulan", "kokap", "temon", "pengasih", "wonosari",
}

LOCATION_PATTERNS = [
    # Pola: di/dekat/sekitar/depan/lokasi/area/lewat Jl. Kaliurang / nologaten / selokan mataram / balaiyasa
    r"(?:di|dj|dekat|sekitar|depan|area|seputar|arah|kawasan|lokasi|loaksi|lewat|pas)\s+((?:jl\.?|jalan|ring\s*road|ringroad|flyover|perempatan|pertigaan|simpang|tugu|pom\s*bensin|pom|spbu|selokan\s*mataram|selokan|jembatan|nologaten|seturan|babarsari|balai\s*yasa|balaiyasa|langensari)\s*[^,.\n]*?)(?=[,\.\n]|arah|kondisi|lalin|korban|sudah|pukul|kejadian|ada|\Z)",
    # Pola langsung: Ring Road Utara / Nologaten / Selokan Mataram / Balai Yasa
    r"\b((?:ring\s*road|ringroad|flyover|simpang|perempatan|jalan|jl\.|selokan\s*mataram|nologaten|seturan|babarsari|balai\s*yasa|balaiyasa|langensari)[a-zA-Z0-9\s]*?)(?=[,\.\n]|arah|kondisi|lalin|korban|sudah|pukul|kejadian|ada|\Z)"
]

class GeocodingService:
    """
    Ekstraksi Entitas Lokasi (NER Regex) + Geocoding ke Koordinat EPSG:4326
    """

    def clean_location_noise(self, text: str) -> str:
        # Bersihkan frasa temporal seperti: sekitar jam 7, jam 19.00, pukul 7, dll
        cleaned = re.sub(r"\b(?:sekitar\s+)?(?:jam|pukul)\s+\d+(?:[\.:]\d+)?\b", "", text, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b(?:tadi\s+pagi|siang\s+ini|sore\s+ini|malam\s+ini|barusan|wib)\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b(?:kronologi|blm|belum|diketahui|mohon|samarkan|akun|saya|min|toko|tokonya|tempat)\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"[&]", " and ", cleaned)
        cleaned = re.sub(r"^(?:di|dj|dekat|sekitar|depan|arah|pas|lewat|seputar|lokasi|area|kawasan|ke|menuju)\s+", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.-")
        return cleaned

    def get_locality_tokens(self, value: str) -> set[str]:
        cleaned = re.sub(r"[^a-z0-9\s]", " ", value.lower())
        tokens = set(re.findall(r"[a-z0-9]+", cleaned))
        return {tok for tok in tokens if len(tok) >= 3}

    def is_locally_relevant(self, location_text: str, candidate_display: str) -> bool:
        location_tokens = self.get_locality_tokens(location_text)
        candidate_tokens = self.get_locality_tokens(candidate_display)
        if not location_tokens:
            return True

        # Prioritas: token spesifik yang paling menentukan area harus muncul di hasil yang dipilih.
        required_tokens = {"cebongan", "sumberadi", "mlati", "sleman", "bantul", "banguntapan", "yogyakarta", "jogja"}
        strong_tokens = location_tokens & required_tokens
        if strong_tokens:
            return bool(strong_tokens & candidate_tokens)

        # Untuk nama toko seperti "rahayu" yang akan dibaca sebagai titik spesifik, cukup cek
        # apakah salah satu token lokasi dari input ada di hasil dan itu bukan asal-asalan.
        return bool(location_tokens & candidate_tokens)

    def extract_location_text(self, text: str) -> Optional[str]:
        text_clean = text.strip()
        text_lower = text_clean.lower()

        # Prioritas 0: Cek apakah nama landmark populer ada di teks mentah
        matched_landmarks = [
            landmark for landmark in YOGYA_LOCATIONS if landmark in text_lower
        ]
        if matched_landmarks:
            specific_matches = [
                landmark for landmark in matched_landmarks
                if landmark not in GENERAL_LOCATION_NAMES
            ]
            return max(specific_matches or matched_landmarks, key=len)

        for pattern in LOCATION_PATTERNS:
            match = re.search(pattern, text_clean, re.IGNORECASE)
            if match:
                loc = match.group(1).strip()
                loc = self.clean_location_noise(loc)
                if len(loc) >= 4:
                    return loc
        return None

    def geocode(self, location_text: str) -> Tuple[float, float, str, str, int]:
        """
        Mengubah teks lokasi menjadi koordinat (latitude, longitude, matched_name, precision, uncertainty_radius_m).
        Prioritas 1: Kamus lokasi cepat Yogyakarta (HIGH precision, radius 150m)
        Prioritas 2: OpenStreetMap Nominatim API terkunci viewbox DIY (MEDIUM precision, radius 400m)
        Prioritas 3: Fallback Pusat Yogya (ESTIMATED precision, radius 1500m)
        """
        loc_lower = location_text.lower().strip()

        if loc_lower in {"wilayah yogyakarta", "yogyakarta", "kota yogyakarta"}:
            return (
                -7.7956,
                110.3695,
                f"{location_text} (Perkiraan Yogyakarta)",
                "ESTIMATED",
                3000,
            )

        # 1. Cek Exact/Sub match di kamus lokal Yogya
        exact_match = None
        candidates = []

        for key, val in YOGYA_LOCATIONS.items():
            if key == loc_lower:
                exact_match = val
                break
            if key in loc_lower or loc_lower in key:
                candidates.append((len(key), val))

        if exact_match is not None:
            precision, radius = DIY_LOCATION_ACCURACY.get(loc_lower, ("HIGH", 150))
            return (exact_match[0], exact_match[1], exact_match[2], precision, radius)

        if candidates:
            _, best_val = max(candidates, key=lambda item: item[0])
            return (best_val[0], best_val[1], best_val[2], "HIGH", 150)

        # 2. Coba Nominatim OSM TERKUNCI STRIK DI KOTAK KOORDINAT D.I. YOGYAKARTA
        # Bounding box DIY: Lon: 110.00 - 110.60, Lat: -8.25 - -7.50
        try:
            query = f"{location_text}, Daerah Istimewa Yogyakarta, Indonesia"
            encoded_query = urllib.parse.quote(query)
            url = f"https://nominatim.openstreetmap.org/search?q={encoded_query}&format=json&limit=1&countrycodes=id&viewbox=110.00,-7.50,110.60,-8.25&bounded=1"
            req = urllib.request.Request(url, headers={"User-Agent": "AccidentWebGIS-Jogja/2.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
                if data and len(data) > 0:
                    display_name = data[0].get("display_name", location_text)
                    if not self.is_locally_relevant(location_text, display_name):
                        return (-7.7956, 110.3695, f"{location_text} (Perkiraan Yogyakarta)", "ESTIMATED", 3000)

                    lat = float(data[0]["lat"])
                    lon = float(data[0]["lon"])
                    return (lat, lon, display_name, "MEDIUM", 400)
        except Exception:
            pass

        # Fallback default ke pusat Yogyakarta jika lokasi spesifik tidak ditemukan
        return (-7.7956, 110.3695, f"{location_text} (Perkiraan Yogyakarta)", "ESTIMATED", 3000)
