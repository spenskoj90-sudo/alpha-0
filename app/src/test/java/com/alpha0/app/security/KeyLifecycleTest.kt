package com.alpha0.app.security

import org.junit.Assert.assertEquals
import org.junit.Test

class KeyLifecycleTest {
    @Test
    fun lifecycleTransitionsAreStrict() {
        val lifecycle = KeyLifecycle()
        assertEquals(KeyState.GENERATED, lifecycle.current())
        lifecycle.activate()
        assertEquals(KeyState.ACTIVE, lifecycle.current())
        lifecycle.beginRotation()
        assertEquals(KeyState.ROTATING, lifecycle.current())
        lifecycle.finishRotation()
        lifecycle.revoke()
        assertEquals(KeyState.REVOKED, lifecycle.current())
    }

    @Test(expected = IllegalArgumentException::class)
    fun cannotRotateGeneratedKey() {
        KeyLifecycle().beginRotation()
    }
}
