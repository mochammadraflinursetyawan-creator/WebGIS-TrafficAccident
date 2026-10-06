import re
from typing import Dict, Any, Tuple

ACCIDENT_TRIGGERS = [
    r"\blaka\b", r"\bkecelakaan\b", r"\btabrakan\b", r"\btabrak\b", r"\bnabrak\b",
    r"\btertabrak\b", r"\bketabrak\b", r"\bterguling\b", r"\btergulingnya\b",
    r"\bmenabrak\b", r"\bterperosok\b", r"\btersenggol\b", r"\bterserempet\b",
    r"\bkesenggol\b", r"\bkeserempet\b", r"\badu banteng\b", r"\badu kambing\b",
    r"\blaka lantas\b", r"\blaka tunggal\b", r"\bjatuh sendiri\b", r"\bterjatuh\b",
    r"\bnyungsep\b", r"\bkejembrung\b", r"\bkecemplung\b", r"\bkejeglong\b",
    r"\bnjebur\b", r"\bnyebur\b", r"\bambles\b", r"\banjlok\b", r"\bkepleset\b",
    r"\bterpeleset\b", r"\bnjungkel\b", r"\bkejungkel\b",
    r"\bmasuk selokan\b", r"\bmasuk parit\b", r"\bmasuk kali\b",
    r"\bmasuk got\b", r"\bmasuk jurang\b", r"\bpatah as\b", r"\boleng\b",
    r"\brem blong\b", r"\btumburan\b", r"\bterbalik\b", r"\bterlindas\b",
    r"\bkelindes\b", r"\btabrak lari\b", r"\bkorban laka\b", r"\bnaik pembatas\b",
    r"\bnabrak tiang\b", r"\bnabrak pohon\b", r"\bnabrak median\b", r"\bmotor ringsek\b",
    r"\bmobil ringsek\b"
]

# Kata-kata yang murni edukasi/himbauan tanpa ada kejadian nyata
NON_ACCIDENT_TRIGGERS = [
    r"^himbauan\s+tertib\s+lalu\s+lintas",
    r"^tips\s+berkendara",
    r"simulasi\s+evakuasi\s+laka",
    r"sosialisasi\s+keselamatan",
    r"jadwal\s+sim\s+keliling"
]

VEHICLE_PATTERNS = [
    (r"\b(?:motor|sepeda motor|pemotor|vario|beat|scoopy|nmax|pcx|aerox|klx|cb|rx\s*king|vespa|r2|roda dua)\b", "Motorcycle"),
    (r"\b(?:mobil|sedan|avanza|innova|brio|calya|sigra|xenia|agya|ayla|yaris|jazz|fortuner|pajero|pickup|pikap|gran\s*max|carry|r4|roda empat)\b", "Car"),
    (r"\b(?:truk|truck|tronton|fuso|trailer|dump\s*truk|kontainer|truk molen|truk pasir)\b", "Truck"),
    (r"\b(?:bus|trans\s*jogja|bis|efisiensi|sumber selamat|sugeng rahayu|mira|eka)\b", "Bus"),
    (r"\b(?:sepeda|ontel|gowes|pesepeda)\b", "Bicycle"),
    (r"\b(?:pejalan\s*kaki|penyebrang|menyebrang|penyeberang)\b", "Pedestrian")
]

class NLPAccidentClassifier:
    """
    Pipeline NLP Sensitivitas Tinggi untuk @Merapi_Uncover:
    1. Mendeteksi ragam istilah lokal Yogyakarta (nyungsep, adu banteng, patah as, dll)
    2. Menghindari false-negative dari kalimat himbauan yang menyertai laporan laka asli
    3. Klasifikasi multi-moda kendaraan
    4. Estimasi confidence score
    """

    def classify(self, text: str) -> Dict[str, Any]:
        text_lower = text.lower()

        # 1. Cek Kata Kunci Kecelakaan Terlebih Dahulu (Sensitivitas Tinggi)
        matched_triggers = [t for t in ACCIDENT_TRIGGERS if re.search(t, text_lower)]
        
        # 2. Cek Negative Triggers murni (Hanya tolak jika tidak ada indikasi kejadian sama sekali)
        if not matched_triggers:
            for non_trigger in NON_ACCIDENT_TRIGGERS:
                if re.search(non_trigger, text_lower):
                    return {
                        "is_accident": False,
                        "confidence": 0.05,
                        "reason": f"Terdeteksi edukasi/himbauan umum (pola: '{non_trigger}')",
                        "accident_type": "None",
                        "vehicles": []
                    }
            return {
                "is_accident": False,
                "confidence": 0.05,
                "reason": "Tidak mengandung kata kunci kecelakaan lalu lintas",
                "accident_type": "None",
                "vehicles": []
            }

        # 3. Deteksi Kendaraan yang terlibat
        detected_vehicles = []
        for pattern, vtype in VEHICLE_PATTERNS:
            if re.search(pattern, text_lower):
                if vtype not in detected_vehicles:
                    detected_vehicles.append(vtype)

        accident_type = "Motorcycle"
        if len(detected_vehicles) > 1:
            accident_type = "Multiple Vehicle"
        elif len(detected_vehicles) == 1:
            accident_type = detected_vehicles[0]

        # 4. Hitung Confidence Score (0.50 s/d 1.00)
        confidence = 0.65  # Base confidence dinaikkan untuk sensitivitas laporan laka

        if len(matched_triggers) >= 2:
            confidence += 0.10
        if detected_vehicles:
            confidence += 0.10
        
        # Kata situasi darurat khas @Merapi_Uncover
        situational_words = [
            r"\btkp\b", r"\bkorban\b", r"\bluka\b", r"\bpadat\b", r"\bmacet\b", 
            r"\bambulans\b", r"\bmeninggal\b", r"\bry\b", r"\barah\b", r"\bmalam ini\b",
            r"\btadi pagi\b", r"\bbaru saja\b", r"\bdilarikan\b", r"\brumah sakit\b", r"\bpku\b", r"\bsardjito\b"
        ]
        for sw in situational_words:
            if re.search(sw, text_lower):
                confidence += 0.05

        confidence = min(0.98, round(confidence, 2))

        return {
            "is_accident": True,
            "confidence": confidence,
            "reason": f"Terdeteksi laporan kejadian nyata ({', '.join(matched_triggers)})",
            "accident_type": accident_type,
            "vehicles": detected_vehicles
        }
