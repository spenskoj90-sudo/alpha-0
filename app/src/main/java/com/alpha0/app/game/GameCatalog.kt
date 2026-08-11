package com.alpha0.app.game

data class SentinelGame(val id: String, val name: String, val platform: String)

object GameCatalog {
    val diablo: List<SentinelGame> = listOf(
        SentinelGame("diablo-1-pc", "Diablo", "Windows"),
        SentinelGame("diablo-2-pc", "Diablo II", "Windows"),
        SentinelGame("diablo-2-resurrected-pc", "Diablo II: Resurrected", "Windows"),
        SentinelGame("diablo-3-pc", "Diablo III", "Windows"),
        SentinelGame("diablo-4-pc", "Diablo IV", "Windows"),
        SentinelGame("diablo-immortal-android", "Diablo Immortal", "Android"),
    )
}
