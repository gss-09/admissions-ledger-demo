// ---- DOM helpers --------------------------------------------------------
const root = () => document.getElementById('root');
const $ = (sel, el = document) => el.querySelector(sel);
const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];
const esc = (s) => (s == null ? '' : String(s)).replace(/[&<>"'/]/g,
  (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;', '/': '&#47;' }[c]));
const initials = (name) =>
  (name || '?').split(' ').slice(0, 2).map((p) => p[0] || '').join('').toUpperCase();

// A password field with a show/hide eye toggle. CSP blocks inline handlers, so the
// toggle is wired by ONE delegated document listener below (CSP-safe, survives re-renders).
function pwInput(id, ph = '') {
  return `<div class="pw-wrap">
    <input class="input" id="${id}" type="password" placeholder="${esc(ph)}"
      autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false" />
    <button type="button" class="pw-toggle" data-show="0" tabindex="-1"
      title="Show password" aria-label="Show password">${icon('eye', 16)}</button>
  </div>`;
}

document.addEventListener('click', (e) => {
  const t = e.target.closest('.pw-toggle');
  if (!t) return;
  const inp = t.parentElement.querySelector('input');
  if (!inp) return;
  const showing = t.dataset.show === '1';
  inp.type = showing ? 'password' : 'text';
  t.dataset.show = showing ? '0' : '1';
  t.title = showing ? 'Show password' : 'Hide password';
  t.setAttribute('aria-label', t.title);
  t.innerHTML = icon(showing ? 'eye' : 'eyeoff', 16);
});
