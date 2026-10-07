// ==========================================================================
// ADMIN DASHBOARD LOGIC — WEBGIS LAKA DIY
// ==========================================================================

let map;
let markerClusterGroup;
let allAccidents = [];
let currentAccidentId = null;
let currentFilter = "ALL";
let isCorrectingLocation = false;
let correctionMarker = null;

const STATUS_COLORS = {
  "VERIFIED": "#10b981",    // Hijau
  "UNDER REVIEW": "#f59e0b",// Kuning
  "DETECTED": "#ef4444",    // Merah
  "REPORTED": "#3b82f6"     // Biru
};

// -------------------------------------------------------------
// 1. Auth Guard & Sesi Petugas
// -------------------------------------------------------------
function checkAdminAuth() {
  const isLoggedIn = sessionStorage.getItem("webgis_admin_logged_in") === "true";
  const overlay = document.getElementById("adminAuthOverlay");
  if (isLoggedIn) {
    overlay.style.display = "none";
  } else {
    overlay.style.display = "flex";
  }
}

function handleAdminLogin(e) {
  e.preventDefault();
  const pin = document.getElementById("adminPinInput").value.trim();
  // PIN Petugas default: 1234
  if (pin === "1234" || pin === "admin123") {
    sessionStorage.setItem("webgis_admin_logged_in", "true");
    document.getElementById("adminAuthOverlay").style.display = "none";
    initAdminApp();
  } else {
    alert("PIN Petugas salah! Silakan masukkan PIN yang benar (Default: 1234).");
    document.getElementById("adminPinInput").value = "";
    document.getElementById("adminPinInput").focus();
  }
}

function handleAdminLogout() {
  if (confirm("Apakah Anda yakin ingin keluar dari Portal Petugas?")) {
    sessionStorage.removeItem("webgis_admin_logged_in");
    document.getElementById("adminAuthOverlay").style.display = "flex";
  }
}

// -------------------------------------------------------------
// 2. Inisialisasi Peta & Basemap
// -------------------------------------------------------------
function initMap() {
  map = L.map("map", {
    center: [-7.7828, 110.3800],
    zoom: 12,
    zoomControl: false
  });

  L.control.zoom({ position: "bottomright" }).addTo(map);

  const osmStandard = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap'
  }).addTo(map);

  const esriSatellite = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
    maxZoom: 19,
    attribution: 'Tiles &copy; Esri'
  });

  L.control.layers({ "OpenStreetMap": osmStandard, "Satelit": esriSatellite }, null, { position: "topright" }).addTo(map);

  markerClusterGroup = L.markerClusterGroup({
    maxClusterRadius: 35,
    spiderfyOnMaxZoom: true,
    showCoverageOnHover: false
  });
  map.addLayer(markerClusterGroup);
}

// -------------------------------------------------------------
// 3. Load Data & Render Antrean Petugas
// -------------------------------------------------------------
async function loadAdminAccidents() {
  try {
    const geojson = await api.getAccidents();
    allAccidents = geojson.features || [];

    updateStats();
    renderQueueList();
    renderMapMarkers();
  } catch (err) {
    console.error("Gagal memuat data laka:", err);
  }
}

function updateStats() {
  const total = allAccidents.length;
  const verified = allAccidents.filter(a => a.properties.status === "VERIFIED").length;
  const detected = allAccidents.filter(a => a.properties.status === "DETECTED" || a.properties.status === "REPORTED").length;

  document.getElementById("statTotal").textContent = total;
  document.getElementById("statVerified").textContent = verified;
  document.getElementById("statDetected").textContent = detected;
}

function filterAdminQueue(tab) {
  currentFilter = tab;
  document.querySelectorAll(".admin-sidebar-header button").forEach(b => {
    b.className = "btn-secondary";
    b.style.background = "";
    b.style.color = "";
  });

  if (tab === "ALL") {
    const btn = document.getElementById("filterTabAll");
    btn.className = "btn-primary";
  } else if (tab === "DETECTED") {
    const btn = document.getElementById("filterTabDetected");
    btn.className = "btn-primary";
    btn.style.background = "#ef4444";
    btn.style.color = "white";
  } else if (tab === "VERIFIED") {
    const btn = document.getElementById("filterTabVerified");
    btn.className = "btn-primary";
    btn.style.background = "#10b981";
    btn.style.color = "white";
  }

  renderQueueList();
}

function renderQueueList() {
  const listEl = document.getElementById("adminQueueList");
  listEl.innerHTML = "";

  let filtered = allAccidents;
  if (currentFilter === "DETECTED") {
    filtered = allAccidents.filter(a => a.properties.status === "DETECTED" || a.properties.status === "REPORTED");
  } else if (currentFilter === "VERIFIED") {
    filtered = allAccidents.filter(a => a.properties.status === "VERIFIED");
  }

  // Urutkan: DETECTED paling atas
  filtered.sort((a, b) => {
    if (a.properties.status === "DETECTED" && b.properties.status !== "DETECTED") return -1;
    if (a.properties.status !== "DETECTED" && b.properties.status === "DETECTED") return 1;
    return b.properties.accident_id - a.properties.accident_id;
  });

  document.getElementById("queueCount").textContent = `${filtered.length} Laporan`;

  if (filtered.length === 0) {
    listEl.innerHTML = `<div style="text-align:center; padding:24px; color:#94a3b8; font-size:0.8rem;">Tidak ada laporan pada kategori ini.</div>`;
    return;
  }

  filtered.forEach(feat => {
    const p = feat.properties;
    const card = document.createElement("div");
    card.className = `queue-card ${p.status === 'DETECTED' ? 'queue-card-detected' : 'queue-card-verified'} ${p.accident_id === currentAccidentId ? 'active' : ''}`;
    
    const badgeColor = STATUS_COLORS[p.status] || '#64748b';
    card.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
        <span style="font-size:0.68rem; font-weight:700; color:${badgeColor}; text-transform:uppercase;">${p.status}</span>
        <span style="font-size:0.68rem; color:#94a3b8;">#${p.accident_id} &bull; ${p.event_time} WIB</span>
      </div>
      <div style="font-size:0.82rem; font-weight:700; color:#1e293b; margin-bottom:4px; line-height:1.3;">
        ${p.location_text || 'Lokasi tidak diketahui'}
      </div>
      <div style="font-size:0.73rem; color:#64748b; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
        ${p.description || '-'}
      </div>
    `;

    card.onclick = () => selectAccident(p.accident_id);
    listEl.appendChild(card);
  });
}

function renderMapMarkers() {
  markerClusterGroup.clearLayers();

  allAccidents.forEach(feat => {
    const [lng, lat] = feat.geometry.coordinates;
    const p = feat.properties;

    const color = STATUS_COLORS[p.status] || "#64748b";
    const pulseClass = (p.status === "DETECTED") ? "pin-active-pulse" : "";

    const customIcon = L.divIcon({
      className: "custom-leaflet-marker",
      html: `
        <div class="pin-marker ${pulseClass}" style="background-color: ${color}; width: 18px; height: 18px; border: 2px solid #ffffff; border-radius: 50%; box-shadow: 0 0 10px rgba(0,0,0,0.25);"></div>
      `,
      iconSize: [18, 18],
      iconAnchor: [9, 9]
    });

    const marker = L.marker([lat, lng], { icon: customIcon });
    marker.on("click", () => selectAccident(p.accident_id));
    markerClusterGroup.addLayer(marker);
  });
}

// -------------------------------------------------------------
// 4. Detail & Moderasi Kejadian
// -------------------------------------------------------------
async function selectAccident(accidentId) {
  currentAccidentId = accidentId;
  renderQueueList();

  const feat = allAccidents.find(a => a.properties.accident_id === accidentId);
  if (!feat) return;

  const [lng, lat] = feat.geometry.coordinates;
  map.setView([lat, lng], 15);

  const drawer = document.getElementById("detailDrawer");
  drawer.style.display = "flex";
  document.getElementById("locCorrectionPanel").style.display = "none";
  if (correctionMarker) {
    map.removeLayer(correctionMarker);
    correctionMarker = null;
  }

  // Reset feedback aksi jika ada
  const feedback = document.getElementById("modActionFeedback");
  if (feedback) feedback.style.display = "none";

  try {
    const data = await api.getAccidentDetail(accidentId);
    
    // Header & Info Rows (Persis seperti di Portal Warga)
    document.getElementById("detailTitle").textContent = `${data.accident_type || 'Traffic'} Accident`;
    document.getElementById("detailLocation").textContent = data.location_text || "-";
    document.getElementById("detailDateTime").textContent = `${data.event_date} — ${data.event_time}`;
    
    const detailSource = document.getElementById("detailSource");
    if (detailSource) {
      detailSource.textContent = data.source_type === "manual" ? "Laporan Warga Manual" : "X / @Merapi_Uncover";
    }

    const precEl = document.getElementById("detailPrecision");
    if (precEl) {
      precEl.textContent = `${data.precision || 'ESTIMATED'} (${data.uncertainty_radius || 150}m)`;
    }

    // Teks Cuitan Warga
    document.getElementById("detailDesc").textContent = data.description || "Tidak ada cuitan.";

    // Status Badge - Standar style badge persis portal publik
    const statusBadge = document.getElementById("detailStatusBadge");
    statusBadge.textContent = data.status;
    statusBadge.style.background = "";
    statusBadge.style.color = "";
    statusBadge.className = `badge-status status-badge-${data.status.replace(' ', '_')}`;

    // Foto Laporan / Rekaman CCTV (Struktur konsisten dengan portal publik)
    const mediaSection = document.getElementById("detailMediaSection");
    const mediaContainer = document.getElementById("detailMedia");
    mediaContainer.replaceChildren();
    if (data.media && data.media.length > 0) {
      mediaSection.hidden = false;
      data.media.forEach((m, index) => {
        const link = document.createElement("a");
        link.className = "incident-media-link";
        link.href = m.media_url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.setAttribute("aria-label", `Buka foto laporan ${index + 1} ukuran penuh`);

        const img = document.createElement("img");
        img.className = "incident-media-image";
        img.src = m.media_url;
        img.alt = m.alt_text || `Foto ${index + 1} dari laporan kecelakaan`;
        img.loading = "lazy";
        img.decoding = "async";
        img.addEventListener("error", () => link.remove(), { once: true });

        link.appendChild(img);
        mediaContainer.appendChild(link);
      });
    } else {
      mediaSection.hidden = true;
    }

    // Catatan / Komentar Situasi Warga (Desain bubble bersih)
    const commentsList = document.getElementById("commentList");
    commentsList.innerHTML = "";
    if (data.comments && data.comments.length > 0) {
      data.comments.forEach(c => {
        const item = document.createElement("div");
        item.className = "comment-bubble";
        item.innerHTML = `
          <div class="comment-user">${c.username || 'Warga'}</div>
          <div class="comment-text">${c.comment_text}</div>
        `;
        commentsList.appendChild(item);
      });
    } else {
      commentsList.innerHTML = `<span style="font-size:0.75rem; color:#94a3b8; font-style:italic;">Belum ada catatan situasi warga.</span>`;
    }

  } catch (err) {
    console.error("Gagal memuat detail:", err);
  }
}

function closeDetailDrawer() {
  document.getElementById("detailDrawer").style.display = "none";
  cancelLocationCorrection();
  currentAccidentId = null;
  renderQueueList();
}

async function handleAdminModeratorDecision(decision) {
  if (!currentAccidentId) return;

  const btnVerify = document.getElementById("btnModVerify");
  const btnReject = document.getElementById("btnModReject");
  btnVerify.disabled = true;
  btnReject.disabled = true;

  try {
    const feedback = document.getElementById("modActionFeedback");
    feedback.style.display = "block";
    feedback.style.background = decision === "VERIFIED" ? "#dcfce7" : "#fee2e2";
    feedback.style.color = decision === "VERIFIED" ? "#15803d" : "#b91c1c";
    feedback.textContent = `Menyimpan keputusan: ${decision}...`;

    await api.reviewAccident(currentAccidentId, {
      decision: decision,
      notes: decision === "VERIFIED" ? "Diverifikasi valid oleh petugas." : "Ditandai sebagai hoax/bukan laka.",
      reviewer_name: "Petugas Admin"
    });

    feedback.textContent = `✓ Kejadian #${currentAccidentId} berhasil di-update: ${decision}!`;

    // Perbarui badge seketika
    const statusBadge = document.getElementById("detailStatusBadge");
    if (statusBadge) {
      statusBadge.textContent = decision;
      statusBadge.style.background = "";
      statusBadge.style.color = "";
      statusBadge.className = `badge-status status-badge-${decision.replace(' ', '_')}`;
    }

    await loadAdminAccidents();
    selectAccident(currentAccidentId);
  } catch (err) {
    alert("Gagal memproses review: " + err.message);
  } finally {
    btnVerify.disabled = false;
    btnReject.disabled = false;
  }
}

// -------------------------------------------------------------
// 5. Koreksi Posisi di Peta (Human-in-the-Loop & Auto-Learn)
// -------------------------------------------------------------
function startLocationCorrection() {
  if (!currentAccidentId) return;

  const feat = allAccidents.find(a => a.properties.accident_id === currentAccidentId);
  if (!feat) return;

  const [lng, lat] = feat.geometry.coordinates;

  const panel = document.getElementById("locCorrectionPanel");
  panel.style.display = "block";

  document.getElementById("editLocLat").value = lat.toFixed(6);
  document.getElementById("editLocLng").value = lng.toFixed(6);
  document.getElementById("editLocText").value = feat.properties.location_text || "";

  if (correctionMarker) map.removeLayer(correctionMarker);

  isCorrectingLocation = true;
  correctionMarker = L.marker([lat, lng], { draggable: true, zIndexOffset: 2000 }).addTo(map);
  correctionMarker.bindPopup("<b>Geser saya</b> ke titik jalan yang benar!").openPopup();

  correctionMarker.on("dragend", function(e) {
    const pos = e.target.getLatLng();
    document.getElementById("editLocLat").value = pos.lat.toFixed(6);
    document.getElementById("editLocLng").value = pos.lng.toFixed(6);
  });

  map.on("click", onMapCorrectionClick);
  map.setView([lat, lng], 15);
}

function onMapCorrectionClick(e) {
  if (isCorrectingLocation && correctionMarker) {
    correctionMarker.setLatLng(e.latlng);
    document.getElementById("editLocLat").value = e.latlng.lat.toFixed(6);
    document.getElementById("editLocLng").value = e.latlng.lng.toFixed(6);
  }
}

function cancelLocationCorrection() {
  isCorrectingLocation = false;
  if (correctionMarker) {
    map.removeLayer(correctionMarker);
    correctionMarker = null;
  }
  map.off("click", onMapCorrectionClick);
  document.getElementById("locCorrectionPanel").style.display = "none";
}

async function saveLocationCorrection() {
  if (!currentAccidentId) return;

  const lat = parseFloat(document.getElementById("editLocLat").value);
  const lng = parseFloat(document.getElementById("editLocLng").value);
  const locText = document.getElementById("editLocText").value.trim();
  const learn = document.getElementById("checkLearnLandmark").checked;

  if (isNaN(lat) || isNaN(lng)) {
    alert("Koordinat tidak valid!");
    return;
  }

  try {
    const feedback = document.getElementById("modActionFeedback");
    feedback.style.display = "block";
    feedback.style.background = "#dbeafe";
    feedback.style.color = "#1d4ed8";
    feedback.textContent = "Menyimpan koordinat baru & memperbarui kamus cerdas...";

    await api.updateLocation(currentAccidentId, {
      latitude: lat,
      longitude: lng,
      location_text: locText || undefined,
      save_as_landmark: learn
    });

    cancelLocationCorrection();
    feedback.style.background = "#dcfce7";
    feedback.style.color = "#15803d";
    feedback.textContent = `✓ Posisi kejadian #${currentAccidentId} berhasil dipindahkan permanen!`;

    await loadAdminAccidents();
    selectAccident(currentAccidentId);
  } catch (err) {
    alert("Gagal mengoreksi lokasi: " + err.message);
  }
}

// -------------------------------------------------------------
// 6. Live Twitter Crawler Scan Trigger
// -------------------------------------------------------------
async function triggerCrawlerScan() {
  const btn = document.getElementById("btnScanTwitter");
  const badgeText = document.getElementById("pollerBadgeText");
  btn.disabled = true;
  badgeText.textContent = "Sedang crawling X...";

  try {
    const res = await fetch("/api/crawler/trigger", { method: "POST" });
    const data = await res.json();
    alert(`Hasil Scan: ${data.crawled_count || 0} cuitan diperiksa. Data baru langsung masuk antrean!`);
    await loadAdminAccidents();
  } catch (err) {
    alert("Scan via server cloud tidak aktif (Gunakan otomatisasi GitHub Actions yang memiliki Google Chrome bawaan).");
  } finally {
    btn.disabled = false;
    badgeText.textContent = "@Merapi_Uncover: Standby";
  }
}

// -------------------------------------------------------------
// 7. Modals: Simulasi & Analitik
// -------------------------------------------------------------
const SAMPLE_TWEETS = [
  "[Min @Merapi_Uncover] Baru saja terjadi laka motor vs mobil di Jalan Kaliurang KM 14 dekat kampus UII. Korban luka, arus lalin padat merayap.",
  "Laka lantas truk box terguling di Ring Road Barat Gamping. Muatan tumpah ke badan jalan, lalu lintas macet parah arah utara.",
  "Info min, ada pohon tumbang di jalan gejayan dekat jembatan merah, tidak ada korban jiwa hanya menimpa kabel telepon."
];

function openSimulatorModal() {
  document.getElementById("simulatorModal").style.display = "flex";
  document.getElementById("simResultBox").style.display = "none";
}

function closeSimulatorModal() {
  document.getElementById("simulatorModal").style.display = "none";
}

function pickSampleTweet(index) {
  document.getElementById("simTweetInput").value = SAMPLE_TWEETS[index];
}

async function executeTweetSimulation() {
  const text = document.getElementById("simTweetInput").value.trim();
  if (!text) {
    alert("Masukkan teks cuitan terlebih dahulu.");
    return;
  }

  const resultBox = document.getElementById("simResultBox");
  const statusEl = document.getElementById("simStatus");
  const detailEl = document.getElementById("simDetail");

  resultBox.style.display = "block";
  statusEl.textContent = "Memproses teks...";
  detailEl.textContent = "Menjalankan NLP Classifier & Geocoder...";

  try {
    const res = await fetch("/api/simulation/ingest-tweet", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ raw_text: text, author: "@Merapi_Uncover" })
    });
    const data = await res.json();

    if (data.success) {
      statusEl.textContent = "Status: SUKSES (Laka Terdeteksi)";
      statusEl.style.color = "#15803d";
      detailEl.innerHTML = `
        <div><strong>Tipe:</strong> ${data.accident_type}</div>
        <div><strong>Lokasi:</strong> ${data.location_text} [${data.coordinates.latitude}, ${data.coordinates.longitude}]</div>
        <div><strong>Keyakinan:</strong> ${(data.confidence * 100).toFixed(0)}%</div>
      `;
      await loadAdminAccidents();
    } else {
      statusEl.textContent = `Status: DITOLAK (${data.status})`;
      statusEl.style.color = "#b91c1c";
      detailEl.textContent = data.reason || data.detail || "Cuitan bukan merupakan laporan kecelakaan.";
    }
  } catch (err) {
    statusEl.textContent = "Error: " + err.message;
  }
}

function openAnalyticsModal() {
  document.getElementById("analyticsModal").style.display = "flex";
  const body = document.getElementById("analyticsBody");
  
  const total = allAccidents.length;
  const motor = allAccidents.filter(a => a.properties.accident_type === "Motorcycle").length;
  const car = allAccidents.filter(a => a.properties.accident_type === "Car").length;
  const truck = allAccidents.filter(a => a.properties.accident_type === "Truck").length;

  body.innerHTML = `
    <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:10px; margin-bottom:14px;">
      <div style="background:#f1f5f9; padding:10px; border-radius:8px; text-align:center;">
        <div style="font-size:1.4rem; font-weight:700; color:#0f172a;">${total}</div>
        <div style="font-size:0.72rem; color:#64748b;">Total Laka</div>
      </div>
      <div style="background:#f1f5f9; padding:10px; border-radius:8px; text-align:center;">
        <div style="font-size:1.4rem; font-weight:700; color:#0f172a;">${motor}</div>
        <div style="font-size:0.72rem; color:#64748b;">Sepeda Motor</div>
      </div>
      <div style="background:#f1f5f9; padding:10px; border-radius:8px; text-align:center;">
        <div style="font-size:1.4rem; font-weight:700; color:#0f172a;">${car + truck}</div>
        <div style="font-size:0.72rem; color:#64748b;">Roda Empat+</div>
      </div>
    </div>
    <p>Data terintegrasi secara real-time dari laporan masyarakat dan saluran informasi darurat lalu lintas DIY.</p>
  `;
}

function closeAnalyticsModal() {
  document.getElementById("analyticsModal").style.display = "none";
}

// -------------------------------------------------------------
// 8. Bootstrap
// -------------------------------------------------------------
function initAdminApp() {
  initMap();
  loadAdminAccidents();
}

window.addEventListener("DOMContentLoaded", () => {
  checkAdminAuth();
  if (sessionStorage.getItem("webgis_admin_logged_in") === "true") {
    initAdminApp();
  }
});
