'use strict';

const { sameSessionContext } = require('./voice-authorization');

/** Read-only snapshot of the current principal; never carry old entitlements
 * across a logout/login, even if the prior provider request resolves later. */
async function accountSnapshot(session) {
  const initialSession = session.status;
  if (!initialSession) return { session: null, features: [], mfa: session.mfaStatus };
  const original = session.knowledgeContext;
  if (!original) return { session: session.status, features: [], mfa: null };

  try {
    const payload = await session.featureStatus();
    if (!sameSessionContext(original, session.knowledgeContext)) {
      return { session: session.status, features: [], mfa: session.mfaStatus };
    }
    return {
      session: session.status,
      features: Array.isArray(payload?.features) ? payload.features : [],
      mfa: null,
    };
  } catch {
    return { session: session.status, features: [], mfa: session.mfaStatus };
  }
}

/** Generation-fenced publisher: a delayed response cannot overwrite a newer
 * account view, and logout invalidates all pending emissions immediately. */
function createAccountSnapshotPublisher(session, emit) {
  let generation = 0;
  return Object.freeze({
    revoke() { generation += 1; },
    async publish() {
      const request = ++generation;
      const snapshot = await accountSnapshot(session);
      if (generation !== request) return false;
      emit(snapshot);
      return true;
    },
  });
}

module.exports = { accountSnapshot, createAccountSnapshotPublisher };
