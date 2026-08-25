'use strict';

const { setTimeout: sleep } = require('node:timers/promises');

const PACKAGE_NAME = 'openclaw';
const REPOSITORY = 'openclaw/openclaw';
const IMAGE_REPOSITORY = `ghcr.io/${REPOSITORY}`;
const REQUEST_TIMEOUT_MS = 10_000;
const MAX_RETRY_AFTER_MS = 5_000;
const TRANSIENT_STATUSES = new Set([429, 502, 503, 504]);
const DIGEST_PATTERN = /^sha256:[a-f0-9]{64}$/;

class AdapterError extends Error {
  constructor(message) {
    super(message);
    this.name = 'AdapterError';
  }
}

function parseStableVersion(version) {
  if (typeof version !== 'string') {
    throw new AdapterError('OpenClaw version must be a string');
  }

  const match = /^(\d{4})\.(\d{1,2})\.(\d+)(?:-(\d+))?$/.exec(version);
  if (!match) {
    throw new AdapterError('OpenClaw version is not a supported stable release');
  }

  const [, year, month, patch, correction] = match;
  if (
    Number(year) < 2020 ||
    Number(month) < 1 ||
    Number(month) > 12 ||
    Number(patch) < 1 ||
    (correction !== undefined && Number(correction) < 1)
  ) {
    throw new AdapterError('OpenClaw version is outside the supported stable release format');
  }

  return version;
}

function normalizeGitHubReleaseTag(release) {
  if (!release || release.draft !== false || release.prerelease !== false) {
    throw new AdapterError('GitHub latest release is draft or prerelease');
  }

  if (typeof release.tag_name !== 'string' || !release.tag_name.startsWith('v')) {
    throw new AdapterError('GitHub latest release tag does not start with v');
  }

  return parseStableVersion(release.tag_name.slice(1));
}

function retryAfterMilliseconds(value, now = Date.now()) {
  if (!value) {
    return 0;
  }

  if (/^\d+$/.test(value)) {
    return Number(value) * 1_000;
  }

  const retryAt = Date.parse(value);
  return Number.isNaN(retryAt) ? 0 : Math.max(0, retryAt - now);
}

async function fetchResponse({ fetchImpl, url, options = {}, timeoutMs, sleepImpl }) {
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    let response;
    try {
      response = await fetchImpl(url, { ...options, signal: controller.signal });
    } catch (error) {
      throw new AdapterError(`request failed for ${new URL(url).hostname}: ${error.message}`);
    } finally {
      clearTimeout(timer);
    }

    if (response.ok) {
      return response;
    }

    if (attempt === 0 && TRANSIENT_STATUSES.has(response.status)) {
      const retryAfterMs = retryAfterMilliseconds(response.headers.get('retry-after'));
      if (retryAfterMs > MAX_RETRY_AFTER_MS) {
        throw new AdapterError(
          `retry-after for ${new URL(url).hostname} exceeds the bounded retry window`,
        );
      }
      await sleepImpl(retryAfterMs);
      continue;
    }

    throw new AdapterError(
      `request to ${new URL(url).hostname} failed with HTTP ${response.status}`,
    );
  }

  throw new AdapterError(`request retries exhausted for ${new URL(url).hostname}`);
}

async function fetchJson(request) {
  const response = await fetchResponse(request);
  try {
    return await response.json();
  } catch (error) {
    throw new AdapterError(`invalid JSON from ${new URL(request.url).hostname}`);
  }
}

async function resolveOpenClawStableInput({
  fetchImpl = globalThis.fetch,
  timeoutMs = REQUEST_TIMEOUT_MS,
  sleepImpl = sleep,
} = {}) {
  if (typeof fetchImpl !== 'function') {
    throw new AdapterError('fetch is unavailable');
  }

  const [npmMetadata, githubRelease] = await Promise.all([
    fetchJson({
      fetchImpl,
      url: `https://registry.npmjs.org/${PACKAGE_NAME}/latest`,
      timeoutMs,
      sleepImpl,
      options: { headers: { accept: 'application/json' } },
    }),
    fetchJson({
      fetchImpl,
      url: `https://api.github.com/repos/${REPOSITORY}/releases/latest`,
      timeoutMs,
      sleepImpl,
      options: {
        headers: {
          accept: 'application/vnd.github+json',
          'user-agent': 'elysium-openclaw-release-adapter',
          'x-github-api-version': '2022-11-28',
        },
      },
    }),
  ]);

  const npmVersion = parseStableVersion(npmMetadata?.version);
  const githubVersion = normalizeGitHubReleaseTag(githubRelease);
  if (npmVersion !== githubVersion) {
    throw new AdapterError('npm latest and GitHub latest release do not match');
  }

  const tokenMetadata = await fetchJson({
    fetchImpl,
    url: `https://ghcr.io/token?service=ghcr.io&scope=repository%3A${REPOSITORY}%3Apull`,
    timeoutMs,
    sleepImpl,
    options: { headers: { accept: 'application/json' } },
  });
  const token = tokenMetadata?.token ?? tokenMetadata?.access_token;
  if (typeof token !== 'string' || token.length === 0) {
    throw new AdapterError('GHCR token response did not include a token');
  }

  const manifestResponse = await fetchResponse({
    fetchImpl,
    url: `https://ghcr.io/v2/${REPOSITORY}/manifests/${npmVersion}`,
    timeoutMs,
    sleepImpl,
    options: {
      headers: {
        accept: [
          'application/vnd.oci.image.index.v1+json',
          'application/vnd.docker.distribution.manifest.list.v2+json',
          'application/vnd.oci.image.manifest.v1+json',
          'application/vnd.docker.distribution.manifest.v2+json',
        ].join(', '),
        authorization: `Bearer ${token}`,
      },
    },
  });

  const digest = manifestResponse.headers.get('docker-content-digest');
  if (!DIGEST_PATTERN.test(digest ?? '')) {
    throw new AdapterError('GHCR manifest response did not include a valid digest');
  }

  return {
    id: 'openclaw-stable',
    repository: IMAGE_REPOSITORY,
    tag: npmVersion,
    digest,
  };
}

function jsonResponse(status, body) {
  return {
    status,
    headers: {
      'cache-control': 'no-store',
      'content-type': 'application/json',
    },
    body: JSON.stringify(body),
  };
}

async function handler() {
  try {
    const input = await resolveOpenClawStableInput();
    return jsonResponse(200, { inputs: [input] });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'unknown adapter failure';
    console.error('openclaw release adapter failed', { message });
    return jsonResponse(502, { error: 'OpenClaw stable release is unavailable' });
  }
}

module.exports = handler;
module.exports.AdapterError = AdapterError;
module.exports.normalizeGitHubReleaseTag = normalizeGitHubReleaseTag;
module.exports.parseStableVersion = parseStableVersion;
module.exports.resolveOpenClawStableInput = resolveOpenClawStableInput;
module.exports.retryAfterMilliseconds = retryAfterMilliseconds;
