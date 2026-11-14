package com.alpha0.app.auth

import org.junit.Assert.*
import org.junit.Test

class GoogleClientIdPolicyTest {
    @Test fun signedFeedRequiresExactNonemptyReviewedId() {
        val pin = "123-client.apps.googleusercontent.com"
        assertTrue(googleClientIdAllowed(pin, pin))
        assertFalse(googleClientIdAllowed(pin, null))
        assertFalse(googleClientIdAllowed(pin, "other.apps.googleusercontent.com"))
        assertFalse(googleClientIdAllowed("", pin))
        assertFalse(googleClientIdAllowed("", ""))
    }
    @Test fun existingChannelsKeepServerManagedConfiguration() {
        assertTrue(googleClientIdAllowed(null, "other.apps.googleusercontent.com"))
        assertTrue(googleClientIdAllowed(null, null))
    }
}
