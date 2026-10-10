import { NextRequest, NextResponse } from 'next/server';
import { proxyAuthenticated, sameOriginWrite } from '../../../_lib/core-session';

// Core validates caller-device ownership and revokes server-side.
const DEVICE_ID = /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/;

export async function POST(request: NextRequest, context: { params: Promise<{ deviceId: string }> }) {
  if (!sameOriginWrite(request)) {
    return NextResponse.json({ error: 'CROSS_SITE_REQUEST_DENIED' }, { status: 403, headers: { 'cache-control': 'no-store' } });
  }
  const { deviceId } = await context.params;
  if (!DEVICE_ID.test(deviceId)) {
    return NextResponse.json({ error: 'DEVICE_ID_INVALID' }, { status: 400, headers: { 'cache-control': 'no-store' } });
  }
  return proxyAuthenticated(request, '/v1/devices/' + deviceId.toLowerCase() + '/revoke', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
  }, true);
}
