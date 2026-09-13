import { NextRequest, NextResponse } from 'next/server';

export const ACCESS_COOKIE = 'sentinel_access';
export const REFRESH_COOKIE = 'sentinel_refresh';
const DEFAULT_REFRESH_MAX_AGE_SECONDS = 2_592_000;

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

async function coreFetch(coreUrl: string, path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  headers.set('accept', 'application/json');
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

async function refreshSession(coreUrl: string, refreshToken: string): Promise<SessionPayload | null> {
  const response = await coreFetch(coreUrl, '/v1/sessions/refresh', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!response.ok) return null;
  return parseSession(response);
}

async function copyUpstream(response: Response): Promise<NextResponse> {
  return new NextResponse(await response.text(), {
    status: response.status,
    headers: {
      'content-type': response.headers.get('content-type') ?? 'application/json',
      'cache-control': 'no-store',
    },
  });
}

export async function authenticateWeb(request: NextRequest, mode: 'login' | 'register'): Promise<NextResponse> {
  if (!sameOriginWrite(request)) {
    return NextResponse.json({ error: 'CROSS_SITE_REQUEST_DENIED' }, { status: 403 });
  }
  const coreUrl = configuredCoreUrl();
  if (!coreUrl) {
    return NextResponse.json({ error: 'SENTINEL_CORE_URL_NOT_CONFIGURED' }, { status: 503 });
  }
  try {
    const response = await coreFetch(coreUrl, `/v1/auth/${mode}`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: await request.text(),
    });
    if (!response.ok) return copyUpstream(response);
    const session = await parseSession(response);
    if (!session) {
      return NextResponse.json({ error: 'INVALID_CORE_SESSION_RESPONSE' }, { status: 502 });
    }
    const result = NextResponse.json({
      authenticated: true,
      expires_at: session.expires_at,
      scopes: session.scopes,
    });
    applySessionCookies(result, session);
    return result;
  } catch {
    return NextResponse.json({ error: 'SENTINEL_CORE_UNAVAILABLE' }, { status: 502 });
  }
}

export async function proxyAuthenticated(
  request: NextRequest,
  path: string,
  init: RequestInit = {},
  requireSameOrigin = false,
): Promise<NextResponse> {
  if (requireSameOrigin && !sameOriginWrite(request)) {
    return NextResponse.json({ error: 'CROSS_SITE_REQUEST_DENIED' }, { status: 403 });
  }
  const coreUrl = configuredCoreUrl();
  if (!coreUrl) {
    return NextResponse.json({ error: 'SENTINEL_CORE_URL_NOT_CONFIGURED' }, { status: 503 });
  }

  const refreshToken = request.cookies.get(REFRESH_COOKIE)?.value;
  let accessToken = request.cookies.get(ACCESS_COOKIE)?.value;
  let refreshed: SessionPayload | null = null;

  try {
    if (!accessToken && refreshToken) {
      refreshed = await refreshSession(coreUrl, refreshToken);
      accessToken = refreshed?.session_token;
    }
    if (!accessToken) {
      const denied = NextResponse.json({ error: 'WEB_SESSION_REQUIRED' }, { status: 401 });
      if (refreshToken) clearSessionCookies(denied);
      return denied;
    }

    const invoke = (token: string) => {
      const headers = new Headers(init.headers);
      headers.set('authorization', `Bearer ${token}`);
      return coreFetch(coreUrl, path, { ...init, headers });
    };

    let upstream = await invoke(accessToken);
    if (upstream.status === 401 && refreshToken && !refreshed) {
      refreshed = await refreshSession(coreUrl, refreshToken);
      if (refreshed) {
        accessToken = refreshed.session_token;
        upstream = await invoke(accessToken);
      }
    }

    const result = await copyUpstream(upstream);
    if (refreshed) applySessionCookies(result, refreshed);
    if (upstream.status === 401) clearSessionCookies(result);
    return result;
  } catch {
    return NextResponse.json({ error: 'SENTINEL_CORE_UNAVAILABLE' }, { status: 502 });
  }
}

export async function logoutWeb(request: NextRequest): Promise<NextResponse> {
  if (!sameOriginWrite(request)) {
    return NextResponse.json({ error: 'CROSS_SITE_REQUEST_DENIED' }, { status: 403 });
  }
  const coreUrl = configuredCoreUrl();
  const accessToken = request.cookies.get(ACCESS_COOKIE)?.value;
  let serverRevoked = false;

  if (coreUrl && accessToken) {
    try {
      const response = await coreFetch(coreUrl, '/v1/sessions/revoke', {
        method: 'POST',
        headers: { authorization: `Bearer ${accessToken}` },
      });
      serverRevoked = response.ok;
    } catch {
      serverRevoked = false;
    }
  }

  const result = NextResponse.json({ authenticated: false, server_revoked: serverRevoked });
  clearSessionCookies(result);
  return result;
}
