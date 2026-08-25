'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const handler = require('./openclaw-release-adapter');

const DIGEST = `sha256:${'a'.repeat(64)}`;

function response(status, { body, headers = {}, url = '' } = {}) {
  return {
    ok: status >= 200 && status < 300,
    status,
    url,
    headers: new Headers(headers),
    async json() {
      if (body instanceof Error) {
        throw body;
      }
      return body;
    },
  };
}

function successfulFetch({ version = '2026.7.1-2', digest = DIGEST, npmResponses } = {}) {
  const calls = [];
  const npmQueue = npmResponses ?? [
    response(200, { body: { name: 'openclaw', version } }),
  ];

  return {
    calls,
    fetchImpl: async (url, options = {}) => {
      calls.push({ url, options });
      if (url === 'https://registry.npmjs.org/openclaw/latest') {
        return npmQueue.shift();
      }
      if (url === 'https://github.com/openclaw/openclaw/releases/latest') {
        return response(200, {
          url: `https://github.com/openclaw/openclaw/releases/tag/v${version}`,
        });
      }
      if (url.startsWith('https://ghcr.io/token?')) {
        return response(200, { body: { token: 'public-registry-token' } });
      }
      if (url === `https://ghcr.io/v2/openclaw/openclaw/manifests/${version}`) {
        return response(200, { headers: { 'docker-content-digest': digest } });
      }
      throw new Error(`unexpected URL: ${url}`);
    },
  };
}

test('returns the immutable image input for a stable correction release', async () => {
  const scenario = successfulFetch();

  const input = await handler.resolveOpenClawStableInput({
    fetchImpl: scenario.fetchImpl,
    sleepImpl: async () => {},
  });

  assert.deepEqual(input, {
    id: 'openclaw-stable',
    repository: 'ghcr.io/openclaw/openclaw',
    tag: '2026.7.1-2',
    digest: DIGEST,
  });
  assert.equal(scenario.calls.length, 4);
  assert.equal(
    scenario.calls.find((call) => call.url.startsWith('https://ghcr.io/v2/')).options.headers.authorization,
    'Bearer public-registry-token',
  );
});

test('accepts an ordinary stable release without a correction suffix', async () => {
  const scenario = successfulFetch({ version: '2026.8.1' });

  const input = await handler.resolveOpenClawStableInput({
    fetchImpl: scenario.fetchImpl,
    sleepImpl: async () => {},
  });

  assert.equal(input.tag, '2026.8.1');
});

test('rejects an npm and GitHub version mismatch before contacting GHCR', async () => {
  const calls = [];
  const fetchImpl = async (url) => {
    calls.push(url);
    if (url === 'https://registry.npmjs.org/openclaw/latest') {
      return response(200, { body: { name: 'openclaw', version: '2026.7.1-2' } });
    }
    if (url === 'https://github.com/openclaw/openclaw/releases/latest') {
      return response(200, {
        url: 'https://github.com/openclaw/openclaw/releases/tag/v2026.7.1-1',
      });
    }
    throw new Error(`GHCR must not be called: ${url}`);
  };

  await assert.rejects(
    handler.resolveOpenClawStableInput({ fetchImpl, sleepImpl: async () => {} }),
    /do not match/,
  );
  assert.equal(calls.length, 2);
});

test('rejects beta, malformed, and zero-valued stable-version candidates', () => {
  for (const version of ['2026.8.1-beta.3', '2026.13.1', '2026.7.0', '2026.7.1-0']) {
    assert.throws(() => handler.parseStableVersion(version), /supported stable release|outside/);
  }
});

test('rejects a GitHub latest-release response that does not resolve to a stable tag', async () => {
  const scenario = successfulFetch();
  const fetchImpl = async (url, options) => {
    if (url === 'https://github.com/openclaw/openclaw/releases/latest') {
      return response(200, {
        url: 'https://github.com/openclaw/openclaw/releases/tag/v2026.7.1-beta.1',
      });
    }
    return scenario.fetchImpl(url, options);
  };

  await assert.rejects(
    handler.resolveOpenClawStableInput({ fetchImpl, sleepImpl: async () => {} }),
    /supported stable release/,
  );
});

test('rejects a missing OCI manifest digest', async () => {
  const scenario = successfulFetch({ digest: '' });

  await assert.rejects(
    handler.resolveOpenClawStableInput({
      fetchImpl: scenario.fetchImpl,
      sleepImpl: async () => {},
    }),
    /valid digest/,
  );
});

test('retries a bounded transient npm response once and honors Retry-After', async () => {
  const scenario = successfulFetch({
    npmResponses: [
      response(503, { headers: { 'retry-after': '1' } }),
      response(200, { body: { name: 'openclaw', version: '2026.7.1-2' } }),
    ],
  });
  const delays = [];

  const input = await handler.resolveOpenClawStableInput({
    fetchImpl: scenario.fetchImpl,
    sleepImpl: async (delay) => delays.push(delay),
  });

  assert.equal(input.tag, '2026.7.1-2');
  assert.deepEqual(delays, [1_000]);
  assert.equal(
    scenario.calls.filter((call) => call.url === 'https://registry.npmjs.org/openclaw/latest').length,
    2,
  );
});

test('fails closed when Retry-After exceeds the function retry budget', async () => {
  const scenario = successfulFetch({
    npmResponses: [response(429, { headers: { 'retry-after': '60' } })],
  });

  await assert.rejects(
    handler.resolveOpenClawStableInput({
      fetchImpl: scenario.fetchImpl,
      sleepImpl: async () => assert.fail('retry must not wait past the bounded budget'),
    }),
    /exceeds the bounded retry window/,
  );
});

test('returns a non-2xx response without partial inputs when resolution fails', async () => {
  const originalConsoleError = console.error;
  const originalFetch = globalThis.fetch;
  console.error = () => {};
  globalThis.fetch = async () => response(500);

  try {
    const result = await handler();
    assert.equal(result.status, 502);
    assert.equal(result.headers['content-type'], 'application/json');
    assert.deepEqual(JSON.parse(result.body), {
      error: 'OpenClaw stable release is unavailable',
    });
  } finally {
    globalThis.fetch = originalFetch;
    console.error = originalConsoleError;
  }
});
