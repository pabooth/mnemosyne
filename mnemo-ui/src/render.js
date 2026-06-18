import { CONTENT_TYPES, INGEST_STEPS, PREVIEW_STEPS } from './config.js';
import { buildPayload, postJson } from './api.js';
import { mockIngest, mockPreview } from './mock-data.js';
import { renderMarkdown } from './markdown.js';
import { escapeHtml, normalizeApiUrl, safeExternalUrl } from './security.js';
import { safeStorageSet } from './storage.js';

let timers = [];

function clearTimers() {
  timers.forEach(clearTimeout);
  timers = [];
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function startSteps(store, count) {
  clearTimers();
  [800, 1600, 2400].slice(0, count - 1).forEach((wait, index) => {
    timers.push(setTimeout(() => {
      store.setState((state) => (state.mode === 'loading' ? { loadingStep: index + 1 } : null));
    }, wait));
  });
}

async function finishSteps(store, count) {
  clearTimers();
  for (let index = store.getState().loadingStep; index < count; index += 1) {
    await delay(160);
    store.setState({ loadingStep: index + 1 });
  }
}

function documentFromResult(state) {
  if (state.resultType === 'ingest' && state.result && state.result.document) {
    return state.result.document;
  }
  return state.result;
}

function typeInfo(type) {
  const types = {
    tutorial: { color: '#2dd4bf', bg: 'rgba(45,212,191,0.12)' },
    'how-to': { color: '#f59e0b', bg: 'rgba(245,158,11,0.12)' },
    reference: { color: '#60a5fa', bg: 'rgba(96,165,250,0.12)' },
    explanation: { color: '#a78bfa', bg: 'rgba(167,139,250,0.12)' },
  };
  return types[type] || { color: '#8892a4', bg: 'rgba(136,146,164,0.12)' };
}

function titleCaseType(type) {
  return String(type || '')
    .split('-')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join('-');
}

async function runPipeline(store, resultType) {
  const state = store.getState();
  if (!state.content.trim()) {
    store.setState({ contentError: 'Document content is required' });
    return;
  }

  const ingest = resultType === 'ingest';
  const stepCount = ingest ? INGEST_STEPS.length : PREVIEW_STEPS.length;
  store.setState({
    mode: 'loading',
    pendingIngest: ingest,
    result: null,
    error: null,
    contentError: null,
    loadingStep: 0,
  });
  startSteps(store, stepCount);

  try {
    let result;
    if (state.useMock) {
      await delay(ingest ? 900 : 700);
      result = ingest ? mockIngest(state) : mockPreview(state);
    } else {
      result = await postJson(state, ingest ? '/api/ingest' : '/api/process', buildPayload(state));
    }

    await finishSteps(store, stepCount);
    await delay(180);
    store.setState({ mode: 'result', resultType, result });
  } catch (error) {
    clearTimers();
    store.setState({ mode: 'error', error: error.message });
  }
}

function setInput(store, key, value) {
  store.setState({ [key]: value, ...(key === 'content' ? { contentError: null } : {}) });
}

function renderHeader(state) {
  return `
    <header class="app-header">
      <div class="brand">
        <img src="./public/assets/logo.png" alt="" class="brand-logo">
        <div>
          <div class="brand-name">Mnemosyne<span>.</span></div>
          <div class="brand-kicker">knowledge, refined</div>
        </div>
      </div>
      <div class="header-actions">
        <button class="icon-button" type="button" data-action="open-settings" aria-label="API settings">Settings</button>
      </div>
    </header>
  `;
}

function renderForm(state) {
  const content = escapeHtml(state.content);
  const title = escapeHtml(state.title);
  const owner = escapeHtml(state.owner);
  const subLabel = escapeHtml(state.subLabel);
  const contentTypes = CONTENT_TYPES.map((type) => {
    const selected = state.contentType === type.id;
    return `
      <button class="content-type ${selected ? 'is-selected' : ''}" type="button" data-action="content-type" data-id="${escapeHtml(type.id)}" aria-pressed="${selected}">
        <span>${escapeHtml(type.label)}</span>
        <small>${escapeHtml(type.description)}</small>
      </button>
    `;
  }).join('');

  return `
    <section class="panel intake-panel" aria-label="Document intake">
      <div class="panel-heading">
        <p class="eyebrow">Intake</p>
        <h1>Prepare knowledge for review</h1>
      </div>

      <label class="field">
        <span>Document content</span>
        <textarea class="${state.contentError ? 'has-error' : ''}" data-field="content" placeholder="Paste source material here">${content}</textarea>
        ${state.contentError ? `<small class="field-error">${escapeHtml(state.contentError)}</small>` : ''}
      </label>

      <div class="form-grid">
        <label class="field">
          <span>Title</span>
          <input data-field="title" value="${title}" placeholder="Optional">
        </label>
        <label class="field">
          <span>Owner</span>
          <input data-field="owner" value="${owner}" placeholder="platform-team">
        </label>
        <label class="field">
          <span>Sub-label</span>
          <input data-field="subLabel" value="${subLabel}" placeholder="postgresql">
        </label>
      </div>

      <div class="content-types" role="group" aria-label="Content type">
        ${contentTypes}
      </div>

      <div class="primary-actions">
        <button class="secondary-button" type="button" data-action="preview">Preview</button>
        <button class="primary-button" type="button" data-action="ingest">Submit for review</button>
      </div>
    </section>
  `;
}

function renderLoading(state) {
  const steps = state.pendingIngest ? INGEST_STEPS : PREVIEW_STEPS;
  const items = steps.map((step, index) => {
    const done = index < state.loadingStep;
    const active = index === state.loadingStep;
    return `
      <li class="${done ? 'is-done' : ''} ${active ? 'is-active' : ''}">
        <span class="step-dot"></span>
        <span>${escapeHtml(step)}</span>
      </li>
    `;
  }).join('');

  return `
    <section class="panel status-panel" aria-live="polite">
      <p class="eyebrow">${state.pendingIngest ? 'Ingesting' : 'Previewing'}</p>
      <h2>Pipeline running</h2>
      <ol class="steps">${items}</ol>
    </section>
  `;
}

function renderError(state) {
  return `
    <section class="panel status-panel" aria-live="polite">
      <p class="eyebrow">Error</p>
      <h2>Pipeline stopped</h2>
      <p class="error-box">${escapeHtml(state.error || 'Something went wrong.')}</p>
      <button class="secondary-button" type="button" data-action="start-over">Start over</button>
    </section>
  `;
}

function renderResult(state) {
  const document = documentFromResult(state);
  if (!document) return '';

  const info = typeInfo(document.type);
  const prUrl = state.result && state.result.publish ? safeExternalUrl(state.result.publish.pr_url) : '';
  const tags = (document.tags || []).map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join('');
  const flags = (document.flags || []).map((flag) => `<li>${escapeHtml(flag)}</li>`).join('');

  return `
    <section class="panel result-panel">
      <div class="result-heading">
        <span class="type-pill" style="--pill-color:${info.color};--pill-bg:${info.bg}">${escapeHtml(titleCaseType(document.type))}</span>
        <h2>${escapeHtml(document.title || 'Untitled document')}</h2>
        <p>${escapeHtml(document.summary || '')}</p>
      </div>

      <dl class="metadata">
        <div><dt>Owner</dt><dd>${escapeHtml(document.owner || '-')}</dd></div>
        <div><dt>Status</dt><dd>${escapeHtml(document.status || '-')}</dd></div>
        <div><dt>Sub-label</dt><dd>${escapeHtml(document.sub_label || '-')}</dd></div>
        <div><dt>Last reviewed</dt><dd>${escapeHtml(document.last_reviewed || '-')}</dd></div>
      </dl>

      ${tags ? `<div class="tags">${tags}</div>` : ''}
      ${flags ? `<div class="flags"><p>Review flags</p><ul>${flags}</ul></div>` : ''}

      <div class="markdown-body">${renderMarkdown(document.body || '')}</div>

      ${state.resultType === 'preview' ? `
        <div class="result-actions">
          <button class="primary-button" type="button" data-action="ingest">Submit for review</button>
          <button class="link-button" type="button" data-action="start-over">Start over</button>
        </div>
      ` : ''}

      ${state.resultType === 'ingest' ? `
        <div class="publish-box">
          <p>Submitted for review</p>
          ${prUrl ? `<a href="${escapeHtml(prUrl)}" target="_blank" rel="noopener noreferrer">View pull request</a>` : ''}
          <dl>
            <div><dt>Branch</dt><dd>${escapeHtml(state.result.publish.branch)}</dd></div>
            <div><dt>Path</dt><dd>${escapeHtml(state.result.publish.file_path)}</dd></div>
          </dl>
          <button class="link-button" type="button" data-action="start-over">Start over</button>
        </div>
      ` : ''}
    </section>
  `;
}

function renderSettings(state) {
  if (!state.showSettings) return '';

  return `
    <div class="modal-backdrop" data-action="close-settings">
      <section class="settings-modal" role="dialog" aria-modal="true" aria-label="API settings">
        <div class="modal-heading">
          <h2>API Settings</h2>
          <button class="icon-button" type="button" data-action="close-settings" aria-label="Close settings">Close</button>
        </div>
        <div class="mock-row">
          <div>
            <p>Mock mode</p>
            <small>Simulated responses, no server needed</small>
          </div>
          <button class="toggle-button ${state.useMock ? 'is-on' : ''}" type="button" data-action="toggle-mock">${state.useMock ? 'On' : 'Off'}</button>
        </div>
        <label class="field">
          <span>API URL</span>
          <input data-field="apiUrl" value="${escapeHtml(state.apiUrl)}" placeholder="http://localhost:7777">
        </label>
        <label class="field">
          <span>API Token</span>
          <input data-field="apiToken" type="password" value="${escapeHtml(state.apiToken)}" placeholder="mnemo_xxxxxxxxxxxxxxxx">
        </label>
      </section>
    </div>
  `;
}

function bindEvents(root, store) {
  root.querySelectorAll('[data-field]').forEach((field) => {
    field.addEventListener('input', (event) => {
      const key = event.currentTarget.dataset.field;
      setInput(store, key, event.currentTarget.value);
    });
    field.addEventListener('change', (event) => {
      const key = event.currentTarget.dataset.field;
      if (key === 'apiUrl') {
        const value = normalizeApiUrl(event.currentTarget.value);
        safeStorageSet('mnemo_url', value);
        store.setState({ apiUrl: value });
      }
      if (key === 'apiToken') {
        safeStorageSet('mnemo_token', event.currentTarget.value);
      }
    });
  });

  root.querySelectorAll('[data-action]').forEach((control) => {
    control.addEventListener('click', (event) => {
      const action = event.currentTarget.dataset.action;
      if (action === 'preview') runPipeline(store, 'preview');
      if (action === 'ingest') runPipeline(store, 'ingest');
      if (action === 'start-over') {
        clearTimers();
        store.setState({ mode: 'idle', result: null, resultType: null, error: null, contentError: null });
      }
      if (action === 'content-type') store.setState({ contentType: event.currentTarget.dataset.id });
      if (action === 'open-settings') store.setState({ showSettings: true });
      if (action === 'close-settings' && event.target === event.currentTarget) store.setState({ showSettings: false });
      if (action === 'toggle-mock') {
        const useMock = !store.getState().useMock;
        safeStorageSet('mnemo_mock', String(useMock));
        store.setState({ useMock });
      }
    });
  });

  const modal = root.querySelector('.settings-modal');
  if (modal) modal.addEventListener('click', (event) => event.stopPropagation());
}

export function renderApp(root, store, state) {
  const workArea = state.mode === 'loading'
    ? renderLoading(state)
    : state.mode === 'error'
      ? renderError(state)
      : state.mode === 'result'
        ? renderResult(state)
        : renderForm(state);

  root.innerHTML = `
    <div class="app-shell">
      ${renderHeader(state)}
      <main class="workspace">
        ${workArea}
      </main>
      ${renderSettings(state)}
    </div>
  `;

  bindEvents(root, store);
}
