import { createHash, randomUUID } from 'node:crypto';
import { NextRequest, NextResponse } from 'next/server';

export const ACCESS_COOKIE = 'sentinel_access';
export const REFRESH_COOKIE = 'sentinel_refresh';
export const MFA_COOKIE = 'sentinel_mfa';
const DEFAULT_REFRESH_MAX_AGE_SECONDS = 2_592_000;
const DEFAULT_MFA_MAX_AGE_SECONDS = 300;
const REQUEST_ID_PATTERN = /^[A-Za-z0-9._:-]{1,128}$/;
const TRACE_ID_PATTERN = /^[0-9a-f]{32}$/;
const CORE_TIMEOUT_MS = 45_000;
const MAX_CORE_RESPONSE_BYTES = 1_048_576;
const MAX_PENDING_REFRESHES = 256;

type SessionPayload = {
  session_token: string;
  refresh_token: string;
  expires_at: string;
  scopes: string[];
};

type MfaChallengePayload = {
  mfa_required: true;
  challenge_token: string;
  expires_at: string;
};

// Share pending work across route modules in one server process. Never retain a
// completed rotation: the Core refresh token remains one-use, with no grace cache.
const sessionGlobal = globalThis as typeof globalThis & {
  sentinelPendingRefreshes?: Map<string, Promise<SessionPayload | null>>;
};
const pendingRefreshes = sessionGlobal.sentinelPendingRefreshes ??= new Map();

function configuredCoreUrl(): string | null {
  const value = process.env.SENTINEL_CORE_URL?.trim();
  if (!value) return null;
  try {
    const url = new URL(value);
    if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password ||
        url.pathname !== '/' || url.search || url.hash) return null;
    return url.origin;
  } catch {
    return null;
  }
}

function cookieBaseOptions() {
  return {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict' as const,
    path: '/',
  };
}

function refreshMaxAgeSeconds(): number {
  const configured = Number.parseInt(process.env.SENTINEL_WEB_REFRESH_MAX_AGE_SECONDS ?? '', 10);
  return Number.isFinite(configured) && configured > 0 ? configured : DEFAULT_REFRESH_MAX_AGE_SECONDS;
}

export function normalizeCorrelationId(value: string | null | undefined): string {
  const candidate = value?.trim() ?? '';
  return REQUEST_ID_PATTERN.test(candidate) ? candidate : randomUUID();
}

function correlationId(request: NextRequest): string {
  return normalizeCorrelationId(request.headers.get('x-request-id'));
}

function applyCorrelation(response: NextResponse, requestId: string, upstream?: Response): NextResponse {
  const upstreamRequestId = upstream?.headers.get('x-request-id')?.trim() ?? '';
  response.headers.set('x-request-id', REQUEST_ID_PATTERN.test(upstreamRequestId) ? upstreamRequestId : requestId);
  const traceId = upstream?.headers.get('x-sentinel-trace-id')?.trim() ?? '';
  if (TRACE_ID_PATTERN.test(traceId)) response.headers.set('x-sentinel-trace-id', traceId);
  return response;
}

export function sameOriginWrite(request: NextRequest): boolean {
  const origin = request.headers.get('origin');
  if (!origin) return false;
  const configured = process.env.SENTINEL_WEB_ORIGIN?.trim().replace(/\/$/, '');
  const expected = configured || request.nextUrl.origin;
  return origin.replace(/\/$/, '') === expected;
}

export function applySessionCookies(response: NextResponse, session: SessionPayload): void {
  const expires = new Date(session.expires_at);
  response.cookies.set(ACCESS_COOKIE, session.session_token, {
    ...cookieBaseOptions(),
    expires: Number.isNaN(expires.getTime()) ? undefined : expires,
  });
  response.cookies.set(REFRESH_COOKIE, session.refresh_token, {
    ...cookieBaseOptions(),
    maxAge: refreshMaxAgeSeconds(),
  });
}

export function clearSessionCookies(response: NextResponse): void {
  response.cookies.set(ACCESS_COOKIE, '', { ...cookieBaseOptions(), maxAge: 0 });
  response.cookies.set(REFRESH_COOKIE, '', { ...cookieBaseOptions(), maxAge: 0 });
}

export function clearMfaCookie(response: NextResponse): void {
  response.cookies.set(MFA_COOKIE, '', { ...cookieBaseOptions(), maxAge: 0 });
}

function applyMfaCookie(response: NextResponse, challenge: MfaChallengePayload): void {
  const expires = new Date(challenge.expires_at);
  response.cookies.set(MFA_COOKIE, challenge.challenge_token, {
    ...cookieBaseOptions(),
    maxAge: Number.isNaN(expires.getTime()) ? DEFAULT_MFA_MAX_AGE_SECONDS : undefined,
    expires: Number.isNaN(expires.getTime()) ? undefined : expires,
  });
}

async function coreFetch(coreUrl: string, path: string, requestId: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  headers.set('accept', 'application/json');
  headers.set('x-request-id', requestId);
  const deadline = AbortSignal.timeout(CORE_TIMEOUT_MS);
  const signal = init.signal ? AbortSignal.any([init.signal, deadline]) : deadline;
  const response = await fetch(`${coreUrl}${path}`, { ...init, headers, signal, redirect: 'manual', cache: 'no-store' });
  if (response.status >= 300 && response.status < 400) {
    await response.body?.cancel();
    throw new Error('CORE_REDIRECT_DENIED');
  }
  if (!response.body) return response;
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  const abort = () => { void reader.cancel().catch(() => {}); };
  signal.addEventListener('abort', abort, { once: true });
  try {
    signal.throwIfAborted();
    while (true) {
      const { done, value } = await reader.read();
      signal.throwIfAborted();
      if (done) break;
      size += value.byteLength;
      if (size > MAX_CORE_RESPONSE_BYTES) throw new Error('CORE_RESPONSE_TOO_LARGE');
      chunks.push(value);
    }
    const bytes = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
    return new Response(bytes, { status: response.status, headers: response.headers });
  } catch (error) {
    await reader.cancel().catch(() => {});
    throw error;
  } finally {
    signal.removeEventListener('abort', abort);
    reader.releaseLock();
  }
}

async function parseSession(response: Response): Promise<SessionPayload | null> {
  try {
    const payload = await response.clone().json() as Partial<SessionPayload>;
    if (
      typeof payload.session_token !== 'string' ||
      typeof payload.refresh_token !== 'string' ||
      typeof payload.expires_at !== 'string' ||
      !Array.isArray(payload.scopes)
    ) return null;
    return payload as SessionPayload;
  } catch {
    return null;
  }
}

async function parseMfaChallenge(response: Response): Promise<MfaChallengePayload | null> {
  try {
    const payload = await response.clone().json() as Partial<MfaChallengePayload>;
    if (
      payload.mfa_required !== true ||
      typeof payload.challenge_token !== 'string' ||
      payload.challenge_token.length < 32 ||
      typeof payload.expires_at !== 'string'
    ) return null;
    return payload as MfaChallengePayload;
  } catch {
    return null;
  }
}

async function refreshSession(coreUrl: string, refreshToken: string, requestId: string): Promise<SessionPayload | null> {
  const key = createHash('sha256').update(coreUrl).update('\0').update(refreshToken).digest('hex');
  const pending = pendingRefreshes.get(key);
  if (pending) return pending;
  if (pendingRefreshes.size >= MAX_PENDING_REFRESHES) throw new Error('REFRESH_CAPACITY_EXCEEDED');
  const rotation = (async () => {
    const response = await coreFetch(coreUrl, '/v1/sessions/refresh', requestId, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!response.ok) return null;
    return parseSession(response);
  })();
  pendingRefreshes.set(key, rotation);
  try { return await rotation; }
  finally { pendingRefreshes.delete(key); }
}

async function copyUpstream(response: Response, requestId: string): Promise<NextResponse> {
  return applyCorrelation(new NextResponse(await response.text(), {
    status: response.status,
    headers: {
      'content-type': response.headers.get('content-type') ?? 'application/json',
      'cache-control': 'no-store',
    },
  }), requestId, response);
}

export async function authenticateWeb(request: NextRequest, mode: 'login' | 'register'): Promise<NextResponse> {
  const requestId = correlationId(request);
  if (!sameOriginWrite(request)) {
    return applyCorrelation(NextResponse.json({ error: 'CROSS_SITE_REQUEST_DENIED' }, { status: 403 }), requestId);
  }
  const coreUrl = configuredCoreUrl();
  if (!coreUrl) {
    return applyCorrelation(NextResponse.json({ error: 'SENTINEL_CORE_URL_NOT_CONFIGURED' }, { status: 503 }), requestId);
  }
  try {
    const response = await coreFetch(coreUrl, `/v1/auth/${mode}`, requestId, {
      method: 'POST',
      headers: { 'content-type': 'application/json', 'accept-language': request.headers.get('accept-language')?.toLowerCase().startsWith('ru') ? 'ru' : 'en' },
      body: await request.text(),
    });
    if (!response.ok) {
      const result = await copyUpstream(response, requestId);
      clearMfaCookie(result);
      return result;
    }
    const mfa = await parseMfaChallenge(response);
    if (mfa) {
      const result = applyCorrelation(NextResponse.json({
        mfa_required: true,
        expires_at: mfa.expires_at,
      }), requestId, response);
      clearSessionCookies(result);
      applyMfaCookie(result, mfa);
      return result;
    }
    const session = await parseSession(response);
    if (!session) {
      return applyCorrelation(NextResponse.json({ error: 'INVALID_CORE_SESSION_RESPONSE' }, { status: 502 }), requestId, response);
    }
    const result = applyCorrelation(NextResponse.json({
      authenticated: true,
      expires_at: session.expires_at,
      scopes: session.scopes,
    }), requestId, response);
    clearMfaCookie(result);
    applySessionCookies(result, session);
    return result;
  } catch {
    return applyCorrelation(NextResponse.json({ error: 'SENTINEL_CORE_UNAVAILABLE' }, { status: 502 }), requestId);
  }
}

export async function passwordResetWeb(request: NextRequest, step: string): Promise<NextResponse> {
  const requestId = correlationId(request);
  const reply = (body: object, status: number, upstream?: Response) => {
    const result = applyCorrelation(NextResponse.json(body, { status }), requestId, upstream);
    result.headers.set('cache-control', 'no-store');
    return result;
  };
  if (!sameOriginWrite(request)) return reply({ error: 'CROSS_SITE_REQUEST_DENIED' }, 403);
  if (step !== 'request' && step !== 'confirm') return reply({ error: 'RECOVERY_ROUTE_DENIED' }, 404);
  const coreUrl = configuredCoreUrl();
  if (!coreUrl) return reply({ error: 'SENTINEL_CORE_URL_NOT_CONFIGURED' }, 503);
  let body: { email: string } | { token: string; password: string; email?: string };
  try {
    const raw = await request.text();
    if (new TextEncoder().encode(raw).byteLength > 2048) return reply({ error: 'RECOVERY_INPUT_INVALID' }, 400);
    const input = JSON.parse(raw);
    if (step === 'request') {
      if (typeof input?.email !== 'string' || input.email.length < 3 || input.email.length > 320) return reply({ error: 'RECOVERY_INPUT_INVALID' }, 400);
      body = { email: input.email };
    } else {
      if (typeof input?.token !== 'string' || input.token.length > 512 ||
          typeof input?.password !== 'string' || input.password.length < 12 || input.password.length > 256) return reply({ error: 'RECOVERY_INPUT_INVALID' }, 400);
      const token = input.token.replace(/\s/g, '');
      const numeric = /^[0-9]{8}$/.test(token);
      if (!numeric && !/^[A-Za-z0-9_-]{32,512}$/.test(token)) return reply({ error: 'RECOVERY_INPUT_INVALID' }, 400);
      if ((numeric || input.email !== undefined) && (typeof input.email !== 'string' || input.email.length < 3 || input.email.length > 320 || !input.email.includes('@'))) return reply({ error: 'RECOVERY_INPUT_INVALID' }, 400);
      body = { token, password: input.password, ...(input.email !== undefined ? { email: input.email.trim().toLowerCase() } : {}) };
    }
  } catch {
    return reply({ error: 'RECOVERY_INPUT_INVALID' }, 400);
  }
  try {
    const upstream = await coreFetch(coreUrl, `/v1/auth/password-reset/${step}`, requestId, {
      method: 'POST', headers: { 'content-type': 'application/json', 'accept-language': request.headers.get('accept-language')?.toLowerCase().startsWith('ru') ? 'ru' : 'en' }, body: JSON.stringify(body),
      signal: AbortSignal.timeout(45_000), redirect: 'manual',
    });
    if (!upstream.ok) {
      if (upstream.status === 429) return reply({ error: 'RECOVERY_RATE_LIMITED' }, 429, upstream);
      if (upstream.status === 400 && step === 'confirm') return reply({ error: 'AUTH_ACTION_TOKEN_INVALID' }, 400, upstream);
      if (upstream.status === 422) return reply({ error: 'RECOVERY_INPUT_INVALID' }, 400, upstream);
      return reply({ error: 'SENTINEL_CORE_UNAVAILABLE' }, 502, upstream);
    }
    const payload = await upstream.json();
    const expected = step === 'request' ? 'ACCEPTED' : 'PASSWORD_UPDATED';
    if (payload?.status !== expected || upstream.status !== (step === 'request' ? 202 : 200)) return reply({ error: 'INVALID_CORE_RECOVERY_RESPONSE' }, 502, upstream);
    const result = reply({ status: expected }, upstream.status, upstream);
    if (step === 'confirm') {
      clearSessionCookies(result);
      clearMfaCookie(result);
    }
    return result;
  } catch {
    return reply({ error: 'SENTINEL_CORE_UNAVAILABLE' }, 502);
  }
}

export async function completeMfaWeb(request: NextRequest): Promise<NextResponse> {
  const requestId = correlationId(request);
  if (!sameOriginWrite(request)) {
    return applyCorrelation(NextResponse.json({ error: 'CROSS_SITE_REQUEST_DENIED' }, { status: 403 }), requestId);
  }
  const coreUrl = configuredCoreUrl();
  if (!coreUrl) {
    return applyCorrelation(NextResponse.json({ error: 'SENTINEL_CORE_URL_NOT_CONFIGURED' }, { status: 503 }), requestId);
  }
  const challengeToken = request.cookies.get(MFA_COOKIE)?.value;
  if (!challengeToken) {
    return applyCorrelation(NextResponse.json({ error: 'WEB_MFA_CHALLENGE_REQUIRED' }, { status: 401 }), requestId);
  }
  let code: string;
  try {
    const payload = await request.json() as { code?: unknown };
    code = typeof payload.code === 'string' ? payload.code.trim() : '';
  } catch {
    code = '';
  }
  if (code.length < 6 || code.length > 64) {
    return applyCorrelation(NextResponse.json({ error: 'MFA_CODE_INVALID' }, { status: 400 }), requestId);
  }
  try {
    const response = await coreFetch(coreUrl, '/v1/auth/mfa/complete', requestId, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ challenge_token: challengeToken, code }),
    });
    if (!response.ok) return copyUpstream(response, requestId);
    const session = await parseSession(response);
    if (!session) {
      return applyCorrelation(NextResponse.json({ error: 'INVALID_CORE_SESSION_RESPONSE' }, { status: 502 }), requestId, response);
    }
    const result = applyCorrelation(NextResponse.json({
      authenticated: true,
      expires_at: session.expires_at,
      scopes: session.scopes,
    }), requestId, response);
    clearMfaCookie(result);
    applySessionCookies(result, session);
    return result;
  } catch {
    return applyCorrelation(NextResponse.json({ error: 'SENTINEL_CORE_UNAVAILABLE' }, { status: 502 }), requestId);
  }
}

export async function proxyAuthenticated(
  request: NextRequest,
  path: string,
  init: RequestInit = {},
  requireSameOrigin = false,
): Promise<NextResponse> {
  const requestId = correlationId(request);
  if (requireSameOrigin && !sameOriginWrite(request)) {
    return applyCorrelation(NextResponse.json({ error: 'CROSS_SITE_REQUEST_DENIED' }, { status: 403 }), requestId);
  }
  const coreUrl = configuredCoreUrl();
  if (!coreUrl) {
    return applyCorrelation(NextResponse.json({ error: 'SENTINEL_CORE_URL_NOT_CONFIGURED' }, { status: 503 }), requestId);
  }

  const refreshToken = request.cookies.get(REFRESH_COOKIE)?.value;
  let accessToken = request.cookies.get(ACCESS_COOKIE)?.value;
  let refreshed: SessionPayload | null = null;

  try {
    if (!accessToken && refreshToken) {
      refreshed = await refreshSession(coreUrl, refreshToken, requestId);
      accessToken = refreshed?.session_token;
    }
    if (!accessToken) {
      const denied = applyCorrelation(NextResponse.json({ error: 'WEB_SESSION_REQUIRED' }, { status: 401 }), requestId);
      // A competing process may already have rotated this browser's cookies.
      // Passive denial cannot safely mutate them; explicit logout clears them.
      return denied;
    }

    const invoke = (token: string) => {
      const headers = new Headers(init.headers);
      headers.set('authorization', `Bearer ${token}`);
      return coreFetch(coreUrl, path, requestId, { ...init, headers });
    };

    let upstream = await invoke(accessToken);
    if (upstream.status === 401 && refreshToken && !refreshed) {
      refreshed = await refreshSession(coreUrl, refreshToken, requestId);
      if (refreshed) {
        accessToken = refreshed.session_token;
        upstream = await invoke(accessToken);
      }
    }

    const result = await copyUpstream(upstream, requestId);
    if (refreshed && upstream.status !== 401) applySessionCookies(result, refreshed);
    // Never erase cookies on a passive 401 that may arrive after a newer login.
    return result;
  } catch {
    return applyCorrelation(NextResponse.json({ error: 'SENTINEL_CORE_UNAVAILABLE' }, { status: 502 }), requestId);
  }
}

export async function logoutWeb(request: NextRequest): Promise<NextResponse> {
  const requestId = correlationId(request);
  if (!sameOriginWrite(request)) {
    return applyCorrelation(NextResponse.json({ error: 'CROSS_SITE_REQUEST_DENIED' }, { status: 403 }), requestId);
  }
  const coreUrl = configuredCoreUrl();
  const accessToken = request.cookies.get(ACCESS_COOKIE)?.value;
  let serverRevoked = false;
  let upstream: Response | undefined;

  if (coreUrl && accessToken) {
    try {
      upstream = await coreFetch(coreUrl, '/v1/sessions/revoke', requestId, {
        method: 'POST',
        headers: { authorization: `Bearer ${accessToken}` },
      });
      serverRevoked = upstream.ok;
    } catch {
      serverRevoked = false;
    }
  }

  const result = applyCorrelation(NextResponse.json({ authenticated: false, server_revoked: serverRevoked }), requestId, upstream);
  clearSessionCookies(result);
  clearMfaCookie(result);
  return result;
}
