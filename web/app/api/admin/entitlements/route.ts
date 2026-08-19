import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  const upstream = process.env.SENTINEL_CORE_URL;
  if (!upstream) return NextResponse.json({ error: 'SENTINEL_CORE_URL_NOT_CONFIGURED' }, { status: 503 });
  const token = request.headers.get('x-sentinel-admin-token');
  if (!token) return NextResponse.json({ error: 'ADMIN_ACCESS_DENIED' }, { status: 403 });
  const body = await request.text();
  const response = await fetch(`${upstream}/v1/admin/entitlements`, { method: 'POST', headers: { 'content-type': 'application/json', 'x-sentinel-admin-token': token }, body, cache: 'no-store' });
  return new NextResponse(await response.text(), { status: response.status, headers: { 'content-type': response.headers.get('content-type') ?? 'application/json' } });
}
