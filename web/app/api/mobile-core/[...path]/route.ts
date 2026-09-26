import { NextRequest, NextResponse } from 'next/server';

const MAX_BODY_BYTES = 1_048_576;
const MAX_RESPONSE_BYTES = 1_048_576;
const REQUEST_ID_PATTERN = /^[A-Za-z0-9._:-]{1,128}$/;
const TRACE_ID_PATTERN = /^[0-9a-f]{32}$/;
const ALLOWED_PREFIXES = [
  '/v1/auth/',
  '/v1/account/',
  '/v1/devices/',
  '/v1/entitlements/',
  '/v1/quality/reports',
];
const ALLOWED_EXACT = new Set([
  '/v1/auth/providers',
  '/v1/audit',
  '/v1/devices/bind',
  '/v1/devices/recover',
  '/v1/entitlements/me',
  '/v1/events:batch',
  '/v1/sessions/refresh',
  '/v1/sessions/revoke',
]);

function coreOrigin(): string | null {
  const value = process.env.SENTINEL_CORE_URL?.trim();
  if (!value) return null;
  try {
    const parsed = new URL(value);
    if (parsed.protocol !== 'https:' || parsed.username || parsed.password || parsed.search || parsed.hash) return null;
    if (parsed.pathname !== '/' && parsed.pathname !== '') return null;
    return parsed.origin;
  } catch {
    return null;
  }
}

function mobilePath(parts: string[]): string | null {
  if (!Array.isArray(parts) || parts.length === 0) return null;
  const path = '/' + parts.map((part) => encodeURIComponent(part)).join('/');
  if (ALLOWED_EXACT.has(path) || ALLOWED_PREFIXES.some((prefix) => path.startsWith(prefix))) return path;
  return null;
}

function copyRequestHeaders(request: NextRequest): Headers {
  const headers = new Headers();
  for (const name of ['accept', 'content-type', 'authorization', 'x-request-id', 'idempotency-key']) {
    const value = request.headers.get(name);
    if (value && value.length <= 8192) headers.set(name, value);
  }
  return headers;
}

async function proxy(request: NextRequest, parts: string[], method: 'GET' | 'POST') {
  const origin = coreOrigin();
  if (!origin) return NextResponse.json({ error: 'SENTINEL_CORE_URL_NOT_CONFIGURED' }, { status: 503 });

  const path = mobilePath(parts);
  if (!path) return NextResponse.json({ error: 'MOBILE_RELAY_ROUTE_DENIED' }, { status: 404 });

  let body: Uint8Array | undefined;
  if (method === 'POST') {
    const declared = Number.parseInt(request.headers.get('content-length') ?? '', 10);
    if (Number.isFinite(declared) && declared > MAX_BODY_BYTES) {
      return NextResponse.json({ error: 'REQUEST_TOO_LARGE' }, { status: 413 });
    }
    body = new Uint8Array(await request.arrayBuffer());
    if (body.byteLength > MAX_BODY_BYTES) {
      return NextResponse.json({ error: 'REQUEST_TOO_LARGE' }, { status: 413 });
    }
  }

  try {
    const upstream = await fetch(origin + path, {
      method,
      headers: copyRequestHeaders(request),
      body,
      cache: 'no-store',
      redirect: 'manual',
    });
    const bytes = new Uint8Array(await upstream.arrayBuffer());
    if (bytes.byteLength > MAX_RESPONSE_BYTES) {
      return NextResponse.json({ error: 'UPSTREAM_RESPONSE_TOO_LARGE' }, { status: 502 });
    }
    const headers = new Headers({
      'content-type': upstream.headers.get('content-type') ?? 'application/json',
      'cache-control': 'no-store',
    });
    const requestId = upstream.headers.get('x-request-id')?.trim() ?? '';
    if (REQUEST_ID_PATTERN.test(requestId)) headers.set('x-request-id', requestId);
    const traceId = upstream.headers.get('x-sentinel-trace-id')?.trim() ?? '';
    if (TRACE_ID_PATTERN.test(traceId)) headers.set('x-sentinel-trace-id', traceId);
    return new NextResponse(bytes, { status: upstream.status, headers });
  } catch {
    return NextResponse.json({ error: 'SENTINEL_CORE_UNAVAILABLE' }, { status: 502 });
  }
}

type RouteContext = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxy(request, path, 'GET');
}

export async function POST(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxy(request, path, 'POST');
}
