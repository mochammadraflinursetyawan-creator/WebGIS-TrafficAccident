// ==========================================================================
// API CLIENT SERVICE - CONNECTS TO FASTAPI BACKEND
// ==========================================================================

const API_BASE = (() => {
  const origin = window.location.origin || "";
  const host = window.location.hostname || "";

  if (!origin || origin === "null") {
    return "http://127.0.0.1:8000/api";
  }

  if (host === "localhost" || host === "127.0.0.1") {
    return new URL(origin).port === "8000" ? "/api" : "http://127.0.0.1:8000/api";
  }

  return "/api";
})();

const api = {
  // SLICE 1 & 5: Ambil data GeoJSON kejadian
  async getAccidents(filters = {}) {
    const params = new URLSearchParams();
    if (filters.status && filters.status !== 'ALL') params.append('status', filters.status);
    if (filters.accident_type && filters.accident_type !== 'ALL') params.append('accident_type', filters.accident_type);
    if (filters.target_date) params.append('target_date', filters.target_date);
    if (filters.until_date) params.append('until_date', filters.until_date);
    if (filters.active_only) params.append('active_only', 'true');

    const url = `${API_BASE}/accidents${params.toString() ? '?' + params.toString() : ''}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error("Gagal mengambil data kecelakaan dari API");
    return await res.json();
  },

  // Ambil detail lengkap satu kejadian
  async getAccidentDetail(accidentId) {
    const res = await fetch(`${API_BASE}/accidents/${accidentId}`);
    if (!res.ok) throw new Error("Gagal memuat detail kejadian");
    return await res.json();
  },

  // SLICE 2: Kirim Laporan Manual Warga (Crowdsourcing)
  async submitReport(payload) {
    const res = await fetch(`${API_BASE}/reports`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error("Gagal mengirim laporan kecelakaan");
    return await res.json();
  },

  // SLICE 3: Review & Verifikasi Status oleh Moderator
  async reviewAccident(accidentId, reviewData) {
    const res = await fetch(`${API_BASE}/accidents/${accidentId}/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(reviewData)
    });
    if (!res.ok) throw new Error("Gagal memperbarui status review");
    return await res.json();
  },

  // Koreksi Titik Lokasi Kejadian oleh Petugas + Auto-Learning
  async updateLocation(accidentId, payload) {
    const res = await fetch(`${API_BASE}/accidents/${accidentId}/location`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error("Gagal menyimpan koreksi lokasi kejadian");
    return await res.json();
  },

  // SLICE 4: Kirim Komentar Warga
  async submitComment(accidentId, commentData) {
    const res = await fetch(`${API_BASE}/accidents/${accidentId}/comments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(commentData)
    });
    if (!res.ok) throw new Error("Gagal mengirim komentar");
    return await res.json();
  },

  // SLICE 6: Simulator Ingestion Pipeline
  async getSimulatorSamples() {
    const res = await fetch(`${API_BASE}/simulator/samples`);
    if (!res.ok) throw new Error("Gagal mengambil sampel tweet");
    return await res.json();
  },

  async runTweetIngest(rawText, author = "@Merapi_Uncover") {
    const res = await fetch(`${API_BASE}/simulator/ingest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ raw_text: rawText, author: author })
    });
    if (!res.ok) throw new Error("Gagal menjalankan pipeline tweet");
    return await res.json();
  },

  // SLICE 7: Trigger Live Selenium Crawler
  async triggerCrawler() {
    const res = await fetch(`${API_BASE}/crawler/trigger`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Gagal menjalankan crawler live");
    }
    return await res.json();
  },

  // Status Poller Otomatis
  async getCrawlerStatus() {
    const res = await fetch(`${API_BASE}/crawler/status`);
    if (!res.ok) throw new Error("Gagal mengambil status crawler");
    return await res.json();
  },

  // Spatial Analytics & Blackspots
  async getBlackspotsAnalytics() {
    const res = await fetch(`${API_BASE}/analytics/blackspots`);
    if (!res.ok) throw new Error("Gagal mengambil data analitik blackspot");
    return await res.json();
  }
};
