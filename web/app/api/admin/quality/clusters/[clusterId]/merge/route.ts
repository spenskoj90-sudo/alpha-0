import { NextRequest, NextResponse } from 'next/server';

function upstreamUrl() {
  const value = process.env.SENTINEL_CORE_URL?.trim();
  if (!value) return null;
  try { return new URL(value).toString().replace(/\/$/, ''); } catch { return null; }
}

export async function POST(request: NextRequest, context: { params: Promise<{ clusterId: string }> }) {
  const upstream = upstreamUrl();
  if (!upstream) return NextResponse.json({ error: 'SENTINEL_CORE_URL_NOT_CONFIGURED' }, { status: 503 });
  const token = request.headers.get('x-sentinel-admin-token');
  if (!token) return NextResponse.json({ error: 'ADMIN_ACCESS_DENIED' }, { status: 403 });
  const { clusterId } = await context.params;
  try {
    const response = await fetch(`${upstream}/v1/admin/quality/clusters/${encodeURIComponent(clusterId)}/merge`, {
      method: 'POST',
      headers: {
        accept: 'application/json',
        'content-type': 'application/json',
        'x-sentinel-admin-token': token,
      },
      body: await request.text(),
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
