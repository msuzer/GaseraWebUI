// static/js/status.js
(() => {
  // Prefer a global status path. Fallback to the history block if present.
  const STATUS_URL =
    (window.API_PATHS && (API_PATHS.status || (API_PATHS.history && API_PATHS.history.status)))
    || "/api/status";

  const dot  = document.getElementById("gasera-status-dot");
  const pill = document.getElementById("gasera-status-pill");
  const sub  = document.getElementById("gasera-status-sub");
  if (!dot || !pill) return; // not on this page

  // Consider offline if we haven't observed ASTS/AMST recently.
  // Tune this if you change the ingester's polling intervals.
  const OFFLINE_MS = 90_000; // 90s

  const setUI = ({color, pillText, subText, bgClass}) => {
    dot.style.background = color;
    pill.className = `badge rounded-pill ${bgClass}`;
    pill.textContent = pillText;
    sub.textContent = subText || "";
  };

  const COLORS = {
    offline:  "#dc3545", // red
    error:    "#dc3545", // red
    idle:     "#ffc107", // yellow
    measuring:"#28a745", // green
    other:    "#0d6efd", // blue
    unknown:  "#6c757d"  // gray
  };

  const BGS = {
    offline:   "bg-danger",
    error:     "bg-danger",
    idle:      "bg-warning text-dark",
    measuring: "bg-success",
    other:     "bg-primary",
    unknown:   "bg-secondary"
  };

  const label = (s, def="Unknown") => (s && String(s)) || def;
  const secs = (n) => `${Math.max(0, Math.round(n))}s`;

  async function refresh() {
    try {
      const r = await fetch(STATUS_URL, { cache: "no-store" });
      const j = await r.json();

      const dev = j.device || {};
      const last = j.last_cycle || {};

      // Online/offline by staleness of observed_at
      const now = Date.now();
      const observedAt = dev.observed_at ? Date.parse(dev.observed_at) : NaN;
      const isOnline = Number.isFinite(observedAt) && (now - observedAt) < OFFLINE_MS;

      // Derive state
      const ds = dev.device_status;           // int or null
      const dsLabel = dev.device_status_label || (isOnline ? "Unknown" : "Offline");
      const phaseLabel = dev.phase_label || "";

      const ingTs = last.ingested_ts ? Date.parse(last.ingested_ts) : NaN;
      const ageText = Number.isFinite(ingTs) ? secs((now - ingTs) / 1000) + " ago" : "n/a";

      // Choose bucket
      let bucket = "unknown";
      if (!isOnline) bucket = "offline";
      else if (ds === 5) bucket = "measuring";
      else if (ds === 2) bucket = "idle";
      else if (ds === 1 || ds === 4 || dev.errorstatus === 1) bucket = "error";
      else bucket = "other";

      const pillText = (!isOnline) ? "Offline"
                        : (bucket === "measuring" ? "Measuring"
                        : (bucket === "idle" ? "Idle"
                        : (bucket === "error" ? "Error"
                        : dsLabel)));

      let subText = "";
      if (isOnline) {
        subText = phaseLabel ? `· ${phaseLabel} · Last cycle ${ageText}` : `· Last cycle ${ageText}`;
      } else {
        if (Number.isFinite(observedAt)) {
          const stale = secs((now - observedAt) / 1000);
          subText = `· No contact for ${stale}`;
        }
      }

      setUI({ color: COLORS[bucket], pillText, subText, bgClass: BGS[bucket] });
    } catch (e) {
      // Network/API failure → gray "Unknown"
      setUI({ color: COLORS.unknown, pillText: "Unknown", subText: "· Status API unreachable", bgClass: BGS.unknown });
    }
  }

  // Initial + interval
  refresh();
  setInterval(refresh, 10_000);
})();
