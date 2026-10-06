'use strict';

const { randomUUID } = require('node:crypto');
const { URL } = require('node:url');

const KNOWLEDGE_MAX_BYTES = 262144;
const KNOWLEDGE_MAX_JSON_BYTES = 4 * Math.ceil(KNOWLEDGE_MAX_BYTES / 3) + 4096;
const KNOWLEDGE_TIMEOUT_MS = 10000;
const KNOWLEDGE_PROFILE_KEYS = ['game', 'platform', 'patch', 'environment', 'profile'];
const DIGEST = /^[0-9a-f]{64}$/;

function isLoopbackHostname(hostname) {
  const normalized = String(hostname || '').toLowerCase().replace(/^\[/, '').replace(/\]$/, '');
  return normalized === 'localhost' || normalized === '127.0.0.1' || normalized === '::1';
}

function normalizeCoreUrl(value) {
  const url = new URL(String(value || '').trim());
  if (!['http:', 'https:'].includes(url.protocol)) throw new Error('INVALID_CORE_URL');
  if (url.protocol === 'http:' && !isLoopbackHostname(url.hostname)) throw new Error('INSECURE_CORE_URL');
  if (url.username || url.password || url.search || url.hash) throw new Error('INVALID_CORE_URL');
  url.pathname = url.pathname.replace(/\/$/, '');
  return url.toString().replace(/\/$/, '');
}

function publicSession(session) {
  if (!session) return null;
  return {
    authenticated: true,
    expiresAt: session.expires_at || null,
    scopes: Array.isArray(session.scopes) ? [...session.scopes] : [],
  };
}

function requestId() { return randomUUID(); }

function validKnowledgeProfile(profile) {
  return profile && typeof profile === 'object' && !Array.isArray(profile) &&
    Object.keys(profile).length === KNOWLEDGE_PROFILE_KEYS.length &&
    KNOWLEDGE_PROFILE_KEYS.every(key => Object.hasOwn(profile, key) &&
      typeof profile[key] === 'string' && profile[key].length > 0 &&
      profile[key].length <= (key === 'patch' ? 64 : 128)) &&
    ['android', 'windows'].includes(profile.platform);
}

function knowledgeUrl(coreUrl, route, profile, extra = {}) {
  if (!validKnowledgeProfile(profile)) throw new Error('KNOWLEDGE_PROFILE_INVALID');
  const url = new URL(`${coreUrl}${route}`);
  for (const key of KNOWLEDGE_PROFILE_KEYS) url.searchParams.set(key, profile[key]);
  for (const [key, value] of Object.entries(extra)) {
    if (value !== null && value !== undefined) url.searchParams.set(key, value);
  }
  return url.toString();
}

async function readBounded(response, limit) {
  const declared = response.headers?.get?.('content-length');
  if (declared !== null && declared !== undefined) {
    if (!/^(0|[1-9][0-9]*)$/.test(declared) || Number(declared) > limit) {
      throw new Error('KNOWLEDGE_SIZE_INVALID');
    }
  }
  if (!response.body?.getReader) {
    const bytes = Buffer.from(await response.arrayBuffer());
    if (bytes.length > limit) throw new Error('KNOWLEDGE_SIZE_INVALID');
    return bytes;
  }
  const chunks = [];
  let length = 0;
  const reader = response.body.getReader();
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    length += value.byteLength;
    if (length > limit) {
      await reader.cancel().catch(() => {});
      throw new Error('KNOWLEDGE_SIZE_INVALID');
    }
    chunks.push(Buffer.from(value));
  }
  return Buffer.concat(chunks, length);
}

async function readBoundedJson(response) {
  const raw = await readBounded(response, KNOWLEDGE_MAX_JSON_BYTES);
  try {
    return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(raw));
  } catch {
    throw new Error('KNOWLEDGE_RESPONSE_INVALID');
  }
}

class CoreSessionManager {
  #fetch;
  #session = null;
  #coreUrl = null;
  #mfaChallenge = null;
  #mfaExpiresAt = null;
  #sessionEpoch = 0;

  constructor({ fetchImpl = globalThis.fetch } = {}) {
    if (typeof fetchImpl !== 'function') throw new Error('FETCH_UNAVAILABLE');
    this.#fetch = fetchImpl;
  }

  get coreUrl() { return this.#coreUrl; }
  get accessToken() { return this.#session?.session_token || null; }
  get refreshToken() { return this.#session?.refresh_token || null; }
  get status() { return publicSession(this.#session); }
  get mfaStatus() {
    return this.#mfaChallenge
      ? Object.freeze({ required: true, expiresAt: this.#mfaExpiresAt || null })
      : null;
  }

  async login({ coreUrl, email, password }) {
    const normalized = normalizeCoreUrl(coreUrl);
    if (typeof email !== 'string' || !email.trim() || typeof password !== 'string' || !password) {
      throw new Error('CREDENTIALS_REQUIRED');
    }
    const rid = requestId();
    const response = await this.#fetch(`${normalized}/v1/auth/login`, {
      method: 'POST',
      headers: { 'content-type': 'application/json', 'X-Request-ID': rid },
      body: JSON.stringify({ email: email.trim(), password }),
    });
    const payload = await readJson(response);
    if (!response.ok) throw new Error(errorCode(payload, 'LOGIN_FAILED'));
    if (payload?.mfa_required === true) {
      if (typeof payload.challenge_token !== 'string' || payload.challenge_token.length < 32) {
        throw new Error('INVALID_MFA_CHALLENGE_RESPONSE');
      }
      this.#session = null;
      this.#coreUrl = normalized;
      this.#mfaChallenge = payload.challenge_token;
      this.#mfaExpiresAt = typeof payload.expires_at === 'string' ? payload.expires_at : null;
      return this.status;
    }
    this.#setSession(normalized, payload);
    return this.status;
  }

  async completeMfa(code) {
    if (!this.#coreUrl || !this.#mfaChallenge) throw new Error('MFA_CHALLENGE_REQUIRED');
    const normalizedCode = typeof code === 'string' ? code.trim() : '';
    if (normalizedCode.length < 6 || normalizedCode.length > 64) throw new Error('MFA_CODE_INVALID');
    const rid = requestId();
    const response = await this.#fetch(`${this.#coreUrl}/v1/auth/mfa/complete`, {
      method: 'POST',
      headers: { 'content-type': 'application/json', 'X-Request-ID': rid },
      body: JSON.stringify({
        challenge_token: this.#mfaChallenge,
        code: normalizedCode,
      }),
    });
    const payload = await readJson(response);
    if (!response.ok) throw new Error(errorCode(payload, 'MFA_VERIFICATION_FAILED'));
    this.#setSession(this.#coreUrl, payload);
    return this.status;
  }

  async refresh(rid = requestId()) {
    if (!this.#coreUrl || !this.refreshToken) throw new Error('REFRESH_UNAVAILABLE');
    const response = await this.#fetch(`${this.#coreUrl}/v1/sessions/refresh`, {
      method: 'POST',
      headers: { 'content-type': 'application/json', 'X-Request-ID': rid },
      body: JSON.stringify({ refresh_token: this.refreshToken }),
    });
    const payload = await readJson(response);
    if (!response.ok) {
      this.clear();
      throw new Error(errorCode(payload, 'REFRESH_FAILED'));
    }
    this.#setSession(this.#coreUrl, payload, { refresh: true });
    return this.status;
  }

  async featureStatus() {
    return this.#authorizedJson('/v1/billing/features', {}, 'FEATURE_LOOKUP_FAILED');
  }

  async voiceStatus() {
    return this.#authorizedJson('/v1/companion/voice/status', {}, 'VOICE_STATUS_FAILED');
  }

  async transcribeVoice({ audioBase64, locale, recommendationId, consentGranted }) {
    return this.#authorizedJson(
      '/v1/companion/voice/transcribe',
      {
        method: 'POST',
        body: {
          audio_b64: audioBase64,
          locale,
          recommendation_id: recommendationId,
          consent_granted: consentGranted === true,
        },
      },
      'VOICE_TRANSCRIBE_FAILED',
    );
  }

  async synthesizeVoice({ text, locale, consentGranted }) {
    return this.#authorizedJson(
      '/v1/companion/voice/synthesize',
      { method: 'POST', body: { text, locale, consent_granted: consentGranted === true } },
      'VOICE_SYNTHESIS_FAILED',
    );
  }

  async knowledgeManifest(profile, knownDigest = null) {
    if (knownDigest !== null && !DIGEST.test(knownDigest)) throw new Error('KNOWLEDGE_DIGEST_INVALID');
    const url = knowledgeUrl(this.#requireKnowledgeOrigin(), '/v1/knowledge/manifest', profile, {
      known_digest: knownDigest,
    });
    return this.#knowledgeRequest(url, { kind: 'json', notFound: 'KNOWLEDGE_UNAVAILABLE' });
  }

  async knowledgePack(profile, digest) {
    if (!DIGEST.test(digest)) throw new Error('KNOWLEDGE_DIGEST_INVALID');
    const url = knowledgeUrl(this.#requireKnowledgeOrigin(), `/v1/knowledge/packs/${digest}`, profile);
    return this.#knowledgeRequest(url, { kind: 'bytes', notFound: 'KNOWLEDGE_PACK_UNAVAILABLE' });
  }

  async knowledgeDelta(profile, destinationDigest, baseDigest) {
    if (!DIGEST.test(destinationDigest) || !DIGEST.test(baseDigest)) {
      throw new Error('KNOWLEDGE_DIGEST_INVALID');
    }
    const url = knowledgeUrl(
      this.#requireKnowledgeOrigin(), `/v1/knowledge/deltas/${destinationDigest}`,
      profile, { base_digest: baseDigest },
    );
    return this.#knowledgeRequest(url, { kind: 'json', notFound: 'KNOWLEDGE_DELTA_UNAVAILABLE' });
  }

  clear() {
    this.#sessionEpoch += 1;
    this.#session = null;
    this.#coreUrl = null;
    this.#mfaChallenge = null;
    this.#mfaExpiresAt = null;
  }

  async #authorizedJson(path, { method = 'GET', body = null } = {}, fallback = 'CORE_REQUEST_FAILED') {
    if (!this.#coreUrl || !this.accessToken) throw new Error('AUTHENTICATION_REQUIRED');
    const rid = requestId();
    const send = () => {
      const headers = { Authorization: `Bearer ${this.accessToken}`, 'X-Request-ID': rid };
      const init = { method, headers };
      if (body !== null) {
        headers['content-type'] = 'application/json';
        init.body = JSON.stringify(body);
      }
      return this.#fetch(`${this.#coreUrl}${path}`, init);
    };

    let response = await send();
    if (response.status === 401 && this.refreshToken) {
      await this.refresh(rid);
      response = await send();
    }
    const payload = await readJson(response);
    if (!response.ok) throw new Error(errorCode(payload, fallback));
    return payload;
  }

  #requireKnowledgeOrigin() {
    if (!this.#coreUrl || !this.accessToken) throw new Error('AUTHENTICATION_REQUIRED');
    return this.#coreUrl;
  }

  async #knowledgeRequest(url, { kind, notFound }) {
    const origin = this.#requireKnowledgeOrigin();
    const epoch = this.#sessionEpoch;
    const rid = requestId();
    const send = () => {
      if (epoch !== this.#sessionEpoch || this.#coreUrl !== origin || !this.accessToken) {
        throw new Error('KNOWLEDGE_SESSION_CHANGED');
      }
      return this.#fetch(url, {
        method: 'GET',
        headers: { Authorization: `Bearer ${this.accessToken}`, 'X-Request-ID': rid },
        redirect: 'error',
        cache: 'no-store',
        signal: AbortSignal.timeout(KNOWLEDGE_TIMEOUT_MS),
      });
    };

    let response;
    try {
      response = await send();
      if (response.status === 401 && this.refreshToken) {
        try { await this.refresh(rid); }
        catch {
          this.clear();
          throw new Error('AUTHENTICATION_REQUIRED');
        }
        if (epoch !== this.#sessionEpoch || this.#coreUrl !== origin) {
          throw new Error('KNOWLEDGE_SESSION_CHANGED');
        }
        response = await send();
      }
    } catch (error) {
      if (['AUTHENTICATION_REQUIRED', 'KNOWLEDGE_SESSION_CHANGED'].includes(error?.message)) throw error;
      if (error?.name === 'TimeoutError' || error?.name === 'AbortError') {
        throw new Error('KNOWLEDGE_TIMEOUT');
      }
      throw new Error('KNOWLEDGE_NETWORK_ERROR');
    }
    if (epoch !== this.#sessionEpoch || this.#coreUrl !== origin) {
      throw new Error('KNOWLEDGE_SESSION_CHANGED');
    }
    if (response.status === 401) {
      this.clear();
      throw new Error('AUTHENTICATION_REQUIRED');
    }
    if (response.status === 403) throw new Error('KNOWLEDGE_ACCESS_DENIED');
    if (response.status === 404) throw new Error(notFound);
    if (!response.ok) throw new Error('KNOWLEDGE_REQUEST_FAILED');

    const value = kind === 'bytes'
      ? await readBounded(response, KNOWLEDGE_MAX_BYTES)
      : await readBoundedJson(response);
    if (epoch !== this.#sessionEpoch || this.#coreUrl !== origin) {
      throw new Error('KNOWLEDGE_SESSION_CHANGED');
    }
    return value;
  }

  #setSession(coreUrl, payload, { refresh = false } = {}) {
    if (!payload || typeof payload.session_token !== 'string' || !payload.session_token ||
        typeof payload.refresh_token !== 'string' || !payload.refresh_token) {
      throw new Error('INVALID_SESSION_RESPONSE');
    }
    if (!refresh) this.#sessionEpoch += 1;
    this.#coreUrl = coreUrl;
    this.#mfaChallenge = null;
    this.#mfaExpiresAt = null;
    this.#session = {
      session_token: payload.session_token,
      refresh_token: payload.refresh_token,
      expires_at: payload.expires_at || null,
      scopes: Array.isArray(payload.scopes) ? payload.scopes : [],
    };
  }
}

async function readJson(response) {
  try { return await response.json(); } catch { return {}; }
}

function errorCode(payload, fallback) {
  if (payload && typeof payload.code === 'string' && payload.code) return payload.code;
  if (payload && typeof payload.detail === 'string' && payload.detail) return payload.detail;
  return fallback;
}

module.exports = { CoreSessionManager, normalizeCoreUrl, publicSession, requestId, isLoopbackHostname };
