import { NextRequest } from 'next/server';
import { passwordResetWeb } from '../../../_lib/core-session';

export async function POST(request: NextRequest, context: { params: Promise<{ step: string }> }) {
  const { step } = await context.params;
  return passwordResetWeb(request, step);
}
