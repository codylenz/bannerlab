let lastBanners = []; // last batch returned from server
let currentPage = "generate";
let currentGridWidth = null;
let currentGridHeight = null;

// --- Info panel ---

function showBannerInfo(index) {
  const infoPanel = document.getElementById("info-panel");
  const banner = lastBanners[index];

  if (!banner) {
    infoPanel.innerHTML = `
      <h2>Info</h2>
      <div class="info-empty">No banner data.</div>
    `;
    return;
  }

  const layers = banner.layers || [];

  let slugHtml = "";
  if (banner.slug) {
    slugHtml = `<div class="info-slug">Slug: ${banner.slug}</div>`;
  }

  let layersHtml = "";
  if (layers.length === 0) {
    layersHtml = `<div class="info-empty">No layer data.</div>`;
  } else {
    const items = layers
      .map((layer, i) => {
        const kind = layer.kind || "pattern";
        const pat = layer.pattern || "?";
        const color = layer.color || "?";
        return `<li>#${i} <strong>${kind}</strong> — ${pat} — <span style="color:#ccc;">${color}</span></li>`;
      })
      .join("");
    layersHtml = `<ul class="info-layers-list">${items}</ul>`;
  }

  infoPanel.innerHTML = `
    <h2>Info</h2>
    ${slugHtml}
    ${layersHtml}
  `;
}

// --- Helpers to read filters ---

function getFilterConfig() {
  const excludePatterns = [];
  document.querySelectorAll(".pattern-checkbox").forEach((cb) => {
    if (!cb.checked) {
      excludePatterns.push(cb.value);
    }
  });

  const excludeColors = [];
  document.querySelectorAll(".color-checkbox").forEach((cb) => {
    if (!cb.checked) {
      excludeColors.push(cb.value);
    }
  });

  return { excludePatterns, excludeColors };
}

// --- Rendering helpers ---

function renderGrid(width, height, banners) {
  const bannerArea = document.getElementById("banner-area");

  currentGridWidth = width;
  currentGridHeight = height;
  lastBanners = banners || [];

  bannerArea.innerHTML = "";
  bannerArea.classList.add("grid-mode");
  bannerArea.style.gridTemplateColumns = `repeat(${width}, 80px)`; // keep in sync with CSS .banner-image width

  const frag = document.createDocumentFragment();

  lastBanners.forEach((banner, index) => {
    const img = document.createElement("img");
    img.src = banner.src;
    img.className = "banner-image";
    img.alt = banner.slug || `grid-banner-${index}`;
    img.dataset.index = String(index);
    img.addEventListener("click", () => showBannerInfo(index));
    frag.appendChild(img);
  });

  bannerArea.appendChild(frag);
}

// --- Generate single batch (Generate tab) ---

async function generateBanners() {
  const countInput = document.getElementById("count-input");
  const bannerArea = document.getElementById("banner-area");
  const status = document.getElementById("status");

  let count = parseInt(countInput.value, 10);
  if (isNaN(count) || count < 1) count = 1;

  const { excludePatterns, excludeColors } = getFilterConfig();

  status.textContent = "Generating...";
  bannerArea.innerHTML = "";

  try {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        count,
        exclude_patterns: excludePatterns,
        exclude_colors: excludeColors,
      }),
    });

    if (!res.ok) {
      throw new Error("Server error");
    }

    const data = await res.json();
    const banners = data.banners || [];
    lastBanners = banners;

    // Ensure we are in flex mode (not grid)
    bannerArea.classList.remove("grid-mode");
    bannerArea.style.gridTemplateColumns = "";

    const frag = document.createDocumentFragment();

    banners.forEach((banner, index) => {
      const img = document.createElement("img");
      img.src = banner.src;
      img.className = "banner-image";
      img.alt = banner.slug || `banner-${index}`;
      img.dataset.index = String(index);
      img.addEventListener("click", () => showBannerInfo(index));
      frag.appendChild(img);
    });

    bannerArea.appendChild(frag);
    status.textContent = `Generated ${banners.length} banner(s).`;
  } catch (err) {
    console.error(err);
    status.textContent = "Error: could not reach server.";
  }
}

// --- Generate grid (Grid tab) ---

async function generateGrid() {
  const widthInput = document.getElementById("grid-width-input");
  const heightInput = document.getElementById("grid-height-input");
  const bannerArea = document.getElementById("banner-area");
  const status = document.getElementById("status");

  let w = parseInt(widthInput.value, 10);
  let h = parseInt(heightInput.value, 10);

  if (isNaN(w) || w < 1) w = 1;
  if (isNaN(h) || h < 1) h = 1;

  // Soft caps so we don't request absurd grids
  if (w > 32) w = 32;
  if (h > 32) h = 32;

  const total = w * h;
  if (total > 400) {
    // extra safety cap
    status.textContent = "Grid too large; please use at most 400 cells.";
    return;
  }

  const { excludePatterns, excludeColors } = getFilterConfig();

  status.textContent = "Generating grid...";
  bannerArea.innerHTML = "";

  try {
    const res = await fetch("/api/generate_grid", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        width: w,
        height: h,
        exclude_patterns: excludePatterns,
        exclude_colors: excludeColors,
      }),
    });

    if (!res.ok) {
      throw new Error("Server error");
    }

    const data = await res.json();
    const banners = data.banners || [];

    renderGrid(data.width || w, data.height || h, banners);

    status.textContent = `Generated ${banners.length} banner(s) in a ${w}×${h} grid.`;
  } catch (err) {
    console.error(err);
    status.textContent = "Error: could not reach server.";
  }
}

// --- Mirror grid (server-side art brain) ---

async function mirrorGrid(axis) {
  const status = document.getElementById("status");

  if (currentPage !== "grid") {
    status.textContent = "Mirroring only works in Grid view.";
    return;
  }

  if (!currentGridWidth || !currentGridHeight || !lastBanners.length) {
    status.textContent = "No grid to mirror yet. Generate a grid first.";
    return;
  }

    status.textContent = axis === "horizontal"
    ? "Mirroring horizontally (top/bottom)..."
    : "Mirroring vertically (left/right)...";


  try {
    const res = await fetch("/api/mirror_grid", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        axis,
        width: currentGridWidth,
        height: currentGridHeight,
        banners: lastBanners,
      }),
    });

    if (!res.ok) {
      throw new Error("Server error");
    }

    const data = await res.json();
    const banners = data.banners || [];
    const width = data.width || currentGridWidth;
    const height = data.height || currentGridHeight;

    renderGrid(width, height, banners);

    if (axis === "horizontal") {
        status.textContent = "Mirrored grid horizontally (top/bottom).";
    } else {
        status.textContent = "Mirrored grid vertically (left/right).";
    }

  } catch (err) {
    console.error(err);
    status.textContent = "Error: could not reach server for mirror operation.";
  }
}

// --- Load filters ---

async function loadPatterns() {
  const list = document.getElementById("pattern-list");
  list.innerHTML = "<div style='color:#888;'>Loading patterns...</div>";

  try {
    const res = await fetch("/api/patterns");
    if (!res.ok) {
      list.innerHTML = "<div style='color:#f88;'>Error loading patterns.</div>";
      return;
    }
    const data = await res.json();
    const patterns = data.patterns || [];

    if (patterns.length === 0) {
      list.innerHTML = "<div style='color:#888;'>No patterns found.</div>";
      return;
    }

    const frag = document.createDocumentFragment();

    patterns.forEach((name, idx) => {
      const id = `pat-${idx}`;
      const wrapper = document.createElement("div");
      wrapper.style.marginBottom = "2px";
      wrapper.style.display = "flex";
      wrapper.style.alignItems = "center";

      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.id = id;
      checkbox.value = name;
      checkbox.checked = true; // default: include this pattern
      checkbox.className = "pattern-checkbox";

      const label = document.createElement("label");
      label.htmlFor = id;
      label.textContent = name;

      wrapper.appendChild(checkbox);
      wrapper.appendChild(label);
      frag.appendChild(wrapper);
    });

    list.innerHTML = "";
    list.appendChild(frag);
  } catch (err) {
    console.error(err);
    list.innerHTML = "<div style='color:#f88;'>Error loading patterns.</div>";
  }
}

async function loadColors() {
  const list = document.getElementById("color-list");
  list.innerHTML = "<div style='color:#888;'>Loading colors...</div>";

  try {
    const res = await fetch("/api/colors");
    if (!res.ok) {
      list.innerHTML = "<div style='color:#f88;'>Error loading colors.</div>";
      return;
    }
    const data = await res.json();
    const colors = data.colors || [];

    if (colors.length === 0) {
      list.innerHTML = "<div style='color:#888;'>No colors found.</div>";
      return;
    }

    const frag = document.createDocumentFragment();

    colors.forEach((name, idx) => {
      const id = `color-${idx}`;
      const wrapper = document.createElement("div");
      wrapper.style.marginBottom = "2px";
      wrapper.style.display = "flex";
      wrapper.style.alignItems = "center";

      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.id = id;
      checkbox.value = name;
      checkbox.checked = true; // default: include this color
      checkbox.className = "color-checkbox";

      const label = document.createElement("label");
      label.htmlFor = id;
      label.textContent = name;

      wrapper.appendChild(checkbox);
      wrapper.appendChild(label);
      frag.appendChild(wrapper);
    });

    list.innerHTML = "";
    list.appendChild(frag);
  } catch (err) {
    console.error(err);
    list.innerHTML = "<div style='color:#f88;'>Error loading colors.</div>";
  }
}

// --- Top navigation ---

function setPage(page) {
  currentPage = page;
  const mainHeaderTitle = document.getElementById("main-header-title");
  const controlsGenerate = document.getElementById("controls-generate");
  const controlsGrid = document.getElementById("controls-grid");
  const bannerArea = document.getElementById("banner-area");

  document.querySelectorAll(".topbar-nav a").forEach((link) => {
    const linkPage = link.getAttribute("data-page");
    if (linkPage === page) {
      link.classList.add("active");
    } else {
      link.classList.remove("active");
    }
  });

  if (page === "generate") {
    mainHeaderTitle.textContent = "Generated Banners";
    controlsGenerate.style.display = "";
    controlsGrid.style.display = "none";
    bannerArea.classList.remove("grid-mode");
    bannerArea.style.gridTemplateColumns = "";
  } else if (page === "grid") {
    mainHeaderTitle.textContent = "Banner Grid";
    controlsGenerate.style.display = "none";
    controlsGrid.style.display = "";
    // grid-mode will be enabled when we actually generate/mirror
  } else if (page === "presets") {
    mainHeaderTitle.textContent = "Filter Presets (coming soon)";
    controlsGenerate.style.display = "none";
    controlsGrid.style.display = "none";
  } else if (page === "hall") {
    mainHeaderTitle.textContent = "Hall of Fame (coming soon)";
    controlsGenerate.style.display = "none";
    controlsGrid.style.display = "none";
  }
}

function setupTopNav() {
  document.querySelectorAll(".topbar-nav a").forEach((link) => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      const page = link.getAttribute("data-page");
      if (page) {
        setPage(page);
      }
    });
  });

  // default
  setPage("generate");
}

// --- Boot ---

window.addEventListener("DOMContentLoaded", () => {
  loadPatterns();
  loadColors();
  setupTopNav();

  // Wire up buttons
  const genBtn = document.getElementById("generate-button");
  if (genBtn) {
    genBtn.addEventListener("click", () => generateBanners());
  }
  const gridBtn = document.getElementById("generate-grid-button");
  if (gridBtn) {
    gridBtn.addEventListener("click", () => generateGrid());
  }
  const mirrorHBtn = document.getElementById("mirror-horizontal-button");
  if (mirrorHBtn) {
    mirrorHBtn.addEventListener("click", () => mirrorGrid("horizontal"));
  }
  const mirrorVBtn = document.getElementById("mirror-vertical-button");
  if (mirrorVBtn) {
    mirrorVBtn.addEventListener("click", () => mirrorGrid("vertical"));
  }
});
