import { NextRequest } from 'next/server';

const REQUIRED_CONTROL_HEADERS = [
  'x-sentinel-admin-token',
  'x-sentinel-admin-totp',
] as const;

export function readAdminAuthHeaders(request: NextRequest): Record<string, string> | null {
  const values = REQUIRED_CONTROL_HEADERS.map(name => [name, request.headers.get(name)?.trim()] as const);
  if (values.some(([, value]) => !value)) return null;
  return Object.fromEntries(values) as Record<string, string>;
}
