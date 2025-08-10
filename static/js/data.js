// static/js/data.js
(() => {
  const A = API_PATHS["history"]; // {gases, measurements, exportCsv, status}
  const chartEl = document.getElementById("data-chart");
  if (!chartEl) return; // tab not present

  // --- state ---
  let chart;
  let liveTimer = null;
  let knownGases = []; // [{cas, name, unit}]
  let selectedGases = new Set(); // cas strings

  // --- utils ---
  const fmtIso = (d) => d.toISOString().replace(/\.\d{3}Z$/, "Z");
  const toLocalInput = (d) => {
    const pad = (n) => String(n).padStart(2, "0");
    const yyyy = d.getFullYear(), mm = pad(d.getMonth() + 1), dd = pad(d.getDate());
    const hh = pad(d.getHours()), mi = pad(d.getMinutes());
    return `${yyyy}-${mm}-${dd}T${hh}:${mi}`;
  };
  const fromLocalInput = (v) => {
    // treat as local time; convert to UTC ISO string
    if (!v) return null;
    const d = new Date(v);
    return new Date(d.getTime() - d.getTimezoneOffset() * 60000); // pseudo-UTC
  };

  const buildExportHref = (startIso, endIso, gasesList) => {
    const params = new URLSearchParams();
    if (startIso) params.set("start", startIso);
    if (endIso)   params.set("end", endIso);
    if (gasesList && gasesList.length) params.set("gases", gasesList.join(","));
    return `${A.exportCsv}?${params.toString()}`;
  };

  const pickColor = (i) => {
    // simple palette; Chart.js will also auto-color if omitted
    const palette = [
      "#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd",
      "#8c564b","#e377c2","#7f7f7f","#bcbd22","#17becf"
    ];
    return palette[i % palette.length];
  };

  const setStatus = (msg) => {
    const el = document.getElementById("data-status-line");
    if (el) el.textContent = msg || "";
  };

  // --- init date range (last 2 hours) ---
  const endInput = document.getElementById("data-end");
  const startInput = document.getElementById("data-start");
  const now = new Date();
  const twoHoursAgo = new Date(now.getTime() - 2 * 3600 * 1000);
  startInput.value = toLocalInput(twoHoursAgo);
  endInput.value = toLocalInput(now);

  // --- fetch gases, render toggles ---
  const loadGases = async () => {
    const r = await fetch(A.gases);
    const items = await r.json(); // [{id,cas,name,unit}]
    knownGases = items.map(g => ({ cas: g.cas, name: g.name || g.cas, unit: g.unit || "ppm" }));

    const box = document.getElementById("data-gas-toggles");
    box.innerHTML = "";
    knownGases.forEach((g, i) => {
      // default ON for first 4 gases
      if (i < 4) selectedGases.add(g.cas);
      const id = `gas-${g.cas.replace(/[^a-zA-Z0-9]/g, "")}`;
      const wrap = document.createElement("div");
      wrap.className = "form-check form-check-inline";
      wrap.innerHTML = `
        <input class="form-check-input" type="checkbox" id="${id}" ${selectedGases.has(g.cas) ? "checked" : ""} data-cas="${g.cas}">
        <label class="form-check-label" for="${id}">${g.name} <span class="text-muted small">(${g.cas})</span></label>
      `;
      box.appendChild(wrap);
      wrap.querySelector("input").addEventListener("change", (e) => {
        const cas = e.target.getAttribute("data-cas");
        if (e.target.checked) selectedGases.add(cas); else selectedGases.delete(cas);
      });
    });
  };

  // --- build chart or update datasets ---
  const ensureChart = () => {
    if (chart) return chart;
    chart = new Chart(chartEl, {
      type: "line",
      data: { datasets: [] },
      options: {
        responsive: true,
        animation: false,
        parsing: false,
        normalized: true,
        scales: {
          x: { type: "time", time: { unit: "minute" }, ticks: { autoSkip: true } },
          y: { title: { display: true, text: "ppm" } }
        },
        plugins: {
          legend: { position: "top" },
          zoom: {
            zoom: { wheel: { enabled: true }, pinch: { enabled: true }, mode: "x" },
            pan: { enabled: true, mode: "x" }
          },
          tooltip: {
            callbacks: {
              title: (items) => {
                const d = new Date(items[0].parsed.x);
                return d.toLocaleString();
              }
            }
          }
        }
      }
    });
    return chart;
  };

  // transform API cycle payload → per-gas datasets
  const toDatasets = (cycles, gases) => {
    const idx = new Map(gases.map((g, i) => [g.cas, i]));
    const series = gases.map((g, i) => ({
      label: `${g.name || g.cas}`,
      data: [],
      borderColor: pickColor(i),
      pointRadius: 0,
      borderWidth: 1.5,
      hidden: !selectedGases.has(g.cas),
    }));
    for (const c of cycles) {
      const x = new Date(c.ts).getTime();
      for (const v of c.values) {
        const i = idx.get(v.cas);
        if (i !== undefined) series[i].data.push({ x, y: v.ppm });
      }
    }
    // remove empty series entirely to keep legend tidy
    return series.filter(s => s.data.length > 0);
  };

  // --- fetch measurements and render ---
  const loadHistory = async () => {
    const start = fromLocalInput(startInput.value);
    const end   = fromLocalInput(endInput.value);
    const qs = new URLSearchParams();
    qs.set("mode", "cycle");
    qs.set("order", "asc");
    if (start) qs.set("start", fmtIso(start));
    if (end)   qs.set("end", fmtIso(end));
    if (selectedGases.size) qs.set("gases", Array.from(selectedGases).join(","));

    setStatus("Loading…");
    const r = await fetch(`${A.measurements}?${qs.toString()}`);
    const cycles = await r.json(); // [{ts, epoch, ingested_ts, values:[{cas,name,ppm}]}]
    setStatus(`Loaded ${cycles.length} cycles.`);

    const c = ensureChart();
    c.data.datasets = toDatasets(cycles, knownGases);
    c.update("none");

    // update export link
    const exportHref = buildExportHref(start ? fmtIso(start) : null, end ? fmtIso(end) : null, Array.from(selectedGases));
    document.getElementById("data-export-btn").href = exportHref;
  };

  const startLive = () => {
    if (liveTimer) return;
    liveTimer = setInterval(async () => {
      // slide the end window to "now"; keep duration same as chosen
      const endNow = new Date();
      const startVal = fromLocalInput(startInput.value);
      const endVal = fromLocalInput(endInput.value);
      const span = (endVal && startVal) ? (endVal.getTime() - startVal.getTime()) : 2 * 3600 * 1000;
      startInput.value = toLocalInput(new Date(endNow.getTime() - span));
      endInput.value = toLocalInput(endNow);
      await loadHistory();
      // also show device status breadcrumb
      try {
        const s = await (await fetch(A.status)).json();
        const dev = s.device || {};
        const last = s.last_cycle || {};
        const statusLabel = dev.device_status_label || "Unknown";
        const phaseLabel = dev.phase_label || "";
        const age = (last.age_seconds != null) ? `${last.age_seconds}s ago` : "n/a";
        setStatus(`Device: ${statusLabel}${phaseLabel ? " · " + phaseLabel : ""} · Last cycle: ${age}`);
      } catch { /* ignore */ }
    }, 10000); // 10s
  };
  const stopLive = () => { if (liveTimer) { clearInterval(liveTimer); liveTimer = null; } };

  // --- bind controls ---
  document.getElementById("data-load-btn").addEventListener("click", async () => {
    stopLive();
    await loadHistory();
  });
  document.getElementById("data-live-toggle").addEventListener("change", (e) => {
    if (e.target.checked) { startLive(); } else { stopLive(); }
  });
  document.getElementById("data-snapshot-btn").addEventListener("click", () => {
    const link = document.createElement("a");
    link.download = `gasera_chart_${Date.now()}.png`;
    link.href = chart.toBase64Image("image/png", 1.0);
    link.click();
  });

  // --- boot ---
  (async () => {
    await loadGases();
    await loadHistory(); // initial load (last 2h)
  })();
})();
