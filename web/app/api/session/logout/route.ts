import { NextRequest } from 'next/server';
import { logoutWeb } from '../../_lib/core-session';

export async function POST(request: NextRequest) {
  return logoutWeb(request);
}
