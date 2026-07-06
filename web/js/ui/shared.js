// ---- Cross-screen render helpers ----------------------------------------
function pageHead(title, sub, eyebrow) {
  return `<div class="page-head">
    <div class="ph-text">
      ${eyebrow ? `<div class="eyebrow">${esc(eyebrow)}</div>` : ''}
      <h1>${esc(title)}</h1>${sub ? `<div class="sub">${esc(sub)}</div>` : ''}
    </div>
    <div class="stat-row" id="phStats"></div>
  </div>`;
}

// One stat chip. `gold` inverts it (the headline figure).
function statChip(value, label, gold = false) {
  return `<div class="stat${gold ? ' gold' : ''}"><div class="v">${value}</div>
    <div class="k">${esc(label)}</div></div>`;
}

// A dashboard stat card (clickable -> opens its module).
function statCard(ic, kind, num, lbl, go) {
  return `<div class="card-stat${go ? ' clickable' : ''}"${go ? ` data-go="${go}"` : ''}>
    <div class="chip chip-${kind}">${icon(ic, 22)}</div>
    <div><div class="num">${num}</div><div class="lbl">${esc(lbl)}</div></div>
  </div>`;
}

function emptyHtml(ic, title, hint) {
  return `<div class="empty"><div class="ec">${icon(ic, 26)}</div>
    <h4>${esc(title)}</h4><p>${esc(hint)}</p></div>`;
}

// Skeleton placeholders shown while a screen's data loads — shimmering "island"
// blocks that mirror the real layout, so a tab paints instantly instead of a lone
// spinner (mirrors the admin-app look). See .skel* in styles.css.
const _sk = (cls) => `<div class="skel ${cls}"></div>`;

// The body skeleton: a row of stat-chip placeholders + a card of list rows. Used on
// its own, or after a screen that renders its own page head (e.g. Home).
function skelBody(rows = 7) {
  const chip = `<div class="stat skel-statline">${_sk('skel-ln w50')}${_sk('skel-ln sm w70')}</div>`;
  const row = `<div class="skel-line-row">${_sk('skel-chip')}<div class="skel-bd">${_sk('skel-ln w60')}${_sk('skel-ln sm w40')}</div></div>`;
  return `<div class="stat-row skel-statrow">${chip + chip + chip}</div>
    <div class="panel skel-list">${row.repeat(rows)}</div>`;
}

// A whole-page skeleton: the tab's real title + the island body, painted the instant
// a tab opens so the previous screen never lingers. Falls back to the current module.
function skelPage(key) {
  key = key || state.module;
  const m = (state.menu || []).find((x) => x.key === key);
  return pageHead(m ? m.label : ' ', '', '') + skelBody();
}

// Plain shimmer bars, used for in-panel list placeholders (audit log, password history).
function skelRows(n = 4) {
  return Array.from({ length: n }, () => `<div class="skel-row"></div>`).join('');
}

// ---- per-city dashboard filter ------------------------------------------
// One control (shown only when 2+ cities are in scope — the "too cluttered"
// case a single-city/bound user never hits) that lets an org-wide viewer slice
// the analytics dashboards by city. The choice lives on `state.cityFilter`
// ('' = all) and persists across the AGMs / Execs / Averages / Income /
// Expenditure screens. AGMs are city-bound, so a city's slice is unambiguous.
function cityFilterHtml(cities) {
  const cs = (cities || []).filter(Boolean);
  if (cs.length < 2) return '';
  return `<label class="cityfilter">${icon('building', 14)}
    <select id="cityFilterSel" aria-label="Filter by city">
      <option value="">All cities</option>
      ${cs.map((c) => `<option value="${esc(c)}" ${state.cityFilter === c ? 'selected' : ''}>${esc(c)}</option>`).join('')}
    </select></label>`;
}
function wireCityFilter(rerender) {
  const sel = $('#cityFilterSel');
  if (sel) sel.onchange = () => { state.cityFilter = sel.value; rerender(); };
}
// Narrow a students array to `state.cityFilter` via a campus→city map ('' = all).
function studentsInCity(students, campusCity) {
  if (!state.cityFilter) return students || [];
  const m = campusCity || {};
  return (students || []).filter((s) => m[s.campus] === state.cityFilter);
}
