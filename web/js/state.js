// ---- App state ----------------------------------------------------------
const state = {
  user: null,    // {id, username, full_name, role, role_label}
  menu: [],      // [{key, label, icon}] the role may see
  module: null,  // current screen key
  roles: [],     // [{key, label}] assignable roles (admin excluded)
  perms: {},     // module -> 'view' | 'edit' (admin -> all 'edit')
  cityFilter: '', // per-city dashboard slice ('' = all); shared across analytics screens
};

// Can the current user EDIT (not just view) the given module/page?
const canEdit = (module) =>
  (state.user && state.user.role === 'admin') || state.perms[module] === 'edit';

// Can the current user VIEW the given module/page? (admin sees all; otherwise the
// module must be present in their perms map — value 'view' or 'edit').
const canView = (module) =>
  (state.user && state.user.role === 'admin') || !!state.perms[module];

// Field-tier mirrors of the server gate (cosmetic — the payload is already stripped
// server-side, this just avoids rendering empty rows/columns). MONEY: any fee-bearing
// tab earns the final_fee field; CONTACT: only the Students directory shows phones etc.
const canMoney = () =>
  canView('students') || canView('income') || canView('averages') || canView('expenditure');
const canContact = () => canView('students');
