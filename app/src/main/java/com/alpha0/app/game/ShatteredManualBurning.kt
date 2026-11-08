package com.alpha0.app.game

/**
 * Reviewed Shattered 4.0.2 Burning/water mechanics in an explicitly manual,
 * hypothetical reference. Never a verified observation or game-action grant.
 */
internal object ShatteredManualBurning {
    enum class Outcome {
        UNSUPPORTED_VERSION, NEEDS_CONTEXT, NO_BURNING,
        FLYING_EXCEPTION, IN_WATER_MAY_EXTINGUISH,
        POSSIBLE_SAFE_WATER_ROUTE, NO_CONFIRMED_SAFE_WATER,
    }

    fun evaluate(
        versionName: String?, versionCode: Long?,
        burning: ShatteredManualHealing.Answer,
        flying: ShatteredManualHealing.Answer,
        inWater: ShatteredManualHealing.Answer,
        safeReachableWater: ShatteredManualHealing.Answer,
    ): Outcome = when {
        versionName != "4.0.2" || versionCode != 922L -> Outcome.UNSUPPORTED_VERSION
        burning == ShatteredManualHealing.Answer.UNKNOWN -> Outcome.NEEDS_CONTEXT
        burning == ShatteredManualHealing.Answer.NO -> Outcome.NO_BURNING
        flying == ShatteredManualHealing.Answer.UNKNOWN -> Outcome.NEEDS_CONTEXT
        flying == ShatteredManualHealing.Answer.YES -> Outcome.FLYING_EXCEPTION
        inWater == ShatteredManualHealing.Answer.UNKNOWN -> Outcome.NEEDS_CONTEXT
        inWater == ShatteredManualHealing.Answer.YES -> Outcome.IN_WATER_MAY_EXTINGUISH
        safeReachableWater == ShatteredManualHealing.Answer.UNKNOWN -> Outcome.NEEDS_CONTEXT
        safeReachableWater == ShatteredManualHealing.Answer.YES -> Outcome.POSSIBLE_SAFE_WATER_ROUTE
        else -> Outcome.NO_CONFIRMED_SAFE_WATER
    }
}
