import { NextRequest } from 'next/server';
import { authenticateWeb } from '../../_lib/core-session';

export async function POST(request: NextRequest) {
  return authenticateWeb(request, 'register');
}
