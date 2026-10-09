import { NextRequest } from 'next/server';
import { emailVerificationWeb } from '../../../_lib/core-session';

export async function POST(request: NextRequest, context: { params: Promise<{ step: string }> }) {
  const { step } = await context.params;
  return emailVerificationWeb(request, step);
}
