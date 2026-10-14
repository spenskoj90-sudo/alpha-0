import { createHash, randomBytes, randomUUID } from 'node:crypto';
import { NextRequest, NextResponse } from 'next/server';

export const ACCESS_COOKIE = 'sentinel_access';
export const REFRESH_COOKIE = 'sentinel_refresh';
export const MFA_COOKIE = 'sentinel_mfa';
export const WEB_SESSION_COOKIE = 'sentinel_web_session';
export const WEB_GENERATION_COOKIE = 'sentinel_web_generation';
const DEFAULT_REFRESH_MAX_AGE_SECONDS = 2_592_000;
const DEFAULT_MFA_MAX_AGE_SECONDS = 300;
const REQUEST_ID_PATTERN = /^[A-Za-z0-9._:-]{1,128}$/;
const TRACE_ID_PATTERN = /^[0-9a-f]{32}$/;
const CORE_TIMEOUT_MS = 45_000;
const MAX_CORE_RESPONSE_BYTES = 1_048_576;
const MAX_PENDING_REFRESHES = 256;
const MAX_TRACKED_WEB_SESSIONS = 2048;
const WEB_SESSION_PATTERN = /^[A-Za-z0-9_-]{32,128}$/;

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
  sentinelPendingRefreshes?: Map<string, Promise<{ session: SessionPayload; generation: number } | null>>;
  sentinelWebGenerations?: Map<string, number>;
};
const pendingRefreshes = sessionGlobal.sentinelPendingRefreshes ??= new Map();
const webGenerations = sessionGlobal.sentinelWebGenerations ??= new Map();

type WebSessionContext = { family: string; generation: number; versioned: boolean };

function familyCookieKey(family: string): string {
  return createHash('sha256').update(family).digest('hex').slice(0, 16);
}

function versionedCookieName(base: string, family: string, generation: number): string {
  return `${base}_${familyCookieKey(family)}_${generation}`;
}

function versionedGeneration(request: NextRequest, family: string): number | null {
  const prefix = `${WEB_GENERATION_COOKIE}_${familyCookieKey(family)}_`;
  let latest: number | null = null;
  for (const cookie of request.cookies.getAll()) {
    if (!cookie.name.startsWith(prefix) || cookie.value !== '1') continue;
    const generation = Number(cookie.name.slice(prefix.length));
    if (Number.isSafeInteger(generation) && generation >= 0 && (latest === null || generation > latest)) {
      latest = generation;
    }
  }
  return latest;
}

function webSessionContext(request: NextRequest): WebSessionContext | null {
  let family = request.cookies.get(WEB_SESSION_COOKIE)?.value ?? '';
  if (!WEB_SESSION_PATTERN.test(family)) {
    // Independent anonymous responses write separate bootstrap cookies. They
    // never overwrite the family selected by a successful credential mutation.
    const bootstrap = request.cookies.getAll().find(cookie =>
      WEB_SESSION_PATTERN.test(cookie.value) &&
      cookie.name === `${WEB_SESSION_COOKIE}_${familyCookieKey(cookie.value)}`,
    );
    return bootstrap ? { family: bootstrap.value, generation: 0, versioned: true } : null;
  }
  const durableGeneration = versionedGeneration(request, family);
  const rawGeneration = durableGeneration === null
    ? request.cookies.get(WEB_GENERATION_COOKIE)?.value ?? '0'
    : String(durableGeneration);
  const generation = Number(rawGeneration);
  if (!Number.isSafeInteger(generation) || generation < 0) return null;
  return { family, generation, versioned: durableGeneration !== null };
}

function applyGenerationMarker(response: NextResponse, family: string, generation: number): void {
  response.cookies.set(versionedCookieName(WEB_GENERATION_COOKIE, family, generation), '1', {
    ...cookieBaseOptions(), maxAge: refreshMaxAgeSeconds(),
  });
}

function retireOlderGenerationCookies(
  request: NextRequest,
  response: NextResponse,
  family: string,
  generation: number,
): void {
  const key = familyCookieKey(family);
  for (const cookie of request.cookies.getAll()) {
    const base = [ACCESS_COOKIE, REFRESH_COOKIE, MFA_COOKIE, WEB_GENERATION_COOKIE]
      .find(candidate => cookie.name.startsWith(`${candidate}_${key}_`));
    if (!base) continue;
    const prior = Number(cookie.name.slice(`${base}_${key}_`.length));
    if (Number.isSafeInteger(prior) && prior >= 0 && prior < generation) {
      response.cookies.set(cookie.name, '', { ...cookieBaseOptions(), maxAge: 0 });
    }
  }
}

function applyWebSessionContext(response: NextResponse, family: string, generation: number): void {
  const bootstrapCookie = `${WEB_SESSION_COOKIE}_${familyCookieKey(family)}`;
  if (generation === 0) {
    response.cookies.set(bootstrapCookie, family, { ...cookieBaseOptions(), maxAge: refreshMaxAgeSeconds() });
    return;
  }
  response.cookies.set(bootstrapCookie, '', { ...cookieBaseOptions(), maxAge: 0 });
  response.cookies.set(WEB_SESSION_COOKIE, family, { ...cookieBaseOptions(), maxAge: refreshMaxAgeSeconds() });
  response.cookies.set(WEB_GENERATION_COOKIE, String(generation), { ...cookieBaseOptions(), maxAge: refreshMaxAgeSeconds() });
  applyGenerationMarker(response, family, generation);
}

function credentialCookie(request: NextRequest, base: string, context: WebSessionContext): string | undefined {
  const selected = request.cookies.get(
    context.versioned ? versionedCookieName(base, context.family, context.generation) : base,
  )?.value;
  // Keep the pre-family refresh proof available for explicit retirement during
  // bootstrap. Never restore legacy access/MFA authority or a positive generation.
  return selected ?? (base === REFRESH_COOKIE && context.generation === 0
    ? request.cookies.get(REFRESH_COOKIE)?.value : undefined);
}

function contextRequired(requestId: string): NextResponse {
  const response = applyCorrelation(NextResponse.json({ error: 'WEB_SESSION_CONTEXT_REQUIRED' }, { status: 409 }), requestId);
  applyWebSessionContext(response, randomBytes(32).toString('base64url'), 0);
  return response;
}

function responseGeneration(response: Response): number | null {
  const generation = Number(response.headers.get('x-sentinel-web-generation'));
  return Number.isSafeInteger(generation) && generation > 0 ? generation : null;
}

function acceptGeneration(coreUrl: string, family: string, generation: number): boolean {
  const key = createHash('sha256').update(coreUrl).update('\0').update(family).digest('hex');
  const current = webGenerations.get(key) ?? 0;
  if (generation < current) return false;
  if (!webGenerations.has(key) && webGenerations.size >= MAX_TRACKED_WEB_SESSIONS) {
    webGenerations.delete(webGenerations.keys().next().value as string);
  }
  webGenerations.set(key, generation);
  return true;
}

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

export function applySessionCookies(
  response: NextResponse,
  session: SessionPayload,
  generation?: number,
  family?: string,
): void {
  const accessCookie = generation !== undefined && family
    ? versionedCookieName(ACCESS_COOKIE, family, generation) : ACCESS_COOKIE;
  const refreshCookie = generation !== undefined && family
    ? versionedCookieName(REFRESH_COOKIE, family, generation) : REFRESH_COOKIE;
  const expires = new Date(session.expires_at);
  response.cookies.set(accessCookie, session.session_token, {
    ...cookieBaseOptions(),
    expires: Number.isNaN(expires.getTime()) ? undefined : expires,
  });
  response.cookies.set(refreshCookie, session.refresh_token, {
    ...cookieBaseOptions(),
    maxAge: refreshMaxAgeSeconds(),
  });
  if (generation !== undefined && family) {
    applyGenerationMarker(response, family, generation);
  } else if (generation !== undefined) {
    response.cookies.set(WEB_GENERATION_COOKIE, String(generation), { ...cookieBaseOptions(), maxAge: refreshMaxAgeSeconds() });
  }
}

export function clearSessionCookies(response: NextResponse): void {
  response.cookies.set(ACCESS_COOKIE, '', { ...cookieBaseOptions(), maxAge: 0 });
  response.cookies.set(REFRESH_COOKIE, '', { ...cookieBaseOptions(), maxAge: 0 });
}

export function clearMfaCookie(response: NextResponse): void {
  response.cookies.set(MFA_COOKIE, '', { ...cookieBaseOptions(), maxAge: 0 });
}

function applyMfaCookie(
  response: NextResponse,
  challenge: MfaChallengePayload,
  generation?: number,
  family?: string,
): void {
  const expires = new Date(challenge.expires_at);
  const cookie = generation !== undefined && family
    ? versionedCookieName(MFA_COOKIE, family, generation) : MFA_COOKIE;
  response.cookies.set(cookie, challenge.challenge_token, {
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

async function refreshSession(coreUrl: string, refreshToken: string, requestId: string, family: string): Promise<{ session: SessionPayload; generation: number } | null> {
  const key = createHash('sha256').update(coreUrl).update('\0').update(family).update('\0').update(refreshToken).digest('hex');
  const pending = pendingRefreshes.get(key);
  if (pending) return pending;
  if (pendingRefreshes.size >= MAX_PENDING_REFRESHES) throw new Error('REFRESH_CAPACITY_EXCEEDED');
  const rotation = (async (): Promise<{ session: SessionPayload; generation: number } | null> => {
    const response = await coreFetch(coreUrl, '/v1/sessions/refresh', requestId, {
      method: 'POST',
      headers: { 'content-type': 'application/json', 'x-sentinel-web-session': family },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!response.ok) return null;
    const session = await parseSession(response);
    const generation = responseGeneration(response);
    return session && generation ? { session, generation } : null;
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
  const existingContext = webSessionContext(request);
  const context = existingContext ?? {
    family: randomBytes(32).toString('base64url'), generation: 0, versioned: true,
  };
  let retiredLegacy = false;
  const finish = (result: NextResponse, generation = 0): NextResponse => {
    if (retiredLegacy) clearSessionCookies(result);
    if (!existingContext) applyWebSessionContext(result, context.family, generation);
    return result;
  };
  try {
    let expectedGeneration: number | undefined;
    const legacyRefresh = context.generation === 0 ? request.cookies.get(REFRESH_COOKIE)?.value : undefined;
    if (legacyRefresh) {
      // A replacement login must not abandon a still-live legacy refresh lineage.
      // Core consumes the proof and serializes its descendants before issuing any
      // new credentials. This explicit credential replacement also retires the
      // prior session when the following password check fails.
      const retired = await coreFetch(coreUrl, '/v1/sessions/web/revoke', requestId, {
        method: 'POST',
        headers: { 'content-type': 'application/json', 'x-sentinel-web-session': context.family },
        body: JSON.stringify({ refresh_token: legacyRefresh }),
      });
      const generation = responseGeneration(retired);
      retiredLegacy = retired.ok && generation !== null;
      if (!retired.ok || !generation || !acceptGeneration(coreUrl, context.family, generation)) {
        const conflicted = retired.status === 409 || (retired.ok && !!generation);
        const result = applyCorrelation(NextResponse.json({ error: conflicted
          ? 'WEB_SESSION_SUPERSEDED' : 'SENTINEL_CORE_UNAVAILABLE' }, { status: conflicted ? 409 : 502 }), requestId, retired);
        // An invalid/consumed proof must not trap subsequent login attempts. Only
        // fixed legacy cookies are cleared; newer versioned credentials survive.
        if (retired.status === 409) clearSessionCookies(result);
        return finish(result);
      }
      expectedGeneration = generation;
    }
    const response = await coreFetch(coreUrl, `/v1/auth/${mode}`, requestId, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'accept-language': request.headers.get('accept-language')?.toLowerCase().startsWith('ru') ? 'ru' : 'en',
        'x-sentinel-web-session': context.family,
        ...(expectedGeneration ? { 'x-sentinel-web-expected-generation': String(expectedGeneration) } : {}),
      },
      body: await request.text(),
    });
    if (!response.ok) {
      // A delayed failed login must not erase a newer MFA challenge.
      return finish(await copyUpstream(response, requestId));
    }
    const mfa = await parseMfaChallenge(response);
    if (mfa) {
      const generation = responseGeneration(response);
      if (!generation || !acceptGeneration(coreUrl, context.family, generation)) {
        return finish(applyCorrelation(NextResponse.json({ error: 'WEB_SESSION_SUPERSEDED' }, { status: 409 }), requestId, response));
      }
      const result = applyCorrelation(NextResponse.json({
        mfa_required: true,
        expires_at: mfa.expires_at,
      }), requestId, response);
      retireOlderGenerationCookies(request, result, context.family, generation);
      clearSessionCookies(result);
      applyMfaCookie(result, mfa, generation, context.family);
      applyWebSessionContext(result, context.family, generation);
      return finish(result, generation);
    }
    const session = await parseSession(response);
    if (!session) {
      return finish(applyCorrelation(NextResponse.json({ error: 'INVALID_CORE_SESSION_RESPONSE' }, { status: 502 }), requestId, response));
    }
    const generation = responseGeneration(response);
    if (!generation || !acceptGeneration(coreUrl, context.family, generation)) {
      return finish(applyCorrelation(NextResponse.json({ error: 'WEB_SESSION_SUPERSEDED' }, { status: 409 }), requestId, response));
    }
    const result = applyCorrelation(NextResponse.json({
      authenticated: true,
      expires_at: session.expires_at,
      scopes: session.scopes,
    }), requestId, response);
    retireOlderGenerationCookies(request, result, context.family, generation);
    clearSessionCookies(result);
    clearMfaCookie(result);
    applySessionCookies(result, session, generation, context.family);
    applyWebSessionContext(result, context.family, generation);
    return finish(result, generation);
  } catch {
    return finish(applyCorrelation(NextResponse.json({ error: 'SENTINEL_CORE_UNAVAILABLE' }, { status: 502 }), requestId));
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
  const context = step === 'confirm' ? webSessionContext(request) : null;
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
  if (step === 'confirm' && !context) return contextRequired(requestId);
  try {
    const upstream = await coreFetch(coreUrl, `/v1/auth/password-reset/${step}`, requestId, {
      method: 'POST', headers: {
        'content-type': 'application/json',
        'accept-language': request.headers.get('accept-language')?.toLowerCase().startsWith('ru') ? 'ru' : 'en',
        ...(context ? { 'x-sentinel-web-session': context.family } : {}),
      }, body: JSON.stringify(body),
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
      const generation = responseGeneration(upstream);
      if (!context) return reply({ error: 'WEB_SESSION_SUPERSEDED' }, 409, upstream);
      if (!generation || !acceptGeneration(coreUrl, context.family, generation)) {
        if (upstream.headers.get('x-sentinel-web-reset-revocation') !== 'identity') {
          return reply({ error: 'WEB_SESSION_SUPERSEDED' }, 409, upstream);
        }
        // Identity revocation is committed. Expire only credentials observed
        // by this request; leave newer family selectors/generations untouched.
        for (const base of [ACCESS_COOKIE, REFRESH_COOKIE, MFA_COOKIE]) {
          result.cookies.set(versionedCookieName(base, context.family, context.generation), '', { ...cookieBaseOptions(), maxAge: 0 });
        }
        clearSessionCookies(result);
        clearMfaCookie(result);
        return result;
      }
      retireOlderGenerationCookies(request, result, context.family, generation);
      clearSessionCookies(result);
      clearMfaCookie(result);
      applyWebSessionContext(result, context.family, generation);
    }
    return result;
  } catch {
    return reply({ error: 'SENTINEL_CORE_UNAVAILABLE' }, 502);
  }
}

/** Public, non-enumerating verification. This flow never issues or updates browser session cookies. */
export async function emailVerificationWeb(request: NextRequest, step: string): Promise<NextResponse> {
  const id = correlationId(request);
  const respond = (body: object, status: number, upstream?: Response) => {
    const result = applyCorrelation(NextResponse.json(body, { status }), id, upstream);
    result.headers.set('cache-control', 'no-store');
    return result;
  };
  if (!sameOriginWrite(request)) return respond({ error: 'CROSS_SITE_REQUEST_DENIED' }, 403);
  if (step !== 'request' && step !== 'confirm') return respond({ error: 'EMAIL_VERIFY_ROUTE_DENIED' }, 404);
  const core = configuredCoreUrl();
  if (!core) return respond({ error: 'SENTINEL_CORE_URL_NOT_CONFIGURED' }, 503);
  let body: { email: string; token?: string };
  try {
    const raw = await request.text();
    if (new TextEncoder().encode(raw).byteLength > 2048) return respond({ error: 'EMAIL_VERIFY_INPUT_INVALID' }, 400);
    const obj: unknown = JSON.parse(raw);
    if (!obj || typeof obj !== 'object' || Array.isArray(obj)) return respond({ error: 'EMAIL_VERIFY_INPUT_INVALID' }, 400);
    const input = obj as Record<string, unknown>;
    if (typeof input.email !== 'string' || input.email.length < 3 || input.email.length > 320) {
      return respond({ error: 'EMAIL_VERIFY_INPUT_INVALID' }, 400);
    }
    const email = input.email.trim().toLowerCase();
    if (email.length < 3 || !email.includes('@')) return respond({ error: 'EMAIL_VERIFY_INPUT_INVALID' }, 400);
    body = { email };
    if (step === 'confirm') {
      if (typeof input.token !== 'string' || input.token.length > 512) return respond({ error: 'EMAIL_VERIFY_INPUT_INVALID' }, 400);
      const token = input.token.replace(/\s/g, '');
      if (!/^[0-9]{8}$/.test(token) && !/^[A-Za-z0-9_-]{32,512}$/.test(token)) return respond({ error: 'EMAIL_VERIFY_INPUT_INVALID' }, 400);
      body.token = token;
    }
  } catch {
    return respond({ error: 'EMAIL_VERIFY_INPUT_INVALID' }, 400);
  }
  try {
    const upstream = await coreFetch(core, '/v1/auth/email-verification/' + step, id, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'accept-language': request.headers.get('accept-language')?.toLowerCase().startsWith('ru') ? 'ru' : 'en',
      },
      body: JSON.stringify(body),
    });
    if (!upstream.ok) {
      if (upstream.status === 429) return respond({ error: 'EMAIL_VERIFY_RATE_LIMITED' }, 429, upstream);
      if (step === 'confirm' && upstream.status === 400) return respond({ error: 'AUTH_ACTION_TOKEN_INVALID' }, 400, upstream);
      if (upstream.status === 422) return respond({ error: 'EMAIL_VERIFY_INPUT_INVALID' }, 400, upstream);
      return respond({ error: 'SENTINEL_CORE_UNAVAILABLE' }, 502, upstream);
    }
    const payload = await upstream.json();
    const expected = step === 'request' ? 'ACCEPTED' : 'VERIFIED';
    const status = step === 'request' ? 202 : 200;
    return upstream.status === status && payload?.status === expected
      ? respond({ status: expected }, status, upstream)
      : respond({ error: 'INVALID_CORE_EMAIL_VERIFY_RESPONSE' }, 502, upstream);
  } catch {
    return respond({ error: 'SENTINEL_CORE_UNAVAILABLE' }, 502);
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
  const context = webSessionContext(request);
  if (!context && !request.cookies.get(MFA_COOKIE)?.value) {
    return applyCorrelation(NextResponse.json({ error: 'WEB_MFA_CHALLENGE_REQUIRED' }, { status: 401 }), requestId);
  }
  if (!context || context.generation < 1) return contextRequired(requestId);
  const challengeToken = credentialCookie(request, MFA_COOKIE, context);
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
      headers: {
        'content-type': 'application/json',
        'x-sentinel-web-session': context.family,
        'x-sentinel-web-generation': String(context.generation),
      },
      body: JSON.stringify({ challenge_token: challengeToken, code }),
    });
    if (!response.ok) return copyUpstream(response, requestId);
    const session = await parseSession(response);
    if (!session) {
      return applyCorrelation(NextResponse.json({ error: 'INVALID_CORE_SESSION_RESPONSE' }, { status: 502 }), requestId, response);
    }
    const generation = responseGeneration(response);
    if (!generation || !acceptGeneration(coreUrl, context.family, generation)) {
      return applyCorrelation(NextResponse.json({ error: 'WEB_SESSION_SUPERSEDED' }, { status: 409 }), requestId, response);
    }
    const result = applyCorrelation(NextResponse.json({
      authenticated: true,
      expires_at: session.expires_at,
      scopes: session.scopes,
    }), requestId, response);
    retireOlderGenerationCookies(request, result, context.family, generation);
    clearMfaCookie(result);
    applySessionCookies(result, session, generation, context.family);
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

  let context = webSessionContext(request);
  let initializedContext = false;
  if (!context) {
    if (request.cookies.get(REFRESH_COOKIE)?.value) {
      const result = applyCorrelation(NextResponse.json({ error: 'WEB_SESSION_CONTEXT_REQUIRED' }, { status: 409 }), requestId);
      applyWebSessionContext(result, randomBytes(32).toString('base64url'), 0);
      return result;
    }
    // One bounded migration request may still carry a pre-family access cookie.
    // It has no refresh authority and the response establishes versioned state.
    context = { family: randomBytes(32).toString('base64url'), generation: 0, versioned: false };
    initializedContext = true;
  }
  const refreshToken = credentialCookie(request, REFRESH_COOKIE, context);
  let accessToken = credentialCookie(request, ACCESS_COOKIE, context);
  let refreshed: { session: SessionPayload; generation: number } | null = null;

  try {
    if (!accessToken && refreshToken) {
      refreshed = await refreshSession(coreUrl, refreshToken, requestId, context.family);
      accessToken = refreshed?.session.session_token;
    }
    if (!accessToken) {
      const denied = applyCorrelation(NextResponse.json({ error: 'WEB_SESSION_REQUIRED' }, { status: 401 }), requestId);
      // A competing process may already have rotated this browser's cookies.
      // Passive denial cannot safely mutate them; explicit logout clears them.
      if (initializedContext) applyWebSessionContext(denied, context.family, context.generation);
      return denied;
    }

    const invoke = (token: string) => {
      const headers = new Headers(init.headers);
      headers.set('authorization', `Bearer ${token}`);
      return coreFetch(coreUrl, path, requestId, { ...init, headers });
    };

    let upstream = await invoke(accessToken);
    if (upstream.status === 401 && refreshToken && !refreshed) {
      refreshed = await refreshSession(coreUrl, refreshToken, requestId, context.family);
      if (refreshed) {
        accessToken = refreshed.session.session_token;
        upstream = await invoke(accessToken);
      }
    }

    const result = await copyUpstream(upstream, requestId);
    if (refreshed && upstream.status !== 401 && acceptGeneration(coreUrl, context.family, refreshed.generation)) {
      applySessionCookies(result, refreshed.session, refreshed.generation, context.family);
    }
    if (initializedContext) applyWebSessionContext(result, context.family, context.generation);
    retireOlderGenerationCookies(request, result, context.family, refreshed?.generation ?? context.generation);
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
  if (!coreUrl) {
    return applyCorrelation(NextResponse.json({ error: 'SENTINEL_CORE_URL_NOT_CONFIGURED' }, { status: 503 }), requestId);
  }
  const context = webSessionContext(request);
  if (!context) return contextRequired(requestId);
  // Bare access is a revocation proof only, never a bootstrap read/auth fallback.
  const accessToken = credentialCookie(request, ACCESS_COOKIE, context) ??
    (context.generation === 0 ? request.cookies.get(ACCESS_COOKIE)?.value : undefined);
  const refreshToken = credentialCookie(request, REFRESH_COOKIE, context);
  let serverRevoked = false;
  let upstream: Response | undefined;

  try {
      upstream = await coreFetch(coreUrl, '/v1/sessions/web/revoke', requestId, {
        method: 'POST',
        headers: {
          ...(refreshToken ? { 'content-type': 'application/json' } : {}),
          'x-sentinel-web-session': context.family,
          ...(accessToken ? { authorization: `Bearer ${accessToken}` } : {}),
        },
        ...(refreshToken ? { body: JSON.stringify({ refresh_token: refreshToken }) } : {}),
      });
      serverRevoked = upstream.ok;
  } catch {
    serverRevoked = false;
  }
  if (!upstream?.ok) return applyCorrelation(NextResponse.json({ error: 'SENTINEL_CORE_UNAVAILABLE' }, { status: 502 }), requestId, upstream);
  const generation = responseGeneration(upstream);
  if (!generation || !acceptGeneration(coreUrl, context.family, generation)) {
    return applyCorrelation(NextResponse.json({ error: 'WEB_SESSION_SUPERSEDED' }, { status: 409 }), requestId, upstream);
  }
  const result = applyCorrelation(NextResponse.json({ authenticated: false, server_revoked: serverRevoked }), requestId, upstream);
  retireOlderGenerationCookies(request, result, context.family, generation);
  clearSessionCookies(result);
  clearMfaCookie(result);
  applyWebSessionContext(result, context.family, generation);
  return result;
}
