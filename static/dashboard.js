/* dashboard.js — AI Log Analyzer v2 */

const dropZone   = document.getElementById('drop-zone');
const fileInput  = document.getElementById('logfile');
const analyzeBtn = document.getElementById('analyze-btn');
const rerunBtn   = document.getElementById('rerun-btn');
const downloadBtn= document.getElementById('download-btn');
const downloadCsvBtn = document.getElementById('download-csv-btn');
const fileNameEl = document.getElementById('file-name');
const form       = document.getElementById('upload-form');
const spinner    = document.getElementById('spinner');
const results    = document.getElementById('results');

let currentData  = null;
let allLogLines  = [];
let filteredLines= [];
let barChart     = null;
let lineChart    = null;
const PAGE_SIZE  = 15;
let currentPage  = 1;

/* ── File selection ──────────────────────────────────────────────────────── */
fileInput.addEventListener('change', () => {
  const f = fileInput.files[0];
  if (f) {
    fileNameEl.textContent = `📄 ${f.name} (${(f.size/1024).toFixed(1)} KB)`;
    analyzeBtn.disabled = false;
  }
});

/* ── Drag & drop ─────────────────────────────────────────────────────────── */
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault(); dropZone.classList.remove('drag-over');
  fileInput.files = e.dataTransfer.files;
  fileInput.dispatchEvent(new Event('change'));
});

/* ── Tabs ────────────────────────────────────────────────────────────────── */
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(btn.dataset.tab).classList.add('active');
  });
});

/* ── Submit / Re-run ─────────────────────────────────────────────────────── */
async function runAnalysis() {
  if (!fileInput.files[0]) return;
  spinner.style.display = 'block';
  results.style.display = 'none';
  analyzeBtn.disabled   = true;
  rerunBtn.disabled     = true;
  downloadBtn.disabled  = true;
  downloadCsvBtn.disabled = true;

  const fd = new FormData();
  fd.append('logfile', fileInput.files[0]);

  try {
    const res  = await fetch('/analyze', { method: 'POST', body: fd });
    const data = await res.json();
    spinner.style.display = 'none';
    analyzeBtn.disabled   = false;
    rerunBtn.disabled     = false;

    if (data.error) {
      results.style.display = 'block';
      results.innerHTML = `<div class="error-box">❌ ${esc(data.error)}</div>`;
      return;
    }
    currentData = data;
    allLogLines = data.log_lines || [];
    filteredLines = [...allLogLines];
    displayResults(data);
    downloadBtn.disabled = false;
    downloadCsvBtn.disabled = false;
  } catch(err) {
    spinner.style.display = 'none';
    analyzeBtn.disabled   = false;
    rerunBtn.disabled     = false;
    results.style.display = 'block';
    results.innerHTML = `<div class="error-box">❌ Network error: ${esc(err.message)}</div>`;
  }
}

form.addEventListener('submit', e => { e.preventDefault(); runAnalysis(); });
rerunBtn.addEventListener('click', runAnalysis);

/* ── Display All Results ─────────────────────────────────────────────────── */
function displayResults(d) {
  results.style.display = 'block';

  /* Health Banner */
  const hb = document.getElementById('health-banner');
  hb.className = `health-banner ${d.system_health}`;
  const icons = { HEALTHY: '✅', WARNING: '⚠️', CRITICAL: '🔴' };
  hb.innerHTML = `
    <div class="health-dot ${d.system_health}"></div>
    <div class="health-info">
      <div class="h-title">${icons[d.system_health]} System Health: ${d.system_health}</div>
      <div class="h-sub">${d.health_summary.substring(0, 100)}…</div>
    </div>
    <div class="error-rate-badge">Error Rate: ${d.error_ratio_pct}%</div>
  `;

  /* Alert badge — no anomalies but high error rate */
  const ab = document.getElementById('alert-badge');
  if (d.anomaly_windows === 0 && d.error_ratio >= 0.4) {
    ab.style.display = 'inline-flex';
    ab.textContent = '⚠ No anomaly pattern, but high error rate detected';
  } else {
    ab.style.display = 'none';
  }

  /* Verdict */
  const vb = document.getElementById('verdict-box');
  vb.className = `verdict ${d.verdict}`;
  vb.textContent = d.verdict_msg;

  /* Method tag */
  document.getElementById('method-tag').textContent =
    d.method === 'isolation_forest'
      ? `🤖 Isolation Forest · Contamination: ${(d.error_ratio*100).toFixed(0)}% dynamic · Confidence: ${d.confidence ?? 'N/A'}%`
      : '🔑 Keyword Detection (fallback)';

  /* Stats */
  setText('s-total',   d.total);
  setText('s-info',    d.infos);
  setText('s-warn',    d.warnings);
  setText('s-err',     d.errors);
  setText('s-anom',    d.anomaly_windows);
  setText('s-rate',    d.anomaly_rate + '%');
  setText('s-windows', d.total_windows);
  setText('s-eratio',  d.error_ratio_pct + '%');

  /* Health summary */
  document.getElementById('health-text').textContent = d.health_summary;

  /* Anomaly/Error sample lines */
  const al  = document.getElementById('anomaly-lines');
  const ah  = document.getElementById('anomaly-section-title');
  const sec = document.getElementById('anomaly-section');
  if (d.sample_anomalies && d.sample_anomalies.length > 0) {
    ah.textContent = d.anomaly_windows > 0 ? '🚨 Anomalous Logs' : '🔴 Error Logs';
    al.innerHTML = d.sample_anomalies.map(l => `<div class="anomaly-line">${esc(l)}</div>`).join('');
    sec.style.display = 'block';
  } else {
    sec.style.display = 'none';
  }

  /* Insights & Recommendations */
  renderInsights(d.insights, d.recommendations);

  /* Charts */
  renderBarChart(d);
  renderLineChart(d);

  /* Log table */
  currentPage = 1;
  filteredLines = [...allLogLines];
  applyLogFilter();

  results.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/* ── Insights & Recommendations ─────────────────────────────────────────── */
function renderInsights(insights, recs) {
  document.getElementById('insights-list').innerHTML =
    (insights || []).map(i => `<li><span class="ins-icon">💡</span>${esc(i)}</li>`).join('');
  document.getElementById('recs-list').innerHTML =
    (recs || []).map(r => `<li><span class="ins-icon">➡</span>${esc(r)}</li>`).join('');
}

/* ── Bar Chart ───────────────────────────────────────────────────────────── */
function renderBarChart(d) {
  if (barChart) barChart.destroy();
  barChart = new Chart(document.getElementById('bar-chart').getContext('2d'), {
    type: 'bar',
    data: {
      labels: ['INFO','WARNING','ERROR','CRITICAL'],
      datasets: [{
        label: 'Log Count',
        data: [d.infos, d.warnings, d.errors, d.criticals||0],
        backgroundColor: ['rgba(34,197,94,.6)','rgba(245,158,11,.6)','rgba(239,68,68,.6)','rgba(239,68,68,.9)'],
        borderColor:     ['#22c55e','#f59e0b','#ef4444','#ff4444'],
        borderWidth: 1, borderRadius: 4,
      }]
    },
    options: chartOpts({ indexAxis: 'x' })
  });
}

/* ── Line Chart (anomaly score per window) ───────────────────────────────── */
function renderLineChart(d) {
  if (lineChart) lineChart.destroy();
  const labels = d.window_data.map(w => w.label);
  const scores = d.window_data.map(w => w.score);
  const colors = d.window_data.map(w => w.is_anomaly ? '#ef4444' : 'rgba(108,99,255,.9)');
  lineChart = new Chart(document.getElementById('line-chart').getContext('2d'), {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Anomaly Score',
        data: scores,
        borderColor: 'rgba(108,99,255,.8)',
        backgroundColor: 'rgba(108,99,255,.06)',
        pointBackgroundColor: colors,
        pointRadius: 5, fill: true, tension: 0.3,
      }]
    },
    options: {
      ...chartOpts(),
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            afterLabel: ctx => {
              const w = d.window_data[ctx.dataIndex];
              return w.is_anomaly ? `ANOMALY: ${w.reason}` : 'Normal';
            }
          }
        }
      }
    }
  });
}

function chartOpts(extra = {}) {
  return {
    responsive: true, maintainAspectRatio: true,
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { color: 'rgba(255,255,255,.05)' }, ticks: { color: '#7a8099', maxTicksLimit: 12 } },
      y: { grid: { color: 'rgba(255,255,255,.05)' }, ticks: { color: '#7a8099' }, beginAtZero: true }
    },
    ...extra
  };
}

/* ── Log Table with Pagination ───────────────────────────────────────────── */
function renderLogTable(logs, page) {
  const tbody = document.getElementById('log-tbody');
  const start = (page - 1) * PAGE_SIZE;
  const slice = logs.slice(start, start + PAGE_SIZE);

  if (!logs.length) {
    tbody.innerHTML = '<tr><td colspan="3" class="no-rows">No matching log lines.</td></tr>';
    document.getElementById('pagination').innerHTML = '';
    document.getElementById('page-info').textContent = '';
    return;
  }

  tbody.innerHTML = slice.map(l => `
    <tr>
      <td>${esc(l.timestamp)}</td>
      <td><span class="level-badge level-${esc(l.level)}">${esc(l.level)}</span></td>
      <td>${esc(l.message)}</td>
    </tr>`).join('');

  renderPagination(logs.length, page);
}

function renderPagination(total, page) {
  const pages = Math.ceil(total / PAGE_SIZE);
  const pg = document.getElementById('pagination');
  const pi = document.getElementById('page-info');
  pi.textContent = `${(page-1)*PAGE_SIZE+1}–${Math.min(page*PAGE_SIZE,total)} of ${total}`;

  let html = '';
  html += `<button class="page-btn" onclick="goPage(${page-1})" ${page===1?'disabled':''}>‹ Prev</button>`;
  for (let i = 1; i <= pages; i++) {
    if (pages <= 7 || Math.abs(i-page) <= 2 || i===1 || i===pages) {
      html += `<button class="page-btn ${i===page?'active':''}" onclick="goPage(${i})">${i}</button>`;
    } else if (Math.abs(i-page) === 3) {
      html += `<span class="page-btn" style="pointer-events:none">…</span>`;
    }
  }
  html += `<button class="page-btn" onclick="goPage(${page+1})" ${page===pages?'disabled':''}>Next ›</button>`;
  pg.innerHTML = html;
}

window.goPage = function(p) {
  currentPage = p;
  renderLogTable(filteredLines, currentPage);
};

/* ── Search & Filter ─────────────────────────────────────────────────────── */
document.getElementById('log-search').addEventListener('input', applyLogFilter);
document.getElementById('log-filter').addEventListener('change', applyLogFilter);

function applyLogFilter() {
  const q  = document.getElementById('log-search').value.toLowerCase();
  const lv = document.getElementById('log-filter').value;
  filteredLines = allLogLines.filter(l =>
    (lv === 'ALL' || l.level === lv) &&
    (l.message.toLowerCase().includes(q) || l.timestamp.includes(q))
  );
  currentPage = 1;
  renderLogTable(filteredLines, currentPage);
}

/* ── Download Report ─────────────────────────────────────────────────────── */
downloadBtn.addEventListener('click', () => {
  if (!currentData) return;
  const d = currentData;
  const lines = [
    '========================================',
    ' AI Log Analyzer — System Health Report ',
    '========================================',
    `Generated  : ${new Date().toLocaleString()}`,
    '',
    `Verdict    : ${d.verdict} — ${d.verdict_msg}`,
    `Health     : ${d.system_health}`,
    `Error Rate : ${d.error_ratio_pct}%`,
    `Method     : ${d.method}`,
    d.confidence != null ? `Confidence : ${d.confidence}%` : '',
    '',
    '--- Metrics ---',
    `Total Logs      : ${d.total}`,
    `INFO            : ${d.infos}`,
    `WARNING         : ${d.warnings}`,
    `ERROR           : ${d.errors}`,
    `CRITICAL        : ${d.criticals||0}`,
    `Time Windows    : ${d.total_windows}`,
    `Anomaly Windows : ${d.anomaly_windows}`,
    `Anomaly Rate    : ${d.anomaly_rate}%`,
    '',
    '--- AI Health Summary ---',
    d.health_summary,
    '',
    '--- Insights ---',
    ...(d.insights||[]).map(i => `• ${i}`),
    '',
    '--- Recommendations ---',
    ...(d.recommendations||[]).map(r => `→ ${r}`),
    '',
    '--- Sample Error/Anomaly Logs ---',
    ...(d.sample_anomalies.length ? d.sample_anomalies : ['None']),
    '',
    '======== End of Report ========',
  ].filter(l => l !== undefined);

  const blob = new Blob([lines.join('\n')], { type: 'text/plain' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url; a.download = `log-report-${Date.now()}.txt`;
  a.click(); URL.revokeObjectURL(url);
});

/* ── Download CSV Logs ───────────────────────────────────────────────────── */
downloadCsvBtn.addEventListener('click', () => {
  if (!currentData || !allLogLines.length) return;
  const headers = ['Timestamp', 'Level', 'Message'];
  const rows = allLogLines.map(l => [
    `"${l.timestamp.replace(/"/g, '""')}"`,
    `"${l.level.replace(/"/g, '""')}"`,
    `"${l.message.replace(/"/g, '""')}"`
  ]);
  const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = `parsed-logs-${Date.now()}.csv`;
  a.click(); URL.revokeObjectURL(url);
});

/* ── Utility ─────────────────────────────────────────────────────────────── */
function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}
function esc(str) {
  return String(str)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
