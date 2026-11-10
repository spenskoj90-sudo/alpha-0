'use strict';

const { sameSessionContext } = require('./voice-authorization');

/** Revokes a pending Companion launch on Stop, account change or newer launch. */
class CompanionStartFence {
  #generation = 0;

  begin(context) {
    const generation = ++this.#generation;
    if (!sameSessionContext(context, context)) return null;
    return Object.freeze({ origin: context.origin, sessionId: context.sessionId, generation });
  }

  revoke() { this.#generation += 1; }

  isCurrent(expected, context) {
    return expected != null && expected.generation === this.#generation &&
      sameSessionContext(expected, context) === true;
  }
}

module.exports = { CompanionStartFence };
