import { escapeHtml, sanitizeHtml } from './security.js';

function inlineMarkdown(value) {
  return escapeHtml(value)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
}

function renderTable(lines) {
  const rows = lines
    .filter((line, index) => index !== 1)
    .map((line) => line.split('|').slice(1, -1).map((cell) => inlineMarkdown(cell.trim())));

  const [head, ...body] = rows;
  const header = `<thead><tr>${head.map((cell) => `<th>${cell}</th>`).join('')}</tr></thead>`;
  const rowsHtml = body.map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join('')}</tr>`).join('');
  return `<table>${header}<tbody>${rowsHtml}</tbody></table>`;
}

export function renderMarkdown(markdown) {
  const source = String(markdown || '').replace(/\r\n/g, '\n');
  const blocks = [];
  const lines = source.split('\n');
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];

    if (!line.trim()) {
      index += 1;
      continue;
    }

    if (line.startsWith('```')) {
      const language = line.slice(3).trim();
      const code = [];
      index += 1;
      while (index < lines.length && !lines[index].startsWith('```')) {
        code.push(lines[index]);
        index += 1;
      }
      index += 1;
      const className = language ? ` class="language-${escapeHtml(language)}"` : '';
      blocks.push(`<pre><code${className}>${escapeHtml(code.join('\n'))}</code></pre>`);
      continue;
    }

    if (/^#{1,3}\s/.test(line)) {
      const level = line.match(/^#+/)[0].length;
      blocks.push(`<h${level}>${inlineMarkdown(line.slice(level).trim())}</h${level}>`);
      index += 1;
      continue;
    }

    if (/^\|.+\|$/.test(line) && /^\|[-\s|:]+\|$/.test(lines[index + 1] || '')) {
      const tableLines = [];
      while (index < lines.length && /^\|.+\|$/.test(lines[index])) {
        tableLines.push(lines[index]);
        index += 1;
      }
      blocks.push(renderTable(tableLines));
      continue;
    }

    if (/^[-*]\s+/.test(line)) {
      const items = [];
      while (index < lines.length && /^[-*]\s+/.test(lines[index])) {
        items.push(`<li>${inlineMarkdown(lines[index].replace(/^[-*]\s+/, ''))}</li>`);
        index += 1;
      }
      blocks.push(`<ul>${items.join('')}</ul>`);
      continue;
    }

    const paragraph = [];
    while (index < lines.length && lines[index].trim() && !/^#{1,3}\s|^```|^[-*]\s+/.test(lines[index])) {
      paragraph.push(lines[index]);
      index += 1;
    }
    blocks.push(`<p>${inlineMarkdown(paragraph.join(' '))}</p>`);
  }

  return sanitizeHtml(blocks.join('\n'));
}
