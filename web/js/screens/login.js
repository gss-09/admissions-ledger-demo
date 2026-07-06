// =========================================================================
// LOGIN
// =========================================================================
function renderLogin() {
  root().innerHTML = `
    <div class="login fade-in">
      <div class="login-card glass">
        <div class="login-brand">
          <div class="brand-badge"><img src="logo.png" alt="logo" class="brand-logo" /></div>
          <div class="brand-eyebrow">Admissions</div>
          <h1>Admissions Ledger</h1>
          <div class="lead">JR Inter · 2026&ndash;27</div>
          <div class="brand-rule"></div>
          <p>Track every applicant through the funnel — reported, dropped, yet to
             arrive — across all AGMs, in one place.</p>
        </div>
        <div class="login-form">
          <div class="eyebrow">Welcome</div>
          <h2>Sign in to your account</h2>
          <label class="field" for="u">Username</label>
          <input id="u" class="input" placeholder="Username" autocomplete="off"
                 autocapitalize="off" autocorrect="off" spellcheck="false" name="al-user" />
          <label class="field" for="p">Password</label>
          ${pwInput('p', '••••••••')}
          <div id="err" class="error-msg" role="alert"></div>
          <button id="go" class="btn btn-primary btn-block">Sign in</button>
          <div class="demo-creds">
            <b>Demo sign-ins</b> (fictional data)<br/>
            Admin: <code>admin</code> / <code>Demo@1234</code> &nbsp;·&nbsp;
            Viewer: <code>viewer</code> / <code>Demo@1234</code>
          </div>
          <div id="loginHelp" class="infobox" style="display:none">
            ${icon('info', 16)}
            <div><b>Forgot your password?</b><br/>
              Contact your administrator — they can reset it for you.</div>
          </div>
          <div class="login-foot">${icon('shield', 14)}<span>Secured area — authorized staff only</span></div>
        </div>
      </div>
    </div>`;

  const doLogin = async () => {
    const btn = $('#go');
    if (btn.disabled) return;
    $('#err').textContent = '';
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span><span>Signing in…</span>`;
    try {
      const res = await api().login($('#u').value, $('#p').value);
      if (res.ok) { state.user = res.user; await enterApp(); return; }
      $('#err').textContent = res.error || 'Invalid username or password.';
      $('#p').value = '';
      const help = $('#loginHelp'); if (help) help.style.display = 'flex';
    } catch {
      $('#err').textContent = 'Could not reach the server — please try again in a moment.';
    }
    btn.disabled = false;
    btn.innerHTML = 'Sign in';
  };
  $('#go').onclick = doLogin;
  $('.login-card').addEventListener('keydown', (e) => { if (e.key === 'Enter') doLogin(); });
  $('#u').focus();
}
