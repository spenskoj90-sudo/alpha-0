'use strict';

const path = require('node:path');
const { createHash } = require('node:crypto');
const { KnowledgeRuntime, validProfile } = require('./knowledge-runtime');

// Main-process closures supply target authority. Public methods accept no
// profile/observation arguments, so renderer assertions cannot create trust.
class KnowledgePresentation {
  #directory; #session; #context; #observation; #factory; #onChange;
  #runtime = null; #origin = null; #binding = null; #active = false;
  #epoch = 0; #pending = false; #timer = null; #state = 'STOPPED';

  constructor({ directory, session, getTrustedContext, getTrustedObservation,
    createRuntime = options => new KnowledgeRuntime(options), onChange = () => {} }) {
    if (!directory || !session || typeof getTrustedContext !== 'function' ||
        typeof getTrustedObservation !== 'function') throw new Error('KNOWLEDGE_LIFECYCLE_INVALID');
    this.#directory = directory; this.#session = session;
    this.#context = getTrustedContext; this.#observation = getTrustedObservation;
    this.#factory = createRuntime; this.#onChange = onChange;
  }

  #trusted() {
    const session = this.#session.knowledgeContext;
    const target = this.#context();
    if (!session || !target || !validProfile(target.profile) ||
        typeof target.sourceId !== 'string' || !target.sourceId || target.sourceId.length > 256) return null;
    return { ...session, profile: { ...target.profile }, sourceId: target.sourceId };
  }

  #key(context) {
    return JSON.stringify([context.origin, context.sessionId, context.sourceId, context.profile]);
  }

  #schedule() {
    if (!this.#active || this.#timer) return;
    this.#timer = setTimeout(() => { this.#timer = null; void this.refresh(); }, 30000);
    this.#timer.unref?.();
  }

  #emit() { this.#onChange(this.status()); }

  async start() {
    this.#active = true;
    return this.refresh();
  }

  stop(reason = 'STOPPED') {
    this.#active = false; this.#epoch += 1;
    if (this.#timer) clearTimeout(this.#timer);
    this.#timer = null;
    this.#session.cancelKnowledge(); this.#runtime?.clear();
    this.#binding = null; this.#state = reason; this.#emit();
  }

  logout() { this.stop('SIGNED_OUT'); }
  deny() { this.stop('DENIED'); }

  status() {
    const authenticated = Boolean(this.#session.knowledgeContext);
    const lease = this.#runtime?.status();
    let state = authenticated ? this.#state : 'SIGNED_OUT';
    if (['READY', 'DEGRADED'].includes(state)) {
      const current = this.#trusted();
      if (!current || this.#key(current) !== this.#binding) state = 'WAITING_FOR_VERIFIED_PROFILE';
    }
    if (['READY', 'DEGRADED'].includes(state) && lease?.status !== 'ready') state = 'UNAVAILABLE';
    return Object.freeze({ state, actionAuthority: false,
      digest: ['READY', 'DEGRADED'].includes(state) ? lease.digest : null,
      remainingLeaseMs: ['READY', 'DEGRADED'].includes(state) ? lease.remainingLeaseMs : null });
  }

  presentations(locale = 'en') {
    if (!this.#active || !['READY', 'DEGRADED'].includes(this.status().state)) return [];
    const trusted = this.#trusted();
    if (!trusted || this.#key(trusted) !== this.#binding) return [];
    const current = this.#observation();
    if (!current || current.sourceId !== trusted.sourceId) return [];
    return this.#runtime.evaluate(current.observation, { sessionId: trusted.sessionId, locale }).items;
  }

  async refresh() {
    if (!this.#active || this.#pending) return this.status();
    if (!this.#session.knowledgeContext) { this.logout(); return this.status(); }
    const context = this.#trusted();
    if (!context) {
      this.#runtime?.clear(); this.#binding = null;
      this.#state = 'WAITING_FOR_VERIFIED_PROFILE'; this.#emit(); this.#schedule();
      return this.status();
    }
    const binding = this.#key(context);
    if (this.#binding !== binding) { this.#runtime?.clear(); this.#binding = binding; }
    if (!this.#runtime || this.#origin !== context.origin) {
      const session = this.#session;
      this.#origin = context.origin;
      try { this.#runtime = this.#factory({
        directory: path.join(this.#directory, createHash('sha256').update(context.origin).digest('hex')),
        authority: context.origin,
        transport: {
          manifest: (profile, digest) => session.knowledgeManifest(profile, digest),
          pack: (profile, digest) => session.knowledgePack(profile, digest),
          delta: (profile, destination, base) => session.knowledgeDelta(profile, destination, base),
        },
      }); } catch {
        this.#runtime = null; this.#state = 'UNAVAILABLE';
        this.#emit(); this.#schedule(); return this.status();
      }
    }
    const epoch = this.#epoch;
    this.#pending = true;
    try {
      const result = await this.#runtime.refresh(context.profile, context.sessionId);
      if (epoch !== this.#epoch || !this.#active) return this.status();
      const latest = this.#trusted();
      if (!latest || this.#key(latest) !== binding) {
        this.#runtime.clear(); this.#state = 'WAITING_FOR_VERIFIED_PROFILE';
      } else this.#state = result.status === 'ready' ? 'READY' : 'UNAVAILABLE';
    } catch (error) {
      if (epoch !== this.#epoch) return this.status();
      if (['AUTHENTICATION_REQUIRED', 'KNOWLEDGE_ACCESS_DENIED'].includes(error?.message)) this.deny();
      else if (['KNOWLEDGE_NETWORK_ERROR', 'KNOWLEDGE_TIMEOUT'].includes(error?.message)) this.#state = 'DEGRADED';
      else { this.#runtime.clear(); this.#state = 'UNAVAILABLE'; }
    } finally {
      this.#pending = false; this.#emit(); this.#schedule();
    }
    return this.status();
  }
}

module.exports = { KnowledgePresentation };
