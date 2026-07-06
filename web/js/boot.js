// =========================================================================
// BOOT
// =========================================================================

// Turn off browser autocomplete/autofill on every input, now and later.
function killAutofill(node) {
  if (!node || node.nodeType !== 1) return;
  const off = (el) => {
    el.setAttribute('autocomplete', 'off');
    el.setAttribute('autocapitalize', 'off');
    el.setAttribute('autocorrect', 'off');
    el.setAttribute('spellcheck', 'false');
  };
  if (node.matches && node.matches('input, textarea')) off(node);
  node.querySelectorAll && node.querySelectorAll('input, textarea').forEach(off);
}

// Every modal is a div.modal-overlay appended to <body>; one central hook gives
// them dialog semantics and returns focus when the last one closes.
let modalReturnFocus = null;
function decorateModal(node) {
  if (node.nodeType !== 1 || !node.classList.contains('modal-overlay')) return;
  modalReturnFocus = document.activeElement;
  const m = node.querySelector('.modal');
  if (!m) return;
  m.setAttribute('role', 'dialog');
  m.setAttribute('aria-modal', 'true');
  const h = m.querySelector('h3');
  if (h && !m.hasAttribute('aria-label')) m.setAttribute('aria-label', h.textContent);
}

async function boot() {
  killAutofill(document.body);
  new MutationObserver((muts) => muts.forEach((m) => {
    m.addedNodes.forEach((n) => { killAutofill(n); decorateModal(n); });
    m.removedNodes.forEach((n) => {
      if (n.nodeType === 1 && n.classList.contains('modal-overlay')
          && !document.querySelector('.modal-overlay') && modalReturnFocus) {
        if (modalReturnFocus.focus) modalReturnFocus.focus();
        modalReturnFocus = null;
      }
    });
  })).observe(document.body, { childList: true, subtree: true });

  // Escape closes the top-most popup, so nothing can get "stuck".
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    const overlays = document.querySelectorAll('.modal-overlay');
    if (overlays.length) overlays[overlays.length - 1].remove();
  });
  // Keep Tab inside the top-most dialog (focus trap).
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Tab') return;
    const overlays = document.querySelectorAll('.modal-overlay');
    if (!overlays.length) return;
    const ov = overlays[overlays.length - 1];
    const focusables = Array.from(ov.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    )).filter((el) => el.offsetParent !== null && !el.disabled);
    if (!focusables.length) return;
    const first = focusables[0], last = focusables[focusables.length - 1];
    if (!ov.contains(document.activeElement)) { first.focus(); e.preventDefault(); }
    else if (e.shiftKey && document.activeElement === first) { last.focus(); e.preventDefault(); }
    else if (!e.shiftKey && document.activeElement === last) { first.focus(); e.preventDefault(); }
  });

  // Stay logged in: bootstrap() returns the user AND menu/roles/perms in one
  // round trip, so a logged-in reopen renders after a single request.
  try {
    const b = await api().bootstrap();
    if (b && b.user) { state.user = b.user; await enterApp(b); return; }
  } catch { /* fall through to login */ }
  renderLogin();
}
if (document.readyState !== 'loading') boot();
else window.addEventListener('DOMContentLoaded', boot);
