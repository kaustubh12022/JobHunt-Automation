// Standalone Job Evaluator Client Script

let allJobs = [];
let currentTab = 'all'; // 'all', 'selected', 'rejected'
let isEvaluating = false;
let eventSource = null;

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
  fetchAvailableDatasets();
  fetchInitialStatus();
  connectEventSource();
});

// ─────────────────────────────────────────────────────────────────────────────
// Real-Time Event Stream (SSE)
// ─────────────────────────────────────────────────────────────────────────────

function connectEventSource() {
  if (eventSource) {
    eventSource.close();
  }

  eventSource = new EventSource('/api/events');

  eventSource.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);
      if (payload.type === 'init') {
        updateSummaryUI(payload.summary);
      } else if (payload.type === 'update') {
        updateSummaryUI(payload.summary);
        if (payload.job) {
          updateSingleJob(payload.job);
        }
      } else if (payload.type === 'log') {
        appendTerminalLog(payload.data);
      }
    } catch (err) {
      console.error('SSE message parse error:', err);
    }
  };

  eventSource.onerror = () => {
    // Retry connection after 3s
    setTimeout(connectEventSource, 3000);
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// API & Data Fetching
// ─────────────────────────────────────────────────────────────────────────────

async function fetchInitialStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    allJobs = data.jobs || [];
    updateSummaryUI(data.summary);
    renderJobsTable();
    
    // Populate recent logs if any
    if (data.logs && data.logs.length > 0) {
      const term = document.getElementById('terminalBody');
      term.innerHTML = '';
      data.logs.forEach(appendTerminalLog);
    }
  } catch (err) {
    console.error('Failed to load initial status:', err);
  }
}

async function fetchAvailableDatasets() {
  try {
    const res = await fetch('/api/available_datasets');
    const data = await res.json();
    const select = document.getElementById('quickDatasetSelect');
    select.innerHTML = '<option value="">Select workspace dataset...</option>';
    
    if (data.datasets && data.datasets.length > 0) {
      data.datasets.forEach(ds => {
        const opt = document.createElement('option');
        opt.value = ds.path;
        opt.textContent = `${ds.name} (${ds.size_mb} MB)`;
        select.appendChild(opt);
      });
    }
  } catch (err) {
    console.error('Failed to fetch available datasets:', err);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// UI Updates & Table Rendering
// ─────────────────────────────────────────────────────────────────────────────

function updateSummaryUI(summary) {
  if (!summary) return;

  isEvaluating = summary.is_running;

  // Running status indicator
  const dot = document.getElementById('statusDot');
  const text = document.getElementById('statusText');
  const startBtn = document.getElementById('startBtn');
  const stopBtn = document.getElementById('stopBtn');

  if (isEvaluating) {
    dot.className = 'w-2 h-2 rounded-full bg-emerald-500 animate-pulse';
    text.className = 'text-emerald-400 font-medium';
    text.textContent = 'Evaluating...';
    startBtn.disabled = true;
    stopBtn.disabled = false;
  } else {
    dot.className = 'w-2 h-2 rounded-full bg-slate-500';
    text.className = 'text-slate-300 font-medium';
    text.textContent = 'Idle';
    startBtn.disabled = false;
    stopBtn.disabled = true;
  }

  // Statistics cards
  document.getElementById('statTotal').innerText = summary.total_jobs || 0;
  document.getElementById('statProcessed').innerText = summary.processed || 0;
  document.getElementById('statAccepted').innerText = summary.accepted || 0;
  document.getElementById('statRejected').innerText = summary.rejected || 0;
  document.getElementById('statGeminiCount').innerText = summary.gemini_count || 0;
  document.getElementById('statGroqCount').innerText = summary.groq_count || 0;
  document.getElementById('statAvgScore').innerHTML = `${summary.avg_score || 0} <span class="text-xs text-slate-400 font-normal">pts</span>`;
  document.getElementById('statAvgLatency').innerText = `Avg: ${summary.avg_latency || 0}s / job`;

  // Filename badge
  const loadedName = summary.current_filename || 'No dataset loaded';
  document.getElementById('statLoadedName').innerText = loadedName;
  document.getElementById('datasetNameBadge').innerText = loadedName;

  // Progress Bar & Pct
  const total = summary.total_jobs || 0;
  const processed = summary.processed || 0;
  const pct = total > 0 ? Math.round((processed / total) * 100) : 0;
  document.getElementById('statProgressPct').innerText = `${pct}%`;
  document.getElementById('statProgressBar').style.width = `${pct}%`;

  // Acceptance / Rejection rates
  const accRate = processed > 0 ? Math.round((summary.accepted / processed) * 100) : 0;
  const rejRate = processed > 0 ? Math.round((summary.rejected / processed) * 100) : 0;
  document.getElementById('statAcceptedRate').innerText = `${accRate}% acceptance rate`;
  document.getElementById('statRejectedRate').innerText = `${rejRate}% rejection rate`;

  // Tab Badge counts
  document.getElementById('tabCountAll').innerText = total;
  document.getElementById('tabCountSelected').innerText = summary.accepted || 0;
  document.getElementById('tabCountRejected').innerText = summary.rejected || 0;
}

function updateSingleJob(jobUpdate) {
  const index = allJobs.findIndex(j => String(j.id) === String(jobUpdate.id));
  if (index !== -1) {
    allJobs[index] = { ...allJobs[index], ...jobUpdate };
  } else {
    allJobs.push(jobUpdate);
  }
  renderJobsTable();
}

function setTab(tab) {
  currentTab = tab;
  
  // Update tab button styles
  const tabs = ['all', 'selected', 'rejected'];
  tabs.forEach(t => {
    const btn = document.getElementById(`tab${t.charAt(0).toUpperCase() + t.slice(1)}`);
    if (t === tab) {
      if (t === 'selected') {
        btn.className = 'px-4 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 text-white shadow transition';
      } else if (t === 'rejected') {
        btn.className = 'px-4 py-1.5 rounded-lg text-xs font-semibold bg-rose-600 text-white shadow transition';
      } else {
        btn.className = 'px-4 py-1.5 rounded-lg text-xs font-semibold bg-blue-600 text-white shadow transition';
      }
    } else {
      btn.className = 'px-4 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-slate-200 transition';
    }
  });

  renderJobsTable();
}

function filterJobsTable() {
  renderJobsTable();
}

function renderJobsTable() {
  const tbody = document.getElementById('jobsTableBody');
  const search = (document.getElementById('tableSearch')?.value || '').toLowerCase().trim();

  // 1. Filter by current tab
  let filtered = allJobs;
  if (currentTab === 'selected') {
    filtered = allJobs.filter(j => j.decision === 'ACCEPTED');
  } else if (currentTab === 'rejected') {
    filtered = allJobs.filter(j => j.decision === 'REJECTED');
  }

  // 2. Filter by search term
  if (search) {
    filtered = filtered.filter(j => {
      const title = (j.title || '').toLowerCase();
      const comp = (j.company || '').toLowerCase();
      const reason = (j.reasoning || '').toLowerCase();
      const skills = (j.missing_skills || []).join(' ').toLowerCase();
      return title.includes(search) || comp.includes(search) || reason.includes(search) || skills.includes(search);
    });
  }

  if (filtered.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="8" class="text-center py-12 text-slate-500">
          <i data-lucide="filter-x" class="w-8 h-8 mx-auto mb-2 text-slate-600"></i>
          <span>No jobs matching current filter (${currentTab}).</span>
        </td>
      </tr>
    `;
    lucide.createIcons();
    return;
  }

  let html = '';
  filtered.forEach((job, idx) => {
    // Status Badge
    let statusBadge = '<span class="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-slate-800 text-slate-400">Pending</span>';
    if (job.status === 'processing') {
      statusBadge = '<span class="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30 animate-pulse">Evaluating...</span>';
    } else if (job.decision === 'ACCEPTED') {
      statusBadge = '<span class="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">SELECTED</span>';
    } else if (job.decision === 'REJECTED') {
      statusBadge = '<span class="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-rose-500/20 text-rose-400 border border-rose-500/40">REJECTED</span>';
    } else if (job.status === 'failed') {
      statusBadge = '<span class="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-red-800/40 text-red-300">FAILED</span>';
    }

    // Score display
    let scoreDisplay = '<span class="text-slate-500">--</span>';
    if (job.fit_score !== null && job.fit_score !== undefined) {
      let scoreColor = 'text-emerald-400';
      if (job.fit_score < 40) scoreColor = 'text-rose-400';
      else if (job.fit_score < 60) scoreColor = 'text-amber-400';

      scoreDisplay = `
        <div class="flex items-center space-x-1.5">
          <span class="font-bold text-sm ${scoreColor}">${job.fit_score}</span>
          <span class="text-[10px] text-slate-500">/100</span>
        </div>
      `;
    }

    // Role type pill
    let roleType = '<span class="text-slate-500">--</span>';
    if (job.is_testing_role !== null && job.is_testing_role !== undefined) {
      if (job.is_testing_role) {
        roleType = '<span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-purple-500/20 text-purple-300 border border-purple-500/30">QA / Testing</span>';
      } else {
        roleType = '<span class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">Dev / Backend</span>';
      }
    }

    // Provider badge
    let providerBadge = '<span class="text-slate-500">--</span>';
    if (job.provider) {
      const isGemini = job.provider.toLowerCase().includes('gemini');
      const provColor = isGemini ? 'bg-sky-500/20 text-sky-300 border-sky-500/40' : 'bg-orange-500/20 text-orange-300 border-orange-500/40';
      const latencyStr = job.latency_seconds ? ` (${job.latency_seconds}s)` : '';
      providerBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-mono border ${provColor}">${job.provider}${latencyStr}</span>`;
    }

    const reasonText = job.reasoning || (job.status === 'processing' ? 'Currently analyzing candidate profile...' : 'Waiting in queue...');

    html += `
      <tr class="hover:bg-slate-800/40 transition">
        <td class="py-3 px-4 text-center font-mono text-slate-500">${idx + 1}</td>
        <td class="py-3 px-4">${statusBadge}</td>
        <td class="py-3 px-4">${scoreDisplay}</td>
        <td class="py-3 px-4">
          <div class="font-medium text-slate-200 truncate max-w-[260px]">${escapeHtml(job.title || 'Untitled')}</div>
          <div class="text-[11px] text-slate-400 truncate max-w-[260px]">${escapeHtml(job.company || 'Unknown')} • ${escapeHtml(job.location || 'Remote')}</div>
        </td>
        <td class="py-3 px-4">
          <p class="text-slate-300 text-xs line-clamp-2 max-w-[360px]">${escapeHtml(reasonText)}</p>
        </td>
        <td class="py-3 px-4">${roleType}</td>
        <td class="py-3 px-4">${providerBadge}</td>
        <td class="py-3 px-4 text-center">
          <button onclick="viewJobDetails('${escapeHtml(job.id)}')" class="p-1 rounded hover:bg-slate-700 text-slate-400 hover:text-white transition" title="View Details">
            <i data-lucide="eye" class="w-4 h-4"></i>
          </button>
        </td>
      </tr>
    `;
  });

  tbody.innerHTML = html;
  lucide.createIcons();
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// ─────────────────────────────────────────────────────────────────────────────
// Terminal Log Output
// ─────────────────────────────────────────────────────────────────────────────

function appendTerminalLog(entry) {
  const terminal = document.getElementById('terminalBody');
  if (!terminal) return;

  const row = document.createElement('div');
  row.className = 'flex items-start space-x-2 py-0.5';

  const timeSpan = document.createElement('span');
  timeSpan.className = 'text-slate-500 text-[11px] shrink-0';
  timeSpan.textContent = `[${entry.time}]`;

  const textSpan = document.createElement('span');
  textSpan.className = 'text-xs break-all';

  if (entry.level === 'SUCCESS' || entry.category === 'accepted') {
    textSpan.className += ' text-emerald-400 font-medium';
  } else if (entry.level === 'REJECTED' || entry.category === 'rejected') {
    textSpan.className += ' text-rose-400';
  } else if (entry.level === 'ERROR') {
    textSpan.className += ' text-red-400 font-bold';
  } else if (entry.level === 'WARN') {
    textSpan.className += ' text-amber-400';
  } else {
    textSpan.className += ' text-slate-300';
  }

  textSpan.textContent = entry.text;

  row.appendChild(timeSpan);
  row.appendChild(textSpan);
  terminal.appendChild(row);

  // Auto-scroll if enabled
  const autoScroll = document.getElementById('autoScrollLogs')?.checked;
  if (autoScroll) {
    terminal.scrollTop = terminal.scrollHeight;
  }
}

function clearTerminalLogs() {
  const terminal = document.getElementById('terminalBody');
  if (terminal) terminal.innerHTML = '';
}

// ─────────────────────────────────────────────────────────────────────────────
// File Upload & Quick Selection
// ─────────────────────────────────────────────────────────────────────────────

async function handleFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch('/api/upload', {
      method: 'POST',
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Upload failed');

    // Reload all jobs
    await fetchInitialStatus();
  } catch (err) {
    alert('File upload error: ' + err.message);
  }
}

async function handleQuickSelect(path) {
  if (!path) return;

  try {
    const res = await fetch('/api/load_dataset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: path }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to load dataset');

    await fetchInitialStatus();
  } catch (err) {
    alert('Error loading dataset: ' + err.message);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Evaluation Controls
// ─────────────────────────────────────────────────────────────────────────────

async function startEvaluation() {
  if (allJobs.length === 0) {
    alert('Please upload or select a JSON dataset first!');
    return;
  }

  const mode = document.getElementById('evalMode').value;
  const threshold = parseInt(document.getElementById('thresholdSlider').value, 10);
  const limitVal = parseInt(document.getElementById('batchLimit').value, 10);

  try {
    const res = await fetch('/api/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        mode: mode,
        threshold: threshold,
        limit: limitVal > 0 ? limitVal : null,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to start');
  } catch (err) {
    alert('Error starting evaluation: ' + err.message);
  }
}

async function stopEvaluation() {
  try {
    await fetch('/api/stop', { method: 'POST' });
  } catch (err) {
    console.error('Stop error:', err);
  }
}

async function clearData() {
  if (!confirm('Are you sure you want to clear all loaded jobs and evaluation results?')) return;
  try {
    await fetch('/api/clear', { method: 'POST' });
    allJobs = [];
    renderJobsTable();
    clearTerminalLogs();
  } catch (err) {
    alert('Clear error: ' + err.message);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Exporting
// ─────────────────────────────────────────────────────────────────────────────

function toggleExportMenu() {
  const menu = document.getElementById('exportMenu');
  menu.classList.toggle('hidden');
}

// Close export menu when clicking outside
window.addEventListener('click', (e) => {
  if (!e.target.closest('#exportMenu') && !e.target.closest('button[onclick="toggleExportMenu()"]')) {
    document.getElementById('exportMenu')?.classList.add('hidden');
  }
});

function exportResults(format, filter) {
  window.open(`/api/export?format=${format}&filter_by=${filter}`, '_blank');
  document.getElementById('exportMenu')?.classList.add('hidden');
}

// ─────────────────────────────────────────────────────────────────────────────
// Modals
// ─────────────────────────────────────────────────────────────────────────────

function viewJobDetails(jobId) {
  const job = allJobs.find(j => String(j.id) === String(jobId));
  if (!job) return;

  const content = document.getElementById('modalContent');
  const isAccepted = job.decision === 'ACCEPTED';

  let skillsHtml = '<span class="text-slate-500">None</span>';
  if (job.missing_skills && job.missing_skills.length > 0) {
    skillsHtml = job.missing_skills.map(s => `<span class="px-2 py-0.5 rounded text-[11px] bg-rose-500/20 text-rose-300 border border-rose-500/30">${escapeHtml(s)}</span>`).join(' ');
  }

  content.innerHTML = `
    <div class="space-y-4 text-xs">
      <div class="flex items-start justify-between">
        <div>
          <span class="px-2.5 py-1 rounded-full text-xs font-bold ${isAccepted ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40' : 'bg-rose-500/20 text-rose-400 border border-rose-500/40'}">
            ${job.decision || 'PENDING'} (Score: ${job.fit_score !== null ? job.fit_score : '--'}/100)
          </span>
          <h2 class="text-base font-bold text-white mt-2">${escapeHtml(job.title)}</h2>
          <p class="text-slate-400">${escapeHtml(job.company)} • ${escapeHtml(job.location || 'Remote')}</p>
        </div>
        ${job.url ? `<a href="${job.url}" target="_blank" class="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium flex items-center space-x-1"><span>Open Job</span><i data-lucide="external-link" class="w-3.5 h-3.5"></i></a>` : ''}
      </div>

      <div class="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-2">
        <div>
          <span class="text-slate-500 block mb-1">Decision Reason:</span>
          <p class="text-slate-200 font-medium text-sm">${escapeHtml(job.reasoning || 'No reason evaluated yet.')}</p>
        </div>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-slate-800 text-[11px]">
          <div><span class="text-slate-500">Evaluator:</span> <span class="text-slate-300 font-mono">${job.provider || '--'}</span></div>
          <div><span class="text-slate-500">Model:</span> <span class="text-slate-300 font-mono">${job.model || '--'}</span></div>
          <div><span class="text-slate-500">Speed:</span> <span class="text-slate-300 font-mono">${job.latency_seconds ? job.latency_seconds + 's' : '--'}</span></div>
          <div><span class="text-slate-500">Role:</span> <span class="text-slate-300">${job.is_testing_role ? 'Testing/QA' : 'Dev'}</span></div>
        </div>
      </div>

      <div>
        <span class="text-slate-400 block mb-1.5 font-medium">Missing Skills Identified by Engine:</span>
        <div class="flex flex-wrap gap-1.5">
          ${skillsHtml}
        </div>
      </div>

      <div>
        <span class="text-slate-400 block mb-1 font-medium">Job Description:</span>
        <div class="bg-slate-950 p-4 rounded-xl border border-slate-800 max-h-60 overflow-y-auto text-slate-300 whitespace-pre-wrap leading-relaxed text-[11px]">
          ${escapeHtml(job.description || 'No job description provided.')}
        </div>
      </div>
    </div>
  `;

  document.getElementById('detailsModal').classList.remove('hidden');
  lucide.createIcons();
}

function closeDetailsModal() {
  document.getElementById('detailsModal').classList.add('hidden');
}

async function openConfigModal() {
  try {
    const res = await fetch('/api/config');
    const data = await res.json();
    if (data.gemini && data.gemini.key_preview) {
      document.getElementById('inputGeminiKey').placeholder = `Current: ${data.gemini.key_preview}`;
    }
    if (data.groq && data.groq.key_preview) {
      document.getElementById('inputGroqKey').placeholder = `Current: ${data.groq.key_preview}`;
    }
  } catch (err) {
    console.error('Config fetch error:', err);
  }
  document.getElementById('configModal').classList.remove('hidden');
}

function closeConfigModal() {
  document.getElementById('configModal').classList.add('hidden');
}

async function saveApiKeys() {
  const gemini = document.getElementById('inputGeminiKey').value.trim();
  const groq = document.getElementById('inputGroqKey').value.trim();

  try {
    const res = await fetch('/api/update_keys', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        gemini_key: gemini,
        groq_key: groq,
      }),
    });
    if (res.ok) {
      alert('API Keys saved successfully!');
      closeConfigModal();
    } else {
      alert('Failed to update keys');
    }
  } catch (err) {
    alert('Error saving keys: ' + err.message);
  }
}
