'use strict';

const { copyFileSync, mkdirSync, readFileSync } = require('node:fs');
const { dirname, join } = require('node:path');

const source = 'squashfs-root/resources/app.asar.unpacked/out/renderer';
const files = JSON.parse(readFileSync(join(source, '.orca-web-client-files.json'), 'utf8'));
if (!Array.isArray(files) || !files.includes('web-index.html')) {
  throw new Error('Orca web asset manifest is missing its entry page');
}
for (const file of files) {
  if (!/^[A-Za-z0-9._-]+(?:\/[A-Za-z0-9._-]+)*$/.test(file)
      || file.split('/').some(segment => segment === '.' || segment === '..')) {
    throw new Error('Unexpected path in Orca web asset manifest');
  }
  const destination = join('/web', file);
  mkdirSync(dirname(destination), { recursive: true });
  copyFileSync(join(source, file), destination);
}
