import { NextRequest, NextResponse } from 'next/server';
import { readAdminAuthHeaders } from '../../_auth';

function upstreamUrl() {
  const value = process.env.SENTINEL_CORE_URL?.trim();
  if (!value) return null;
  try {
    return new URL(value).toString().replace(/\/$/, '');
  } catch {
    return null;
  }
}

async function proxy(request: NextRequest, reportId: string, method: 'GET' | 'POST') {
  const upstream = upstreamUrl();
  if (!upstream) return NextResponse.json({ error: 'SENTINEL_CORE_URL_NOT_CONFIGURED' }, { status: 503 });
  const adminHeaders = readAdminAuthHeaders(request);
  if (!adminHeaders) return NextResponse.json({ error: 'ADMIN_ACCESS_DENIED' }, { status: 403 });
  const suffix = method === 'POST' ? '/status' : '';
  try {
    const response = await fetch(`${upstream}/v1/admin/quality/reports/${encodeURIComponent(reportId)}${suffix}`, {
      method,
      headers: {
        accept: 'application/json',
        ...(method === 'POST' ? { 'content-type': 'application/json' } : {}),
        ...adminHeaders,
      },
      body: method === 'POST' ? await request.text() : undefined,
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

export async function GET(request: NextRequest, context: { params: Promise<{ reportId: string }> }) {
  const { reportId } = await context.params;
  return proxy(request, reportId, 'GET');
}

export async function POST(request: NextRequest, context: { params: Promise<{ reportId: string }> }) {
  const { reportId } = await context.params;
  return proxy(request, reportId, 'POST');
}
