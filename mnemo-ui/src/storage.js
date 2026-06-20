export function safeStorageGet(key, fallback = '') {
  try {
    return localStorage.getItem(key) || fallback;
  } catch {
    return fallback;
  }
}

export function safeStorageSet(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // Storage may be unavailable in private or locked-down browser contexts.
  }
}

export function safeSessionStorageGet(key, fallback = '') {
  try {
    return sessionStorage.getItem(key) || fallback;
  } catch {
    return fallback;
  }
}

export function safeSessionStorageSet(key, value) {
  try {
    sessionStorage.setItem(key, value);
  } catch {
    // Session storage may be unavailable in locked-down browser contexts.
  }
}
