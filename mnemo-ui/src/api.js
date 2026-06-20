import { API_TIMEOUT_MS } from './config.js';
import { normalizeApiUrl } from './security.js';

export function buildPayload(state) {
  const payload = { content: state.content };
  if (state.title) payload.title = state.title;
  if (state.owner) payload.owner = state.owner;
  if (state.contentType !== 'auto') payload.type = state.contentType;
  if (state.subLabel) payload.sub_label = state.subLabel;
  return payload;
}

export async function postJson({ apiUrl, apiToken }, path, body) {
  const headers = { 'Content-Type': 'application/json' };
  const token = String(apiToken || '').trim();
  if (token) headers.Authorization = `Bearer ${token}`;

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), API_TIMEOUT_MS);

  let response;
  try {
    response = await fetch(`${normalizeApiUrl(apiUrl)}${path}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
      credentials: 'omit',
      referrerPolicy: 'no-referrer',
      signal: controller.signal,
    });
  } catch (error) {
    if (error && error.name === 'AbortError') {
      throw new Error('mnemo-core did not respond within 30 seconds.');
    }
    throw new Error('Could not reach mnemo-core. Is the server running?');
  } finally {
    clearTimeout(timeout);
  }

  if (response.status === 401) throw new Error('Authentication failed. Check MNEMO_API_TOKEN.');
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Pipeline error (${response.status})`);
  }

  return response.json();
}

export async function getJson({ apiUrl, apiToken }, path) {
  const headers = {};
  const token = String(apiToken || '').trim();
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${normalizeApiUrl(apiUrl)}${path}`, {
    headers,
    credentials: 'omit',
    referrerPolicy: 'no-referrer',
  });
  if (response.status === 401) throw new Error('Authentication failed. Check MNEMO_API_TOKEN.');
  if (!response.ok) throw new Error(`Request failed (${response.status})`);
  return response.json();
}
