// ==========================================================================
// LEAFLET MAP & APPLICATION LOGIC
// ==========================================================================

let map;
let markerClusterGroup;
let allAccidentsData = [];
let isPickingLocation = false;
let tempPickMarker = null;
let currentAccidentId = null;
let isRefreshingData = false;

// Mode Petugas: default false (Mode Warga / Viewer)
let isOfficerMode = sessionStorage.getItem("webgis_officer_mode") === "true";

// Timeline playback state
let timelineDates = ["2026-09-28", "2026-09-29", "2026-09-30", "2026-10-01", "2026-10-02"];
let timelineInterval = null;
let isPlaying = false;

// Status color mapping (Merah, Kuning, Hijau)
const STATUS_COLORS = {
  "VERIFIED": "#10b981",    // Hijau (Valid)
  "UNDER REVIEW": "#f59e0b",// Kuning (Sedang Ditinjau)
  "DETECTED": "#ef4444",    // Merah (Cuitan Baru)
  "REPORTED": "#ef4444"     // Merah
};

// -------------------------------------------------------------
// 1. Inisialisasi Peta & Basemap
// -------------------------------------------------------------
function initMap() {
  // Pusat peta di Yogyakarta (KM 0 / Tugu Jogja area)
  map = L.map("map", {
    center: [-7.7828, 110.3800],
    zoom: 12,
    zoomControl: false
  });

  L.control.zoom({ position: "bottomright" }).addTo(map);

  // Basemap Utama: OpenStreetMap Standar (100% Free & No API Key Required)
  const osmStandard = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(map);

  // Pilihan layer alternatif berbasis citra satelit
  const esriSatellite = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
    maxZoom: 19,
    attribution: 'Tiles &copy; Esri'
  });

  const baseMaps = {
    "OpenStreetMap": osmStandard,
    "Citra satelit": esriSatellite
  };

  L.control.layers(baseMaps, null, { position: "topright" }).addTo(map);

  // Inisialisasi Leaflet.markercluster
  markerClusterGroup = L.markerClusterGroup({
    spiderfyOnMaxZoom: true,
    showCoverageOnHover: false,
    zoomToBoundsOnClick: true,
    maxClusterRadius: 42,
    iconCreateFunction: function(cluster) {
      const count = cluster.getChildCount();
      let sizeClass = 'cluster-small';
      let dim = 36;
      if (count >= 8) {
        sizeClass = 'cluster-large';
        dim = 44;
      } else if (count >= 4) {
        sizeClass = 'cluster-medium';
        dim = 40;
      }
      return L.divIcon({
        html: `<div class="custom-cluster-icon ${sizeClass}" style="width:${dim}px; height:${dim}px;">${count}</div>`,
        className: 'marker-cluster-custom',
        iconSize: [dim, dim]
      });
    }
  });
  map.addLayer(markerClusterGroup);

  // Event listener untuk klik peta (Pelaporan Manual)
  map.on("click", onMapClick);

  // Load data awal dari backend
  loadAccidents();

  // Inisialisasi status UI Mode Petugas
  updateOfficerUI();

  // Inisialisasi pencarian cepat ruas jalan
  initSearch();
}

// -------------------------------------------------------------
// 2. Load & Render Data Kejadian
// -------------------------------------------------------------
function setRefreshLoadingState(isLoading) {
  isRefreshingData = isLoading;
  const badgeText = document.getElementById("pollerBadgeText");
  if (badgeText) {
    badgeText.textContent = isLoading ? "@Merapi_Uncover: Refreshing..." : "@Merapi_Uncover: Live";
  }

  const playBtn = document.getElementById("timelinePlayBtn");
  if (playBtn) {
    playBtn.style.opacity = isLoading ? "0.7" : "1";
    playBtn.style.transform = isLoading ? "scale(0.98)" : "scale(1)";
  }
}

function bindPanelToggle(panelId, toggleId, collapsedLabel, expandedLabel) {
  const panel = document.getElementById(panelId);
  const toggle = document.getElementById(toggleId);
  if (!panel || !toggle) return;

  toggle.addEventListener("click", () => {
    const isCollapsed = panel.classList.toggle("is-collapsed");
    const label = isCollapsed ? collapsedLabel : expandedLabel;
    toggle.setAttribute("aria-expanded", String(!isCollapsed));
    toggle.setAttribute("aria-label", label);
    toggle.title = label;
    toggle.textContent = isCollapsed ? "+" : "−";
  });
}

async function loadAccidents() {
  try {
    setRefreshLoadingState(true);

    const status = document.getElementById("filterStatus").value;
    const accident_type = document.getElementById("filterType").value;
    
    // Ambil data dari backend API
    const geojsonData = await api.getAccidents({ status, accident_type });
    allAccidentsData = geojsonData.features;

    updateStats(allAccidentsData);
    initTimelineSlider(allAccidentsData);
    renderGeoJson(geojsonData);
  } catch (err) {
    console.error("Gagal memuat data kecelakaan:", err);
  } finally {
    setRefreshLoadingState(false);
  }
}

function renderGeoJson(geojsonData) {
  markerClusterGroup.clearLayers();

  geojsonData.features.forEach(feature => {
    const p = feature.properties;
    // Sembunyikan kejadian yang ditolak/hoax dari peta
    if (p.status === "REJECTED") return;

    const [lon, lat] = feature.geometry.coordinates;
    const status = p.status || "DETECTED";
    const color = STATUS_COLORS[status] || "#ef4444";

    // Animasi pulse untuk cuitan baru atau sedang ditinjau
    const pulseClass = (status === "DETECTED" || status === "UNDER REVIEW") ? "pin-active-pulse" : "";

    const customIcon = L.divIcon({
      className: "custom-pin",
      html: `
        <div class="pin-ring ${pulseClass}" style="background-color: ${color}; box-shadow: 0 0 14px ${color};"></div>
      `,
      iconSize: [22, 22],
      iconAnchor: [11, 11]
    });

    const marker = L.marker([lat, lon], { icon: customIcon });

    // Popup ringkas saat marker di-hover
    marker.bindTooltip(`
      <div style="font-size: 0.8rem; font-weight: 600;">
        <span style="color: ${color}">●</span> ${p.accident_type} 
        <span style="font-size:0.7rem; color:${color}; font-weight:700;">[${status}]</span>
      </div>
      <div style="font-size: 0.72rem; color: #526561;">${p.location_text}</div>
    `, { sticky: true });

    marker.on("click", () => {
      openDetailDrawer(p.accident_id);
    });

    markerClusterGroup.addLayer(marker);
  });
}

function updateStats(features) {
  const activeFeatures = features.filter(f => f.properties.status !== "REJECTED");
  const total = activeFeatures.length;
  const verifiedCount = activeFeatures.filter(f => f.properties.status === "VERIFIED").length;
  const underReviewCount = activeFeatures.filter(f => f.properties.status === "UNDER REVIEW").length;
  const detectedCount = activeFeatures.filter(f => f.properties.status === "DETECTED" || f.properties.status === "REPORTED").length;

  const elTotal = document.getElementById("statTotal");
  const elVerified = document.getElementById("statVerified");
  const elUnderReview = document.getElementById("statUnderReview");
  const elDetected = document.getElementById("statDetected");

  if (elTotal) elTotal.textContent = total;
  if (elVerified) elVerified.textContent = verifiedCount;
  if (elUnderReview) elUnderReview.textContent = underReviewCount;
  if (elDetected) elDetected.textContent = detectedCount;
}

// -------------------------------------------------------------
// 3. Detail Drawer & Komentar Warga
// -------------------------------------------------------------
async function openDetailDrawer(accidentId) {
  currentAccidentId = accidentId;
  const drawer = document.getElementById("detailDrawer");
  drawer.style.display = "flex";

  // Reset feedback aksi jika ada
  const feedback = document.getElementById("modActionFeedback");
  if (feedback) feedback.style.display = "none";

  try {
    const data = await api.getAccidentDetail(accidentId);
    
    document.getElementById("detailTitle").textContent = data.accident_type + " Accident";
    document.getElementById("detailLocation").textContent = data.location_text;
    document.getElementById("detailDateTime").textContent = `${data.event_date} — ${data.event_time}`;
    document.getElementById("detailDesc").textContent = data.description || "Tidak ada cuitan.";

    const mediaSection = document.getElementById("detailMediaSection");
    const mediaGrid = document.getElementById("detailMedia");
    mediaGrid.replaceChildren();
    (data.media || []).forEach((media, index) => {
      const link = document.createElement("a");
      link.className = "incident-media-link";
      link.href = media.media_url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.setAttribute("aria-label", `Buka foto laporan ${index + 1} ukuran penuh`);

      const image = document.createElement("img");
      image.className = "incident-media-image";
      image.src = media.media_url;
      image.alt = media.alt_text || `Foto ${index + 1} dari laporan kecelakaan`;
      image.loading = "lazy";
      image.decoding = "async";
      image.addEventListener("error", () => link.remove(), { once: true });

      link.appendChild(image);
      mediaGrid.appendChild(link);
    });
    mediaSection.hidden = mediaGrid.childElementCount === 0;
    
    const statusEl = document.getElementById("detailStatusBadge");
    statusEl.textContent = data.status;
    statusEl.className = `badge-status status-badge-${data.status.replace(' ', '_')}`;

    // Sumber data selalu terarah ke X / @Merapi_Uncover
    document.getElementById("detailSource").textContent = data.source_type === "manual" ? "Laporan Warga Manual" : "X / @Merapi_Uncover";

    // Pastikan label selalu "Cuitan"
    const descLabel = document.getElementById("detailDescLabel");
    if (descLabel) descLabel.textContent = "Cuitan";

    // Panel tindakan petugas: hanya tampil jika sedang dalam Mode Petugas
    const modBox = document.getElementById("moderatorBox");
    if (modBox) {
      modBox.style.display = isOfficerMode ? "block" : "none";
    }

    // Render Komentar
    renderComments(data.comments || []);

  } catch (err) {
    console.error(err);
  }
}

function closeDetailDrawer() {
  document.getElementById("detailDrawer").style.display = "none";
  currentAccidentId = null;
}

function renderComments(comments) {
  const container = document.getElementById("commentList");
  container.innerHTML = "";

  if (comments.length === 0) {
    container.innerHTML = `<p style="font-size:0.75rem; color:#64748b; font-style:italic;">Belum ada komentar warga pada kejadian ini.</p>`;
    return;
  }

  comments.forEach(c => {
    const el = document.createElement("div");
    el.className = "comment-bubble";
    el.innerHTML = `
      <div class="comment-user">${c.username}</div>
      <div class="comment-text">${c.comment_text}</div>
    `;
    container.appendChild(el);
  });
}

async function handleAddComment(e) {
  e.preventDefault();
  if (!currentAccidentId) return;

  const usernameInput = document.getElementById("inputCommentUser");
  const textInput = document.getElementById("inputCommentText");

  if (!textInput.value.trim()) return;

  try {
    await api.submitComment(currentAccidentId, {
      username: usernameInput.value || "Warga",
      comment_text: textInput.value
    });

    textInput.value = "";
    // Refresh komentar
    const updated = await api.getAccidentDetail(currentAccidentId);
    renderComments(updated.comments);
  } catch (err) {
    alert("Gagal mengirim komentar: " + err.message);
  }
}

// -------------------------------------------------------------
// 4. Moderator Review & LifeCycle (Tombol Verifikasi & Hoax)
// -------------------------------------------------------------
async function handleModeratorDecision(decision) {
  if (!currentAccidentId) return;

  if (!isOfficerMode) {
    alert("Akses Ditolak: Hanya Petugas Terverifikasi yang dapat mengubah status kejadian.");
    return;
  }

  const feedback = document.getElementById("modActionFeedback");
  const btnVerify = document.getElementById("btnModVerify");
  const btnReject = document.getElementById("btnModReject");

  if (btnVerify) btnVerify.disabled = true;
  if (btnReject) btnReject.disabled = true;

  try {
    const notes = decision === "VERIFIED"
      ? "Diverifikasi valid oleh petugas melalui pemantauan lapangan."
      : "Laporan ditolak / terindikasi hoax.";

    await api.reviewAccident(currentAccidentId, {
      decision: decision,
      notes: notes,
      reviewer_name: "Petugas Terverifikasi"
    });

    if (feedback) {
      feedback.style.display = "block";
      if (decision === "VERIFIED") {
        feedback.style.background = "rgba(16, 185, 129, 0.18)";
        feedback.style.color = "#34d399";
        feedback.style.border = "1px solid rgba(16, 185, 129, 0.4)";
        feedback.innerHTML = `✓ Cuitan #${currentAccidentId} Berhasil Diverifikasi (Status: <strong>VALID / Hijau</strong>).`;
      } else {
        feedback.style.background = "rgba(239, 68, 68, 0.18)";
        feedback.style.color = "#f87171";
        feedback.style.border = "1px solid rgba(239, 68, 68, 0.4)";
        feedback.innerHTML = `✕ Cuitan #${currentAccidentId} Ditandai sebagai <strong>HOAX</strong> (Diarsipkan dari Peta).`;
      }
    }

    // Refresh data kejadian & peta seketika
    await loadAccidents();

    // Perbarui badge status pada drawer seketika
    const statusEl = document.getElementById("detailStatusBadge");
    if (statusEl) {
      statusEl.textContent = decision;
      statusEl.className = `badge-status status-badge-${decision.replace(' ', '_')}`;
    }

  } catch (err) {
    alert("Gagal memproses tindakan petugas: " + err.message);
  } finally {
    if (btnVerify) btnVerify.disabled = false;
    if (btnReject) btnReject.disabled = false;
  }
}

// -------------------------------------------------------------
// 5. Mode Petugas vs Mode Warga
// -------------------------------------------------------------
function toggleOfficerModal() {
  if (isOfficerMode) {
    isOfficerMode = false;
    sessionStorage.removeItem("webgis_officer_mode");
    updateOfficerUI();
    alert("Anda telah keluar dari Mode Petugas. Sistem kembali ke Mode Publik (Viewer).");
  } else {
    document.getElementById("officerPinInput").value = "";
    document.getElementById("officerModal").style.display = "flex";
    setTimeout(() => document.getElementById("officerPinInput").focus(), 100);
  }
}

function closeOfficerModal() {
  document.getElementById("officerModal").style.display = "none";
}

function handleOfficerLogin(e) {
  e.preventDefault();
  const pin = document.getElementById("officerPinInput").value.trim();

  if (pin === "1234") {
    isOfficerMode = true;
    sessionStorage.setItem("webgis_officer_mode", "true");
    closeOfficerModal();
    updateOfficerUI();
    alert("✓ Berhasil masuk sebagai Petugas! Panel tindakan verifikasi kini aktif.");
  } else {
    alert("PIN Keamanan salah! Gunakan PIN demo 1234.");
    document.getElementById("officerPinInput").value = "";
    document.getElementById("officerPinInput").focus();
  }
}

function updateOfficerUI() {
  const btn = document.getElementById("btnOfficerMode");
  const text = document.getElementById("officerBtnText");
  const modBox = document.getElementById("moderatorBox");

  if (isOfficerMode) {
    if (text) text.textContent = "Keluar mode petugas";
    if (btn) {
      btn.style.background = "linear-gradient(135deg, #10b981, #059669)";
      btn.style.borderColor = "rgba(16, 185, 129, 0.4)";
    }
    if (modBox && currentAccidentId) modBox.style.display = "block";
  } else {
    if (text) text.textContent = "Mode petugas";
    if (btn) {
      btn.style.background = "rgba(255,255,255,0.08)";
      btn.style.borderColor = "rgba(255,255,255,0.2)";
    }
    if (modBox) modBox.style.display = "none";
  }
}

// -------------------------------------------------------------
// 6. Pencarian Cepat Ruas Jalan & FlyTo
// -------------------------------------------------------------
function initSearch() {
  const searchInput = document.getElementById("searchLocation");
  if (!searchInput) return;

  searchInput.addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase().trim();
    if (!q) {
      loadAccidents();
      return;
    }
    
    // Filter features
    const matched = allAccidentsData.filter(f => {
      const loc = (f.properties.location_text || "").toLowerCase();
      const desc = (f.properties.description || "").toLowerCase();
      const type = (f.properties.accident_type || "").toLowerCase();
      return loc.includes(q) || desc.includes(q) || type.includes(q);
    });

    renderGeoJson({ type: "FeatureCollection", features: matched });
  });

  searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      const q = e.target.value.toLowerCase().trim();
      const match = allAccidentsData.find(f => {
        const loc = (f.properties.location_text || "").toLowerCase();
        return loc.includes(q);
      });
      if (match) {
        const [lon, lat] = match.geometry.coordinates;
        map.flyTo([lat, lon], 15, { duration: 1.2 });
        setTimeout(() => {
          openDetailDrawer(match.properties.accident_id);
        }, 1300);
      }
    }
  });
}

// -------------------------------------------------------------
// 7. Manual Crowdsourcing Flow (Lapor Warga)
// -------------------------------------------------------------
function toggleReportMode() {
  isPickingLocation = !isPickingLocation;
  const btn = document.getElementById("btnToggleReport");

  if (isPickingLocation) {
    btn.style.background = "#e11d48";
    btn.innerHTML = `<span>✕ Batal Klik Peta</span>`;
    document.getElementById("map").style.cursor = "crosshair";
    alert("Mode Lapor Aktif: Silakan klik titik lokasi kejadian kecelakaan pada peta.");
  } else {
    btn.style.background = "";
    btn.innerHTML = `<span>+ Lapor Kecelakaan</span>`;
    document.getElementById("map").style.cursor = "";
    if (tempPickMarker) {
      map.removeLayer(tempPickMarker);
      tempPickMarker = null;
    }
  }
}

function onMapClick(e) {
  if (!isPickingLocation) return;

  const { lat, lng } = e.latlng;

  if (tempPickMarker) {
    map.removeLayer(tempPickMarker);
  }

  tempPickMarker = L.marker([lat, lng]).addTo(map);

  // Buka modal form lapor dengan koordinat terisi
  document.getElementById("reportLat").value = lat.toFixed(6);
  document.getElementById("reportLng").value = lng.toFixed(6);
  
  // Set default tanggal & jam sekarang
  const today = new Date().toISOString().split("T")[0];
  const nowTime = new Date().toTimeString().split(" ")[0].substring(0, 5);
  document.getElementById("reportDate").value = today;
  document.getElementById("reportTime").value = nowTime;

  document.getElementById("reportModal").style.display = "flex";
}

function closeReportModal() {
  document.getElementById("reportModal").style.display = "none";
  toggleReportMode();
}

async function handleReportSubmit(e) {
  e.preventDefault();

  const payload = {
    event_date: document.getElementById("reportDate").value,
    event_time: document.getElementById("reportTime").value + ":00",
    accident_type: document.getElementById("reportType").value,
    location_text: document.getElementById("reportLocationText").value,
    description: document.getElementById("reportDesc").value,
    latitude: parseFloat(document.getElementById("reportLat").value),
    longitude: parseFloat(document.getElementById("reportLng").value)
  };

  try {
    await api.submitReport(payload);
    alert("Laporan kecelakaan berhasil dikirim dengan status 'REPORTED'! Menunggu verifikasi petugas.");
    closeReportModal();
    await loadAccidents();
  } catch (err) {
    alert("Gagal mengirim laporan: " + err.message);
  }
}

// -------------------------------------------------------------
// 8. Temporal Slider & Timeline Playback
// -------------------------------------------------------------
function formatIndoDate(dateStr) {
  if (!dateStr) return "";
  const months = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
  const parts = dateStr.split("-");
  if (parts.length === 3) {
    const d = parseInt(parts[2]);
    const m = months[parseInt(parts[1]) - 1] || parts[1];
    const y = parts[0];
    return `${d} ${m} ${y}`;
  }
  return dateStr;
}

function initTimelineSlider(features) {
  const datesSet = new Set();
  features.forEach(f => {
    if (f.properties && f.properties.event_date) {
      datesSet.add(f.properties.event_date);
    }
  });

  const sortedDates = Array.from(datesSet).sort();
  const slider = document.getElementById("timelineSlider");
  const dateLabel = document.getElementById("currentTimelineDate");
  const rangeLabel = document.getElementById("timelineDateRange");

  if (sortedDates.length === 0) {
    timelineDates = [];
    if (rangeLabel) {
      rangeLabel.textContent = "Belum ada data";
    }
    if (dateLabel) {
      dateLabel.innerHTML = `<span style="color:#ef4444; font-weight:700;">● REAL-TIME</span> (Live Standby)`;
    }
    if (slider) {
      slider.min = "0";
      slider.max = "0";
      slider.value = "0";
    }
    return;
  }

  timelineDates = sortedDates;
  if (rangeLabel) {
    rangeLabel.textContent = `${formatIndoDate(sortedDates[0])} s/d Real-Time`;
  }

  if (slider && timelineDates.length > 0) {
    slider.min = "0";
    slider.max = (timelineDates.length - 1).toString();
    slider.value = (timelineDates.length - 1).toString();

    const latestDate = timelineDates[timelineDates.length - 1];
    if (dateLabel) {
      dateLabel.innerHTML = `<span style="color:#ef4444; font-weight:700;">● REAL-TIME</span> (${formatIndoDate(latestDate)})`;
    }
  }
}

function handleTimelineChange(e) {
  const index = parseInt(e.target.value);
  const selectedDate = timelineDates[index];
  const dateLabel = document.getElementById("currentTimelineDate");
  const isLatest = (index === timelineDates.length - 1);

  if (dateLabel) {
    if (isLatest) {
      dateLabel.innerHTML = `<span style="color:#ef4444; font-weight:700;">● REAL-TIME</span> (${formatIndoDate(selectedDate)})`;
    } else {
      dateLabel.innerHTML = `📅 s/d <strong style="color:#287267;">${formatIndoDate(selectedDate)}</strong>`;
    }
  }

  if (isLatest) {
    // Tampilkan seluruh data live real-time
    renderGeoJson({ type: "FeatureCollection", features: allAccidentsData });
    updateStats(allAccidentsData);
  } else {
    filterAccidentsByDate(selectedDate);
  }
}

function filterAccidentsByDate(dateStr) {
  const filtered = allAccidentsData.filter(f => f.properties.event_date <= dateStr);
  renderGeoJson({ type: "FeatureCollection", features: filtered });
  updateStats(filtered);
}

function resetToRealtime() {
  const slider = document.getElementById("timelineSlider");
  if (slider && timelineDates.length > 0) {
    slider.value = (timelineDates.length - 1).toString();
    slider.dispatchEvent(new Event("input"));
  }
}

function toggleTimelinePlay() {
  const playBtn = document.getElementById("timelinePlayBtn");
  const slider = document.getElementById("timelineSlider");

  if (isPlaying) {
    clearInterval(timelineInterval);
    isPlaying = false;
    playBtn.textContent = "▶";
  } else {
    isPlaying = true;
    playBtn.textContent = "⏸";

    timelineInterval = setInterval(() => {
      let currentVal = parseInt(slider.value);
      currentVal = (currentVal + 1) % timelineDates.length;
      slider.value = currentVal;
      slider.dispatchEvent(new Event("input"));
      
      // Jika sampai akhir (real-time), pause sejenak
      if (currentVal === timelineDates.length - 1) {
        clearInterval(timelineInterval);
        isPlaying = false;
        playBtn.textContent = "▶";
      }
    }, 1200);
  }
}

// -------------------------------------------------------------
// 9. Dashboard Analisis Spasial & Blackspots
// -------------------------------------------------------------
async function openAnalyticsModal() {
  const modal = document.getElementById("analyticsModal");
  modal.style.display = "flex";

  try {
    const data = await api.getBlackspotsAnalytics();
    
    // Top Metrics
    document.getElementById("analyticsTotalRecords").textContent = data.total_records;
    document.getElementById("analyticsActiveRecords").textContent = data.status_count.ACTIVE || 0;
    document.getElementById("analyticsResolvedRecords").textContent = data.status_count.RESOLVED || 0;
    
    const verifiedPercent = Math.round(((data.status_count.VERIFIED || 0) / (data.total_records || 1)) * 100);
    document.getElementById("analyticsVerifiedRatio").textContent = `${verifiedPercent}%`;

    // Render Corridor Rankings
    const corridorContainer = document.getElementById("corridorRankingsList");
    corridorContainer.innerHTML = "";
    const maxCorridorCount = data.top_corridors.length > 0 ? data.top_corridors[0].count : 1;

    data.top_corridors.forEach((c, index) => {
      const percentage = Math.round((c.count / maxCorridorCount) * 100);
      let riskBadge = `<span class="risk-badge risk-high">Prioritas</span>`;
      if (index >= 3) {
        riskBadge = `<span class="risk-badge risk-watch">Pantau</span>`;
      }

      const el = document.createElement("div");
      el.className = "corridor-item";
      el.innerHTML = `
        <div class="corridor-header">
          <span style="font-weight: 600; color: #263b37;">#${index + 1} ${c.corridor}</span>
          <div style="display:flex; align-items:center; gap:8px;">
            <span style="color: #287267; font-weight:700;">${c.count} laporan</span>
            ${riskBadge}
          </div>
        </div>
        <div class="corridor-bar-track">
          <div class="corridor-bar-fill" style="width: ${percentage}%;"></div>
        </div>
      `;
      corridorContainer.appendChild(el);
    });

    // Render Hourly Distribution
    const hourlyContainer = document.getElementById("hourlyDistributionList");
    hourlyContainer.innerHTML = "";
    const totalHourly = Object.values(data.time_distribution).reduce((a, b) => a + b, 0) || 1;

    for (const [timeLabel, count] of Object.entries(data.time_distribution)) {
      const pct = Math.round((count / totalHourly) * 100);
      const isPeak = timeLabel.includes("Sibuk");
      const el = document.createElement("div");
      el.className = "distribution-row";
      el.innerHTML = `
        <div style="display: flex; justify-content: space-between;">
          <span class="distribution-label ${isPeak ? 'is-peak' : ''}">${timeLabel}</span>
          <span class="distribution-value">${count} (${pct}%)</span>
        </div>
        <div class="distribution-track">
          <div class="distribution-fill ${isPeak ? 'is-peak' : ''}" style="width: ${pct}%;"></div>
        </div>
      `;
      hourlyContainer.appendChild(el);
    }

    // Render Vehicle Breakdown
    const vehicleContainer = document.getElementById("vehicleDistributionList");
    vehicleContainer.innerHTML = "";
    const totalVehicles = Object.values(data.vehicles_count).reduce((a, b) => a + b, 0) || 1;

    for (const [vtype, count] of Object.entries(data.vehicles_count)) {
      const pct = Math.round((count / totalVehicles) * 100);
      const el = document.createElement("div");
      el.className = "distribution-row";
      el.innerHTML = `
        <div style="display: flex; justify-content: space-between;">
          <span class="distribution-label">${vtype}</span>
          <span class="distribution-value">${count} (${pct}%)</span>
        </div>
        <div class="distribution-track">
          <div class="distribution-fill" style="width: ${pct}%;"></div>
        </div>
      `;
      vehicleContainer.appendChild(el);
    }

  } catch (err) {
    console.error("Gagal memuat analitik:", err);
  }
}

function closeAnalyticsModal() {
  document.getElementById("analyticsModal").style.display = "none";
}

// -------------------------------------------------------------
// 10. Social Media Ingestion Pipeline Simulator
// -------------------------------------------------------------
async function openSimulatorModal() {
  document.getElementById("simulatorModal").style.display = "flex";
  await loadSimulatorSamples();
}

function closeSimulatorModal() {
  document.getElementById("simulatorModal").style.display = "none";
}

async function loadSimulatorSamples() {
  const container = document.getElementById("sampleTweetButtons");
  try {
    const samples = await api.getSimulatorSamples();
    container.innerHTML = "";

    samples.forEach(s => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = `sample-tweet-button ${s.type === "positive" ? "is-positive" : "is-negative"}`;
      btn.style.cssText = `
        text-align: left;
        padding: 8px 10px;
        border-radius: 8px;
        font-size: 0.73rem;
        cursor: pointer;
        transition: all 0.15s ease;
      `;
      btn.innerHTML = `<strong><span class="sample-status-dot"></span>${s.label}</strong><span class="sample-tweet-preview">"${s.text.substring(0, 75)}..."</span>`;

      btn.addEventListener("click", () => {
        document.getElementById("simulatorTweetInput").value = s.text;
      });

      container.appendChild(btn);
    });
  } catch (err) {
    console.error("Gagal memuat sampel:", err);
  }
}

async function runTweetSimulation() {
  const text = document.getElementById("simulatorTweetInput").value.trim();
  if (!text) {
    alert("Masukkan teks tweet terlebih dahulu.");
    return;
  }

  const traceBox = document.getElementById("pipelineTraceBox");
  const traceContent = document.getElementById("traceContent");
  traceBox.style.display = "flex";
  traceContent.innerHTML = `<span style="color:#287267;">Menjalankan klasifikasi dan pencarian lokasi...</span>`;

  try {
    const result = await api.runTweetIngest(text, "@Merapi_Uncover");

    if (result.success) {
      traceContent.innerHTML = `
        <div style="color: #28634f; font-weight: 600;">Laporan terdeteksi</div>
        <div><strong>Tipe Laka:</strong> ${result.accident_type}</div>
        <div><strong>Lokasi Ekstraksi:</strong> ${result.location_text}</div>
        <div><strong>Geocoding:</strong> [Lat: ${result.coordinates.latitude}, Lng: ${result.coordinates.longitude}]</div>
        <div><strong>Confidence Score:</strong> ${(result.confidence * 100).toFixed(0)}%</div>
        <div><strong>Tersimpan di basis data:</strong> ID #${result.accident_id} (Status: <span style="color:#8e6114; font-weight:700;">DETECTED</span>)</div>
      `;

      // Muat ulang data peta & fokuskan ke lokasi baru
      await loadAccidents();
      map.flyTo([result.coordinates.latitude, result.coordinates.longitude], 14, { duration: 1.2 });
      
      // Buka detail drawer setelah animasi
      setTimeout(() => {
        openDetailDrawer(result.accident_id);
      }, 1300);

    } else {
      traceContent.innerHTML = `
        <div style="color: #a84635; font-weight: 600;">Laporan tidak memenuhi kriteria kejadian</div>
        <div><strong>Alasan:</strong> ${result.reason}</div>
        <div style="color: #64748b; font-style: italic;">Sistem tidak menyimpan ke database untuk mencegah polusi data / hoax.</div>
      `;
    }
  } catch (err) {
    traceContent.innerHTML = `<span style="color:#a84635;">Terjadi kesalahan: ${err.message}</span>`;
  }
}

async function runLiveCrawler() {
  const btn = document.getElementById("btnLiveCrawler");
  const traceBox = document.getElementById("pipelineTraceBox");
  const traceContent = document.getElementById("traceContent");

  btn.disabled = true;
  btn.textContent = "Menyiapkan pengambilan laporan...";
  traceBox.style.display = "flex";
  traceContent.innerHTML = `
    <span style="color:#287267;">Menjalankan pengambilan laporan dari X...</span><br>
    <span style="color:#526561;">1. Menyiapkan sesi akun...</span><br>
    <span style="color:#526561;">2. Membuka profil @Merapi_Uncover...</span><br>
    <span style="color:#526561;">3. Membaca laporan terbaru...</span>
  `;

  try {
    const res = await api.triggerCrawler();
    btn.disabled = false;
    btn.textContent = "Ambil laporan terbaru";

    if (res.results && res.results.length > 0) {
      let html = `<div style="color:#28634f; font-weight:600;">Berhasil memeriksa ${res.results.length} laporan terbaru dari X.</div>`;
      
      res.results.forEach((r, idx) => {
        if (r.success) {
          html += `
            <div style="border-left: 2px solid #10b981; padding-left: 6px; margin-top: 4px;">
              <strong>[Cuitan #${idx+1}] TERDETEKSI LAKA (${r.accident_type})</strong><br>
              <span style="color:#526561;">"${r.raw_text.substring(0, 60)}..."</span><br>
              <span style="color:#287267;">${r.location_text} (Skor: ${(r.confidence*100).toFixed(0)}%)</span>
            </div>
          `;
        } else if (r.status === 'DUPLICATE_SKIPPED') {
          html += `<div style="color:#526561; font-size:0.7rem;">[Laporan #${idx+1}] Duplikat (sudah tersimpan di basis data).</div>`;
        } else {
          html += `<div style="color:#526561; font-size:0.7rem;">[Laporan #${idx+1}] ${r.reason || 'Bukan laporan laka baru.'}</div>`;
        }
      });

      traceContent.innerHTML = html;
      await loadAccidents();
    } else {
      traceContent.innerHTML = `
        <div style="color:#8e6114; font-weight:600;">Belum ada laporan baru atau sesi X memerlukan verifikasi.</div>
        <div style="color:#526561; font-size:0.7rem; margin-top:4px;">Pastikan sesi X masih aktif.</div>
      `;
    }
  } catch (err) {
    btn.disabled = false;
    btn.textContent = "Ambil laporan terbaru";
    traceContent.innerHTML = `<span style="color:#a84635;">Pengambilan laporan gagal: ${err.message}</span>`;
  }
}

// -------------------------------------------------------------
// 11. Auto-Poller Status Monitor & Background Sync
// -------------------------------------------------------------
async function updatePollerStatus() {
  try {
    const status = await api.getCrawlerStatus();
    const badgeText = document.getElementById("pollerBadgeText");
    const pollerDot = document.getElementById("pollerDot");
    const statusLabel = document.getElementById("pollerStatusLabel");
    const totalRuns = document.getElementById("pollerTotalRuns");
    const lastRun = document.getElementById("pollerLastRun");
    const lastMsg = document.getElementById("pollerLastMsg");

    if (status.is_crawling_now) {
      if (badgeText) badgeText.textContent = "Auto-Poller X: Sedang Crawling...";
      if (pollerDot) {
        pollerDot.style.background = "#38bdf8";
        pollerDot.style.boxShadow = "0 0 10px #38bdf8";
      }
      if (statusLabel) {
        statusLabel.textContent = "Crawling...";
        statusLabel.classList.remove("is-active", "is-disabled");
        statusLabel.classList.add("is-crawling");
      }
    } else if (status.enabled) {
      if (badgeText) badgeText.textContent = `Auto-Poller X: Aktif (${status.interval_minutes}m)`;
      if (pollerDot) {
        pollerDot.style.background = "#10b981";
        pollerDot.style.boxShadow = "0 0 8px #10b981";
      }
      if (statusLabel) {
        statusLabel.textContent = "Aktif";
        statusLabel.classList.remove("is-crawling", "is-disabled");
        statusLabel.classList.add("is-active");
      }
    } else {
      if (badgeText) badgeText.textContent = "Auto-Poller X: Nonaktif";
      if (pollerDot) {
        pollerDot.style.background = "#64748b";
        pollerDot.style.boxShadow = "none";
      }
      if (statusLabel) {
        statusLabel.textContent = "Nonaktif";
        statusLabel.classList.remove("is-crawling", "is-active");
        statusLabel.classList.add("is-disabled");
      }
    }

    if (totalRuns) totalRuns.textContent = status.total_runs;
    if (lastRun) lastRun.textContent = status.last_run || "Menunggu siklus...";
    if (lastMsg) lastMsg.textContent = `Status: ${status.last_status}`;
  } catch (e) {
    // Abaikan error saat backend reload
  }
}

// -------------------------------------------------------------
// 12. Inisialisasi saat Halaman Selesai Dimuat
// -------------------------------------------------------------
window.addEventListener("DOMContentLoaded", () => {
  initMap();
  bindPanelToggle("navigationPanel", "navigationToggle", "Buka panel navigasi", "Minimalkan panel navigasi");
  bindPanelToggle("timelinePanel", "timelineToggle", "Buka kronologi waktu", "Minimalkan kronologi waktu");

  // Filter dropdown listeners
  document.getElementById("filterStatus").addEventListener("change", loadAccidents);
  document.getElementById("filterType").addEventListener("change", loadAccidents);

  // Timeline events
  const slider = document.getElementById("timelineSlider");
  slider.addEventListener("input", handleTimelineChange);
  document.getElementById("timelinePlayBtn").addEventListener("click", toggleTimelinePlay);

  // Form submit listeners
  document.getElementById("commentForm").addEventListener("submit", handleAddComment);
  document.getElementById("reportForm").addEventListener("submit", handleReportSubmit);

  // Auto-Poller & Real-Time Sync Loop
  updatePollerStatus();
  setInterval(updatePollerStatus, 5000);  // Monitor status poller tiap 5 detik
  setInterval(loadAccidents, 15000);      // Auto-refresh titik peta tiap 15 detik agar live data terlihat lebih cepat
});
