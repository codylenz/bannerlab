
let lastBanners = []; // store last batch with slug + layers

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

    let layersHtml = "";
    if (layers.length === 0) {
    layersHtml = `<li>No layers recorded.</li>`;
    } else {
    layersHtml = layers.map((layer, i) => {
        const kind = layer.kind || "pattern";
        const pattern = layer.pattern || "unknown";
        const color = layer.color || "unknown";
        const label = (kind === "base") ? "Base" : `Layer ${i}`;
        return `<li><strong>${label}</strong>: ${pattern} (<span style="color:#9cf;">${color}</span>)</li>`;
    }).join("");
    }

    infoPanel.innerHTML = `
    <h2>Info</h2>
    <div class="info-slug">Slug: ${banner.slug}</div>
    <div><strong>Layers:</strong></div>
    <ul class="info-layers-list">
        ${layersHtml}
    </ul>
    `;
}

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
    patterns.forEach((name) => {
        const id = "pattern-" + name.replace(/[^a-zA-Z0-9_-]/g, "_");

        const wrapper = document.createElement("div");
        wrapper.style.marginBottom = "2px";
        wrapper.style.display = "flex";
        wrapper.style.alignItems = "center";

        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.id = id;
        checkbox.value = name;
        checkbox.checked = true; // default: use this pattern
        checkbox.className = "pattern-checkbox";

        const label = document.createElement("label");
        label.htmlFor = id;
        label.textContent = name;
        label.style.marginLeft = "4px";

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
    colors.forEach((name) => {
        const id = "color-" + name.replace(/[^a-zA-Z0-9_-]/g, "_");

        const wrapper = document.createElement("div");
        wrapper.style.marginBottom = "2px";
        wrapper.style.display = "flex";
        wrapper.style.alignItems = "center";

        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.id = id;
        checkbox.value = name;
        checkbox.checked = true; // default: use this color
        checkbox.className = "color-checkbox";

        const label = document.createElement("label");
        label.htmlFor = id;
        label.textContent = name;
        label.style.marginLeft = "4px";

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

async function generateBanners() {
    const countInput = document.getElementById("count-input");
    const bannerArea = document.getElementById("banner-area");
    const status = document.getElementById("status");

    let count = parseInt(countInput.value, 10);
    if (isNaN(count) || count < 1) count = 1;

    // Collect unchecked patterns -> excluded
    const excludePatterns = [];
    document.querySelectorAll(".pattern-checkbox").forEach((cb) => {
    if (!cb.checked) {
        excludePatterns.push(cb.value);
    }
    });

    // Collect unchecked colors -> excluded
    const excludeColors = [];
    document.querySelectorAll(".color-checkbox").forEach((cb) => {
    if (!cb.checked) {
        excludeColors.push(cb.value);
    }
    });

    status.textContent = "Generating...";
    try {
    const res = await fetch("/api/generate", {
        method: "POST",
        headers: {
        "Content-Type": "application/json"
        },
        body: JSON.stringify({
        count: count,
        exclude_patterns: excludePatterns,
        exclude_colors: excludeColors
        })
    });

    if (!res.ok) {
        status.textContent = "Error from server.";
        return;
    }

    const data = await res.json();
    const banners = data.banners || [];
    lastBanners = banners; // store full metadata

    // Clear previous banners
    bannerArea.innerHTML = "";
    // Reset info panel
    const infoPanel = document.getElementById("info-panel");
    infoPanel.innerHTML = `
        <h2>Info</h2>
        <div class="info-empty">Click a banner to see its details here.</div>
    `;

    // Append new banners
    banners.forEach((banner, index) => {
        const img = document.createElement("img");
        img.src = banner.src;
        img.className = "banner-image";
        img.alt = banner.slug;
        img.addEventListener("click", () => showBannerInfo(index));
        bannerArea.appendChild(img);
    });

    status.textContent = `Generated ${banners.length} banner(s).`;
    } catch (err) {
    console.error(err);
    status.textContent = "Error: could not reach server.";
    }
}

function setupTopNav() {
    const mainHeaderTitle = document.getElementById("main-header-title");

    document.querySelectorAll(".topbar-nav a").forEach((link) => {
    link.addEventListener("click", (e) => {
        e.preventDefault();
        const page = link.getAttribute("data-page");
        if (page === "generate") {
        mainHeaderTitle.textContent = "Generated Banners";
        } else if (page === "presets") {
        mainHeaderTitle.textContent = "Filter Presets (coming soon)";
        } else if (page === "hall") {
        mainHeaderTitle.textContent = "Hall of Fame (coming soon)";
        }
    });
    });
}

// Load lists on page load
window.addEventListener("DOMContentLoaded", () => {
    loadPatterns();
    loadColors();
    setupTopNav();
});

