package com.alpha0.app.auth

/** Null preserves existing server-managed channels; empty disables signed-feed Google auth. */
internal fun googleClientIdAllowed(pin: String?, supplied: String?): Boolean =
    if (pin == null) true else pin.isNotEmpty() && supplied == pin
