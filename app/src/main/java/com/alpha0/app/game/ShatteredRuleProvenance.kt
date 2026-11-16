package com.alpha0.app.game

/** Exact public upstream source for manual-only rules. This does NOT certify
 * the captured window, game's actual status or permission to issue actions.
 */
internal object ShatteredRuleProvenance {
    const val VERSION_NAME = "4.0.2"
    const val VERSION_CODE = 922L
    /** Immutable upstream tag target, independently resolved for v4.0.2. */
    const val SOURCE_COMMIT = "57a4e06a4caf162446d1c28caa7983f0493fecf0"
    val SOURCE_SHORT_REVISION: String get() = SOURCE_COMMIT.take(12)
    const val HEALING_SOURCE =
        "https://github.com/00-Evan/shattered-pixel-dungeon/blob/${SOURCE_COMMIT}/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/potions/PotionOfHealing.java"
    const val BURNING_SOURCE =
        "https://github.com/00-Evan/shattered-pixel-dungeon/blob/${SOURCE_COMMIT}/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/buffs/Burning.java"

    fun supports(name: String?, code: Long?): Boolean =
        name == VERSION_NAME && code == VERSION_CODE
}
