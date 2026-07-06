// =========================================================================
// HOME — "The Admissions Briefing"
// One screen that synthesises the whole student payload into things you can
// read at a glance and act on: the funnel shape, a top-execs leaderboard, a
// follow-up action queue (deep-links into a pre-filtered Students view via
// ST.preset), a campus split and the latest reported students.
// Everything is computed client-side from api().students() — the same payload
// the directory/AGMs/Execs screens already load — so there is no extra
// endpoint and the dashboard is identical for every role that can see it.
// =========================================================================

// Funnel order (best → worst) + a monochrome shade per stage.
const FUNNEL_STAGES = [
  { key: 'REPORTED', label: 'Reported', cls: 'fs-reported' },
  { key: 'SETTLED', label: 'Settled', cls: 'fs-settled' },
  { key: 'YET TO ARRIVE', label: 'Yet to arrive', cls: 'fs-coming' },
  { key: 'NOT LIFTING', label: 'Not lifting', cls: 'fs-notlift' },
  { key: 'DROPPED', label: 'Dropped', cls: 'fs-dropped' },
];

async function renderHome() {
  const u = state.user;
  const head = pageHead(`Welcome, ${u.full_name.split(' ')[0]}`,
    `You're signed in as ${u.role_label}.`, 'Dashboard');
  $('#main').innerHTML = head + skelBody();

  // The dashboard rides on the same view access as the Students screen. If the
  // role can't read students, fall back to the same friendly empty state.
  let data = null;
  try { data = await api().students(); } catch (e) { data = null; }
  const all = data && data.students ? data.students : null;

  if (!all || !all.length) {
    $('#main').innerHTML = head + emptyHtml('home', 'Nothing to show yet',
      'Admissions will appear here as they come in.');
    return;
  }

  $('#main').innerHTML = head + buildBriefing(all);
  wireBriefing();
}

// ---- aggregation --------------------------------------------------------
function briefingStats(all) {
  const total = all.length;
  const by = {};
  FUNNEL_STAGES.forEach((s) => { by[s.key] = 0; });
  let reportedIncome = 0;
  const execs = new Map(), campuses = new Map();

  all.forEach((r) => {
    const st = r.status_category || 'YET TO ARRIVE';
    if (by[st] == null) by[st] = 0;
    by[st]++;

    // Total reported income = booked fee of every student who has actually
    // reported (blank fees just count as 0).
    if (st === 'REPORTED') {
      const fee = Number(r.final_fee);
      if (Number.isFinite(fee)) reportedIncome += fee;
    }

    const a = (r.agm || '').trim();
    const ex = (r.marketing_exec || '').trim();
    // Execs leaderboard: only real sub-execs. Skip an AGM acting as their own
    // exec (marketing_exec === agm) — their primary job is managing recruitment,
    // not personally bringing admissions.
    if (ex && ex !== a) {
      const m = execs.get(ex) || { name: ex, total: 0, reported: 0 };
      m.total++; if (st === 'REPORTED') m.reported++; execs.set(ex, m);
    }

    const c = (r.campus || '').trim();
    if (c) campuses.set(c, (campuses.get(c) || 0) + 1);
  });

  const reported = by['REPORTED'] || 0;
  const execLeaders = [...execs.values()]
    .map((m) => ({ ...m, conv: m.total ? Math.round(m.reported / m.total * 100) : 0 }))
    .sort((x, y) => y.reported - x.reported || y.total - x.total)
    .slice(0, 5);

  return {
    total, by, reported, reportedIncome,
    conversion: total ? Math.round(reported / total * 100) : 0,
    execLeaders,
    campuses: [...campuses.entries()].map(([name, n]) => ({ name, n })).sort((a, b) => b.n - a.n),
  };
}

// ---- markup -------------------------------------------------------------
function buildBriefing(all) {
  const s = briefingStats(all);
  return heroBlock(s) +
    `<div class="dash-grid">
       <div class="dash-col">
         ${leaderboardPanel('Top execs · by reported', s.execLeaders, 'exec')}
         ${latestPanel(all)}
       </div>
       <div class="dash-col">${actionPanel(s)}${campusPanel(s)}</div>
     </div>`;
}

function heroBlock(s) {
  const segs = FUNNEL_STAGES.filter((f) => s.by[f.key] > 0).map((f) => {
    const pct = (s.by[f.key] / s.total * 100);
    return `<div class="funnel-seg ${f.cls}" style="width:${pct}%" title="${esc(f.label)}: ${s.by[f.key]}"></div>`;
  }).join('');
  const legend = FUNNEL_STAGES.map((f) => {
    const pct = s.total ? Math.round(s.by[f.key] / s.total * 100) : 0;
    return `<div class="fl-item"><span class="fl-sw ${f.cls}"></span>
      <span class="fl-k">${esc(f.label)}</span>
      <span class="fl-v mono">${s.by[f.key]}<small>${pct}%</small></span></div>`;
  }).join('');
  // Reported income is shown only to users who can view the Income tab — the
  // server also withholds final_fee from the payload unless they hold a money tab,
  // so this just keeps the hero from rendering an empty figure.
  const incomeFig = canView('income')
    ? `<div class="hero-fig"><div class="hf-v mono">${fmtLk(s.reportedIncome)}</div><div class="hf-k">Reported income</div></div>`
    : '';
  return `<div class="dash-hero">
    <div class="hero-figs">
      <div class="hero-fig"><div class="hf-v mono">${s.total}</div><div class="hf-k">Total admissions</div></div>
      <div class="hero-fig"><div class="hf-v mono">${s.reported}</div><div class="hf-k">Reported</div></div>
      ${incomeFig}
      <div class="hero-fig"><div class="hf-v mono">${s.conversion}<small>%</small></div><div class="hf-k">Conversion</div></div>
    </div>
    <div class="funnel-bar">${segs}</div>
    <div class="funnel-legend">${legend}</div>
  </div>`;
}

// kind is 'agm' or 'exec' — drives the deep-link on click (data-kind).
function leaderboardPanel(title, leaders, kind) {
  if (!leaders.length) return '';
  const max = leaders[0].reported || 1;
  const rows = leaders.map((m, i) => `
    <button class="lead-row" data-kind="${kind}" data-name="${esc(m.name)}">
      <span class="lead-rank mono">${i + 1}</span>
      <span class="lead-name">${esc(m.name)}</span>
      <span class="lead-bar"><span class="lead-fill" style="width:${Math.round(m.reported / max * 100)}%"></span></span>
      <span class="lead-fig"><b class="mono">${m.reported}</b><small>reported</small></span>
      <span class="lead-fig"><b class="mono">${m.conv}%</b><small>conv</small></span>
    </button>`).join('');
  return `<div class="panel">
    <div class="eyebrow">${esc(title)}</div>
    <div class="lead-list">${rows}</div>
  </div>`;
}

function actionPanel(s) {
  const items = [];
  if ((s.by['NOT LIFTING'] || 0) > 0)
    items.push({ ic: 'alert', n: s.by['NOT LIFTING'], label: 'Not lifting — follow up', field: 'status', value: 'NOT LIFTING' });
  if ((s.by['YET TO ARRIVE'] || 0) > 0)
    items.push({ ic: 'history', n: s.by['YET TO ARRIVE'], label: 'Yet to arrive — awaiting', field: 'status', value: 'YET TO ARRIVE' });

  const body = items.length
    ? items.map((it) => `
      <button class="act-item" data-field="${esc(it.field)}" data-value="${esc(it.value)}">
        <span class="act-ic">${icon(it.ic, 16)}</span>
        <span class="act-cnt mono">${it.n}</span>
        <span class="act-txt">${esc(it.label)}</span>
        ${icon('chevron', 16)}
      </button>`).join('')
    : `<p class="muted-note">Nothing needs attention.</p>`;
  return `<div class="panel">
    <div class="eyebrow">Needs attention</div>
    <div class="actq">${body}</div>
  </div>`;
}

function campusPanel(s) {
  if (!s.campuses.length) return '';
  const max = s.campuses[0].n || 1;
  const rows = s.campuses.map((c) => `
    <div class="camp-row">
      <span class="camp-name">${esc(c.name)}</span>
      <span class="camp-bar"><span class="camp-fill" style="width:${Math.round(c.n / max * 100)}%"></span></span>
      <span class="camp-n mono">${c.n}</span>
    </div>`).join('');
  return `<div class="panel">
    <div class="eyebrow">Campus split</div>
    <div class="camp-list">${rows}</div>
  </div>`;
}

function latestPanel(all) {
  const recent = all
    .filter((r) => r.status_category === 'REPORTED' && r.reported_date)
    .sort((a, b) => String(b.reported_date).localeCompare(String(a.reported_date)))
    .slice(0, 6);
  if (!recent.length) return '';
  const rows = recent.map((r) => `
    <button class="latest-row" data-id="${r.id}">
      <span class="lt-id">
        <span class="lt-name">${esc(r.student_name)}</span>
        <span class="lt-sub">${esc(r.campus || '—')} · ${esc(r.agm || '—')}</span>
      </span>
      <span class="lt-date mono">${esc(fmtDate(r.reported_date))}</span>
      ${stPill(r.status_category)}
    </button>`).join('');
  return `<div class="panel">
    <div class="eyebrow">Latest reported</div>
    <div class="latest-list">${rows}</div>
  </div>`;
}

// ---- interactions -------------------------------------------------------
// All deep-links route through ST.preset, a one-shot filter the Students
// directory applies (and clears) on its next render.
function gotoStudents(field, value) {
  ST.preset = { field, value };
  openModule('students');
}
function wireBriefing() {
  $('#main').querySelectorAll('.lead-row').forEach((el) =>
    el.onclick = () => {
      // AGM rows deep-link to a filtered directory; exec rows open the Execs
      // module (the directory has no marketing-exec filter) on that exec.
      if (el.dataset.kind === 'exec') { ST.preset = { field: 'exec', value: el.dataset.name }; openModule('execs'); }
      else gotoStudents('agm', el.dataset.name);
    });
  $('#main').querySelectorAll('.act-item').forEach((el) =>
    el.onclick = () => gotoStudents(el.dataset.field, el.dataset.value));
  $('#main').querySelectorAll('.latest-row').forEach((el) =>
    el.onclick = () => openStudent(el.dataset.id));
}
