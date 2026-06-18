import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';

import { buildPayload } from '../src/api.js';
import { escapeHtml, normalizeApiUrl, safeExternalUrl } from '../src/security.js';

const read = (path) => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');

const index = read('index.html');
const dockerfile = read('Dockerfile');
const nginxConf = read('nginx.conf');
const packageJson = JSON.parse(read('package.json'));
const renderer = read('src/render.js');

assert.match(index, /<script type="module" src="\.\/src\/main\.js"><\/script>/);
assert.match(index, /<link rel="stylesheet" href="\.\/src\/styles\.css">/);
assert.doesNotMatch(index, /__bundler\/manifest/);
assert.doesNotMatch(index, /__bundler\/template/);
assert.match(renderer, /escapeHtml/);
assert.doesNotMatch(renderer, /dangerouslysetinnerhtml/i);

for (const path of [
  'src/api.js',
  'src/config.js',
  'src/main.js',
  'src/markdown.js',
  'src/render.js',
  'src/security.js',
  'src/state.js',
  'src/storage.js',
  'src/styles.css',
  'public/assets/logo.png',
]) {
  assert.ok(existsSync(new URL(`../${path}`, import.meta.url)), `${path} should exist`);
}

assert.equal(normalizeApiUrl('https://example.com/api///?x=1#hash'), 'https://example.com/api');
assert.equal(normalizeApiUrl('file:///tmp/app'), 'http://localhost:7777');
assert.equal(safeExternalUrl('javascript:alert(1)'), '');
assert.equal(safeExternalUrl('https://github.com/org/repo/pull/1'), 'https://github.com/org/repo/pull/1');
assert.equal(escapeHtml('<img src=x onerror=1>'), '&lt;img src=x onerror=1&gt;');

assert.deepEqual(
  buildPayload({
    content: 'Body',
    title: 'Title',
    owner: 'docs',
    contentType: 'tutorial',
    subLabel: 'postgres',
  }),
  {
    content: 'Body',
    title: 'Title',
    owner: 'docs',
    type: 'tutorial',
    sub_label: 'postgres',
  },
);

assert.equal(packageJson.scripts.build, 'node scripts/build.mjs');
assert.match(dockerfile, /FROM node:22-alpine AS build/);
assert.match(dockerfile, /COPY --from=build \/app\/dist \/usr\/share\/nginx\/html/);
assert.match(nginxConf, /frame-ancestors 'none'/);

execFileSync('npm', ['run', 'build'], { stdio: 'pipe' });
assert.ok(existsSync(new URL('../dist/index.html', import.meta.url)), 'dist/index.html should exist');
assert.ok(existsSync(new URL('../dist/src/main.js', import.meta.url)), 'dist/src/main.js should exist');
assert.ok(existsSync(new URL('../dist/public/assets/logo.png', import.meta.url)), 'dist logo should exist');
