package com.alpha0.app.game

/**
 * Offline, manually entered *hypothetical* game-rule reference. It must never
 * consume OCR or upgrade manual answers to a trusted observation/action intent.
 */
internal object ShatteredManualHealing {
    enum class Answer { UNKNOWN, YES, NO }
    enum class Outcome { UNSUPPORTED_VERSION, NEEDS_CONTEXT, POISON_WARNING, POSSIBLE_OPTION, NO_RULE_MATCH }

    fun evaluate(
        versionName: String?, versionCode: Long?,
        lowHealth: Answer, pharmacophobia: Answer, knownPotion: Answer,
    ): Outcome = when {
        versionName != "4.0.2" || versionCode != 922L -> Outcome.UNSUPPORTED_VERSION
        pharmacophobia == Answer.YES -> Outcome.POISON_WARNING
        lowHealth == Answer.UNKNOWN || pharmacophobia == Answer.UNKNOWN || knownPotion == Answer.UNKNOWN ->
            Outcome.NEEDS_CONTEXT
        lowHealth == Answer.YES && pharmacophobia == Answer.NO && knownPotion == Answer.YES ->
            Outcome.POSSIBLE_OPTION
        else -> Outcome.NO_RULE_MATCH
    }
}
