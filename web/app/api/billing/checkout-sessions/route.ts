import { NextRequest, NextResponse } from 'next/server';
import { proxyAuthenticated, sameOriginWrite } from '../../_lib/core-session';

const PLAN_CODE = /^[A-Za-z0-9._-]{1,64}$/;

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
  if (typeof payload.plan_code !== 'string' || !PLAN_CODE.test(payload.plan_code)) {
    return NextResponse.json({ error: 'INVALID_PLAN_CODE' }, { status: 400 });
  }

  // The browser may select only the canonical SENTINEL plan code. Core owns
  // Stripe provider selection, price IDs, mode, redirect URLs and metadata.
  return proxyAuthenticated(request, '/v1/billing/checkout-sessions', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ plan_code: payload.plan_code }),
  });
}
