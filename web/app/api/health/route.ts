import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function GET() {
  const sourceSha = [process.env.RENDER_GIT_COMMIT, process.env.GITHUB_SHA]
    .find(value => typeof value === 'string' && /^[0-9a-f]{40}$/.test(value)) ?? null;
  return NextResponse.json({ service: 'sentinel-web', sourceSha }, {
    headers: { 'cache-control': 'no-store' },
  });
}
