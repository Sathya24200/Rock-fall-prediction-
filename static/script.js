/* ═══════════════════════════════════════════════════════════
   Rockfall & Landslide Early Warning System — Client JS
   ═══════════════════════════════════════════════════════════ */

// ── SocketIO Connection ────────────────────────────────────
const socket = io();

// ── DOM Elements ───────────────────────────────────────────
const alertBanner       = document.getElementById("alert-banner");
const alertReasons      = document.getElementById("alert-reasons");
const alertDismiss      = document.getElementById("alert-dismiss");
const vibrationValue    = document.getElementById("vibration-value");
const tiltValue         = document.getElementById("tilt-value");
const systemStatus      = document.getElementById("system-status");
const vibrationBarFill  = document.getElementById("vibration-bar-fill");
const tiltBarFill       = document.getElementById("tilt-bar-fill");
const connectionBadge   = document.getElementById("connection-badge");
const connectionText    = document.getElementById("connection-text");
const clockEl           = document.getElementById("clock");
const phoneUrlEl        = document.getElementById("phone-url");
const noCamNotice       = document.getElementById("no-cam-notice");
const camBadge          = document.getElementById("cam-badge");
const camLabel          = document.getElementById("cam-label");

// ── Alert Sound ────────────────────────────────────────────
const alertSound = new Audio("/static/alert.mp3");
alertSound.loop = true;
let alertActive  = false;
let alertTimeout = null;

// ── Chart Configuration ────────────────────────────────────
const MAX_POINTS = 60;
const labels = Array.from({ length: MAX_POINTS }, () => "");

function createGradient(ctx, color1, color2) {
    const gradient = ctx.createLinearGradient(0, 0, 0, 280);
    gradient.addColorStop(0, color1);
    gradient.addColorStop(1, color2);
    return gradient;
}

const chartDefaults = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { intersect: false, mode: "index" },
    animation: { duration: 300, easing: "easeOutQuart" },
    plugins: {
        legend: { display: false },
        tooltip: {
            backgroundColor: "rgba(17, 24, 39, 0.95)",
            titleColor: "#f1f5f9",
            bodyColor: "#94a3b8",
            borderColor: "rgba(99, 102, 241, 0.3)",
            borderWidth: 1,
            cornerRadius: 8,
            padding: 12,
            titleFont: { family: "'Inter'", weight: "600" },
            bodyFont: { family: "'JetBrains Mono'" },
        },
    },
    scales: {
        x: { display: false },
        y: {
            beginAtZero: true,
            grid: {
                color: "rgba(148, 163, 184, 0.06)",
                drawBorder: false,
            },
            ticks: {
                color: "#64748b",
                font: { family: "'JetBrains Mono'", size: 11 },
                padding: 8,
            },
            border: { display: false },
        },
    },
};

// ── Vibration Chart ────────────────────────────────────────
const vibCtx = document.getElementById("vibration-chart").getContext("2d");
const vibrationChart = new Chart(vibCtx, {
    type: "line",
    data: {
        labels: [...labels],
        datasets: [
            {
                label: "Vibration",
                data: Array(MAX_POINTS).fill(0),
                borderColor: "#fbbf24",
                borderWidth: 2.5,
                backgroundColor: createGradient(vibCtx, "rgba(251, 191, 36, 0.15)", "rgba(251, 191, 36, 0)"),
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 5,
                pointHoverBackgroundColor: "#fbbf24",
                pointHoverBorderColor: "#fff",
                pointHoverBorderWidth: 2,
            },
            {
                label: "Threshold",
                data: Array(MAX_POINTS).fill(15),
                borderColor: "rgba(239, 68, 68, 0.4)",
                borderWidth: 1.5,
                borderDash: [6, 4],
                pointRadius: 0,
                fill: false,
            },
        ],
    },
    options: {
        ...chartDefaults,
        scales: {
            ...chartDefaults.scales,
            y: { ...chartDefaults.scales.y, max: 40 },
        },
    },
});

// ── Tilt Chart ─────────────────────────────────────────────
const tiltCtx = document.getElementById("tilt-chart").getContext("2d");
const tiltChart = new Chart(tiltCtx, {
    type: "line",
    data: {
        labels: [...labels],
        datasets: [
            {
                label: "Tilt Angle",
                data: Array(MAX_POINTS).fill(0),
                borderColor: "#34d399",
                borderWidth: 2.5,
                backgroundColor: createGradient(tiltCtx, "rgba(52, 211, 153, 0.15)", "rgba(52, 211, 153, 0)"),
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 5,
                pointHoverBackgroundColor: "#34d399",
                pointHoverBorderColor: "#fff",
                pointHoverBorderWidth: 2,
            },
            {
                label: "Threshold",
                data: Array(MAX_POINTS).fill(30),
                borderColor: "rgba(239, 68, 68, 0.4)",
                borderWidth: 1.5,
                borderDash: [6, 4],
                pointRadius: 0,
                fill: false,
            },
        ],
    },
    options: {
        ...chartDefaults,
        scales: {
            ...chartDefaults.scales,
            y: { ...chartDefaults.scales.y, max: 90 },
        },
    },
});

// ── Push data to charts ────────────────────────────────────
function pushChartData(chart, value) {
    const data = chart.data.datasets[0].data;
    data.push(value);
    if (data.length > MAX_POINTS) data.shift();
    chart.data.labels.push("");
    if (chart.data.labels.length > MAX_POINTS) chart.data.labels.shift();
    chart.update("none");
}

// ── Socket Events ──────────────────────────────────────────
socket.on("connect", () => {
    console.log("✅ Connected to server");
    connectionBadge.className = "status-badge online";
    connectionText.textContent = "Connected";
});

socket.on("disconnect", () => {
    console.log("❌ Disconnected from server");
    connectionBadge.className = "status-badge offline";
    connectionText.textContent = "Disconnected";
});

// Server info received on connect — update IP, generate QR code, camera status
let qrInstance = null;
socket.on("server_info", (info) => {
    const ip   = info.local_ip;
    const port = 5001;
    const sensorUrl = `https://${ip}:${port}/sensor`;

    // Update phone URL box
    if (phoneUrlEl) {
        phoneUrlEl.innerHTML =
            `<a href="${sensorUrl}" style="color:inherit;font-weight:700;" target="_blank">${sensorUrl}</a>`;
    }

    // Generate / refresh QR code
    const qrEl = document.getElementById("qr-code");
    if (qrEl && typeof QRCode !== "undefined") {
        qrEl.innerHTML = ""; // clear previous
        qrInstance = new QRCode(qrEl, {
            text: sensorUrl,
            width: 160,
            height: 160,
            colorDark: "#1a1f35",
            colorLight: "#ffffff",
            correctLevel: QRCode.CorrectLevel.M,
        });
    }

    // Camera status
    if (!info.camera_available) {
        if (noCamNotice) noCamNotice.style.display = "block";
        if (camBadge) {
            camBadge.textContent = "⚠ Offline";
            camBadge.className = "card-badge";
            camBadge.style.cssText =
                "background:rgba(100,116,139,0.15);color:#64748b;border:1px solid rgba(100,116,139,0.25);";
        }
        if (camLabel) {
            camLabel.innerHTML =
                `<span class="rec-dot" style="background:#64748b;animation:none;"></span>` +
                `No Camera — Sensor-Only Mode`;
        }
    }
});

socket.on("update", (data) => {
    // Update stat cards
    vibrationValue.textContent = data.vibration.toFixed(1);
    tiltValue.textContent      = data.tilt.toFixed(1) + "°";

    // Update progress bars (normalised)
    const vibPct  = Math.min((data.vibration / 40) * 100, 100);
    const tiltPct = Math.min((data.tilt / 90) * 100, 100);
    vibrationBarFill.style.width = vibPct  + "%";
    tiltBarFill.style.width      = tiltPct + "%";

    // Push to charts
    pushChartData(vibrationChart, data.vibration);
    pushChartData(tiltChart, data.tilt);

    // Handle alert
    if (data.alert) {
        triggerAlert(data.reasons);
    } else {
        systemStatus.textContent = "NORMAL";
        systemStatus.className   = "stat-value status-val";
    }
});

// ── Alert Logic ────────────────────────────────────────────
function triggerAlert(reasons) {
    alertBanner.classList.add("active");
    alertReasons.textContent = reasons.join(" • ");
    systemStatus.textContent = "⚠ ALERT";
    systemStatus.className   = "stat-value status-val alert-state";

    if (!alertActive) {
        alertActive = true;
        alertSound.play().catch(() => {});
    }

    // Auto-dismiss after 5s of no new alerts
    clearTimeout(alertTimeout);
    alertTimeout = setTimeout(dismissAlert, 5000);
}

function dismissAlert() {
    alertBanner.classList.remove("active");
    alertActive = false;
    alertSound.pause();
    alertSound.currentTime = 0;
    systemStatus.textContent = "NORMAL";
    systemStatus.className   = "stat-value status-val";
}

alertDismiss.addEventListener("click", dismissAlert);

// ── Clock ──────────────────────────────────────────────────
function updateClock() {
    const now = new Date();
    clockEl.textContent = now.toLocaleTimeString("en-US", {
        hour:   "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
    });
}
setInterval(updateClock, 1000);
updateClock();

// ── ngrok tunnel detection (polls every 3s) ────────────────
let ngrokActive = false;
function pollNgrok() {
    fetch("/ngrok-url")
        .then(r => r.json())
        .then(data => {
            if (data.active && !ngrokActive) {
                ngrokActive = true;
                const url = data.url;

                // Upgrade QR code to ngrok HTTPS URL
                const qrEl = document.getElementById("qr-code");
                if (qrEl && typeof QRCode !== "undefined") {
                    qrEl.innerHTML = "";
                    new QRCode(qrEl, {
                        text: url, width: 160, height: 160,
                        colorDark: "#1a1f35", colorLight: "#ffffff",
                        correctLevel: QRCode.CorrectLevel.M,
                    });
                }

                // Show ngrok tip banner
                const tip     = document.getElementById("ngrok-tip");
                const tipText = document.getElementById("ngrok-url-text");
                if (tip && tipText) {
                    tipText.innerHTML =
                        `🎉 ngrok active! <a href="${url}" target="_blank" ` +
                        `style="color:inherit;font-weight:700;">${url}</a>`;
                    tip.style.display = "flex";
                }

                // Update URL bar
                if (phoneUrlEl) {
                    phoneUrlEl.innerHTML =
                        `<a href="${url}" style="color:inherit;font-weight:700;" ` +
                        `target="_blank">${url}</a>`;
                }
            } else if (!data.active && ngrokActive) {
                ngrokActive = false;
            }
        })
        .catch(() => {});
}
setInterval(pollNgrok, 3000);
pollNgrok();
