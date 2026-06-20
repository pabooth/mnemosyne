import { DEFAULT_API_URL } from './config.js';
import { normalizeApiUrl } from './security.js';
import { safeSessionStorageGet, safeStorageGet } from './storage.js';

export function createInitialState() {
  return {
    content: '',
    title: '',
    owner: '',
    contentType: 'auto',
    subLabel: '',
    mode: 'idle',
    resultType: null,
    pendingIngest: false,
    loadingStep: 0,
    result: null,
    error: null,
    contentError: null,
    showSettings: false,
    showHistory: false,
    history: [],
    historyError: null,
    apiToken: safeSessionStorageGet('mnemo_token'),
    apiUrl: normalizeApiUrl(safeStorageGet('mnemo_url', DEFAULT_API_URL)),
    useMock: safeStorageGet('mnemo_mock') === 'true',
  };
}

export function createStore(initialState, onChange) {
  let state = { ...initialState };

  return {
    getState() {
      return state;
    },
    setState(patch) {
      const nextPatch = typeof patch === 'function' ? patch(state) : patch;
      if (!nextPatch) return;
      state = { ...state, ...nextPatch };
      onChange(state);
    },
    updateState(patch) {
      const nextPatch = typeof patch === 'function' ? patch(state) : patch;
      if (!nextPatch) return;
      state = { ...state, ...nextPatch };
    },
  };
}
