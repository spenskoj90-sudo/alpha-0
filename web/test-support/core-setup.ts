type SetupData = { session_token?: string; secret?: string; recovery_codes?: string[] };

// Node fetch avoids Playwright's credential-bearing request call logs. Never let
// transport or JSON errors (which can include payloads) reach retained reporters.
export async function coreSetupPost(url: string, data: object = {}, token?: string): Promise<{ status: number; data: SetupData }> {
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: JSON.stringify(data),
      signal: AbortSignal.timeout(45_000),
    });
    return { status: response.status, data: await response.json() as SetupData };
  } catch {
    throw new Error('Core test setup failed; sensitive request details redacted.');
  }
}

export async function redactSensitiveOperation<T>(operation: () => Promise<T>): Promise<T> {
  try {
    return await operation();
  } catch {
    throw new Error('Sensitive browser operation failed; credential details redacted.');
  }
}
