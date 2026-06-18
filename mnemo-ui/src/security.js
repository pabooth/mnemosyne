import { DEFAULT_API_URL } from './config.js';

export function normalizeApiUrl(value) {
  const raw = String(value || '').trim() || DEFAULT_API_URL;

  try {
    const url = new URL(raw);
    if (!['http:', 'https:'].includes(url.protocol)) return DEFAULT_API_URL;
    url.pathname = url.pathname.replace(/\/+$/, '');
    url.search = '';
    url.hash = '';
    return url.toString().replace(/\/$/, '');
  } catch {
    return DEFAULT_API_URL;
  }
}

export function safeExternalUrl(value) {
  try {
    const url = new URL(String(value || ''));
    return ['http:', 'https:'].includes(url.protocol) ? url.href : '';
  } catch {
    return '';
  }
}

export function escapeHtml(value) {
  return String(value || '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

export function sanitizeHtml(html) {
  const template = document.createElement('template');
  template.innerHTML = String(html || '');

  template.content
    .querySelectorAll('script, style, iframe, object, embed, link, meta, base, form, input, button')
    .forEach((node) => node.remove());

  template.content.querySelectorAll('*').forEach((node) => {
    for (const attr of [...node.attributes]) {
      const name = attr.name.toLowerCase();
      const value = attr.value.trim();

      if (name.startsWith('on') || name === 'srcdoc') node.removeAttribute(attr.name);
      if (name === 'href' && value && !/^(https?:|mailto:|#|\/[^/])/i.test(value)) {
        node.removeAttribute(attr.name);
      }
      if (name === 'src' && value && !/^(https?:|blob:|data:image\/)/i.test(value)) {
        node.removeAttribute(attr.name);
      }
    }

    if (node.tagName === 'A') {
      node.setAttribute('rel', 'noopener noreferrer');
      if (node.getAttribute('target') === '_blank' && !node.getAttribute('href')) {
        node.removeAttribute('target');
      }
    }
  });

  return template.innerHTML;
}
