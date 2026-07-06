// ---- Backend bridge -----------------------------------------------------
// The UI talks to the Flask backend over HTTP. `api().anyMethod(a, b)` posts
// {args:[a,b]} to /api/anyMethod and resolves with the JSON result. Requests are
// same-origin, so the signed login cookie is sent automatically.
const api = () => new Proxy({}, {
  get(_t, method) {
    return (...args) =>
      fetch('/api/' + method, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ args }),
      }).then((r) => {
        if (r.status === 401) {
          // Signed out or session revoked: a full reload lands on the login
          // screen via boot(). Return a never-settling promise so the calling
          // screen doesn't render against a dead session meanwhile.
          location.reload();
          return new Promise(() => {});
        }
        if (!r.ok) throw new Error('API ' + method + ' failed (' + r.status + ')');
        return r.json();
      });
  },
});
