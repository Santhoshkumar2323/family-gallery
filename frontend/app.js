const API_BASE = "https://onrender.com";

async function apiFetch(path, options = {}) {
  const token = localStorage.getItem("gallery_token");
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { "Authorization": `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });
  if (res.status === 401) {
    localStorage.removeItem("gallery_token");
    window.location.href = "index.html";
    return null;
  }
  return res;
}

// ---------- PIN PAGE ----------
async function submitPin() {
  const pin = document.getElementById("pinInput").value.trim();
  const errorEl = document.getElementById("pinError");
  errorEl.textContent = "";
  if (!pin) return;

  const res = await fetch(`${API_BASE}/api/pin-check`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pin }),
  });

  if (res.ok) {
    const data = await res.json();
    localStorage.setItem("gallery_token", data.token);
    window.location.href = "gallery.html";
  } else {
    errorEl.textContent = "Incorrect PIN — please try again.";
  }
}

// ---------- GALLERY PAGE ----------
async function loadAlbums() {
  const grid = document.getElementById("albumGrid");
  const res = await apiFetch("/api/albums");
  if (!res) return;
  const albums = await res.json();

  grid.innerHTML = albums.map(a => `
    <div class="album-card" onclick="location.href='gallery.html?album=${a.id}&name=${encodeURIComponent(a.name)}'">
      <div class="album-cover">📷</div>
      <div class="album-info">
        <h3>${a.name}</h3>
        <span>${a.photo_count} photos</span>
      </div>
    </div>
  `).join("");
}

let currentPhotos = [];
let currentPhotoIndex = 0;

async function loadPhotos(albumId, albumName) {
  document.getElementById("albumTitle").textContent = albumName;
  const grid = document.getElementById("photoGrid");
  const res = await apiFetch(`/api/albums/${albumId}/photos`);
  if (!res) return;
  const photos = await res.json();

  currentPhotos = photos;

  grid.innerHTML = photos.map((p, index) => `
    <div class="photo-thumb" onclick="openLightbox(${index})">
      <img src="${p.thumb_url}" loading="lazy" alt="${p.filename}">
    </div>
  `).join("");
}

function openLightbox(index) {
  currentPhotoIndex = index;
  const photo = currentPhotos[index];

  document.getElementById("lightboxImg").src = photo.web_url;
  document.getElementById("lightbox").classList.add("open");
  document.getElementById("downloadBtn").onclick = () => downloadPhoto(photo.download_url);

  // Background log event for tracking views
  apiFetch("/api/events/log", {
    method: "POST",
    body: JSON.stringify({ photo_id: photo.id, type: "view" }),
  });

  updateNavButtons();
}

function updateNavButtons() {
  document.getElementById("prevBtn").style.visibility = currentPhotoIndex > 0 ? "visible" : "hidden";
  document.getElementById("nextBtn").style.visibility = currentPhotoIndex < currentPhotos.length - 1 ? "visible" : "hidden";
}

function nextPhoto() {
  if (currentPhotoIndex < currentPhotos.length - 1) {
    openLightbox(currentPhotoIndex + 1);
  }
}

function prevPhoto() {
  if (currentPhotoIndex > 0) {
    openLightbox(currentPhotoIndex - 1);
  }
}

function closeLightbox() {
  document.getElementById("lightbox").classList.remove("open");
}

document.addEventListener("keydown", (e) => {
  const lightbox = document.getElementById("lightbox");
  if (!lightbox || !lightbox.classList.contains("open")) return;
  if (e.key === "ArrowRight") nextPhoto();
  if (e.key === "ArrowLeft") prevPhoto();
  if (e.key === "Escape") closeLightbox();
});

// Swipe support
let touchStartX = 0;
document.addEventListener("touchstart", (e) => {
  touchStartX = e.changedTouches[0].screenX;
});
document.addEventListener("touchend", (e) => {
  const lightbox = document.getElementById("lightbox");
  if (!lightbox || !lightbox.classList.contains("open")) return;
  const touchEndX = e.changedTouches[0].screenX;
  const diff = touchEndX - touchStartX;
  if (Math.abs(diff) > 50) {
    if (diff < 0) nextPhoto();
    else prevPhoto();
  }
});

async function downloadPhoto(url) {
  const photo = currentPhotos[currentPhotoIndex];
  const btn = document.getElementById("downloadBtn");
  btn.textContent = "Downloading...";

  apiFetch("/api/events/log", {
    method: "POST",
    body: JSON.stringify({ photo_id: photo.id, type: "download" }),
  });

  try {
    const response = await fetch(url);
    const blob = await response.blob();
    const blobUrl = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = blobUrl;
    a.download = photo.filename || "photo.jpg";
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(blobUrl);
  } catch (error) {
    console.error("Download failed:", error);
  } finally {
    btn.textContent = "⬇ Download Original";
  }
}

// ---------- DASHBOARD PAGE ----------
async function loadDashboard() {
  const res = await apiFetch("/api/dashboard");
  if (!res) return;
  const d = await res.json();

  document.getElementById("statsGrid").innerHTML = `
    <div class="stat-card"><div class="num">${d.total_views}</div><div class="label">Total Views</div></div>
    <div class="stat-card"><div class="num">${d.total_downloads}</div><div class="label">Total Downloads</div></div>
    <div class="stat-card"><div class="num">${d.most_popular_album ? d.most_popular_album.name : "—"}</div><div class="label">Most Popular Album</div></div>
  `;

  const highlightEl = document.getElementById("highlightCard");
  if (d.most_downloaded_photo) {
    highlightEl.innerHTML = `
      <img src="${d.most_downloaded_photo.thumb_url}" alt="">
      <div>
        <h3>🔥 Most Downloaded</h3>
        <p>${d.most_downloaded_photo.filename} — downloaded ${d.most_downloaded_photo.count} times</p>
      </div>
    `;
  } else {
    highlightEl.innerHTML = `<div><h3>No downloads yet</h3><p>Once family starts downloading, the top photo shows here.</p></div>`;
  }

  const maxCount = Math.max(...d.timeline.map(t => t.count), 1);
  document.getElementById("timelineBars").innerHTML = d.timeline.map(t => `
    <div class="timeline-bar" style="height:${(t.count / maxCount) * 100}%">
      <span>${t.count}</span>
    </div>
  `).join("") || `<div class="loading">No activity yet</div>`;

  document.getElementById("activityList").innerHTML = d.recent_activity.map(a => `
    <div class="activity-item">
      <span>${a.filename}</span>
      <span class="tag ${a.type}">${a.type}</span>
    </div>
  `).join("") || `<div class="loading">No activity yet</div>`;
}
