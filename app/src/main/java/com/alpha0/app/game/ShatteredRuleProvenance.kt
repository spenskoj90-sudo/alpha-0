package com.alpha0.app.game

/** Exact public upstream source for manual-only rules. This does NOT certify
 * the captured window, game's actual status or permission to issue actions.
 */
internal object ShatteredRuleProvenance {
    const val VERSION_NAME = "4.0.2"
    const val VERSION_CODE = 922L
    const val HEALING_SOURCE =
        "https://github.com/00-Evan/shattered-pixel-dungeon/blob/v4.0.2/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/items/potions/PotionOfHealing.java"
    const val BURNING_SOURCE =
        "https://github.com/00-Evan/shattered-pixel-dungeon/blob/v4.0.2/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon/actors/buffs/Burning.java"

    fun supports(name: String?, code: Long?): Boolean =
        name == VERSION_NAME && code == VERSION_CODE
}
