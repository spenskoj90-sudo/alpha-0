'use strict';

/** Revoke every account-bound runtime before accepting a replacement identity.
 * Keep cleanup bounded even if one subsystem throws; never reveal a token in
 * the error returned to the renderer. */
function revokeAccountBoundRuntime({
  session, companion, knowledge, wowBridge, overlayStore,
  resetEvidence, resetVoice, publishOverlay,
}, reason = 'ACCOUNT_LOGOUT') {
  let failed = false;
  const attempt = operation => {
    try { operation(); } catch { failed = true; }
  };
  // Invalidate pending Core requests first. The old worker must also be
  // stopped before the new login/MFA can install a replacement principal.
  attempt(() => session.clear());
  attempt(() => companion.stop(reason));
  attempt(() => knowledge?.logout());
  attempt(() => wowBridge?.stop());
  attempt(() => overlayStore.clear());
  attempt(() => resetEvidence());
  attempt(() => resetVoice('AUTHENTICATION_REQUIRED'));
  attempt(() => publishOverlay());
  if (failed) throw new Error('ACCOUNT_BOUNDARY_CLEANUP_FAILED');
}

module.exports = { revokeAccountBoundRuntime };
