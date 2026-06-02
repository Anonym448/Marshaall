/* ===========================================================
   Marshaall — Frontend SPA
   Vanilla JS · Chart.js · Routing por hash
   =========================================================== */

(() => {
  "use strict";

  const API = "/api";
  const TK = "marshaall_token";
  const USER_KEY = "marshaall_user";
  const ROLE_KEY = "marshaall_role";

  /* ---------- Token helpers ---------- */
  const saveSession = (token, username, role) => {
    localStorage.setItem(TK, token);
    localStorage.setItem(USER_KEY, username);
    localStorage.setItem(ROLE_KEY, role);
  };
  const getToken = () => localStorage.getItem(TK);
  const getUser = () => localStorage.getItem(USER_KEY) || "?";
  const getRole = () => localStorage.getItem(ROLE_KEY) || "viewer";
  const clearSession = () => { localStorage.removeItem(TK); localStorage.removeItem(USER_KEY); localStorage.removeItem(ROLE_KEY); };

  // Export for login.html
  window.Marshaall = { getToken };

  /* ---------- API fetch wrapper ---------- */
  async function api(path, opts = {}) {
    const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const res = await fetch(`${API}${path}`, { ...opts, headers });
    let data;
    try { data = await res.json(); } catch { data = null; }
    if (res.status === 401) { clearSession(); showLogin(); throw new Error("Sesión expirada"); }
    if (!res.ok) throw new Error(data?.error || `Error ${res.status}`);
    return data;
  }

  /* ---------- Toasts ---------- */
  function toast(msg, type = "info") {
    // Filtrar errores de red transitorios que ensucian la UI
    if (msg.includes("NetworkError") || msg.includes("Failed to fetch")) return;
    
    const c = document.getElementById("toastContainer");
    if (!c) return;
    const el = document.createElement("div");
    el.className = `toast ${type}`;
    el.textContent = msg;
    c.appendChild(el);
    setTimeout(() => { el.style.opacity = "0"; setTimeout(() => el.remove(), 300); }, 3500);
  }

  /* ---------- Helpers ---------- */
  const $ = (id) => document.getElementById(id);
  const html = (el, h) => { if (el) el.innerHTML = h; };
  const esc = (s) => (s ?? "").toString().replace(/</g, "&lt;").replace(/>/g, "&gt;");

  function sevBadge(sev) {
    const s = parseInt(sev);
    if (s === 1) return `<span class="badge badge-sev1">Alta</span>`;
    if (s === 2) return `<span class="badge badge-sev2">Media</span>`;
    if (s === 3) return `<span class="badge badge-sev3">Baja</span>`;
    return `<span class="badge badge-info">Info</span>`;
  }

  function statusBadge(st) {
    const cls = `badge-${st || "nueva"}`;
    const labels = { nueva: "Nueva", investigacion: "Investigación", cerrada: "Cerrada" };
    return `<span class="badge ${cls}">${labels[st] || st}</span>`;
  }

  function incStatusBadge(st) {
    const cls = `badge-${st || "abierto"}`;
    const labels = { abierto: "Abierto", en_progreso: "En progreso", cerrado: "Cerrado" };
    return `<span class="badge ${cls}">${labels[st] || st}</span>`;
  }

  function critBadge(isCrit) {
    return isCrit ? `<span class="badge badge-critical" style="margin-left:8px;">⚠ CRÍTICO</span>` : '';
  }

  function fmtDate(d) {
    if (!d) return "—";
    if (typeof d === "string" && d.endsWith("GMT")) {
      d = d.replace(" GMT", "");
    }
    const dt = new Date(d);
    return dt.toLocaleString("es-ES", { day: "2-digit", month: "2-digit", year: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit" });
  }

  function skeleton(rows = 4) {
    let h = "";
    for (let i = 0; i < rows; i++) h += `<div class="skeleton" style="height:16px;margin-bottom:8px;width:${60 + Math.random() * 40}%"></div>`;
    return h;
  }

  function paginationHtml(page, total, perPage) {
    const pages = Math.ceil(total / perPage) || 1;
    return `
    <div class="pagination">
      <button class="btn btn-sm btn-secondary" ${page <= 1 ? "disabled" : ""} data-page="${page - 1}">← Anterior</button>
      <span>Pág. ${page} de ${pages} (${total} registros)</span>
      <button class="btn btn-sm btn-secondary" ${page >= pages ? "disabled" : ""} data-page="${page + 1}">Siguiente →</button>
    </div>
  `;
  }

  function bindPagination(container, callback) {
    container.querySelectorAll(".pagination button").forEach(btn => {
      btn.addEventListener("click", () => {
        const p = parseInt(btn.dataset.page);
        if (p) callback(p);
      });
    });
  }

  /* ---------- Auth check / routing ---------- */
  function showLogin() {
    stopAlertPolling();
    lastKnownAlertId = 0;
    const layout = $("appLayout");
    const login = $("loginPage");
    if (layout) layout.style.display = "none";
    if (login) login.style.display = "";
  }

  function showApp() {
    const layout = $("appLayout");
    const login = $("loginPage");
    if (layout) layout.style.display = "";
    if (login) login.style.display = "none";

    // Update sidebar user info
    const user = getUser();
    const role = getRole();
    html($("sidebarUsername"), esc(user));
    html($("sidebarRole"), esc(role));
    const av = $("avatarLetter");
    if (av) av.textContent = (user[0] || "?").toUpperCase();

    // Show/hide admin links
    const navUsers = $("navUsers");
    const navHealth = $("navHealth");
    const sectionSistema = $("sectionSistema");
    const isAdmin = (role === "admin");
    const isAnalista = (role === "analista");
    if (navUsers) navUsers.style.display = isAdmin ? "flex" : "none";
    if (navHealth) navHealth.style.display = isAdmin ? "flex" : "none";
    if (sectionSistema) sectionSistema.style.display = isAdmin ? "block" : "none";

    // Show/hide report options
    const reportDropdown = $("reportDropdown");
    const btnPdf = $("btnDownloadPdfTopbar");
    const btnCsv = $("btnDownloadCsvTopbar");
    if (reportDropdown) {
      reportDropdown.style.display = (isAdmin || isAnalista) ? "block" : "none";
    }
    if (btnPdf) btnPdf.style.display = isAdmin ? "block" : "none";
    if (btnCsv) btnCsv.style.display = (isAdmin || isAnalista) ? "block" : "none";

    // Start polling for new alerts
    startAlertPolling();
  }

  /* ---------- Chart helpers ---------- */
  function chartGradient(context, r, g, b, alphaTop, alphaBot) {
    alphaTop = alphaTop || 0.25; alphaBot = alphaBot || 0;
    const chart = context.chart;
    const {ctx: c, chartArea} = chart;
    if (!chartArea) return `rgba(${r},${g},${b},0.1)`;
    const grad = c.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
    grad.addColorStop(0, `rgba(${r},${g},${b},${alphaTop})`);
    grad.addColorStop(0.7, `rgba(${r},${g},${b},${alphaTop * 0.15})`);
    grad.addColorStop(1, `rgba(${r},${g},${b},${alphaBot})`);
    return grad;
  }

  const chartTooltipOpts = {
    backgroundColor: "rgba(3, 7, 18, 0.95)",
    titleColor: "#f1f5f9",
    bodyColor: "#94a3b8",
    borderColor: "rgba(96, 165, 250, 0.2)",
    borderWidth: 1,
    cornerRadius: 8,
    padding: 12,
    displayColors: true,
    boxPadding: 4,
    titleFont: { weight: "600", family: 'Geist' },
    bodyFont: { family: 'Geist' }
  };

  const chartLegendOpts = {
    position: "bottom",
    labels: {
      boxWidth: 10,
      color: "#94a3b8",
      font: { size: 11, family: 'Geist' },
      usePointStyle: true,
      pointStyle: "circle",
      padding: 16,
    }
  };

  function makeLineDataset(label, data, borderColor, r, g, b, hoverColor) {
    return {
      label: label,
      data: data,
      borderColor: borderColor,
      backgroundColor: function(context) { return chartGradient(context, r, g, b); },
      fill: 'origin',
      tension: 0.4,
      borderWidth: 2,
      pointRadius: 0,
      pointHoverRadius: 5,
      pointHoverBackgroundColor: hoverColor,
      pointHoverBorderColor: "#fff",
      pointHoverBorderWidth: 2,
    };
  }

  /* ---------- Chart instances ---------- */
  let epmChart = null;
  let sevDoughnutChart = null;
  let attackPieChart = null;
  let portsPolarChart = null;

  /* Shared chart palette - Modern & Subtle */
  const chartColors = {
    red:    { bg: 'rgba(239, 68, 68, 0.4)',  border: '#ef4444' },
    orange: { bg: 'rgba(245, 158, 11, 0.4)', border: '#f59e0b' },
    yellow: { bg: 'rgba(234, 179, 8, 0.4)',  border: '#eab308' },
    blue:   { bg: 'rgba(0, 112, 243, 0.4)',  border: '#0070f3' },
    cyan:   { bg: 'rgba(34, 211, 238, 0.4)', border: '#22d3ee' },
    purple: { bg: 'rgba(167, 139, 250, 0.4)',border: '#a78bfa' },
    green:  { bg: 'rgba(16, 185, 129, 0.4)', border: '#10b981' },
    pink:   { bg: 'rgba(236, 72, 153, 0.4)', border: '#ec4899' },
    indigo: { bg: 'rgba(99, 102, 241, 0.4)', border: '#6366f1' },
    teal:   { bg: 'rgba(20, 184, 166, 0.4)', border: '#14b8a6' },
  };
  const paletteKeys = Object.keys(chartColors);
  const paletteBg = paletteKeys.map(k => chartColors[k].bg);
  const paletteBorder = paletteKeys.map(k => chartColors[k].border);

  /* Severity-specific colors */
  const sevColors = {
    1: chartColors.red,
    2: chartColors.orange,
    3: chartColors.yellow,
    4: chartColors.blue,
  };

  /* Shared Doughnut/Pie/Polar tooltip */
  const roundChartTooltip = {
    backgroundColor: "rgba(3, 7, 18, 0.95)",
    titleColor: "#f1f5f9",
    bodyColor: "#94a3b8",
    borderColor: "rgba(96, 165, 250, 0.2)",
    borderWidth: 1,
    cornerRadius: 6,
    padding: 12,
    displayColors: true,
    boxPadding: 4,
    titleFont: { weight: "600", size: 12, family: 'Geist' },
    bodyFont: { size: 11, family: 'Geist' },
    callbacks: {
      label: function(ctx) {
        const val = typeof ctx.parsed === 'object' ? (ctx.parsed.r ?? ctx.raw) : ctx.parsed;
        // Solo calcular porcentaje si los datos son números simples (Pie/Doughnut/Polar)
        if (typeof val === 'number' && typeof ctx.dataset.data[0] === 'number') {
          const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
          if (!total) return ` ${ctx.label}: 0 (0%)`;
          
          let pct = (val / total) * 100;
          let pctStr = "";
          
          if (pct === 0) {
            pctStr = "0%";
          } else if (pct < 0.01) {
            pctStr = "<0.01%";
          } else if (pct < 0.1) {
            pctStr = pct.toFixed(2) + "%";
          } else {
            pctStr = pct.toFixed(1) + "%";
          }
          
          return ` ${ctx.label}: ${Number(val).toLocaleString()} (${pctStr})`;
        }
        // Para otros tipos de datos (Bubble, Radar), mostrar valor directo
        return ` ${ctx.label || ''}: ${JSON.stringify(val)}`;
      }
    }
  };

  /* Shared legend config for round charts */
  const roundChartLegend = {
    position: "bottom",
    labels: {
      color: "#94a3b8",
      font: { size: 10, weight: "500", family: 'Geist' },
      usePointStyle: true,
      pointStyle: "circle",
      padding: 16,
      boxWidth: 6,
    },
  };

  /* ---------- PAGES ---------- */

  // ——— DASHBOARD ———
  async function pageDashboard() {
    const pc = $("pageContent");
    html(pc, `
    <div class="stats-grid" id="dashStats">${skeleton(1)}</div>

    <div class="section-header"><h2>Analítica de amenazas</h2><div class="section-line"></div></div>
    <div class="dash-charts-row">
      <div class="card">
        <div class="card-header"><span class="card-title">Alertas por severidad</span></div>
        <div class="chart-container-sm"><canvas id="chartSevDoughnut"></canvas></div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">Tipos de ataque</span></div>
        <div class="chart-container-sm"><canvas id="chartAttackPie"></canvas></div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">Puertos más atacados</span></div>
        <div class="chart-container-sm"><canvas id="chartPortsPolar"></canvas></div>
      </div>
    </div>

    <div class="section-header"><h2>Actividad en tiempo real</h2></div>
    <div class="card" style="margin-bottom: 24px;">
      <div class="card-header">
        <span class="card-title">Eventos por minuto</span>
        <div class="topbar-spacer"></div>
        <div class="range-tabs" id="epmRange">
          <button class="range-tab active" data-min="60">1h</button>
          <button class="range-tab" data-min="360">6h</button>
          <button class="range-tab" data-min="1440">24h</button>
          <button class="range-tab" data-min="10080">7d</button>
        </div>
      </div>
      <div class="chart-container"><canvas id="chartEpm"></canvas></div>
    </div>
    <div class="card">
      <div class="card-header">
        <span class="card-title">Últimas alertas</span>
      </div>
      <div class="table-wrap" id="dashAlerts">${skeleton(5)}</div>
    </div>
  `);

    loadDashStats();
    loadSevDoughnut();
    loadAttackPie();
    loadPortsPolar();
    loadEpmChart(60);
    loadDashAlerts();

    // Range tabs
    $("epmRange")?.addEventListener("click", e => {
      const btn = e.target.closest(".range-tab");
      if (!btn) return;
      $("epmRange").querySelectorAll(".range-tab").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      loadEpmChart(parseInt(btn.dataset.min));
    });
  }

  async function loadDashStats() {
    try {
      const s = await api("/stats/summary");
      html($("dashStats"), `
      <div class="stat-card"><div class="stat-label">Alertas totales</div><div class="stat-value accent">${s.total_alerts.toLocaleString()}</div></div>
      <div class="stat-card"><div class="stat-label">Alertas abiertas</div><div class="stat-value red">${s.open_alerts.toLocaleString()}</div></div>
      <div class="stat-card"><div class="stat-label">Incidentes abiertos</div><div class="stat-value">${s.open_incidents}</div></div>
      <div class="stat-card"><div class="stat-label">Eventos 24h</div><div class="stat-value green">${s.events_24h.toLocaleString()}</div></div>
    `);
    } catch (e) { toast(e.message, "error"); }
  }

  /* --- Doughnut: Alertas por severidad --- */
  async function loadSevDoughnut() {
    try {
      const rows = await api("/stats/severity_distribution");
      const ctx = $("chartSevDoughnut");
      if (!ctx) return;
      if (sevDoughnutChart) { sevDoughnutChart.destroy(); sevDoughnutChart = null; }

      if (!rows.length) {
        ctx.parentElement.innerHTML = '<div class="empty-state" style="padding:32px 0;"><div class="empty-state-text">Sin datos de severidad</div></div>';
        return;
      }

      const labels = rows.map(r => {
        const s = parseInt(r.severity);
        return s === 1 ? "Alta" : s === 2 ? "Media" : s === 3 ? "Baja" : "Info";
      });
      const data = rows.map(r => r.count);
      const bgArr = rows.map(r => (sevColors[parseInt(r.severity)] || chartColors.blue).bg);
      const borderArr = rows.map(r => (sevColors[parseInt(r.severity)] || chartColors.blue).border);

      sevDoughnutChart = new Chart(ctx, {
        type: "doughnut",
        data: {
          labels,
          datasets: [{
            data,
            backgroundColor: bgArr,
            borderColor: borderArr,
            borderWidth: 2,
            borderRadius: 4,
            borderAlign: "inner",
            hoverOffset: 8,
            spacing: 3,
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: "62%",
          animation: { animateRotate: true, animateScale: true },
          plugins: {
            legend: roundChartLegend,
            tooltip: roundChartTooltip,
          },
        }
      });
    } catch (e) { /* silent */ }
  }

  /* --- Pie: Tipos de ataque --- */
  const attackTypeTranslations = {
    // Categorías Suricata estándar
    "A Network Trojan was detected": "Troyano de red detectado",
    "Attempted Information Leak": "Intento de fuga de información",
    "Information Leak": "Fuga de información",
    "Network Trojan": "Troyano de red",
    "Misc activity": "Actividad diversa",
    "Misc Attack": "Ataque diverso",
    "Potentially Bad Traffic": "Tráfico potencialmente malicioso",
    "Bad Traffic": "Tráfico malicioso",
    "Web Application Attack": "Ataque a aplicación web",
    "Attempted Denial of Service": "Intento de denegación de servicio",
    "Denial of Service": "Denegación de servicio",
    "Detection of a Network Scan": "Escaneo de red detectado",
    "Network Scan": "Escaneo de red",
    "Attempted User Privilege Gain": "Intento de escalada de privilegios",
    "Attempted Administrator Privilege Gain": "Intento de acceso como administrador",
    "Successful Administrator Privilege Gain": "Acceso de administrador logrado",
    "Successful User Privilege Gain": "Escalada de privilegios lograda",
    "Decode of an RPC Query": "Decodificación de consulta RPC",
    "Executable Code was Detected": "Código ejecutable detectado",
    "A suspicious filename was detected": "Nombre de archivo sospechoso",
    "Not Suspicious Traffic": "Tráfico no sospechoso",
    "Unknown Traffic": "Tráfico desconocido",
    "Generic Protocol Command Decode": "Decodificación genérica de protocolo",
    "access to a potentially vulnerable web application": "Acceso a aplicación web vulnerable",
    "Policy Violation": "Violación de política",
    // Categorías adicionales frecuentes
    "Exploit Kit Activity": "Actividad de exploit kit",
    "Exploit Kit": "Exploit kit",
    "Brute Force": "Fuerza bruta",
    "SSH Brute Force": "Fuerza bruta SSH",
    "Credential Theft": "Robo de credenciales",
    "Malware Command and Control Activity": "Actividad C2 de malware",
    "Command and Control": "Mando y control (C2)",
    "Ransomware": "Ransomware",
    "Phishing": "Phishing",
    "SQL Injection": "Inyección SQL",
    "Cross Site Scripting": "Cross-Site Scripting (XSS)",
    "Remote Code Execution": "Ejecución remota de código",
    "Local File Inclusion": "Inclusión de archivo local",
    "Remote File Inclusion": "Inclusión de archivo remoto",
    "Directory Traversal": "Salto de directorio",
    "Trojan Activity": "Actividad de troyano",
    "Botnet Activity": "Actividad de botnet",
    "Cryptocurrency Mining": "Minería de criptomonedas",
    "Suspicious Traffic": "Tráfico sospechoso",
    "Targeted Malicious Activity": "Actividad maliciosa dirigida",
  };

  function translateAttackType(t) {
    if (!t) return "Desconocido";
    if (attackTypeTranslations[t]) return attackTypeTranslations[t];
    for (const [en, es] of Object.entries(attackTypeTranslations)) {
      if (t.toLowerCase().includes(en.toLowerCase())) return es;
    }
    return t;
  }

  async function loadAttackPie() {
    try {
      const rows = await api("/stats/attack_types");
      const ctx = $("chartAttackPie");
      if (!ctx) return;
      if (attackPieChart) { attackPieChart.destroy(); attackPieChart = null; }

      if (!rows.length) {
        ctx.parentElement.innerHTML = '<div class="empty-state" style="padding:32px 0;"><div class="empty-state-text">Sin datos de ataques</div></div>';
        return;
      }

      const labels = rows.map(r => {
        const t = translateAttackType(r.attack_type);
        return t.length > 28 ? t.slice(0, 26) + "…" : t;
      });
      const fullLabels = rows.map(r => translateAttackType(r.attack_type));
      const data = rows.map(r => r.count);
      const bgArr = rows.map((_, i) => paletteBg[i % paletteBg.length]);
      const borderArr = rows.map((_, i) => paletteBorder[i % paletteBorder.length]);

      attackPieChart = new Chart(ctx, {
        type: "pie",
        data: {
          labels,
          datasets: [{
            data,
            backgroundColor: bgArr,
            borderColor: borderArr,
            borderWidth: 2,
            borderAlign: "inner",
            hoverOffset: 8,
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: { animateRotate: true, animateScale: false },
          plugins: {
            legend: roundChartLegend,
            tooltip: {
              ...roundChartTooltip,
              callbacks: {
                title: function(items) {
                  if (!items.length) return '';
                  return fullLabels[items[0].dataIndex] || items[0].label;
                },
                label: function(ctx) {
                  const val = ctx.parsed;
                  const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                  const pct = total ? ((val / total) * 100).toFixed(1) : 0;
                  const name = fullLabels[ctx.dataIndex] || ctx.label;
                  return ` ${name}: ${Number(val).toLocaleString()} (${pct}%)`;
                }
              }
            },
          },
        }
      });
    } catch (e) { /* silent */ }
  }

  /* --- Polar Area: Puertos más atacados --- */
  async function loadPortsPolar() {
    try {
      const rows = await api("/stats/top_ports");
      const ctx = $("chartPortsPolar");
      if (!ctx) return;
      if (portsPolarChart) { portsPolarChart.destroy(); portsPolarChart = null; }

      if (!rows.length) {
        ctx.parentElement.innerHTML = '<div class="empty-state" style="padding:32px 0;"><div class="empty-state-text">Sin datos de puertos</div></div>';
        return;
      }

      const labels = rows.map(r => r.service ? `${r.service} (:${r.dest_port})` : `:${r.dest_port}`);
      const data = rows.map(r => r.count);
      const bgArr = rows.map((_, i) => paletteBg[i % paletteBg.length].replace("0.85", "0.55"));
      const borderArr = rows.map((_, i) => paletteBorder[i % paletteBorder.length]);

      portsPolarChart = new Chart(ctx, {
        type: "polarArea",
        data: {
          labels,
          datasets: [{
            data,
            backgroundColor: bgArr,
            borderColor: borderArr,
            borderWidth: 2,
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: { animateRotate: true, animateScale: true },
          scales: {
            r: {
              ticks: { display: false },
              grid: { color: "rgba(255,255,255,0.04)" },
              pointLabels: { display: false },
              beginAtZero: true,
            }
          },
          plugins: {
            legend: roundChartLegend,
            tooltip: roundChartTooltip,
          },
        }
      });
    } catch (e) { /* silent */ }
  }

  async function loadEpmChart(minutes) {
    try {
      const rows = await api(`/stats/events_per_minute?minutes=${minutes}`);
      const labels = rows.map(r => {
        const d = new Date(r.minute_bucket);
        return minutes <= 360
          ? d.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" })
          : d.toLocaleDateString("es-ES", { day: "2-digit", month: "2-digit" }) + " " + d.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" });
      });

      const ctx = $("chartEpm");
      if (!ctx) return;
      if (epmChart) epmChart.destroy();

      const dataSev1 = rows.map(r => +(r.sev_1 || 0));
      const dataSev2 = rows.map(r => +(r.sev_2 || 0));
      const dataSev3 = rows.map(r => +(r.sev_3 || 0));
      const dataNone = rows.map(r => +(r.sev_none || 0));
      const maxVal = Math.max(...rows.map(r => +(r.total || 0)), 1);

      epmChart = new Chart(ctx, {
        type: "line",
        data: {
          labels,
          datasets: [
            {
              label: "Sev Alta",
              data: dataSev1,
              borderColor: chartColors.red.border,
              backgroundColor: chartColors.red.bg,
              borderWidth: 1.5,
              fill: "origin",
              tension: 0.4,
              pointRadius: 0,
              pointHoverRadius: 4,
              pointHoverBackgroundColor: chartColors.red.border,
              order: 1,
            },
            {
              label: "Sev Media",
              data: dataSev2,
              borderColor: chartColors.orange.border,
              backgroundColor: chartColors.orange.bg,
              borderWidth: 1.5,
              fill: "origin",
              tension: 0.4,
              pointRadius: 0,
              pointHoverRadius: 4,
              pointHoverBackgroundColor: chartColors.orange.border,
              order: 2,
            },
            {
              label: "Sev Baja",
              data: dataSev3,
              borderColor: chartColors.yellow.border,
              backgroundColor: chartColors.yellow.bg,
              borderWidth: 1.5,
              fill: "origin",
              tension: 0.4,
              pointRadius: 0,
              pointHoverRadius: 4,
              pointHoverBackgroundColor: chartColors.yellow.border,
              order: 3,
            },
            {
              label: "Otros",
              data: dataNone,
              borderColor: chartColors.blue.border,
              backgroundColor: chartColors.blue.bg,
              borderWidth: 1.5,
              fill: "origin",
              tension: 0.4,
              pointRadius: 0,
              pointHoverRadius: 4,
              pointHoverBackgroundColor: chartColors.blue.border,
              order: 4,
            },
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: "index", intersect: false },
          plugins: {
            legend: roundChartLegend,
            tooltip: roundChartTooltip,
          },
          scales: {
            x: {
              ticks: { maxRotation: 0, autoSkipPadding: 20, color: "#666", font: { size: 10, family: 'Geist Mono' } },
              grid: { color: "rgba(255,255,255,0.03)" },
              border: { display: false },
            },
            y: {
              beginAtZero: true,
              suggestedMax: maxVal < 5 ? 5 : undefined,
              ticks: { color: "#666", font: { size: 10, family: 'Geist Mono' }, padding: 8, precision: 0 },
              grid: { color: "rgba(255,255,255,0.03)" },
              border: { display: false },
            }
          }
        }
      });
    } catch (e) { toast(e.message, "error"); }
  }

  async function loadDashAlerts() {
    try {
      const res = await api("/alerts?per_page=10&page=1");
      const rows = res.data || [];
      if (!rows.length) {
        html($("dashAlerts"), `<div class="empty-state"><div class="empty-state-icon"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg></div><div class="empty-state-text">Sin alertas registradas</div></div>`);
        return;
      }
      let t = `<table><thead><tr><th>Fecha</th><th>Origen</th><th>Destino</th><th>Firma</th><th>Sev</th><th>Estado</th></tr></thead><tbody>`;
      for (const r of rows) {
        t += `<tr class="clickable" data-alert="${r.id}">
        <td>${fmtDate(r.ts)}</td><td>${esc(r.src_ip)}</td><td>${esc(r.dest_ip)}</td>
        <td>${esc((r.signature || "").slice(0, 60))}${critBadge(r.is_critical)}</td><td>${sevBadge(r.severity)}</td><td>${statusBadge(r.status)}</td>
      </tr>`;
      }
      t += `</tbody></table>`;
      html($("dashAlerts"), t);
      $("dashAlerts").querySelectorAll("tr.clickable").forEach(tr => {
        tr.addEventListener("click", () => { location.hash = `#alert/${tr.dataset.alert}`; });
      });
    } catch (e) { toast(e.message, "error"); }
  }

  // ——— ALERTS LIST ———
  let alertsPage = 1;
  async function pageAlerts(page = 1) {
    alertsPage = page;
    const pc = $("pageContent");
    html(pc, `
    <div class="filters-bar" id="alertFilters">
      <div class="form-group" style="max-width: 100px;"><label>ID</label><input id="fId" type="text" placeholder="ID..." /></div>
      <div class="form-group"><label>Búsqueda</label><input id="fQ" type="text" placeholder="IP, firma..." /></div>
      <div class="form-group"><label>Severidad</label><select id="fSev"><option value="">Todas</option><option value="1">Alta</option><option value="2">Media</option><option value="3">Baja</option></select></div>
      <div class="form-group"><label>Estado</label><select id="fSt"><option value="">Todos</option><option value="nueva">Nueva</option><option value="investigacion">Investigación</option><option value="cerrada">Cerrada</option></select></div>
      <div class="form-group"><label>Desde</label><input id="fFrom" type="date" /></div>
      <div class="form-group"><label>Hasta</label><input id="fTo" type="date" /></div>
      <div class="form-group" style="align-self:flex-end;"><button class="btn btn-primary btn-sm" id="btnFilterAlerts">Filtrar</button></div>
    </div>
    <div class="card"><div class="table-wrap" id="alertsTable">${skeleton(6)}</div><div id="alertsPag"></div></div>
  `);

    loadAlerts(page);

    $("btnFilterAlerts")?.addEventListener("click", () => loadAlerts(1));
    // Enter in filter fields
    ["fId", "fQ", "fSev", "fSt", "fFrom", "fTo"].forEach(id => {
      $(id)?.addEventListener("keydown", e => { if (e.key === "Enter") loadAlerts(1); });
    });
  }

  async function loadAlerts(page) {
    alertsPage = page;
    const params = new URLSearchParams({ page, per_page: 25 });
    const aid = $("fId")?.value; if (aid) params.set("id", aid);
    const q = $("fQ")?.value; if (q) params.set("q", q);
    const sev = $("fSev")?.value; if (sev) params.set("severity", sev);
    const st = $("fSt")?.value; if (st) params.set("status", st);
    const from = $("fFrom")?.value; if (from) params.set("from", from);
    const to = $("fTo")?.value; if (to) params.set("to", to);

    try {
      const res = await api(`/alerts?${params}`);
      const rows = res.data || [];
      if (!rows.length) {
        html($("alertsTable"), `<div class="empty-state"><div class="empty-state-icon"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg></div><div class="empty-state-text">Sin resultados</div></div>`);
        html($("alertsPag"), "");
        return;
      }
      let t = `<table><thead><tr><th>ID</th><th>Fecha</th><th>Origen</th><th>Destino</th><th>Proto</th><th>Firma</th><th>Sev</th><th>Estado</th></tr></thead><tbody>`;
      for (const r of rows) {
        t += `<tr class="clickable" data-alert="${r.id}">
        <td>${r.id}</td><td>${fmtDate(r.ts)}</td><td>${esc(r.src_ip)}</td><td>${esc(r.dest_ip)}</td>
        <td>${esc(r.proto)}</td><td>${esc((r.signature || "").slice(0, 70))}${critBadge(r.is_critical)}</td>
        <td>${sevBadge(r.severity)}</td><td>${statusBadge(r.status)}</td>
      </tr>`;
      }
      t += `</tbody></table>`;
      html($("alertsTable"), t);
      html($("alertsPag"), paginationHtml(res.page, res.total, res.per_page));

      $("alertsTable").querySelectorAll("tr.clickable").forEach(tr => {
        tr.addEventListener("click", () => { location.hash = `#alert/${tr.dataset.alert}`; });
      });
      bindPagination($("alertsPag"), loadAlerts);
    } catch (e) { toast(e.message, "error"); }
  }

  // ——— ALERT DETAIL ———
  async function pageAlertDetail(id) {
    const pc = $("pageContent");
    html(pc, skeleton(8));
    try {
      const res = await api(`/alerts/${id}`);
      const a = res.alert;
      const role = getRole();
      const canEdit = role === "admin" || role === "analista";

      let rawPretty = "";
      try { rawPretty = JSON.stringify(JSON.parse(a.raw_json), null, 2); } catch { rawPretty = a.raw_json || ""; }

      let h = `
      <div style="margin-bottom:12px;"><button class="btn btn-secondary btn-sm" id="btnBackAlerts">← Alertas</button></div>
      <div class="detail-grid">
        <div class="card ${a.is_critical ? 'critical-border' : ''}">
          <div class="card-header"><span class="card-title">Alerta #${a.id}</span> ${sevBadge(a.severity)} ${statusBadge(a.status)} ${critBadge(a.is_critical)}</div>
          <div class="detail-field"><div class="detail-label">Firma</div><div class="detail-value">${esc(a.signature)}</div></div>
          <div class="detail-field"><div class="detail-label">Categoría</div><div class="detail-value">${esc(translateAttackType(a.category)) || "—"}</div></div>
          <div class="detail-field"><div class="detail-label">Fecha</div><div class="detail-value">${fmtDate(a.ts)}</div></div>
          <div style="display:flex;gap:16px;flex-wrap:wrap;">
            <div class="detail-field"><div class="detail-label">IP Origen</div><div class="detail-value">${esc(a.src_ip)}${a.src_port ? ":" + a.src_port : ""}</div></div>
            <div class="detail-field"><div class="detail-label">IP Destino</div><div class="detail-value">${esc(a.dest_ip)}${a.dest_port ? ":" + a.dest_port : ""}</div></div>
            <div class="detail-field"><div class="detail-label">Protocolo</div><div class="detail-value">${esc(a.proto)}</div></div>
            <div class="detail-field"><div class="detail-label">Flow ID</div><div class="detail-value">${a.flow_id || "—"}</div></div>
          </div>
          ${canEdit ? `
          <div style="margin-top:12px;" class="btn-group">
            <button class="btn btn-sm ${a.status === 'nueva' ? 'btn-primary' : 'btn-secondary'}" data-st="nueva">Nueva</button>
            <button class="btn btn-sm ${a.status === 'investigacion' ? 'btn-primary' : 'btn-secondary'}" data-st="investigacion">Investigación</button>
            <button class="btn btn-sm ${a.status === 'cerrada' ? 'btn-primary' : 'btn-secondary'}" data-st="cerrada">Cerrada</button>
          </div>` : ""}
        </div>

        <div class="card">
          <div class="card-header"><span class="card-title">Incidentes vinculados</span></div>
          ${res.incidents.length ? res.incidents.map(inc => `
            <div style="margin-bottom:6px;"><a href="#incident/${inc.id}">#${inc.id} — ${esc(inc.title)}</a> ${incStatusBadge(inc.status)}</div>
          `).join("") : '<div class="empty-state" style="padding:16px;"><div class="empty-state-text">Sin incidentes vinculados</div></div>'}
        </div>
      </div>

      ${res.related_events.length ? `
      <div class="card" style="margin-bottom:16px;">
        <div class="card-header"><span class="card-title">Eventos relacionados (flow_id)</span><span class="card-subtitle">${res.related_events.length} eventos</span></div>
        <div class="table-wrap"><table><thead><tr><th>ID</th><th>Fecha</th><th>Tipo</th><th>Origen</th><th>Destino</th><th>Firma</th><th>Sev</th></tr></thead><tbody>
          ${res.related_events.map(e => `<tr><td>${e.id}</td><td>${fmtDate(e.ts)}</td><td>${esc(e.event_type)}</td><td>${esc(e.src_ip)}</td><td>${esc(e.dest_ip)}</td><td>${esc((e.signature || "").slice(0, 50))}</td><td>${sevBadge(e.severity)}</td></tr>`).join("")}
        </tbody></table></div>
      </div>` : ""}

      <div class="card" style="margin-bottom:16px;">
        <div class="card-header"><span class="card-title">Comentarios</span></div>
        <div id="alertComments">
          ${res.comments.length ? res.comments.map(c => `
            <div class="comment"><div class="comment-meta">${esc(c.author)} · ${fmtDate(c.created_at)}</div><div class="comment-body">${esc(c.body)}</div></div>
          `).join("") : '<p style="color:var(--txt-3);font-size:13px;">Sin comentarios</p>'}
        </div>
        ${canEdit ? `
        <div style="margin-top:12px;">
          <textarea id="alertCommentBody" placeholder="Añadir comentario..." style="width:100%;"></textarea>
          <button class="btn btn-primary btn-sm" id="btnAddAlertComment" style="margin-top:6px;">Enviar</button>
        </div>` : ""}
      </div>

      <details class="card" style="cursor:pointer;">
        <summary class="card-title" style="padding:4px 0;">Evento RAW (JSON)</summary>
        <pre style="margin-top:10px;font-size:11px;color:var(--txt-3);overflow:auto;max-height:300px;">${esc(rawPretty)}</pre>
      </details>
    `;

      html(pc, h);

      // Back
      $("btnBackAlerts")?.addEventListener("click", () => { location.hash = "#alerts"; });

      // Status change
      if (canEdit) {
        pc.querySelectorAll("[data-st]").forEach(btn => {
          btn.addEventListener("click", async () => {
            try {
              await api(`/alerts/${id}/status`, { method: "PATCH", body: JSON.stringify({ status: btn.dataset.st }) });
              toast("Estado actualizado", "success");
              pageAlertDetail(id);
            } catch (e) { toast(e.message, "error"); }
          });
        });

        $("btnAddAlertComment")?.addEventListener("click", async () => {
          const body = $("alertCommentBody")?.value?.trim();
          if (!body) return;
          try {
            await api(`/alerts/${id}/comments`, { method: "POST", body: JSON.stringify({ body }) });
            toast("Comentario añadido", "success");
            pageAlertDetail(id);
          } catch (e) { toast(e.message, "error"); }
        });
      }

    } catch (e) { html(pc, `<p style="color:var(--red);">Error: ${esc(e.message)}</p>`); }
  }

  // ——— INCIDENTS LIST ———
  async function pageIncidents(page = 1) {
    const pc = $("pageContent");
    const role = getRole();
    const canCreate = role === "admin" || role === "analista";

    html(pc, `
    <div class="filters-bar">
      <div class="form-group"><label>Estado</label><select id="fIncSt"><option value="">Todos</option><option value="abierto">Abierto</option><option value="en_progreso">En progreso</option><option value="cerrado">Cerrado</option></select></div>
      <div class="form-group" style="align-self:flex-end;"><button class="btn btn-primary btn-sm" id="btnFilterInc">Filtrar</button></div>
      ${canCreate ? '<div class="form-group" style="align-self:flex-end;margin-left:auto;"><button class="btn btn-primary btn-sm" id="btnNewInc">+ Incidente</button></div>' : ''}
    </div>
    <div class="card"><div class="table-wrap" id="incTable">${skeleton(5)}</div><div id="incPag"></div></div>
  `);

    loadIncidents(page);
    $("btnFilterInc")?.addEventListener("click", () => loadIncidents(1));
    $("btnNewInc")?.addEventListener("click", showNewIncidentModal);
  }

  async function loadIncidents(page) {
    const params = new URLSearchParams({ page, per_page: 25 });
    const st = $("fIncSt")?.value; if (st) params.set("status", st);

    try {
      const res = await api(`/incidents?${params}`);
      const rows = res.data || [];
      if (!rows.length) {
        html($("incTable"), `<div class="empty-state"><div class="empty-state-icon"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg></div><div class="empty-state-text">Sin incidentes</div></div>`);
        html($("incPag"), "");
        return;
      }
      let t = `<table><thead><tr><th>ID</th><th>Título</th><th>Sev</th><th>Estado</th><th>Alertas</th><th>Creado</th><th>Actualizado</th></tr></thead><tbody>`;
      for (const r of rows) {
        t += `<tr class="clickable" data-inc="${r.id}">
        <td>${r.id}</td><td>${esc(r.title)}${critBadge(r.is_critical)}</td><td>${sevBadge(r.severity)}</td>
        <td>${incStatusBadge(r.status)}</td><td>${r.alert_count || 0}</td>
        <td>${fmtDate(r.created_at)}</td><td>${fmtDate(r.updated_at)}</td>
      </tr>`;
      }
      t += `</tbody></table>`;
      html($("incTable"), t);
      html($("incPag"), paginationHtml(res.page, res.total, res.per_page));

      $("incTable").querySelectorAll("tr.clickable").forEach(tr => {
        tr.addEventListener("click", () => { location.hash = `#incident/${tr.dataset.inc}`; });
      });
      bindPagination($("incPag"), loadIncidents);
    } catch (e) { toast(e.message, "error"); }
  }

  function showNewIncidentModal() {
    const overlay = document.createElement("div");
    overlay.className = "modal-overlay";
    overlay.innerHTML = `
    <div class="modal">
      <div class="modal-title">Nuevo incidente</div>
      <div class="form-group"><label>Título</label><input id="mIncTitle" type="text" style="width:100%;" /></div>
      <div class="form-group"><label>Descripción</label><textarea id="mIncDesc" style="width:100%;"></textarea></div>
      <div class="form-row">
        <div class="form-group"><label>Severidad</label><select id="mIncSev"><option value="1">Alta</option><option value="2">Media</option><option value="3" selected>Baja</option></select></div>
        <div class="form-group"><label>Etiquetas</label><input id="mIncTags" type="text" placeholder="tag1, tag2" /></div>
      </div>
      <div class="btn-group" style="margin-top:12px;">
        <button class="btn btn-primary" id="mIncSave">Crear</button>
        <button class="btn btn-secondary" id="mIncCancel">Cancelar</button>
      </div>
    </div>
  `;
    document.body.appendChild(overlay);

    $("mIncCancel").addEventListener("click", () => overlay.remove());
    overlay.addEventListener("click", e => { if (e.target === overlay) overlay.remove(); });

    $("mIncSave").addEventListener("click", async () => {
      const title = $("mIncTitle").value.trim();
      if (!title) { toast("Título requerido", "error"); return; }
      try {
        const res = await api("/incidents", {
          method: "POST",
          body: JSON.stringify({
            title,
            description: $("mIncDesc").value,
            severity: parseInt($("mIncSev").value),
            tags: $("mIncTags").value,
          }),
        });
        overlay.remove();
        toast("Incidente creado", "success");
        location.hash = `#incident/${res.id}`;
      } catch (e) { toast(e.message, "error"); }
    });
  }

  // ——— INCIDENT DETAIL ———
  async function pageIncidentDetail(id) {
    const pc = $("pageContent");
    html(pc, skeleton(8));
    try {
      const res = await api(`/incidents/${id}`);
      const inc = res.incident;
      const role = getRole();
      const canEdit = role === "admin" || role === "analista";

      let h = `
      <div style="margin-bottom:12px;"><button class="btn btn-secondary btn-sm" id="btnBackInc">← Incidentes</button></div>
      <div class="card ${inc.is_critical ? 'critical-border' : ''}" style="margin-bottom:16px;">
        <div class="card-header">
          <span class="card-title">Incidente #${inc.id}</span> ${sevBadge(inc.severity)} ${incStatusBadge(inc.status)} ${critBadge(inc.is_critical)}
        </div>
        <div class="detail-field"><div class="detail-label">Título</div><div class="detail-value">${esc(inc.title)}</div></div>
        <div class="detail-field"><div class="detail-label">Descripción</div><div class="detail-value">${esc(inc.description) || "—"}</div></div>
        <div style="display:flex;gap:16px;flex-wrap:wrap;">
          <div class="detail-field"><div class="detail-label">Creado por</div><div class="detail-value">${esc(inc.created_by)}</div></div>
          <div class="detail-field"><div class="detail-label">Etiquetas</div><div class="detail-value">${esc(inc.tags) || "—"}</div></div>
          <div class="detail-field"><div class="detail-label">Creado</div><div class="detail-value">${fmtDate(inc.created_at)}</div></div>
          <div class="detail-field"><div class="detail-label">Actualizado</div><div class="detail-value">${fmtDate(inc.updated_at)}</div></div>
        </div>
        ${canEdit ? `
        <div style="margin-top:12px;" class="btn-group">
          <button class="btn btn-sm ${inc.status === 'abierto' ? 'btn-primary' : 'btn-secondary'}" data-ist="abierto">Abierto</button>
          <button class="btn btn-sm ${inc.status === 'en_progreso' ? 'btn-primary' : 'btn-secondary'}" data-ist="en_progreso">En progreso</button>
          <button class="btn btn-sm ${inc.status === 'cerrado' ? 'btn-primary' : 'btn-secondary'}" data-ist="cerrado">Cerrado</button>
        </div>` : ""}
      </div>

      <div class="card" style="margin-bottom:16px;">
        <div class="card-header"><span class="card-title">Alertas vinculadas</span><span class="card-subtitle">${res.alerts.length} alertas</span></div>
        ${res.alerts.length ? `
        <div class="table-wrap"><table><thead><tr><th>ID</th><th>Fecha</th><th>Origen</th><th>Firma</th><th>Sev</th><th>Estado</th>${canEdit ? "<th></th>" : ""}</tr></thead><tbody>
          ${res.alerts.map(a => `<tr>
            <td><a href="#alert/${a.id}">#${a.id}</a></td><td>${fmtDate(a.ts)}</td><td>${esc(a.src_ip)}</td>
            <td>${esc((a.signature || "").slice(0, 50))}</td><td>${sevBadge(a.severity)}</td><td>${statusBadge(a.status)}</td>
            ${canEdit ? `<td><button class="btn btn-danger btn-sm" data-unlink="${a.id}">✕</button></td>` : ""}
          </tr>`).join("")}
        </tbody></table></div>` : '<div class="empty-state" style="padding:16px;"><div class="empty-state-text">Sin alertas vinculadas</div></div>'}

        ${canEdit ? `
        <div style="margin-top:12px;display:flex;gap:8px;align-items:center;">
          <input id="linkAlertIds" type="text" placeholder="IDs de alerta: 1,2,3" style="flex:1;" />
          <button class="btn btn-primary btn-sm" id="btnLinkAlerts">Vincular</button>
        </div>` : ""}
      </div>

      <div class="card" style="margin-bottom:16px;">
        <div class="card-header"><span class="card-title">Comentarios</span></div>
        <div id="incComments">
          ${res.comments.length ? res.comments.map(c => `
            <div class="comment"><div class="comment-meta">${esc(c.author)} · ${fmtDate(c.created_at)}</div><div class="comment-body">${esc(c.body)}</div></div>
          `).join("") : '<p style="color:var(--txt-3);font-size:13px;">Sin comentarios</p>'}
        </div>
        ${canEdit ? `
        <div style="margin-top:12px;">
          <textarea id="incCommentBody" placeholder="Añadir comentario..." style="width:100%;"></textarea>
          <button class="btn btn-primary btn-sm" id="btnAddIncComment" style="margin-top:6px;">Enviar</button>
        </div>` : ""}
      </div>
    `;

      html(pc, h);

      $("btnBackInc")?.addEventListener("click", () => { location.hash = "#incidents"; });

      // Status change
      if (canEdit) {
        pc.querySelectorAll("[data-ist]").forEach(btn => {
          btn.addEventListener("click", async () => {
            try {
              await api(`/incidents/${id}`, { method: "PATCH", body: JSON.stringify({ status: btn.dataset.ist }) });
              toast("Estado actualizado", "success");
              pageIncidentDetail(id);
            } catch (e) { toast(e.message, "error"); }
          });
        });

        // Unlink alert
        pc.querySelectorAll("[data-unlink]").forEach(btn => {
          btn.addEventListener("click", async (ev) => {
            ev.stopPropagation();
            try {
              await api(`/incidents/${id}/alerts/${btn.dataset.unlink}`, { method: "DELETE" });
              toast("Alerta desvinculada", "success");
              pageIncidentDetail(id);
            } catch (e) { toast(e.message, "error"); }
          });
        });

        // Link alerts
        $("btnLinkAlerts")?.addEventListener("click", async () => {
          const raw = $("linkAlertIds")?.value || "";
          const ids = raw.split(",").map(s => parseInt(s.trim())).filter(n => !isNaN(n));
          if (!ids.length) { toast("Indica IDs separados por coma", "error"); return; }
          try {
            await api(`/incidents/${id}/alerts`, { method: "POST", body: JSON.stringify({ event_ids: ids }) });
            toast("Alertas vinculadas", "success");
            pageIncidentDetail(id);
          } catch (e) { toast(e.message, "error"); }
        });

        // Comment
        $("btnAddIncComment")?.addEventListener("click", async () => {
          const body = $("incCommentBody")?.value?.trim();
          if (!body) return;
          try {
            await api(`/incidents/${id}/comments`, { method: "POST", body: JSON.stringify({ body }) });
            toast("Comentario añadido", "success");
            pageIncidentDetail(id);
          } catch (e) { toast(e.message, "error"); }
        });
      }

    } catch (e) { html(pc, `<p style="color:var(--red);">Error: ${esc(e.message)}</p>`); }
  }

  // ——— EVENTS ———
  async function pageEvents(page = 1) {
    const pc = $("pageContent");
    html(pc, `
    <div class="card" style="margin-bottom:16px;">
      <div class="card-header">
        <span class="card-title">Análisis de orígenes de amenazas</span>
      </div>
      <div class="chart-container"><canvas id="chartTopIps"></canvas></div>
    </div>
    <div class="card"><div class="table-wrap" id="evtTable">${skeleton(6)}</div><div id="evtPag"></div></div>
  `);

    loadTopIpsChart();
    loadEvents(page);
  }

  let topIpsChart = null;
  async function loadTopIpsChart() {
    try {
      const rows = await api("/stats/top_ips?limit=10");
      const ctx = $("chartTopIps");
      if (!ctx) return;
      if (topIpsChart) { topIpsChart.destroy(); topIpsChart = null; }

      if (!rows.length) {
        ctx.parentElement.innerHTML = '<div class="empty-state" style="padding:32px 0;"><div class="empty-state-text">Sin datos de IPs atacantes</div></div>';
        return;
      }

      const labels = rows.map(r => r.src_ip);
      const alertCounts = rows.map(r => r.alert_count);
      const maxSeverities = rows.map(r => r.max_severity);

      const bgColors = rows.map(r => {
        if (r.max_severity === 1) return 'rgba(239, 68, 68, 0.8)';
        if (r.max_severity === 2) return 'rgba(245, 158, 11, 0.8)';
        if (r.max_severity === 3) return 'rgba(234, 179, 8, 0.8)';
        return 'rgba(59, 130, 246, 0.8)';
      });
      const borderColors = rows.map(r => {
        if (r.max_severity === 1) return '#ef4444';
        if (r.max_severity === 2) return '#f59e0b';
        if (r.max_severity === 3) return '#eab308';
        return '#3b82f6';
      });

      topIpsChart = new Chart(ctx, {
        type: "bar",
        data: {
          labels,
          datasets: [
            {
              label: "Volumen de alertas",
              data: alertCounts,
              backgroundColor: function(context) {
                const chart = context.chart;
                const {ctx: c, chartArea} = chart;
                if (!chartArea) return "rgba(59, 130, 246, 0.5)";
                const grad = c.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
                grad.addColorStop(0, "rgba(59, 130, 246, 0.05)");
                grad.addColorStop(1, "rgba(59, 130, 246, 0.8)");
                return grad;
              },
              borderColor: "#3b82f6",
              borderWidth: 2,
              borderRadius: 8,
              borderSkipped: false,
              hoverBackgroundColor: "#ffffff",
              hoverBorderColor: "#ffffff",
              barThickness: 32,
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              ...roundChartTooltip,
              callbacks: {
                label: (ctx) => ` Intensidad: ${ctx.parsed.y} eventos`
              }
            },
          },
          scales: {
            x: {
              grid: { display: false },
              ticks: { color: "#94a3b8", font: { size: 10, family: 'Geist Mono', weight: '500' }, maxRotation: 45, minRotation: 45 }
            },
            y: {
              beginAtZero: true,
              grid: { color: "rgba(255,255,255,0.03)", drawBorder: false },
              ticks: { color: "#64748b", font: { size: 10, family: 'Geist Mono' }, stepSize: 5 }
            }
          },
          animation: {
            duration: 2000,
            easing: 'easeOutQuart'
          }
        }
      });
    } catch (e) { toast(e.message, "error"); }
  }

  async function loadEvents(page) {
    const params = new URLSearchParams({ page, per_page: 30 });
    try {
      const res = await api(`/events?${params}`);
      const rows = res.data || [];
      if (!rows.length) {
        html($("evtTable"), `<div class="empty-state"><div class="empty-state-icon"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg></div><div class="empty-state-text">Sin eventos</div></div>`);
        html($("evtPag"), "");
        return;
      }
      let t = `<table><thead><tr><th>ID</th><th>Fecha</th><th>Tipo</th><th>Origen</th><th>Destino</th><th>Proto</th><th>Firma</th><th>Sev</th></tr></thead><tbody>`;
      for (const r of rows) {
        t += `<tr>
        <td>${r.id}</td><td>${fmtDate(r.ts)}</td><td>${esc(r.event_type)}</td>
        <td>${esc(r.src_ip)}</td><td>${esc(r.dest_ip)}</td><td>${esc(r.proto)}</td>
        <td>${esc((r.signature || "").slice(0, 60))}</td><td>${sevBadge(r.severity)}</td>
      </tr>`;
      }
      t += `</tbody></table>`;
      html($("evtTable"), t);
      html($("evtPag"), paginationHtml(res.page, res.total, res.per_page));
      bindPagination($("evtPag"), loadEvents);
    } catch (e) { toast(e.message, "error"); }
  }

  // ——— USERS (admin) ———
  async function pageUsers() {
    const pc = $("pageContent");
    html(pc, `
    <div style="margin-bottom:16px;"><button class="btn btn-primary btn-sm" id="btnNewUser">+ Usuario</button></div>
    <div class="card"><div class="table-wrap" id="usersTable">${skeleton(4)}</div></div>
  `);

    loadUsers();
    $("btnNewUser")?.addEventListener("click", showNewUserModal);
  }

  async function loadUsers() {
    try {
      const rows = await api("/users");
      if (!rows.length) {
        html($("usersTable"), `<div class="empty-state"><div class="empty-state-text">Sin usuarios</div></div>`);
        return;
      }
      let t = `<table><thead><tr><th>ID</th><th>Usuario</th><th>Rol</th><th>Activo</th><th>Creado</th><th>Acciones</th></tr></thead><tbody>`;
      for (const r of rows) {
        t += `<tr>
        <td>${r.id}</td><td>${esc(r.username)}</td>
        <td><span class="badge badge-info">${esc(r.role)}</span></td>
        <td>${r.active ? '<span class="badge badge-cerrada">Sí</span>' : '<span class="badge badge-nueva">No</span>'}</td>
        <td>${fmtDate(r.created_at)}</td>
        <td class="btn-group">
          <button class="btn btn-secondary btn-sm" data-edit-user="${r.id}" data-username="${esc(r.username)}" data-role="${esc(r.role)}" data-active="${r.active}">Editar</button>
        </td>
      </tr>`;
      }
      t += `</tbody></table>`;
      html($("usersTable"), t);

      $("usersTable").querySelectorAll("[data-edit-user]").forEach(btn => {
        btn.addEventListener("click", () => showEditUserModal(btn.dataset.editUser, btn.dataset.username, btn.dataset.role, btn.dataset.active === "1"));
      });
    } catch (e) { toast(e.message, "error"); }
  }

  function showNewUserModal() {
    const overlay = document.createElement("div");
    overlay.className = "modal-overlay";
    overlay.innerHTML = `
    <div class="modal">
      <div class="modal-title">Nuevo usuario</div>
      <div class="form-group"><label>Usuario</label><input id="mNewUsr" type="text" style="width:100%;" /></div>
      <div class="form-group"><label>Contraseña</label><input id="mNewPwd" type="password" style="width:100%;" /></div>
      <div class="form-group"><label>Rol</label><select id="mNewRole" style="width:100%;"><option value="viewer">Viewer</option><option value="analista">Analista</option><option value="admin">Admin</option></select></div>
      <div class="btn-group" style="margin-top:12px;"><button class="btn btn-primary" id="mNewSave">Crear</button><button class="btn btn-secondary" id="mNewCancel">Cancelar</button></div>
    </div>
  `;
    document.body.appendChild(overlay);
    $("mNewCancel").addEventListener("click", () => overlay.remove());
    overlay.addEventListener("click", e => { if (e.target === overlay) overlay.remove(); });

    $("mNewSave").addEventListener("click", async () => {
      try {
        await api("/users", {
          method: "POST",
          body: JSON.stringify({ username: $("mNewUsr").value, password: $("mNewPwd").value, role: $("mNewRole").value }),
        });
        overlay.remove();
        toast("Usuario creado", "success");
        loadUsers();
      } catch (e) { toast(e.message, "error"); }
    });
  }

  function showEditUserModal(userId, username, role, active) {
    const overlay = document.createElement("div");
    overlay.className = "modal-overlay";
    overlay.innerHTML = `
    <div class="modal">
      <div class="modal-title">Editar: ${esc(username)}</div>
      <div class="form-group"><label>Rol</label><select id="mEdRole" style="width:100%;">
        <option value="viewer" ${role === 'viewer' ? 'selected' : ''}>Viewer</option>
        <option value="analista" ${role === 'analista' ? 'selected' : ''}>Analista</option>
        <option value="admin" ${role === 'admin' ? 'selected' : ''}>Admin</option>
      </select></div>
      <div class="form-group"><label>Activo</label><select id="mEdActive" style="width:100%;">
        <option value="1" ${active ? 'selected' : ''}>Sí</option>
        <option value="0" ${!active ? 'selected' : ''}>No</option>
      </select></div>
      <div class="form-group"><label>Nueva contraseña (dejar vacío para no cambiar)</label><input id="mEdPwd" type="password" style="width:100%;" /></div>
      <div class="btn-group" style="margin-top:12px;"><button class="btn btn-primary" id="mEdSave">Guardar</button><button class="btn btn-secondary" id="mEdCancel">Cancelar</button></div>
    </div>
  `;
    document.body.appendChild(overlay);
    $("mEdCancel").addEventListener("click", () => overlay.remove());
    overlay.addEventListener("click", e => { if (e.target === overlay) overlay.remove(); });

    $("mEdSave").addEventListener("click", async () => {
      const body = { role: $("mEdRole").value, active: $("mEdActive").value === "1" };
      const pwd = $("mEdPwd").value;
      if (pwd) body.password = pwd;
      try {
        await api(`/users/${userId}`, { method: "PATCH", body: JSON.stringify(body) });
        overlay.remove();
        toast("Usuario actualizado", "success");
        loadUsers();
      } catch (e) { toast(e.message, "error"); }
    });
  }

  // ——— HEALTH ———
  async function pageHealth() {
    const pc = $("pageContent");
    html(pc, skeleton(4));
    try {
      const h = await api("/health");
      html(pc, `
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">API</div>
          <div style="display:flex;align-items:center;gap:8px;">
            <span class="status-dot ${h.api === 'ok' ? 'ok' : 'error'}"></span>
            <span class="stat-value" style="font-size:18px;">${h.api === 'ok' ? 'Activa' : esc(h.api)}</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Base de datos</div>
          <div style="display:flex;align-items:center;gap:8px;">
            <span class="status-dot ${h.db === 'ok' ? 'ok' : 'error'}"></span>
            <span class="stat-value" style="font-size:18px;">${h.db === 'ok' ? 'Activa' : esc(h.db)}</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Ingesta Suricata</div>
          <div style="display:flex;align-items:center;gap:8px;">
            <span class="status-dot ${h.ingest === 'activa' ? 'ok' : h.ingest === 'inactiva' ? 'warn' : 'unknown'}"></span>
            <span class="stat-value" style="font-size:18px;">${esc(h.ingest)}</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Último evento</div>
          <div class="stat-value" style="font-size:14px;">${h.last_event ? fmtDate(h.last_event) : "Sin datos"}</div>
          ${h.ingest_lag_seconds != null ? `<div style="font-size:12px;color:var(--txt-3);margin-top:4px;">Lag: ${h.ingest_lag_seconds}s</div>` : ""}
        </div>
      </div>
    `);
    } catch (e) { html(pc, `<p style="color:var(--red);">Error: ${esc(e.message)}</p>`); }
  }

  // ——— CORRELATION (sub-page in incidents) ———
  async function pageCorrelation() {
    const pc = $("pageContent");
    html(pc, `
    <div class="card">
      <div class="card-header"><span class="card-title">Sugerencias de correlación</span></div>
      <div class="filters-bar" style="margin-bottom:12px;">
        <div class="form-group"><label>Minutos</label><input id="cMin" type="number" value="30" style="width:80px;" /></div>
        <div class="form-group"><label>Umbral</label><input id="cThresh" type="number" value="5" style="width:80px;" /></div>
        <div class="form-group" style="align-self:flex-end;"><button class="btn btn-primary btn-sm" id="btnRunCorr">Analizar</button></div>
      </div>
      <div id="corrResults">${skeleton(3)}</div>
    </div>
  `);

    loadCorrelation();
    $("btnRunCorr")?.addEventListener("click", loadCorrelation);
  }

  async function loadCorrelation() {
    const minutes = $("cMin")?.value || 30;
    const threshold = $("cThresh")?.value || 5;
    try {
      const rows = await api(`/correlation/suggestions?minutes=${minutes}&threshold=${threshold}`);
      if (!rows.length) {
        html($("corrResults"), `<div class="empty-state"><div class="empty-state-text">Sin correlaciones detectadas con estos parámetros</div></div>`);
        return;
      }
      let t = `<table><thead><tr><th>Firma</th><th>IP origen</th><th>Ocurrencias</th><th>Primera</th><th>Última</th><th>Acción</th></tr></thead><tbody>`;
      for (const r of rows) {
        t += `<tr>
        <td>${esc((r.signature || "").slice(0, 60))}</td><td>${esc(r.src_ip)}</td><td><strong>${r.cnt}</strong></td>
        <td>${fmtDate(r.first_seen)}</td><td>${fmtDate(r.last_seen)}</td>
        <td><button class="btn btn-primary btn-sm" data-corr='${JSON.stringify(r.event_ids)}' data-sig="${esc(r.signature)}">Crear incidente</button></td>
      </tr>`;
      }
      t += `</tbody></table>`;
      html($("corrResults"), t);

      $("corrResults").querySelectorAll("[data-corr]").forEach(btn => {
        btn.addEventListener("click", async () => {
          try {
            const ids = JSON.parse(btn.dataset.corr);
            const sig = btn.dataset.sig;
            const res = await api("/incidents", {
              method: "POST",
              body: JSON.stringify({ title: `Correlación: ${sig}`, description: `Agrupación automática de ${ids.length} alertas similares`, severity: 2 }),
            });
            await api(`/incidents/${res.id}/alerts`, { method: "POST", body: JSON.stringify({ event_ids: ids }) });
            toast("Incidente creado con alertas vinculadas", "success");
            location.hash = `#incident/${res.id}`;
          } catch (e) { toast(e.message, "error"); }
        });
      });
    } catch (e) { toast(e.message, "error"); }
  }

  /* ---------- ALERT BUBBLE NOTIFICATIONS ---------- */
  let lastKnownAlertId = 0;
  let alertPollTimer = null;
  const MAX_BUBBLES = 5;

  function getSevClass(sev) {
    const s = parseInt(sev);
    if (s === 1) return "high";
    if (s === 2) return "medium";
    if (s === 3) return "low";
    return "info";
  }

  function getSevLabel(sev) {
    const s = parseInt(sev);
    if (s === 1) return "Alta";
    if (s === 2) return "Media";
    if (s === 3) return "Baja";
    return "Info";
  }

  function getSevIcon(sev) {
    const s = parseInt(sev);
    if (s === 1) return '<svg width="14" height="14" viewBox="0 0 14 14"><circle cx="7" cy="7" r="6" fill="#f43f5e"/></svg>';
    if (s === 2) return '<svg width="14" height="14" viewBox="0 0 14 14"><circle cx="7" cy="7" r="6" fill="#f59e0b"/></svg>';
    if (s === 3) return '<svg width="14" height="14" viewBox="0 0 14 14"><circle cx="7" cy="7" r="6" fill="#eab308"/></svg>';
    return '<svg width="14" height="14" viewBox="0 0 14 14"><circle cx="7" cy="7" r="6" fill="#3b82f6"/></svg>';
  }

  function showAlertBubble(alert) {
    const container = $("alertBubbleContainer");
    if (!container) return;

    // Limit visible bubbles
    while (container.children.length >= MAX_BUBBLES) {
      const oldest = container.firstElementChild;
      if (oldest) oldest.remove();
    }

    const sevClass = getSevClass(alert.severity);
    const bubble = document.createElement("div");
    bubble.className = "alert-bubble";
    bubble.style.position = "relative";
    bubble.innerHTML = `
      <div class="alert-bubble-indicator sev-${sevClass}"></div>
      <span class="alert-bubble-icon">${getSevIcon(alert.severity)}</span>
      <div class="alert-bubble-content">
        <div class="alert-bubble-title">
          Nueva alerta
          <span class="bubble-badge ${sevClass}">${getSevLabel(alert.severity)}</span>
        </div>
        <div class="alert-bubble-sig">${esc((alert.signature || "Evento detectado").slice(0, 60))}</div>
        <div class="alert-bubble-meta">
          <span>${esc(alert.src_ip || "—")} → ${esc(alert.dest_ip || "—")}</span>
          <span>${fmtDate(alert.ts)}</span>
        </div>
      </div>
      <button class="alert-bubble-close" title="Cerrar">✕</button>
    `;

    // Click on bubble -> go to alert detail
    bubble.addEventListener("click", (e) => {
      if (e.target.closest(".alert-bubble-close")) return;
      dismissBubble(bubble, () => {
        location.hash = `#alert/${alert.id}`;
      });
    });

    // Close button 
    bubble.querySelector(".alert-bubble-close").addEventListener("click", (e) => {
      e.stopPropagation();
      dismissBubble(bubble);
    });

    container.appendChild(bubble);

    // Auto-dismiss after 12 seconds
    setTimeout(() => {
      if (bubble.parentNode) {
        dismissBubble(bubble);
      }
    }, 12000);
  }

  function dismissBubble(bubble, callback) {
    bubble.classList.add("removing");
    setTimeout(() => {
      bubble.remove();
      if (callback) callback();
    }, 350);
  }

  async function pollNewAlerts() {
    if (!getToken()) return;
    try {
      const res = await api("/alerts?per_page=5&page=1");
      const rows = res.data || [];
      if (!rows.length) return;

      // On first poll, just record the latest ID
      if (lastKnownAlertId === 0) {
        lastKnownAlertId = rows[0].id;
        return;
      }

      // Show bubbles for new alerts (newest first, but show oldest new first)
      const newAlerts = rows.filter(r => r.id > lastKnownAlertId);
      if (newAlerts.length > 0) {
        lastKnownAlertId = newAlerts[0].id;
        // Show in chronological order (oldest new to newest new)
        for (const alert of newAlerts.reverse()) {
          showAlertBubble(alert);
        }
      }
    } catch (e) {
      // Silently fail polling - don't spam toasts
    }
  }

  function startAlertPolling() {
    if (alertPollTimer) clearInterval(alertPollTimer);
    // Initial poll after 2 seconds
    setTimeout(pollNewAlerts, 2000);
    // Then poll every 15 seconds
    alertPollTimer = setInterval(pollNewAlerts, 15000);
  }

  function stopAlertPolling() {
    if (alertPollTimer) {
      clearInterval(alertPollTimer);
      alertPollTimer = null;
    }
  }

  // ——— THREAT INTEL ———
  async function pageThreatIntel() {
    const pc = $("pageContent");
    html(pc, `
    <div class="section-header"><h2>Análisis de inteligencia y riesgos</h2></div>
    <div class="dash-grid" style="height: calc(100vh - 180px);">
      <div class="card" style="flex: 1.2; display: flex; flex-direction: column;">
        <div class="card-header"><span class="card-title">Perfil de riesgo de incidentes</span></div>
        <div class="chart-container" style="flex: 1; min-height: 0;"><canvas id="chartRiskMatrix"></canvas></div>
      </div>
      <div class="card" style="flex: 1; display: flex; flex-direction: column;">
        <div class="card-header"><span class="card-title">Análisis de progresión de amenazas por IP</span></div>
        <div class="chart-container" style="flex: 1; min-height: 0; padding: 10px;"><canvas id="chartEscalation"></canvas></div>
      </div>
    </div>
    `);

    try {
      const res = await api("/stats/threat_intel");
      
      // Render Radar Chart (More appropriate for Threat Intel)
      const ctx = $("chartRiskMatrix");
      if (ctx) {
        // Tomamos los incidentes y los preparamos para el radar
        const incidents = res.risk_matrix || [];
        
        const datasets = incidents.slice(0, 5).map((inc, i) => {
          const colors = [chartColors.red, chartColors.orange, chartColors.blue, chartColors.yellow, chartColors.green];
          const color = colors[i % colors.length];
          return {
            label: inc.title.length > 25 ? inc.title.slice(0, 25) + '...' : inc.title,
            data: [
              inc.impact, 
              inc.urgency, 
              Math.min(5, Math.max(1, Math.log2(inc.event_count + 1) * 1.5)) // Frecuencia normalizada 1-5
            ],
            backgroundColor: color.bg,
            borderColor: color.border,
            borderWidth: 2,
            pointBackgroundColor: color.border,
            fill: true,
            incidentId: inc.id
          };
        });

        if (incidents.length === 0) {
           ctx.parentElement.innerHTML = '<div class="empty-state" style="display:flex; flex-direction:column; align-items:center; justify-content:center; height:100%;"><div class="empty-state-text">No hay incidentes activos para analizar</div></div>';
        } else {
          new Chart(ctx, {
            type: 'radar',
            data: {
              labels: ['Impacto', 'Urgencia', 'Frecuencia'],
              datasets: datasets
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              scales: {
                r: {
                  min: 0, max: 5,
                  beginAtZero: true,
                  grid: { color: 'rgba(255,255,255,0.05)' },
                  angleLines: { color: 'rgba(255,255,255,0.1)' },
                  ticks: { display: false, stepSize: 1 },
                  pointLabels: {
                    color: '#94a3b8',
                    font: { family: 'Geist Mono', size: 10, weight: '600' }
                  }
                }
              },
              plugins: {
                legend: {
                  display: true,
                  position: 'bottom',
                  labels: { color: '#94a3b8', font: { family: 'Geist Mono', size: 10 }, boxWidth: 10, padding: 15 }
                },
                tooltip: {
                  backgroundColor: "rgba(3, 7, 18, 0.95)",
                  callbacks: {
                    label: function(c) {
                      const labels = ['Impacto', 'Urgencia', 'Frecuencia'];
                      return ` ${c.dataset.label} - ${labels[c.dataIndex]}: ${c.raw.toFixed(1)}`;
                    }
                  }
                }
              },
              onClick: (e, elements) => {
                if (elements.length > 0) {
                  const dsIndex = elements[0].datasetIndex;
                  const incId = datasets[dsIndex].incidentId;
                  location.hash = `#incident/${incId}`;
                }
              }
            }
          });
        }
      }

      // Render Escalation Chart (Horizontal Bar)
      const escCtx = $("chartEscalation");
      if (escCtx) {
        const ips = res.escalation_ips || [];
        if (!ips.length) {
          escCtx.parentElement.innerHTML = '<div class="empty-state" style="display:flex; flex-direction:column; align-items:center; justify-content:center; height:100%;"><div class="empty-state-text">Sin atacantes reincidentes detectados</div></div>';
        } else {
          new Chart(escCtx, {
            type: 'bar',
            data: {
              labels: ips.map(ip => ip.src_ip),
              datasets: [{
                label: 'Probabilidad de escalada (%)',
                data: ips.map(ip => ip.probability_score),
                backgroundColor: ips.map(ip => {
                  const p = ip.probability_score;
                  return p > 75 ? chartColors.red.bg : p > 50 ? chartColors.orange.bg : chartColors.blue.bg;
                }),
                borderColor: ips.map(ip => {
                  const p = ip.probability_score;
                  return p > 75 ? chartColors.red.border : p > 50 ? chartColors.orange.border : chartColors.blue.border;
                }),
                borderWidth: 1,
                borderRadius: 4
              }]
            },
            options: {
              indexAxis: 'y',
              responsive: true,
              maintainAspectRatio: false,
              scales: {
                x: {
                  min: 0, max: 100,
                  grid: { color: 'rgba(255,255,255,0.03)' },
                  ticks: { color: '#64748b', font: { family: 'Geist Mono', size: 10 } }
                },
                y: {
                  grid: { display: false },
                  ticks: { color: '#94a3b8', font: { family: 'Geist Mono', size: 10 } }
                }
              },
              plugins: {
                legend: { display: false },
                tooltip: {
                  backgroundColor: "rgba(3, 7, 18, 0.95)",
                  callbacks: {
                    afterLabel: function(c) {
                      return ` Fase: ${ips[c.dataIndex].phase}\n Alertas: ${ips[c.dataIndex].alert_count}`;
                    }
                  }
                }
              }
            }
          });
        }
      }

    } catch (e) {
      toast(e.message, "error");
    }
  }

  /* ---------- ROUTER ---------- */
  const titles = {
    dashboard: "Panel",
    alerts: "Alertas",
    alert: "Detalle de alerta",
    incidents: "Incidentes",
    incident: "Detalle de incidente",
    events: "Eventos",
    users: "Usuarios",
    health: "Estado del sistema",
    correlation: "Correlación",
    "threat-intel": "Inteligencia de amenazas",
  };

  function route() {
    const hash = location.hash.replace("#", "") || "dashboard";
    const [page, param] = hash.split("/");

    // Actualizar active link
    document.querySelectorAll(".sidebar-nav a").forEach(a => {
      const ap = a.dataset.page;
      a.classList.toggle("active", ap === page || (page === "alert" && ap === "alerts") || (page === "incident" && ap === "incidents") || (page === "correlation" && ap === "incidents"));
    });

    const topTitle = $("topbarTitle");
    if (topTitle) topTitle.textContent = titles[page] || "Marshaall";

    switch (page) {
      case "dashboard": pageDashboard(); break;
      case "alerts": pageAlerts(); break;
      case "alert": pageAlertDetail(param); break;
      case "incidents": pageIncidents(); break;
      case "incident": pageIncidentDetail(param); break;
      case "events": pageEvents(); break;
      case "users": pageUsers(); break;
      case "health": 
        if (getRole() === "admin") pageHealth(); 
        else location.hash = "#dashboard";
        break;
      case "correlation": pageCorrelation(); break;
      case "threat-intel": pageThreatIntel(); break;
      default: pageDashboard();
    }
  }


  /* ---------- INIT ---------- */
  function init() {
    // --- Always register hashchange listener first ---
    window.addEventListener("hashchange", route);

    // --- Always register sidebar, logout, refresh, dropdown listeners ---
    const toggle = $("menuToggle");
    const sidebar = $("sidebar");
    const overlay = $("sidebarOverlay");
    if (toggle && sidebar) {
      toggle.addEventListener("click", () => {
        sidebar.classList.toggle("open");
        overlay?.classList.toggle("visible");
      });
      overlay?.addEventListener("click", () => {
        sidebar.classList.remove("open");
        overlay.classList.remove("visible");
      });
    }
    document.querySelectorAll(".sidebar-nav a").forEach(a => {
      a.addEventListener("click", () => {
        if (window.innerWidth <= 768) {
          sidebar?.classList.remove("open");
          overlay?.classList.remove("visible");
        }
      });
    });

    $("btnLogout")?.addEventListener("click", () => { stopAlertPolling(); lastKnownAlertId = 0; clearSession(); showLogin(); });
    $("btnRefresh")?.addEventListener("click", route);

    // Report dropdown
    const reportDropdown = $("reportDropdown");
    if (reportDropdown) {
      $("btnReportToggle")?.addEventListener("click", (e) => {
        e.stopPropagation();
        reportDropdown.classList.toggle("open");
      });
      document.addEventListener("click", (e) => {
        if (!reportDropdown.contains(e.target)) {
          reportDropdown.classList.remove("open");
        }
      });
      // Reemplaza los listeners de btnDownloadPdfTopbar y btnDownloadCsvTopbar por estos:

$("btnDownloadPdfTopbar")?.addEventListener("click", () => {
  reportDropdown.classList.remove("open");
  const token = getToken();
  if (!token) { toast("Sesión no válida", "error"); return; }
  
  toast("Generando informe PDF...", "success");
  const url = `${API}/reports/events.pdf?range=24h&token=${encodeURIComponent(token)}&t=${Date.now()}`;
  const a = document.createElement("a");
  a.href = url;
  a.style.display = 'none';
  document.body.appendChild(a);
  a.click();
  setTimeout(() => document.body.removeChild(a), 1000);
});

$("btnDownloadCsvTopbar")?.addEventListener("click", () => {
  reportDropdown.classList.remove("open");
  const token = getToken();
  if (!token) { toast("Sesión no válida", "error"); return; }

  toast("Descargando CSV...", "success");
  const url = `${API}/reports/events.csv?range=24h&token=${encodeURIComponent(token)}&t=${Date.now()}`;
  const a = document.createElement("a");
  a.href = url;
  a.style.display = 'none';
  document.body.appendChild(a);
  a.click();
  setTimeout(() => document.body.removeChild(a), 1000);
});
    }

    // --- Login handler ---
    const btnLogin = $("btnLogin");
    if (btnLogin) {
      const doLogin = async () => {
        const usr = ($("loginUser")?.value || "").trim();
        const pwd = $("loginPass")?.value || "";
        const msg = $("loginMsg");
        if (msg) msg.textContent = "";
        try {
          const data = await api("/login", { method: "POST", body: JSON.stringify({ username: usr, password: pwd }) });
          saveSession(data.token, data.username, data.role);
          if (location.pathname.includes("login.html")) {
            location.href = "/";
          } else {
            showApp();
            if (!location.hash || location.hash === "#") {
              location.hash = "#dashboard";
            }
            route();
          }
        } catch (e) {
          if (msg) msg.textContent = e.message;
        }
      };
      btnLogin.addEventListener("click", doLogin);
      $("loginPass")?.addEventListener("keydown", e => { if (e.key === "Enter") doLogin(); });
      $("loginUser")?.addEventListener("keydown", e => { if (e.key === "Enter") $("loginPass")?.focus(); });
    }

    // If on login.html standalone, don't proceed
    if (location.pathname.includes("login.html")) {
      if (getToken()) location.href = "/";
      return;
    }

    // --- Check auth ---
    if (!getToken()) {
      showLogin();
      return;
    }

    // --- Authenticated: show app and route ---
    showApp();
    if (reportDropdown) {
      const role = getRole();
      if (role !== "admin" && role !== "analista") {
        reportDropdown.style.display = "none";
      }
    }
    route();
  }

  document.addEventListener("DOMContentLoaded", init);

})();
