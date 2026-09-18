import { NextRequest, NextResponse } from 'next/server';
import { readAdminAuthHeaders } from '../../_auth';

function upstreamUrl() {
  const value = process.env.SENTINEL_CORE_URL?.trim();
  if (!value) return null;
  try { return new URL(value).toString().replace(/\/$/, ''); } catch { return null; }
}

export async function GET(request: NextRequest) {
  const upstream = upstreamUrl();
  if (!upstream) return NextResponse.json({ error: 'SENTINEL_CORE_URL_NOT_CONFIGURED' }, { status: 503 });
  const adminHeaders = readAdminAuthHeaders(request);
  if (!adminHeaders) return NextResponse.json({ error: 'ADMIN_ACCESS_DENIED' }, { status: 403 });
  const query = new URLSearchParams();
  for (const key of ['limit', 'status', 'severity', 'category']) {
    const value = request.nextUrl.searchParams.get(key);
    if (value) query.set(key, value);
  }
  if (!query.has('limit')) query.set('limit', '100');
  try {
    const response = await fetch(`${upstream}/v1/admin/quality/clusters?${query.toString()}`, {
      headers: { accept: 'application/json', ...adminHeaders },
      cache: 'no-store',
    });
    return new NextResponse(await response.text(), {
      status: response.status,
      headers: { 'content-type': response.headers.get('content-type') ?? 'application/json', 'cache-control': 'no-store' },
    });
  } catch {
    return NextResponse.json({ error: 'SENTINEL_CORE_UNAVAILABLE' }, { status: 502 });
  }
}
