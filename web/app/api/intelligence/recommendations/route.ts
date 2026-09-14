import { NextRequest } from 'next/server';
import { proxyAuthenticated } from '../../_lib/core-session';

const COMMAND_CENTER_CONTEXT = {
  surface: 'web-command-center',
  data_quality: 'UNKNOWN',
  provenance: ['web-command-center:live-request'],
};

export async function POST(request: NextRequest) {
  return proxyAuthenticated(request, '/v1/recommendations', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ context: COMMAND_CENTER_CONTEXT }),
  }, true);
}
