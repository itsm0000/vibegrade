/* ─────────────────────────────────────────────────────
   VibeGrade · Frontend JS
   Handles file uploads, preset selection, grading API calls
───────────────────────────────────────────────────── */

const API = 'http://localhost:5000/api';

// ── State ──
let uploadedFiles = [];   // [{job_id, filename, preview_url}]
let selectedPreset = null;
let selectedFormat = 'jpg';

// ── DOM refs ──
const dropZone      = document.getElementById('dropZone');
const fileInput     = document.getElementById('fileInput');
const photoGrid     = document.getElementById('photoGrid');
const vibeGrid      = document.getElementById('vibeGrid');
const vibeSection   = document.getElementById('vibeSection');
const styleSection  = document.getElementById('styleSection');
const refDropZone   = document.getElementById('refDropZone');
const refFileInput  = document.getElementById('refFileInput');
const refStatus     = document.getElementById('refStatus');
const optionsSection= document.getElementById('optionsSection');
const actionSection = document.getElementById('actionSection');
const gradeBtn      = document.getElementById('gradeBtn');
const gradeBtnCount = document.getElementById('gradeBtnCount');
const strengthSlider= document.getElementById('strengthSlider');
const strengthLabel = document.getElementById('strengthLabel');
const grainToggle   = document.getElementById('grainToggle');
const progressSection=document.getElementById('progressSection');
const progressLabel = document.getElementById('progressLabel');
const progressPct   = document.getElementById('progressPct');
const progressFill  = document.getElementById('progressFill');
const progressSteps = document.getElementById('progressSteps');
const resultsSection= document.getElementById('resultsSection');
const resultsGrid   = document.getElementById('resultsGrid');
const downloadAllBtn= document.getElementById('downloadAllBtn');
const gradeMoreBtn  = document.getElementById('gradeMoreBtn');

// ── Init ──
async function init() {
  await loadPresets();
  setupDropZone();
  setupRefDropZone();
  setupSlider();
  setupFormatBtns();
  gradeBtn.addEventListener('click', startGrading);
  gradeMoreBtn.addEventListener('click', resetAll);
  downloadAllBtn.addEventListener('click', downloadAll);
}

// ── Load presets from API ──
async function loadPresets() {
  try {
    const res = await fetch(`${API}/presets`);
    const presets = await res.json();
    renderVibeGrid(presets);
  } catch (e) {
    // Fallback hardcoded presets
    renderVibeGrid([
      { id:'cinematic',       emoji:'🎬', name:'Cinematic',        description:'Teal & orange split tones, lifted blacks, rich midtone contrast',        palette:['#1a3a3a','#c86030','#f0d090'] },
      { id:'retro_film',      emoji:'📷', name:'Retro Film',       description:'Kodak warmth, faded shadows, halation glow, 35mm grain',                palette:['#3d2b1a','#c8a060','#fff0d0'] },
      { id:'cyberpunk',       emoji:'🌆', name:'Cyberpunk',        description:'Neon cyan & magenta, crushed blacks, electric highlights',               palette:['#050512','#00ffee','#ff00cc'] },
      { id:'futuristic_warm', emoji:'🌅', name:'Futuristic Warm',  description:'Golden hour glow, clean airy highlights, soft warm mids',               palette:['#2a1a0a','#e8a030','#fff8e0'] },
      { id:'moody_dark',      emoji:'🌑', name:'Moody Dark',       description:'Desaturated, lifted blacks, deep cool shadows, filmic silence',          palette:['#1a1a2a','#607080','#d0d8e0'] },
      { id:'your_style',      emoji:'✨', name:'Your Style',       description:'Upload your favourite edited photos — AI matches your personal look',    palette:['#6030c0','#c060f0','#f0c0ff'] },
    ]);
  }
}

function renderVibeGrid(presets) {
  vibeGrid.innerHTML = '';
  presets.forEach(p => {
    const card = document.createElement('div');
    card.className = 'vibe-card';
    card.dataset.id = p.id;
    card.innerHTML = `
      <div class="vibe-selected-badge">✓</div>
      <div class="vibe-emoji">${p.emoji}</div>
      <div class="vibe-palette">
        ${(p.palette||[]).map(c=>`<div class="vibe-palette-dot" style="background:${c}"></div>`).join('')}
      </div>
      <div class="vibe-name">${p.name}</div>
      <div class="vibe-desc">${p.description}</div>
    `;
    card.addEventListener('click', () => selectVibe(p.id, card));
    vibeGrid.appendChild(card);
  });
}

function selectVibe(id, card) {
  document.querySelectorAll('.vibe-card').forEach(c => c.classList.remove('active'));
  card.classList.add('active');
  selectedPreset = id;

  // Show/hide Your Style reference section
  styleSection.style.display = (id === 'your_style') ? 'flex' : 'none';

  updateGradeBtn();
}

// ── File upload ──
function setupDropZone() {
  dropZone.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', e => handleFiles(e.target.files));

  dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('dragover'); });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
  dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    handleFiles(e.dataTransfer.files);
  });
}

async function handleFiles(files) {
  if (!files.length) return;

  const formData = new FormData();
  Array.from(files).forEach(f => formData.append('files', f));

  // Add loading thumbs
  const loadingIds = Array.from(files).map(f => {
    return addLoadingThumb(f.name);
  });

  try {
    const res = await fetch(`${API}/upload`, { method: 'POST', body: formData });
    const data = await res.json();

    if (!res.ok) throw new Error(data.error || 'Upload failed');

    // Remove loading placeholders and add real previews
    loadingIds.forEach(id => {
      const el = document.getElementById(id);
      if (el) el.remove();
    });

    data.files.forEach(f => {
      uploadedFiles.push(f);
      addThumb(f);
    });

    updateGradeBtn();
  } catch (e) {
    loadingIds.forEach(id => { const el = document.getElementById(id); if (el) el.remove(); });
    showError('Upload failed: ' + e.message);
  }
}

function addLoadingThumb(filename) {
  const id = 'thumb-' + Math.random().toString(36).slice(2);
  const div = document.createElement('div');
  div.className = 'photo-thumb';
  div.id = id;
  div.innerHTML = `
    <div class="photo-thumb-loading"><div class="spinner"></div></div>
    <div class="photo-thumb-label">${filename}</div>
  `;
  photoGrid.appendChild(div);
  return id;
}

function addThumb(file) {
  const div = document.createElement('div');
  div.className = 'photo-thumb';
  div.id = 'thumb-' + file.job_id;

  if (file.preview_url) {
    div.innerHTML = `
      <img src="${file.preview_url}" alt="${file.filename}" loading="lazy" />
      <div class="photo-thumb-label">${file.filename}</div>
    `;
  } else {
    div.innerHTML = `
      <div class="photo-thumb-loading" style="background:var(--bg-3);flex-direction:column;gap:0.3rem;">
        <span style="font-size:1.5rem">📄</span>
        <span style="font-size:0.7rem;color:var(--text-muted)">RAW</span>
      </div>
      <div class="photo-thumb-label">${file.filename}</div>
    `;
  }

  photoGrid.appendChild(div);
}

// ── Reference photos ──
function setupRefDropZone() {
  refDropZone.addEventListener('click', () => refFileInput.click());
  refFileInput.addEventListener('change', e => handleRefFiles(e.target.files));

  refDropZone.addEventListener('dragover', e => { e.preventDefault(); refDropZone.classList.add('dragover'); });
  refDropZone.addEventListener('dragleave', () => refDropZone.classList.remove('dragover'));
  refDropZone.addEventListener('drop', e => {
    e.preventDefault();
    refDropZone.classList.remove('dragover');
    handleRefFiles(e.dataTransfer.files);
  });
}

async function handleRefFiles(files) {
  if (!files.length) return;
  const formData = new FormData();
  Array.from(files).forEach(f => formData.append('files', f));
  refStatus.textContent = 'Uploading references…';

  try {
    const res = await fetch(`${API}/upload_reference`, { method: 'POST', body: formData });
    const data = await res.json();
    refStatus.textContent = `✓ ${data.count} reference photo${data.count !== 1 ? 's' : ''} loaded. Style fingerprint ready.`;
  } catch (e) {
    refStatus.textContent = 'Failed to upload references.';
    refStatus.style.color = '#ff6060';
  }
}

// ── Options ──
function setupSlider() {
  strengthSlider.addEventListener('input', () => {
    strengthLabel.textContent = strengthSlider.value + '%';
  });
}

function setupFormatBtns() {
  document.getElementById('formatGroup').addEventListener('click', e => {
    const btn = e.target.closest('.format-btn');
    if (!btn) return;
    document.querySelectorAll('.format-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    selectedFormat = btn.dataset.fmt;
  });
}

// ── Grade button state ──
function updateGradeBtn() {
  const ready = uploadedFiles.length > 0 && selectedPreset;
  gradeBtn.disabled = !ready;
  gradeBtnCount.textContent = uploadedFiles.length > 0 ? `${uploadedFiles.length} photo${uploadedFiles.length !== 1 ? 's' : ''}` : '';
}

// ── Start grading ──
async function startGrading() {
  if (!uploadedFiles.length || !selectedPreset) return;

  gradeBtn.disabled = true;

  // Show progress
  progressSection.style.display = 'flex';
  resultsSection.style.display = 'none';
  progressSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

  const steps = [
    { label: 'Reading RAW files…', pct: 10 },
    { label: 'Applying color science…', pct: 40 },
    { label: 'Running AI grade…', pct: 70 },
    { label: 'Exporting images…', pct: 90 },
    { label: 'Done!', pct: 100 },
  ];

  // Animate progress steps while waiting
  let stepIdx = 0;
  const stepInterval = setInterval(() => {
    if (stepIdx >= steps.length - 1) { clearInterval(stepInterval); return; }
    setProgress(steps[stepIdx].pct, steps[stepIdx].label, stepIdx, steps);
    stepIdx++;
  }, 800);

  try {
    const body = {
      jobs: uploadedFiles.map(f => f.job_id),
      preset: selectedPreset,
      strength: parseInt(strengthSlider.value) / 100,
      grain: grainToggle.checked,
      format: selectedFormat,
    };

    const res = await fetch(`${API}/grade`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json();

    clearInterval(stepInterval);
    setProgress(100, 'Done!', steps.length - 1, steps);

    await sleep(600);
    progressSection.style.display = 'none';

    if (data.errors?.length) {
      data.errors.forEach(e => showError(`${e.job_id}: ${e.error}`));
    }

    if (data.outputs?.length) {
      showResults(data.outputs, selectedPreset);
    }

  } catch (e) {
    clearInterval(stepInterval);
    progressSection.style.display = 'none';
    showError('Grading failed: ' + e.message);
    gradeBtn.disabled = false;
  }
}

function setProgress(pct, label, doneIdx, steps) {
  progressFill.style.width = pct + '%';
  progressPct.textContent = pct + '%';
  progressLabel.textContent = label;

  progressSteps.innerHTML = steps.map((s, i) => {
    const cls = i < doneIdx ? 'done' : i === doneIdx ? 'active' : '';
    const icon = i < doneIdx ? '✓' : i === doneIdx ? '◎' : '○';
    return `<div class="progress-step ${cls}">${icon} ${s.label}</div>`;
  }).join('');
}

// ── Show results ──
function showResults(outputs, presetId) {
  const presetMeta = {
    cinematic:       { emoji: '🎬', name: 'Cinematic' },
    retro_film:      { emoji: '📷', name: 'Retro Film' },
    cyberpunk:       { emoji: '🌆', name: 'Cyberpunk' },
    futuristic_warm: { emoji: '🌅', name: 'Futuristic Warm' },
    moody_dark:      { emoji: '🌑', name: 'Moody Dark' },
    your_style:      { emoji: '✨', name: 'Your Style' },
  };
  const meta = presetMeta[presetId] || { emoji: '✦', name: presetId };

  resultsGrid.innerHTML = '';
  outputs.forEach(out => {
    const card = document.createElement('div');
    card.className = 'result-card';
    const imgUrl = `http://localhost:5000${out.output_url}`;
    card.innerHTML = `
      <div class="result-img-wrap">
        <img src="${imgUrl}" alt="${out.filename}" loading="lazy" />
        <div class="result-preset-tag">${meta.emoji} ${meta.name}</div>
      </div>
      <div class="result-info">
        <span class="result-filename">${out.filename}</span>
        <a class="result-dl-btn" href="${imgUrl}" download="${out.filename}">⬇ Save</a>
      </div>
    `;
    resultsGrid.appendChild(card);
  });

  resultsSection.style.display = 'flex';
  resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  gradeBtn.disabled = false;
}

// ── Download all ──
function downloadAll() {
  document.querySelectorAll('.result-dl-btn').forEach(btn => {
    btn.click();
  });
}

// ── Reset ──
function resetAll() {
  uploadedFiles = [];
  selectedPreset = null;
  photoGrid.innerHTML = '';
  resultsSection.style.display = 'none';
  progressSection.style.display = 'none';
  document.querySelectorAll('.vibe-card').forEach(c => c.classList.remove('active'));
  styleSection.style.display = 'none';
  updateGradeBtn();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── Error toast ──
function showError(msg) {
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = '⚠ ' + msg;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 5000);
}

// ── Util ──
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// ── Start ──
init();
