from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Platform(StrEnum):
    WINDOWS = "windows"
    ANDROID = "android"


@dataclass(frozen=True)
class GameDefinition:
    id: str
    name: str
    platform: Platform
    family: str
    versioning: str
    launcher_supported: bool
    interaction_mode: str


DIABLO_CATALOG: tuple[GameDefinition, ...] = (
    GameDefinition("diablo-1-pc", "Diablo", Platform.WINDOWS, "Diablo", "release", True, "adapter"),
    GameDefinition("diablo-2-pc", "Diablo II", Platform.WINDOWS, "Diablo", "release", True, "adapter"),
    GameDefinition("diablo-2-resurrected-pc", "Diablo II: Resurrected", Platform.WINDOWS, "Diablo", "release", True, "adapter"),
    GameDefinition("diablo-3-pc", "Diablo III", Platform.WINDOWS, "Diablo", "season-patch", True, "adapter"),
    GameDefinition("diablo-4-pc", "Diablo IV", Platform.WINDOWS, "Diablo", "season-patch", True, "adapter"),
    GameDefinition("diablo-immortal-android", "Diablo Immortal", Platform.ANDROID, "Diablo", "server-client-patch", False, "android-adapter"),
)


def get_game(game_id: str) -> GameDefinition | None:
    return next((game for game in DIABLO_CATALOG if game.id == game_id), None)
