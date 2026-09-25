import { beforeEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';

import { GET as listReports } from './route';
import { GET as getReport, POST as updateReport } from './[reportId]/route';
import { GET as listClusters } from './clusters/route';
import { GET as getCluster, POST as updateCluster } from './clusters/[clusterId]/route';
import { POST as mergeCluster } from './clusters/[clusterId]/merge/route';

const ADMIN_HEADERS = {
  'x-sentinel-admin-token': 'admin-token',
  'x-sentinel-admin-totp': '123456',
};

function request(url: string, method = 'GET', body?: string, admin = true): NextRequest {
  return new NextRequest(url, {
    method,
    headers: {
      ...(admin ? ADMIN_HEADERS : {}),
      ...(body !== undefined ? { 'content-type': 'application/json' } : {}),
    },
    ...(body !== undefined ? { body } : {}),
  });
}

const reportContext = (reportId: string) => ({ params: Promise.resolve({ reportId }) });
const clusterContext = (clusterId: string) => ({ params: Promise.resolve({ clusterId }) });

describe('admin quality Web proxy surface', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  it('fails closed on every route when Core URL is absent or invalid', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'not a url');
    expect((await listReports(request('http://localhost/api/admin/quality'))).status).toBe(503);
    expect((await getReport(request('http://localhost/api/admin/quality/r'), reportContext('r'))).status).toBe(503);
    expect((await updateReport(request('http://localhost/api/admin/quality/r', 'POST', '{}'), reportContext('r'))).status).toBe(503);
    expect((await listClusters(request('http://localhost/api/admin/quality/clusters'))).status).toBe(503);
    expect((await getCluster(request('http://localhost/api/admin/quality/clusters/c'), clusterContext('c'))).status).toBe(503);
    expect((await updateCluster(request('http://localhost/api/admin/quality/clusters/c', 'POST', '{}'), clusterContext('c'))).status).toBe(503);
    expect((await mergeCluster(request('http://localhost/api/admin/quality/clusters/c/merge', 'POST', '{}'), clusterContext('c'))).status).toBe(503);
  });

  it('denies every route without both admin factors before fetch', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    const fetchMock = vi.spyOn(globalThis, 'fetch');
    expect((await listReports(request('http://localhost/api/admin/quality', 'GET', undefined, false))).status).toBe(403);
    expect((await getReport(request('http://localhost/api/admin/quality/r', 'GET', undefined, false), reportContext('r'))).status).toBe(403);
    expect((await updateReport(request('http://localhost/api/admin/quality/r', 'POST', '{}', false), reportContext('r'))).status).toBe(403);
    expect((await listClusters(request('http://localhost/api/admin/quality/clusters', 'GET', undefined, false))).status).toBe(403);
    expect((await getCluster(request('http://localhost/api/admin/quality/clusters/c', 'GET', undefined, false), clusterContext('c'))).status).toBe(403);
    expect((await updateCluster(request('http://localhost/api/admin/quality/clusters/c', 'POST', '{}', false), clusterContext('c'))).status).toBe(403);
    expect((await mergeCluster(request('http://localhost/api/admin/quality/clusters/c/merge', 'POST', '{}', false), clusterContext('c'))).status).toBe(403);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('forwards report list/read/status operations with bounded query and encoded IDs', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example/');
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async () => new Response('{"ok":true}', {
      status: 200,
      headers: { 'content-type': 'application/json' },
    }));

    const filtered = await listReports(request('http://localhost/api/admin/quality?status=OPEN&limit=25'));
    expect(filtered.status).toBe(200);
    expect(fetchMock.mock.calls[0]?.[0]).toBe('https://core.example/v1/admin/quality/reports?limit=25&status=OPEN');

    await listReports(request('http://localhost/api/admin/quality'));
    expect(fetchMock.mock.calls[1]?.[0]).toBe('https://core.example/v1/admin/quality/reports?limit=100');

    await getReport(request('http://localhost/api/admin/quality/report%2Fone'), reportContext('report/one'));
    expect(fetchMock.mock.calls[2]?.[0]).toBe('https://core.example/v1/admin/quality/reports/report%2Fone');
    expect(fetchMock.mock.calls[2]?.[1]?.method).toBe('GET');
    expect(fetchMock.mock.calls[2]?.[1]?.body).toBeUndefined();

    const body = JSON.stringify({ status: 'RESOLVED' });
    await updateReport(request('http://localhost/api/admin/quality/report%2Fone', 'POST', body), reportContext('report/one'));
    expect(fetchMock.mock.calls[3]?.[0]).toBe('https://core.example/v1/admin/quality/reports/report%2Fone/status');
    expect(fetchMock.mock.calls[3]?.[1]?.method).toBe('POST');
    expect(fetchMock.mock.calls[3]?.[1]?.body).toBe(body);
    expect(new Headers(fetchMock.mock.calls[3]?.[1]?.headers).get('content-type')).toBe('application/json');
  });

  it('forwards cluster list/read/update/merge with defaults and explicit filters', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async () => new Response('ok', { status: 200 }));

    await listClusters(request('http://localhost/api/admin/quality/clusters'));
    expect(fetchMock.mock.calls[0]?.[0]).toBe('https://core.example/v1/admin/quality/clusters?limit=100');

    await listClusters(request('http://localhost/api/admin/quality/clusters?limit=20&status=OPEN&severity=HIGH&category=CRASH'));
    const filteredUrl = String(fetchMock.mock.calls[1]?.[0]);
    expect(filteredUrl).toContain('limit=20');
    expect(filteredUrl).toContain('status=OPEN');
    expect(filteredUrl).toContain('severity=HIGH');
    expect(filteredUrl).toContain('category=CRASH');

    await getCluster(request('http://localhost/api/admin/quality/clusters/c%2F1'), clusterContext('c/1'));
    expect(fetchMock.mock.calls[2]?.[0]).toBe('https://core.example/v1/admin/quality/clusters/c%2F1');
    expect(fetchMock.mock.calls[2]?.[1]?.method).toBe('GET');

    const updateBody = JSON.stringify({ severity: 'CRITICAL' });
    await updateCluster(request('http://localhost/api/admin/quality/clusters/c%2F1', 'POST', updateBody), clusterContext('c/1'));
    expect(fetchMock.mock.calls[3]?.[1]?.method).toBe('POST');
    expect(fetchMock.mock.calls[3]?.[1]?.body).toBe(updateBody);

    const mergeBody = JSON.stringify({ target_cluster_id: 'c2' });
    await mergeCluster(request('http://localhost/api/admin/quality/clusters/c%2F1/merge', 'POST', mergeBody), clusterContext('c/1'));
    expect(fetchMock.mock.calls[4]?.[0]).toBe('https://core.example/v1/admin/quality/clusters/c%2F1/merge');
    expect(fetchMock.mock.calls[4]?.[1]?.method).toBe('POST');
    expect(fetchMock.mock.calls[4]?.[1]?.body).toBe(mergeBody);
    expect(new Headers(fetchMock.mock.calls[4]?.[1]?.headers).get('x-sentinel-admin-token')).toBe('admin-token');
  });

  it('maps transport failure to bounded 502 on every quality route', async () => {
    vi.stubEnv('SENTINEL_CORE_URL', 'https://core.example');
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('network down'));

    expect((await listReports(request('http://localhost/api/admin/quality'))).status).toBe(502);
    expect((await getReport(request('http://localhost/api/admin/quality/r'), reportContext('r'))).status).toBe(502);
    expect((await updateReport(request('http://localhost/api/admin/quality/r', 'POST', '{}'), reportContext('r'))).status).toBe(502);
    expect((await listClusters(request('http://localhost/api/admin/quality/clusters'))).status).toBe(502);
    expect((await getCluster(request('http://localhost/api/admin/quality/clusters/c'), clusterContext('c'))).status).toBe(502);
    expect((await updateCluster(request('http://localhost/api/admin/quality/clusters/c', 'POST', '{}'), clusterContext('c'))).status).toBe(502);
    expect((await mergeCluster(request('http://localhost/api/admin/quality/clusters/c/merge', 'POST', '{}'), clusterContext('c'))).status).toBe(502);
  });
});
