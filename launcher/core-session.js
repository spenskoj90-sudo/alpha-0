'use strict';

const { URL } = require('node:url');

function normalizeCoreUrl(value) {
  const url = new URL(String(value || '').trim());
  if (!['http:', 'https:'].includes(url.protocol)) throw new Error('INVALID_CORE_URL');
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

class CoreSessionManager {
  #fetch;
  #session = null;
  #coreUrl = null;

  constructor({ fetchImpl = globalThis.fetch } = {}) {
    if (typeof fetchImpl !== 'function') throw new Error('FETCH_UNAVAILABLE');
    this.#fetch = fetchImpl;
  }

  get coreUrl() { return this.#coreUrl; }
  get accessToken() { return this.#session?.session_token || null; }
  get refreshToken() { return this.#session?.refresh_token || null; }
  get status() { return publicSession(this.#session); }

  async login({ coreUrl, email, password }) {
    const normalized = normalizeCoreUrl(coreUrl);
    if (typeof email !== 'string' || !email.trim() || typeof password !== 'string' || !password) {
      throw new Error('CREDENTIALS_REQUIRED');
    }
    const response = await this.#fetch(`${normalized}/v1/auth/login`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ email: email.trim(), password }),
    });
    const payload = await readJson(response);
    if (!response.ok) throw new Error(errorCode(payload, 'LOGIN_FAILED'));
    this.#setSession(normalized, payload);
    return this.status;
  }

  async refresh() {
    if (!this.#coreUrl || !this.refreshToken) throw new Error('REFRESH_UNAVAILABLE');
    const response = await this.#fetch(`${this.#coreUrl}/v1/sessions/refresh`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ refresh_token: this.refreshToken }),
    });
    const payload = await readJson(response);
    if (!response.ok) {
      this.clear();
      throw new Error(errorCode(payload, 'REFRESH_FAILED'));
    }
    this.#setSession(this.#coreUrl, payload);
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

  clear() {
    this.#session = null;
    this.#coreUrl = null;
  }

  async #authorizedJson(path, { method = 'GET', body = null } = {}, fallback = 'CORE_REQUEST_FAILED') {
    if (!this.#coreUrl || !this.accessToken) throw new Error('AUTHENTICATION_REQUIRED');
    const send = () => {
      const headers = { Authorization: `Bearer ${this.accessToken}` };
      const init = { method, headers };
      if (body !== null) {
        headers['content-type'] = 'application/json';
        init.body = JSON.stringify(body);
      }
      return this.#fetch(`${this.#coreUrl}${path}`, init);
    };

    let response = await send();
    if (response.status === 401 && this.refreshToken) {
      await this.refresh();
      response = await send();
    }
    const payload = await readJson(response);
    if (!response.ok) throw new Error(errorCode(payload, fallback));
    return payload;
  }

  #setSession(coreUrl, payload) {
    if (!payload || typeof payload.session_token !== 'string' || !payload.session_token ||
        typeof payload.refresh_token !== 'string' || !payload.refresh_token) {
      throw new Error('INVALID_SESSION_RESPONSE');
    }
    this.#coreUrl = coreUrl;
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

module.exports = { CoreSessionManager, normalizeCoreUrl, publicSession };
