// ---- Toast notifications ------------------------------------------------
function toast(text, ok = true) {
  const t = document.createElement('div');
  t.className = 'toast';
  t.innerHTML = icon(ok ? 'check' : 'alert', 16) + `<span>${esc(text)}</span>`;
  if (!ok) t.querySelector('svg').style.color = 'var(--danger)';
  document.getElementById('toasts').appendChild(t);
  setTimeout(() => t.remove(), 2800);
}
