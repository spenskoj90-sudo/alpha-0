import { randomUUID } from 'node:crypto';
import { NextRequest, NextResponse } from 'next/server';

export const ACCESS_COOKIE = 'sentinel_access';
export const REFRESH_COOKIE = 'sentinel_refresh';
const DEFAULT_REFRESH_MAX_AGE_SECONDS = 2_592_000;
const REQUEST_ID_PATTERN = /^[A-Za-z0-9._:-]{1,128}$/;
const TRACE_ID_PATTERN = /^[0-9a-f]{32}$/;

type SessionPayload = {
  session_token: string;
  refresh_token: string;
  expires_at: string;
  scopes: string[];
};

function configuredCoreUrl(): string | null {
  const value = process.env.SENTINEL_CORE_URL?.trim();
  if (!value) return null;
  try {
    return new URL(value).toString().replace(/\/$/, '');
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

async function coreFetch(coreUrl: string, path: string, requestId: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  headers.set('accept', 'application/json');
  headers.set('x-request-id', requestId);
  return fetch(`${coreUrl}${path}`, { ...init, headers, cache: 'no-store' });
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

async function refreshSession(coreUrl: string, refreshToken: string, requestId: string): Promise<SessionPayload | null> {
  const response = await coreFetch(coreUrl, '/v1/sessions/refresh', requestId, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!response.ok) return null;
  return parseSession(response);
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
      headers: { 'content-type': 'application/json' },
      body: await request.text(),
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
      if (refreshToken) clearSessionCookies(denied);
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
    if (refreshed) applySessionCookies(result, refreshed);
    if (upstream.status === 401) clearSessionCookies(result);
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
  return result;
}
