const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
window.setTimeout(() => document.querySelector('#app-splash')?.remove(), 2400);
const escapeHTML = (v) => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pretty = (v) => `<pre>${escapeHTML(JSON.stringify(v, null, 2))}</pre>`;
const badge = (s) => `<span class="badge ${String(s).toLowerCase().replace(/[^a-z0-9_]/g, '')}">${escapeHTML(String(s).replaceAll('_',' '))}</span>`;

let currentView = 'research', currentRun = null, currentTab = 'answer', pollTimer, config;
let cachedRuns = [];

const smartSuggestions = [
  'What jewellery revenue did Titan report for FY2023-24?',
  'How many Kalyan Jewellers showrooms existed at 31 March 2024?',
  'What amount did Zepto raise in June 2024 and from which investors?',
  'What is the history of the Mughal Empire and its major rulers?'
];

const titles = {
  research: [
    'Research',
    'Find the verified truth that you deserve',
    'An analyst finds the facts. An independent auditor checks the receipts. Every correction makes the next question better.'
  ],
  challenge: [
    'Challenge Lab',
    'Put the auditor to the test.',
    'Introduce controlled errors, inspect the evidence, and follow each correction through the loop.'
  ],
  memory: [
    'Feedback Memory',
    'Keep the lesson. Recheck the fact.',
    'Evidence-backed checking rules, carried into later research. Every lesson has an origin and a scope.'
  ],
  evaluation: [
    'Evaluation',
    'Does the next answer get better?',
    'The same held-out questions, with and without memory. Comparable budgets. Honest results.'
  ]
};

async function api(path, options) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail));
  return data;
}

function toast(message) {
  const el = $('#toast');
  if (!el) return;
  el.textContent = message;
  el.classList.remove('hidden');
  setTimeout(() => el.classList.add('hidden'), 7000);
}

function showView(view, keepRun = false) {
  currentView = view;
  $$('.view').forEach(el => el.classList.toggle('hidden', el.id !== `${view}-view`));
  $$('.nav-link').forEach(el => el.classList.toggle('active', el.dataset.view === view));
  
  if ($('#breadcrumb')) $('#breadcrumb').textContent = titles[view][0];
  if ($('#page-title')) $('#page-title').textContent = titles[view][1];
  if ($('#page-description')) $('#page-description').textContent = titles[view][2];
  
  if (!keepRun) {
    $('#run-panel').classList.add('hidden');
    clearTimeout(pollTimer);
    currentRun = null;
  }
  
  const emptyState = $('#empty-state');
  if (emptyState) emptyState.classList.toggle('hidden', Boolean(currentRun));
  
  if (view === 'memory') loadMemory().catch(e => toast(e.message));
  if (view === 'evaluation') loadEvaluation().catch(e => toast(e.message));
}

$$('[data-view]').forEach(el => el.addEventListener('click', () => showView(el.dataset.view)));

// Quick Challenge Trigger Buttons
const triggerChallengeAction = () => {
  showView('challenge');
  const startBtn = $('#challenge-start');
  if (startBtn) startBtn.click();
};

const tryChallengeBtn = $('#try-challenge');
if (tryChallengeBtn) tryChallengeBtn.addEventListener('click', triggerChallengeAction);

const headerDemoBtn = $('#header-demo-btn');
if (headerDemoBtn) headerDemoBtn.addEventListener('click', triggerChallengeAction);

const bottomDemoBtn = $('#bottom-demo-btn');
if (bottomDemoBtn) bottomDemoBtn.addEventListener('click', triggerChallengeAction);

const bottomScrollTopBtn = $('#bottom-scroll-top');
if (bottomScrollTopBtn) {
  bottomScrollTopBtn.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
    const q = $('#question');
    if (q) q.focus();
  });
}

// Category Cards 1-Click Fillers
$$('.category-card').forEach(card => {
  card.addEventListener('click', () => {
    const qInput = $('#question');
    if (!qInput) return;
    qInput.value = card.dataset.sample || '';
    if (card.dataset.start) $('#start-date').value = card.dataset.start;
    if (card.dataset.end) $('#end-date').value = card.dataset.end;
    showView('research');
    window.scrollTo({ top: 0, behavior: 'smooth' });
    qInput.focus();
  });
});

// View Latest Run Quick Action
const viewLatestRunBtn = $('#view-latest-run-btn');
if (viewLatestRunBtn) {
  viewLatestRunBtn.addEventListener('click', () => {
    if (cachedRuns.length) {
      openRun(cachedRuns[0].id).then(() => {
        $('#run-panel').scrollIntoView({ behavior: 'smooth' });
      });
    } else {
      toast('No previous runs found yet. Try running a research question or challenge demo!');
    }
  });
}

// History Drawer Functionality
const drawer = $('#history-drawer');
const openDrawer = () => {
  if (drawer) {
    drawer.classList.remove('hidden');
    drawer.setAttribute('aria-hidden', 'false');
  }
};
const closeDrawer = () => {
  if (drawer) {
    drawer.classList.add('hidden');
    drawer.setAttribute('aria-hidden', 'true');
  }
};

const historyToggleBtn = $('#history-drawer-toggle');
if (historyToggleBtn) historyToggleBtn.addEventListener('click', openDrawer);

const closeDrawerBtn = $('#close-history-drawer');
if (closeDrawerBtn) closeDrawerBtn.addEventListener('click', closeDrawer);

const drawerBackdrop = $('#history-drawer-backdrop');
if (drawerBackdrop) drawerBackdrop.addEventListener('click', closeDrawer);

// Drawer Search Filter
const drawerSearchInput = $('#drawer-search-input');
if (drawerSearchInput) {
  drawerSearchInput.addEventListener('input', (e) => {
    const term = e.target.value.toLowerCase().trim();
    renderHistoryItems(term);
  });
}

// Suggestion Chips
$$('[data-question]').forEach(el => el.addEventListener('click', () => {
  const qInput = $('#question');
  if (!qInput) return;
  qInput.value = el.dataset.question;
  if (el.dataset.question.includes('June 2024')) {
    $('#start-date').value = '2024-06-01';
    $('#end-date').value = '2024-06-30';
  } else if (el.dataset.question.includes('FY2023-24')) {
    $('#start-date').value = '2023-04-01';
    $('#end-date').value = '2024-03-31';
  } else {
    $('#start-date').value = '2024-04-01';
    $('#end-date').value = '2025-03-31';
  }
  qInput.focus();
}));

function renderSuggestions() {
  const input = $('#question'), box = $('#question-suggestions');
  if (!input || !box) return;
  const term = input.value.trim().toLowerCase();
  const matches = term.length < 2
    ? smartSuggestions.slice(0, 3)
    : smartSuggestions.filter(q => q.toLowerCase().includes(term)).slice(0, 3);
  if (!matches.length || document.activeElement !== input) {
    box.innerHTML = '';
    box.classList.remove('visible');
    return;
  }
  box.innerHTML = matches.map(q => `
    <button type="button" role="option" data-smart-question="${escapeHTML(q)}">
      <span class="suggestion-search">?</span>
      <span>${escapeHTML(q)}</span>
    </button>
  `).join('');
  box.classList.add('visible');
  box.querySelectorAll('[data-smart-question]').forEach(btn => btn.addEventListener('click', () => {
    input.value = btn.dataset.smartQuestion;
    box.classList.remove('visible');
    input.focus();
  }));
}

const qInput = $('#question');
if (qInput) {
  qInput.addEventListener('input', renderSuggestions);
  qInput.addEventListener('focus', renderSuggestions);
  qInput.addEventListener('blur', () => setTimeout(() => {
    const box = $('#question-suggestions');
    if (box) box.classList.remove('visible');
  }, 180));
}

// Research Form Submission
const researchForm = $('#research-form');
if (researchForm) {
  researchForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    if ($('#start-date').value > $('#end-date').value) {
      toast('The start date must precede the end date.');
      return;
    }
    const submitBtn = $('#research-submit');
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = `<span>Starting research…</span>`;
    }
    try {
      const result = await api('/api/runs', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          question: $('#question').value,
          start_date: $('#start-date').value,
          end_date: $('#end-date').value,
          memory_enabled: $('#memory-enabled').checked
        })
      });
      currentTab = 'answer';
      await openRun(result.id);
      $('#run-panel').scrollIntoView({ behavior: 'smooth' });
    } catch (e) {
      toast(e.message);
    } finally {
      if (submitBtn) {
        submitBtn.disabled = !config?.live_ready;
        submitBtn.innerHTML = `<span>Begin Research</span><span class="btn-arrow" aria-hidden="true">↗</span>`;
      }
    }
  });
}

// Online source search: Tavily search and page retrieval, no Gemini calls.
const sourceSearchBtn = $('#source-search-submit');
if (sourceSearchBtn) {
  sourceSearchBtn.addEventListener('click', async () => {
    if ($('#start-date').value > $('#end-date').value) { toast('The start date must precede the end date.'); return; }
    sourceSearchBtn.disabled = true;
    sourceSearchBtn.innerHTML = '<span>Searching sources…</span>';
    try {
      const result = await api('/api/source-search', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({
        question: $('#question').value, start_date: $('#start-date').value, end_date: $('#end-date').value,
        memory_enabled: $('#memory-enabled').checked
      })});
      currentTab = 'sources'; await openRun(result.id); $('#run-panel').scrollIntoView({behavior:'smooth'});
    } catch (e) { toast(e.message); }
    finally { sourceSearchBtn.disabled = false; sourceSearchBtn.innerHTML = '<span>Search sources only</span><span class="btn-arrow" aria-hidden="true">↗</span>'; }
  });
}

// Challenge Start
const challengeStart = $('#challenge-start');
if (challengeStart) {
  challengeStart.addEventListener('click', async () => {
    challengeStart.disabled = true;
    challengeStart.innerHTML = `<span>Running Challenge…</span>`;
    try {
      const result = await api('/api/challenge', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({use_model: $('#challenge-provider').value === 'model'})
      });
      currentTab = 'audit';
      await openRun(result.id);
      $('#run-panel').scrollIntoView({ behavior: 'smooth' });
    } catch (e) {
      toast(e.message);
    } finally {
      challengeStart.disabled = false;
      challengeStart.innerHTML = `<span>Run Challenge</span><span class="btn-arrow" aria-hidden="true">↗</span>`;
    }
  });
}

function renderHistoryItems(filterTerm = '') {
  const historyEl = $('#history');
  if (!historyEl) return;
  const filtered = filterTerm
    ? cachedRuns.filter(r => r.question.toLowerCase().includes(filterTerm) || r.mode.toLowerCase().includes(filterTerm))
    : cachedRuns;
    
  historyEl.innerHTML = filtered.length
    ? filtered.map(r => `
      <button class="history-item" data-run="${escapeHTML(r.id)}">
        <strong>${escapeHTML(r.question)}</strong>
        <span>${escapeHTML(r.mode.replaceAll('_', ' '))} · ${escapeHTML(r.status)}</span>
      </button>
    `).join('')
    : '<p class="muted small">No matching research runs found.</p>';
    
  $$('[data-run]').forEach(el => el.addEventListener('click', () => {
    currentTab = 'answer';
    closeDrawer();
    openRun(el.dataset.run)
      .then(() => $('#run-panel').scrollIntoView({ behavior: 'smooth' }))
      .catch(e => toast(e.message));
  }));
}

async function loadHistory() {
  try {
    const runs = await api('/api/runs');
    cachedRuns = runs;
    const historyCountEl = $('#history-count');
    if (historyCountEl) historyCountEl.textContent = runs.length;
    renderHistoryItems();
  } catch (e) {
    console.error('Failed to load history:', e);
  }
}

const refreshHistoryBtn = $('#refresh-history');
if (refreshHistoryBtn) {
  refreshHistoryBtn.addEventListener('click', () => loadHistory().catch(e => toast(e.message)));
}

async function openRun(id) {
  clearTimeout(pollTimer);
  const run = await api(`/api/runs/${encodeURIComponent(id)}`);
  currentRun = run;
  if (run.status === 'completed' && run.mode === 'live' && !run.final_claims?.length && run.sources?.length) currentTab = 'sources';
  showView(['live', 'source_search'].includes(run.mode) ? 'research' : 'challenge', true);
  renderRun();
  if (['running', 'queued'].includes(run.status)) {
    pollTimer = setTimeout(() => openRun(id).catch(e => toast(e.message)), 1200);
  } else {
    await loadHistory();
    await loadMemory(false);
  }
}

function renderRun() {
  const r = currentRun;
  if (!r) return;
  
  $('#run-panel').classList.remove('hidden');
  const emptyState = $('#empty-state');
  if (emptyState) emptyState.classList.add('hidden');
  
  $('#run-mode').textContent = `${r.mode === 'live' ? 'LIVE RESEARCH' : r.mode === 'source_search' ? 'ONLINE SOURCES ONLY' : 'CHALLENGE · SYNTHETIC DOCUMENTS'} / ${r.id}`;
  $('#run-question').textContent = r.question;
  $('#run-status').outerHTML = `<span id="run-status" class="badge ${escapeHTML(r.status)}">${escapeHTML(r.status)}</span>`;
  $('#export-run').href = `/api/runs/${encodeURIComponent(r.id)}/export`;
  
  $('#run-error').innerHTML = r.error ? `
    <div class="notice error run-error-card">
      <div class="error-heading">
        <span class="error-icon" style="font-weight:bold;margin-right:6px;">!</span>
        <div>
          <strong>${r.error.includes('429') ? 'Provider quota reached' : 'This run could not finish'}</strong>
          <p style="margin:4px 0 0;">${escapeHTML(r.error)}</p>
        </div>
      </div>
      ${r.error.includes('429') ? '<p class="error-help" style="margin-top:8px;">Your workspace is healthy, but the selected model is temporarily unavailable. Use <b>Challenge Lab · Fixture mode</b> for an offline demo, or retry after the provider quota resets.</p>' : ''}
    </div>
  ` : '';
  
  const score = r.challenge_score;
  $('#run-score').innerHTML = score ? `
    <div class="score-banner">
      <div class="notice" style="margin-bottom:8px;"><strong>${escapeHTML(r.evaluator || 'Evaluator')}</strong>: Score uses first-pass verdicts against labels fixed before the run.</div>
      <div class="score-grid">
        <div>
          <strong>${score.errors_caught} / ${score.introduced_errors}</strong>
          <span>Introduced errors caught</span>
        </div>
        <div>
          <strong>${score.correct_wrongly_flagged} / ${score.correct_controls}</strong>
          <span>Correct controls wrongly flagged</span>
        </div>
        <div>
          <strong>${score.unverifiable} / ${score.total_cases}</strong>
          <span>Unverifiable cases</span>
        </div>
      </div>
    </div>
  ` : '';
  
  if (score && r.memory_written && r.memory_written.length) {
    $('#run-score').innerHTML += `
      <div class="transfer-prompt-card">
        <div>
          <h3>Does the lesson transfer?</h3>
          <p class="muted">Apply it to Cedar Retail, a different synthetic company and period. Compare memory off and on.</p>
        </div>
        <button id="transfer-start" class="btn-demo-action">Test lesson transfer ↗</button>
      </div>
    `;
    const transferBtn = $('#transfer-start');
    if (transferBtn) {
      transferBtn.addEventListener('click', async () => {
        transferBtn.disabled = true;
        transferBtn.textContent = 'Testing transfer…';
        try {
          const result = await api('/api/transfer', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({parent_run_id: r.id})
          });
          await openRun(result.id);
        } catch (e) {
          toast(e.message);
          if ($('#transfer-start')) {
            $('#transfer-start').disabled = false;
            $('#transfer-start').textContent = 'Test lesson transfer ↗';
          }
        }
      });
    }
  }
  
  if (r.transfer_arms) {
    $('#run-score').innerHTML = `
      ${r.transfer_conclusion ? `<div class="notice" style="margin:12px 0;"><strong>Conclusion:</strong> ${escapeHTML(r.transfer_conclusion)}</div>` : ''}
      <div class="repair-grid transfer-grid">
        ${Object.entries(r.transfer_arms).map(([key, arm]) => `
          <div class="panel-card">
            <small class="muted"><strong>${escapeHTML(key.replaceAll('_', ' ').toUpperCase())}</strong></small>
            <p style="margin:8px 0;">${arm.claims.map(c => escapeHTML(c.text)).join('<br>')}</p>
            <p class="muted" style="font-size:12px;">${arm.evidence_gaps.map(escapeHTML).join('<br>')}</p>
            <span class="claim-meta">${arm.lessons_used.length} verified lessons used</span>
            <details style="margin-top:8px;"><summary style="cursor:pointer;font-size:12px;color:var(--primary);">Inspect plan and audits</summary>${pretty(arm)}</details>
          </div>
        `).join('')}
      </div>
    `;
  }
  
  const m = r.metrics || {};
  const tokens = (m.input_tokens ?? 0) + (m.output_tokens_including_thinking ?? 0);
  const metrics = [
    ['Elapsed', m.elapsed_seconds == null ? '—' : `${m.elapsed_seconds}s`],
    ['Tool calls', m.tool_calls ?? '.'],
    ['Tokens', m.elapsed_seconds == null ? '—' : tokens.toLocaleString()],
    ['Est. cost', m.estimated_cost_inr == null ? 'Unknown' : `₹${m.estimated_cost_inr.toFixed(3)}`],
    ['Sources', r.sources ? r.sources.length : 0]
  ];
  $('#run-metrics').innerHTML = metrics.map(([label, value]) => `
    <div class="metric">
      <small>${label}</small>
      <strong>${value}</strong>
    </div>
  `).join('');
  $('#run-metrics').title = m.cost_note || 'Metrics are recorded as the run completes.';
  
  renderTab();
}

$$('[data-tab]').forEach(el => el.addEventListener('click', () => {
  currentTab = el.dataset.tab;
  renderTab();
}));

function sourceLink(source) {
  if (!source) return '';
  let safe = false;
  try { safe = ['https:', 'http:'].includes(new URL(source.url).protocol); } catch {}
  return safe
    ? `<a class="cite" href="${escapeHTML(source.url)}" target="_blank" rel="noopener noreferrer">${escapeHTML(source.id)} ↗</a>`
    : `<span class="cite">${escapeHTML(source.id)} · fixture</span>`;
}

function renderTab() {
  if (!currentRun) return;
  const r = currentRun;
  
  $$('[data-tab]').forEach(el => {
    el.classList.toggle('selected', el.dataset.tab === currentTab);
    el.setAttribute('aria-selected', String(el.dataset.tab === currentTab));
  });
  
  const sources = Object.fromEntries((r.sources || []).map(s => [s.id, s]));
  const out = $('#run-content');
  if (!out) return;
  
  if (currentTab === 'answer') {
    const final = ['completed', 'failed', 'interrupted'].includes(r.status);
    const claims = final ? r.final_claims : r.claims;
    const audits = Object.fromEntries((final ? r.final_audits : r.audits).map(a => [a.claim_id, a]));
    out.innerHTML = `
      <div class="panel-card">
        ${claims && claims.length ? claims.map(c => `
          <div class="claim-row">
            <span class="claim-id">${escapeHTML(c.id)}</span>
            <div class="claim-body">
              <p>${escapeHTML(c.text)}</p>
              <div style="margin:4px 0;">${(c.source_ids || []).map(s => sourceLink(sources[s])).join('')}</div>
              <div class="claim-meta">${escapeHTML(c.entity)} · ${escapeHTML(c.metric)} · ${escapeHTML(c.period)}</div>
            </div>
            ${badge(audits[c.id]?.verdict || audits[c.id]?.verification_status || 'PENDING')}
          </div>
        `).join('') : `<p class="muted">${final ? 'No factual answer was retained. Inspect evidence gaps and corrections.' : 'Waiting for evidence. The plan and activity update as research proceeds.'}</p>`}
      </div>
      ${r.coverage ? `<div class="notice" style="margin-top:12px;"><strong>Coverage:</strong> ${escapeHTML(r.coverage)}</div>` : ''}
      ${r.evidence_gaps && r.evidence_gaps.length ? `
        <div class="panel-card" style="margin-top:14px;">
          <h3 style="margin-top:0;font-size:15px;">Evidence gaps</h3>
          <ul style="margin:0;padding-left:18px;">${r.evidence_gaps.map(g => `<li><p style="margin:4px 0;">${escapeHTML(g)}</p></li>`).join('')}</ul>
        </div>
      ` : ''}
    `;
  } else if (currentTab === 'plan') {
    out.innerHTML = r.plan ? `
      <div class="panel-card plan-grid">
        ${Object.entries(r.plan).map(([key, value]) => `
          <div>
            <h3>${escapeHTML(key.replaceAll('_', ' '))}</h3>
            ${Array.isArray(value) ? `<ul>${value.map(v => `<li>${escapeHTML(v)}</li>`).join('')}</ul>` : `<p>${escapeHTML(value)}</p>`}
          </div>
        `).join('')}
      </div>
    ` : '<p class="muted">The analyst has not produced a plan yet.</p>';
  } else if (currentTab === 'audit') {
    out.innerHTML = `<p class="muted small" style="margin-bottom:14px;">First-pass audit · primary sources fetched independently · exact quote membership checked in code</p>` + (r.audits && r.audits.length ? r.audits.map(a => {
      const c = (r.claims || []).find(c => c.id === a.claim_id);
      return `
        <div class="panel-card">
          <div class="claim-row">
            <span class="claim-id">${escapeHTML(a.claim_id)}</span>
            <div class="claim-body">
              <p>${escapeHTML(c?.text)}</p>
              <div class="claim-meta">${escapeHTML((a.checked_dimensions || []).join(' · '))}</div>
            </div>
            ${badge(a.verdict || a.verification_status)}
          </div>
          ${a.passage ? `<blockquote>${escapeHTML(a.passage)}</blockquote>` : ''}
          <p class="muted" style="margin:8px 0;font-size:13px;">${escapeHTML(a.explanation)}</p>
          <div class="claim-meta" style="margin-top:6px;">
            ${a.quote_verified ? '✓ Exact quote verified' : 'No verified source quote'} · ${escapeHTML(a.verification_status)} ${a.source_id ? `· ${sourceLink(sources[a.source_id])}` : ''}
          </div>
          <details style="margin-top:8px;"><summary style="cursor:pointer;font-size:12px;color:var(--primary);">Inspect independently fetched source records</summary>${pretty(a.sources)}</details>
        </div>
      `;
    }).join('') : '<p class="muted">Audits will appear after claims are drafted.</p>');
  } else if (currentTab === 'repairs') {
    out.innerHTML = (r.repairs && r.repairs.length) ? r.repairs.map(p => `
      <div class="panel-card">
        <div class="claim-meta" style="margin-bottom:8px;">${escapeHTML(p.claim_id)} · ONE REPAIR ATTEMPT</div>
        <div class="repair-grid">
          <div>
            <small>ORIGINAL CLAIM</small>
            <p style="margin:6px 0;">${escapeHTML(p.original.text)}</p>
            ${badge(p.first_verdict.verdict || p.first_verdict.verification_status)}
          </div>
          <div>
            <small>REVISION AFTER AUDIT</small>
            <p style="margin:6px 0;">${escapeHTML(p.revision?.text || 'No revision retained')}</p>
            ${badge(p.final_verdict?.verdict || p.final_verdict?.verification_status || 'WITHDRAWN OR FAILED')}
          </div>
        </div>
        <p class="muted" style="font-size:13px;margin:8px 0;">${escapeHTML(p.explanation)}</p>
        ${p.final_verdict?.passage ? `<blockquote>${escapeHTML(p.final_verdict.passage)}</blockquote>` : ''}
      </div>
    `).join('') : '<p class="muted">No correction attempts recorded.</p>';
  } else if (currentTab === 'sources') {
    out.innerHTML = (r.sources && r.sources.length) ? r.sources.map(s => `
      <div class="panel-card">
        <div class="claim-meta">${escapeHTML(s.id)} · Retrieved ${escapeHTML(s.retrieved_at)} · Published ${escapeHTML(s.published_at || 'unknown')}</div>
        <h3 style="margin:8px 0 4px;font-size:16px;">${escapeHTML(s.title)}</h3>
        <p class="source-url" style="margin:4px 0 8px;">${sourceLink(s)} <span class="muted" style="font-size:12px;">${escapeHTML(s.url)}</span></p>
        ${badge(s.status)}${s.truncated ? '<span class="badge" style="margin-left:6px;">TRUNCATED</span>' : ''}
        <details style="margin-top:8px;"><summary style="cursor:pointer;font-size:12px;color:var(--primary);">Read fetched primary document</summary><pre style="white-space:pre-wrap;font-size:12px;max-height:300px;overflow-y:auto;background:var(--bg-subtle);padding:12px;border-radius:8px;">${escapeHTML(s.text || s.error)}</pre></details>
      </div>
    `).join('') : '<p class="muted">No sources fetched yet.</p>';
  } else if (currentTab === 'activity') {
    out.innerHTML = `
      <div class="panel-card">
        ${(r.activity && r.activity.length) ? r.activity.map(a => `
          <div style="display:flex;align-items:flex-start;gap:12px;padding:8px 0;border-bottom:1px solid var(--border-subtle);">
            <time style="font-family:var(--font-mono);font-size:11px;color:var(--text-muted);min-width:65px;">${escapeHTML(new Date(a.at).toLocaleTimeString())}</time>
            <strong style="font-size:13px;min-width:110px;">${escapeHTML(a.kind.replaceAll('_', ' '))}</strong>
            <details style="flex:1;">
              <summary style="cursor:pointer;font-size:13px;color:var(--text-secondary);">${escapeHTML(a.stage || a.query || a.url || a.message || a.claim_id || 'Recorded event')}</summary>
              ${pretty(a)}
            </details>
          </div>
        `).join('') : '<p class="muted">No activity recorded yet.</p>'}
      </div>
    `;
  } else {
    out.innerHTML = `
      <h3 style="margin-top:0;font-size:16px;">Memory used in this plan</h3>
      ${lessonCards(r.memory_used || [])}
      <h3 style="margin-top:24px;font-size:16px;">Verified lessons from this run</h3>
      ${lessonCards(r.memory_written || [])}
    `;
  }
}

function lessonCards(lessons) {
  return lessons && lessons.length ? lessons.map(l => `
    <div class="panel-card" style="margin-bottom:12px;">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
        ${badge(l.verification_status)}
        <span class="claim-meta">${escapeHTML(l.mode.replaceAll('_', ' '))}</span>
      </div>
      <h3 style="margin:4px 0 8px;font-size:15px;">${escapeHTML(l.rule)}</h3>
      <p class="muted" style="font-size:13px;margin:0 0 6px;">Applies to: ${escapeHTML((l.scope || []).join(', '))}</p>
      <small style="color:var(--text-dim);">From run ${escapeHTML(l.triggering_run_id)} · ${(l.uses || []).length} later uses</small>
      <details style="margin-top:8px;"><summary style="cursor:pointer;font-size:12px;color:var(--primary);">View triggering evidence and uses</summary>${pretty({evidence: l.evidence, uses: l.uses})}</details>
    </div>
  `).join('') : '<div class="panel-card"><p class="muted">No verified lessons yet. A lesson is stored only after a correction passes re-audit.</p></div>';
}

async function loadMemory(render = true) {
  const lessons = await api('/api/memory');
  const countEl = $('#memory-count');
  if (countEl) countEl.textContent = lessons.length;
  if (render) {
    const listEl = $('#memory-list');
    if (listEl) listEl.innerHTML = lessonCards(lessons);
  }
}

async function loadEvaluation() {
  const {questions, results} = await api('/api/evaluation');
  const resultsEl = $('#evaluation-results');
  if (resultsEl) {
    resultsEl.innerHTML = results ? `
      <div class="panel-card">
        ${badge(results.status || 'recorded')}
        <p style="margin:10px 0;">${escapeHTML(results.conclusion)}</p>
        ${results.blockers ? `<p class="muted">Missing configuration: ${escapeHTML(results.blockers.join(', '))}</p>` : ''}
        <details><summary style="cursor:pointer;color:var(--primary);font-size:13px;">Inspect evaluation report</summary>${pretty(results)}</details>
      </div>
    ` : `
      <div class="panel-card">
        <h3 style="margin-top:0;">No live comparison recorded yet.</h3>
        <p class="muted">Run the evaluation command after configuring the providers. Offline fixture scores do not establish memory improvement.</p>
        <pre style="background:var(--bg-subtle);padding:12px;border-radius:8px;font-family:var(--font-mono);font-size:12px;">.\\.venv\\Scripts\\python.exe -m evidenceloop.evaluation --mode live</pre>
      </div>
    `;
  }
  
  const suiteEl = $('#question-suite');
  if (suiteEl) {
    suiteEl.innerHTML = `
      <table style="width:100%;border-collapse:collapse;margin-top:12px;font-size:13px;">
        <thead>
          <tr style="text-align:left;border-bottom:2px solid var(--border-subtle);color:var(--text-dim);">
            <th style="padding:10px 8px;">ID</th>
            <th style="padding:10px 8px;">Question &amp; frozen period</th>
            <th style="padding:10px 8px;">Split</th>
          </tr>
        </thead>
        <tbody>
          ${questions.map(q => `
            <tr style="border-bottom:1px solid var(--border-subtle);">
              <td style="padding:10px 8px;font-family:var(--font-mono);">${q.id}</td>
              <td style="padding:10px 8px;">
                <div style="font-weight:600;">${escapeHTML(q.question)}</div>
                <div class="claim-meta" style="margin-top:4px;">${q.start_date} → ${q.end_date} · Difficulty ${q.difficulty}/8</div>
              </td>
              <td style="padding:10px 8px;">${badge(q.split)}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  }
}

function initTheme() {
  const saved = localStorage.getItem('evidenceloop_theme') || 'light';
  document.documentElement.setAttribute('data-theme', saved);
  const btn = $('#theme-toggle');
  if (btn) {
    btn.innerHTML = saved === 'dark' ? '☼' : '☾';
    btn.setAttribute('title', saved === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode');
    btn.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme') || 'light';
      const next = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('evidenceloop_theme', next);
      btn.innerHTML = next === 'dark' ? '☼' : '☾';
      btn.setAttribute('title', next === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode');
    });
  }
}

async function init() {
  initTheme();
  config = await api('/api/config');
  const notice = $('#config-notice');
  if (notice) {
    notice.className = config.live_ready ? 'notice notice-ready config-ready-hidden' : 'notice error';
    notice.innerHTML = config.live_ready
      ? '<span class="notice-icon" aria-hidden="true">✓</span><span>Workspace ready · Every result is traceable to its research plan, sources, and audit receipts.</span>'
      : '<span class="notice-icon" aria-hidden="true">!</span><span>Live research setup requires API keys. The offline Challenge Lab is ready to use immediately.</span>';
  }
  const submitBtn = $('#research-submit');
  if (submitBtn) submitBtn.disabled = !config.live_ready;
  
  const modelOption = $('#challenge-provider option[value="model"]');
  if (modelOption) modelOption.disabled = !config.model_ready;

  const modelPill = $('#model-pill');
  if (modelPill && config.model) {
    modelPill.textContent = config.model;
  }
  
  await Promise.all([loadHistory(), loadMemory(false)]);

  // If there are existing runs, auto-open the latest completed run so the user immediately sees live data!
  if (cachedRuns.length > 0) {
    const latest = cachedRuns[0];
    openRun(latest.id).catch(console.error);
  }
}

init().catch(e => {
  console.error('Initialization error:', e);
  toast(`Could not connect to the local server: ${e.message}`);
});
