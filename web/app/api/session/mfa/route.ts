import { NextRequest } from 'next/server';
import { completeMfaWeb } from '../../_lib/core-session';

export async function POST(request: NextRequest) {
  return completeMfaWeb(request);
}
