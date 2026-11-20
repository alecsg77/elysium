'use strict';

const http = require('node:http');
const { execFile } = require('node:child_process');
const { createHash } = require('node:crypto');

const { ORCA_CODER_URL, ORCA_CODER_WORKSPACE, ORCA_CODER_OWNER } = process.env;
const domain = new URL(ORCA_CODER_URL).hostname;
const appHosts = new Set(['orca', 'orca--main'].map(
  prefix => `${prefix}--${ORCA_CODER_WORKSPACE}--${ORCA_CODER_OWNER}.${domain}`.toLowerCase()
));
const cli = process.argv[2];
const storageKey = 'elysium.orca.web-bootstrapped';

const browser = `
(async () => {
  const client = '/web-index.html';
  if (location.hash) {
    location.replace(client + location.hash);
    return;
  }
  try {
    if (localStorage.getItem('${storageKey}') && !new URLSearchParams(location.search).has('pair')) {
      location.replace(client);
      return;
    }
    const response = await fetch('/_coder_orca/pair', {
      method: 'POST',
      headers: { 'X-Orca-Bootstrap': '1' },
      cache: 'no-store',
    });
    if (!response.ok) throw new Error('Pairing unavailable');
    const { url } = await response.json();
    localStorage.setItem('${storageKey}', '1');
    location.replace(url);
  } catch {
    document.getElementById('status').textContent = 'Could not connect to Orca. Reload to retry or open Orca to pair manually.';
  }
})();`;
const scriptHash = createHash('sha256').update(browser).digest('base64');
const landing = `<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Orca</title>
<p id="status">Connecting to Orca…</p><p><a href="/web-index.html">Open Orca</a></p><script>${browser}</script></html>`;

function pairingOrigin(req) {
  try {
    const origin = new URL(req.headers.origin);
    if (origin.protocol === 'https:' && appHosts.has(origin.hostname) &&
        req.headers.origin === origin.origin && !origin.port &&
        req.headers['sec-fetch-site'] === 'same-origin' && req.headers['x-orca-bootstrap'] === '1') {
      return origin;
    }
  } catch { /* No valid browser origin. */ }
}

function upstream(req) {
  const headers = { ...req.headers };
  // Coder authenticates the outside request. Orca authenticates its own socket.
  for (const name of ['cookie', 'authorization', 'coder-session-token']) delete headers[name];
  return http.request({ host: '127.0.0.1', port: 6768, method: req.method, path: req.url, headers });
}

let pairing = false;
const server = http.createServer((req, res) => {
  const path = req.url.split('?')[0];
  if (path === '/' && req.method === 'GET') {
    res.writeHead(200, {
      'Content-Type': 'text/html; charset=utf-8',
      'Cache-Control': 'no-store',
      'Referrer-Policy': 'no-referrer',
      'Content-Security-Policy': `default-src 'none'; script-src 'sha256-${scriptHash}'; connect-src 'self'; frame-ancestors 'none'`,
    });
    res.end(landing);
    return;
  }
  if (path === '/_coder_orca/pair') {
    res.setHeader('Cache-Control', 'no-store');
    const origin = pairingOrigin(req);
    if (req.method !== 'POST' || !origin) {
      res.writeHead(403).end();
      return;
    }
    if (pairing) {
      res.writeHead(429).end();
      return;
    }
    pairing = true;
    execFile(cli, ['pair', '--address', `wss://${origin.host}`, '--json'],
      { timeout: 10000, maxBuffer: 256 * 1024 }, (error, stdout) => {
        pairing = false;
        try {
          if (error) throw error;
          const url = new URL(JSON.parse(stdout).result.webClientUrl);
          if (url.origin !== origin.origin || url.pathname !== '/web-index.html' ||
              url.search || !url.hash.startsWith('#pairing=')) throw new Error('Invalid offer');
          res.writeHead(200, { 'Content-Type': 'application/json', 'Referrer-Policy': 'no-referrer' });
          res.end(JSON.stringify({ url: url.href }));
        } catch {
          res.writeHead(503).end();
        }
      });
    return;
  }
  if (path === '/_coder_orca/health') req.url = '/web-index.html';
  const proxy = upstream(req);
  proxy.on('response', response => {
    res.writeHead(response.statusCode, response.headers);
    response.pipe(res);
  });
  proxy.on('error', () => res.destroy());
  req.pipe(proxy);
});

server.on('upgrade', (req, client, head) => {
  const proxy = upstream(req);
  proxy.on('upgrade', (response, socket, upstreamHead) => {
    const headers = response.rawHeaders;
    const lines = [`HTTP/1.1 ${response.statusCode} ${response.statusMessage}`];
    for (let i = 0; i < headers.length; i += 2) lines.push(`${headers[i]}: ${headers[i+1]}`);
    client.write(lines.join('\r\n') + '\r\n\r\n');
    if (upstreamHead.length) client.write(upstreamHead);
    if (head.length) socket.write(head);
    client.on('close', () => socket.destroy());
    socket.on('close', () => client.destroy());
    client.on('error', () => socket.destroy());
    socket.on('error', () => client.destroy());
    client.pipe(socket).pipe(client);
  });
  proxy.on('response', response => {
    response.resume();
    client.destroy();
  });
  proxy.on('error', () => client.destroy());
  proxy.end();
});

server.listen(6769, '127.0.0.1');
