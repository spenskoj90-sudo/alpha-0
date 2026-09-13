import { NextRequest, NextResponse } from 'next/server';
import { proxyAuthenticated, sameOriginWrite } from '../../_lib/core-session';

export async function GET(request: NextRequest) {
  return proxyAuthenticated(request, '/v1/billing/subscriptions');
}

export async function POST(request: NextRequest) {
  if (!sameOriginWrite(request)) {
    return NextResponse.json({ error: 'CROSS_SITE_REQUEST_DENIED' }, { status: 403 });
  }

  let payload: { plan_code?: unknown };
  try {
    payload = await request.json() as { plan_code?: unknown };
  } catch {
    return NextResponse.json({ error: 'INVALID_JSON' }, { status: 400 });
  }
  if (typeof payload.plan_code !== 'string' || payload.plan_code.length === 0 || payload.plan_code.length > 64) {
    return NextResponse.json({ error: 'INVALID_PLAN_CODE' }, { status: 400 });
  }

  return proxyAuthenticated(request, '/v1/billing/subscriptions', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ plan_code: payload.plan_code, provider: 'manual' }),
  });
}
