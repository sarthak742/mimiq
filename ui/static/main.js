/* FILE: ui/static/main.js */

const API_BASE = '';

/* ─── Polling ─── */
function pollBrainStatus() {
  fetch(`${API_BASE}/api/brain/status`)
    .then(r => r.json())
    .then(data => {
      const badge = document.getElementById('amd-badge');
      const dot = badge.querySelector('.dot');
      const text = badge.querySelector('.badge-text');
      const provider = data.active_provider || 'unknown';
      const model = data.active_model || 'unknown';
      text.textContent = `${provider} · ${model}`;
      dot.className = 'dot';
      if (provider === 'PUTER' || provider.includes('PUTER')) {
        dot.classList.add('amber');
      } else if (data.status === 'offline' || provider.includes('offline')) {
        dot.classList.add('red');
      }
    })
    .catch(() => {
      const badge = document.getElementById('amd-badge');
      badge.querySelector('.badge-text').textContent = 'AMD — offline · unknown';
      badge.querySelector('.dot').classList.add('red');
    });
}

function pollHitlState() {
  fetch(`${API_BASE}/api/hitl/state`)
    .then(r => r.json())
    .then(state => {
      const panel = document.getElementById('hitl-panel');
      if (state.pending) {
        panel.classList.add('visible');
        document.getElementById('hitl-message').textContent = state.message || 'Action pending approval...';
      } else {
        panel.classList.remove('visible');
      }
    })
    .catch(() => {
      document.getElementById('hitl-panel').classList.remove('visible');
    });
}

/* ─── Compose ─── */
async function handleCompose() {
  const btn = document.getElementById('compose-btn');
  const spinner = document.getElementById('compose-spinner');
  const goal = document.getElementById('goal-input').value.trim();
  if (!goal) { alert('Enter a goal first.'); return; }

  btn.disabled = true;
  spinner.classList.remove('hidden');

  try {
    const resp = await fetch(`${API_BASE}/api/compose`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        goal,
        manifest_1: { phases: [] },
        manifest_2: null,
      }),
    });
    const data = await resp.json();
    if (data.error) {
      alert(data.error);
      return;
    }
    renderPhaseCards(data.final_manifest.phases || []);
    document.getElementById('execute-section').classList.remove('hidden');
  } catch (e) {
    alert('Compose failed: ' + e.message);
  } finally {
    btn.disabled = false;
    spinner.classList.add('hidden');
  }
}

/* ─── HITL ─── */
function handleHitlDecide(decision) {
  fetch(`${API_BASE}/api/hitl/decide`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision }),
  }).then(() => pollHitlState());
}

/* ─── Rendering ─── */
function renderPhaseCards(phases) {
  const grid = document.getElementById('phase-grid');
  grid.innerHTML = '';
  if (!phases.length) {
    grid.innerHTML = '<p style="color:var(--text-2)">No phases returned.</p>';
    return;
  }
  phases.forEach(p => {
    const conf = Math.round((p.confidence_score || 0) * 100);
    const card = document.createElement('div');
    card.className = 'phase-card';
    card.innerHTML = `
      <div class="header-row">
        <span class="phase-id">Phase ${p.phase_id}</span>
        <span class="timecode">${p.timecode || '00:00:00'}</span>
      </div>
      <div class="phase-title">${p.description || 'Untitled'}</div>
      <div>
        <span class="pill">${p.phase_mode || 'unknown'}</span>
        <span class="pill">${p.expected_focus || 'unknown'}</span>
      </div>
      <div class="confidence-bar"><div class="fill" style="width:${conf}%"></div></div>
    `;
    grid.appendChild(card);
  });
}

function handleVideoUpload(inputEl, labelEl) {
  inputEl.addEventListener('change', () => {
    const file = inputEl.files[0];
    if (file) labelEl.textContent = file.name;
  });
}

function checkReport() {
  fetch(`${API_BASE}/api/report`)
    .then(r => {
      const link = document.getElementById('report-link');
      if (r.status === 200) link.classList.remove('hidden');
      else link.classList.add('hidden');
    })
    .catch(() => document.getElementById('report-link').classList.add('hidden'));
}

/* ─── Init ─── */
document.addEventListener('DOMContentLoaded', () => {
  pollBrainStatus();
  setInterval(pollBrainStatus, 10000);
  setInterval(pollHitlState, 2000);
  setInterval(checkReport, 10000);
  checkReport();

  document.getElementById('compose-btn').addEventListener('click', handleCompose);
  document.getElementById('btn-approve').addEventListener('click', () => handleHitlDecide('APPROVE'));
  document.getElementById('btn-reject').addEventListener('click', () => handleHitlDecide('REJECT'));
  document.getElementById('btn-skip').addEventListener('click', () => handleHitlDecide('SKIP'));

  handleVideoUpload(
    document.getElementById('video-input'),
    document.getElementById('video-label')
  );
  handleVideoUpload(
    document.getElementById('video2-input'),
    document.getElementById('video2-label')
  );
});
