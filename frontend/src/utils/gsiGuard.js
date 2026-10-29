/**
 * Controlled Google Identity Services (GIS) Initializer Guard.
 *
 * Prevents redundant calls to `google.accounts.id.initialize()` during React
 * component remounts, state re-renders, and React StrictMode cycles, which
 * trigger the GIS browser console warning:
 * "google.accounts.id.initialize() is called multiple times."
 */

let activeClientKey = null;

export function installGsiGuard() {
  if (typeof window === "undefined" || window.__palp_gsi_guard_installed) {
    return;
  }
  window.__palp_gsi_guard_installed = true;

  const patchIdObject = (accountsId) => {
    if (!accountsId || accountsId.__palp_patched) return;
    accountsId.__palp_patched = true;

    const originalInit = accountsId.initialize.bind(accountsId);
    accountsId.initialize = (config) => {
      const key = `${config?.client_id || ""}_${Boolean(config?.callback)}`;
      if (activeClientKey === key) {
        return;
      }
      activeClientKey = key;
      return originalInit(config);
    };
  };

  if (window.google?.accounts?.id) {
    patchIdObject(window.google.accounts.id);
  } else {
    let currentGoogle = window.google;
    Object.defineProperty(window, "google", {
      configurable: true,
      enumerable: true,
      get() {
        return currentGoogle;
      },
      set(val) {
        currentGoogle = val;
        if (val?.accounts?.id) {
          patchIdObject(val.accounts.id);
        }
      },
    });
  }
}
