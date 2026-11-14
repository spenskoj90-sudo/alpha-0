'use strict';

/** Account-bound, consent-generation-bound voice authority; contains no token
 * or audio, and never grants game-action or network authority by itself. */
function sameSessionContext(a, b) {
  return a && b && typeof a.origin === 'string' && a.origin.length > 0 &&
    typeof a.sessionId === 'string' && a.sessionId.length > 0 &&
    a.origin === b.origin && a.sessionId === b.sessionId;
}

function bindVoiceRequest(context, consentGeneration) {
  if (!sameSessionContext(context, context) ||
      !Number.isSafeInteger(consentGeneration) || consentGeneration < 0) return null;
  return Object.freeze({
    origin: context.origin, sessionId: context.sessionId, consentGeneration,
  });
}

function voiceRequestStillCurrent(expected, context, consentGeneration, consentGranted, companionState) {
  return expected !== null && expected !== undefined &&
    sameSessionContext(expected, context) &&
    expected.consentGeneration === consentGeneration &&
    consentGranted === true &&
    companionState === 'ACTIVE';
}

module.exports = { sameSessionContext, bindVoiceRequest, voiceRequestStillCurrent };
