package com.alpha0.app.security

import java.util.concurrent.atomic.AtomicReference

enum class KeyState { GENERATED, ACTIVE, ROTATING, REVOKED }

class KeyLifecycle(initial: KeyState = KeyState.GENERATED) {
    private val state = AtomicReference(initial)

    fun current(): KeyState = state.get()

    @Synchronized
    fun activate() {
        require(current() == KeyState.GENERATED) { "Only GENERATED keys can become ACTIVE" }
        state.set(KeyState.ACTIVE)
    }

    @Synchronized
    fun beginRotation() {
        require(current() == KeyState.ACTIVE) { "Only ACTIVE keys can rotate" }
        state.set(KeyState.ROTATING)
    }

    @Synchronized
    fun finishRotation() {
        require(current() == KeyState.ROTATING) { "Only ROTATING keys can finish rotation" }
        state.set(KeyState.ACTIVE)
    }

    @Synchronized
    fun revoke() {
        check(current() != KeyState.REVOKED) { "Key is already revoked" }
        state.set(KeyState.REVOKED)
    }
}
