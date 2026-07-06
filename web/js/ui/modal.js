// =========================================================================
// MODAL DIALOGS — overlays appended to <body>; boot.js gives them a11y + Esc.
// =========================================================================
function modalPrompt({ title, label = 'Name', value = '', confirmText = 'Save' }) {
  return new Promise((res) => {
    const ov = document.createElement('div');
    ov.className = 'modal-overlay';
    ov.innerHTML = `<div class="modal compact">
      <h3>${esc(title)}</h3>
      <label class="field">${esc(label)}</label>
      <input class="input" id="mIn" value="${esc(value)}" />
      <div class="modal-actions">
        <button class="btn btn-ghost" id="mCancel">Cancel</button>
        <button class="btn btn-primary" id="mOk">${esc(confirmText)}</button>
      </div></div>`;
    document.body.appendChild(ov);
    const inp = ov.querySelector('#mIn');
    inp.focus(); inp.select();
    const done = (v) => { ov.remove(); res(v); };
    ov.querySelector('#mCancel').onclick = () => done(null);
    ov.querySelector('#mOk').onclick = () => done(inp.value.trim() || null);
    inp.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') done(inp.value.trim() || null);
      if (e.key === 'Escape') done(null);
    });
    ov.addEventListener('mousedown', (e) => { if (e.target === ov) done(null); });
  });
}

function modalConfirm({ title, message, confirmText = 'Delete', danger = true }) {
  return new Promise((res) => {
    const ov = document.createElement('div');
    ov.className = 'modal-overlay';
    ov.innerHTML = `<div class="modal compact">
      <h3>${esc(title)}</h3>
      <p class="modal-msg">${esc(message)}</p>
      <div class="modal-actions">
        <button class="btn btn-ghost" id="mCancel">Cancel</button>
        <button class="btn ${danger ? 'btn-danger' : 'btn-primary'}" id="mOk">${esc(confirmText)}</button>
      </div></div>`;
    document.body.appendChild(ov);
    const done = (v) => { ov.remove(); res(v); };
    ov.querySelector('#mCancel').onclick = () => done(false);
    ov.querySelector('#mOk').onclick = () => done(true);
    ov.addEventListener('mousedown', (e) => { if (e.target === ov) done(false); });
  });
}
