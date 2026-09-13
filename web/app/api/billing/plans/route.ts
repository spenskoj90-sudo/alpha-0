import { NextRequest } from 'next/server';
import { proxyAuthenticated } from '../../_lib/core-session';

export async function GET(request: NextRequest) {
  return proxyAuthenticated(request, '/v1/billing/plans');
}
