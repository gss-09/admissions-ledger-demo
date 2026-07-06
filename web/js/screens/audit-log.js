// =========================================================================
// ACTIVITY LOG (admin): edits and sign-ins, each its own tab.
// =========================================================================
const LOG = { tab: 'edit', data: null };

async function buildAuditLog() {
  $('#main').innerHTML = pageHead('Activity Log', 'Who changed what, and who signed in.', 'Audit') +
    `<div class="seg-tabs" id="logTabs">
       <button class="seg-tab" data-lt="edit">Changes</button>
       <button class="seg-tab" data-lt="login">Sign-ins</button>
     </div>
     <div class="panel"><div id="logBody">${skelRows(6)}</div></div>`;
  LOG.data = await api().activity_log();
  $('#logTabs').querySelectorAll('[data-lt]').forEach((b) =>
    b.onclick = () => { LOG.tab = b.dataset.lt; renderLog(); });
  renderLog();
}

function renderLog() {
  $('#logTabs').querySelectorAll('[data-lt]').forEach((b) =>
    b.classList.toggle('active', b.dataset.lt === LOG.tab));
  const events = (LOG.data && LOG.data[LOG.tab]) || [];
  if (!events.length) {
    $('#logBody').innerHTML = emptyHtml('history', 'Nothing yet', 'Activity will show up here.');
    return;
  }
  $('#logBody').innerHTML = events.map((e) => `
    <div class="log-row">
      <div class="chip chip-${e.failed ? 'danger' : 'accent'}">${icon(e.category === 'login' ? 'lock' : 'edit', 15)}</div>
      <div class="acct-id">
        <div class="nm">${esc(e.action)}${e.detail ? ` <span class="muted">— ${esc(e.detail)}</span>` : ''}</div>
        <div class="sub muted">${esc(e.who)}${e.username ? ` @${esc(e.username)}` : ''} · ${esc(e.when)}</div>
      </div>
      <div class="spacer"></div>
      ${e.can_delete ? `<button class="iconbtn sm" data-del-src="${e.src}" data-del-ref="${e.ref}" title="Delete entry">${icon('trash', 15)}</button>` : ''}
    </div>`).join('');
  $('#logBody').querySelectorAll('[data-del-ref]').forEach((b) =>
    b.onclick = async () => {
      const r = await api().log_delete(b.dataset.delSrc, parseInt(b.dataset.delRef));
      if (r.ok) { LOG.data = await api().activity_log(); renderLog(); }
      else toast(r.message || 'Could not delete', false);
    });
}
