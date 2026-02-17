"""Level presets for Fruit Blocks VR."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Sequence

from .core import FruitBlocksGame, FruitType


@dataclass(frozen=True)
class LevelDefinition:
    level_id: str
    title: str
    layout: Sequence[Sequence[FruitType]]
    lower_capacity: int


LEVELS: Dict[str, LevelDefinition] = {
    "tutorial": LevelDefinition(
        level_id="tutorial",
        title="Первые пары",
        layout=(
            (FruitType.APPLE, FruitType.BANANA, FruitType.APPLE, FruitType.BANANA),
        ),
        lower_capacity=4,
    ),
    "tower_intro": LevelDefinition(
        level_id="tower_intro",
        title="Фруктовая башня",
        layout=(
            (FruitType.APPLE, FruitType.PEAR, FruitType.APPLE, FruitType.PEAR),
            (FruitType.BANANA, FruitType.GRAPE, FruitType.BANANA, FruitType.GRAPE),
            (FruitType.CHERRY, FruitType.ORANGE, FruitType.CHERRY, FruitType.ORANGE),
        ),
        lower_capacity=7,
    ),
    "dense_stack": LevelDefinition(
        level_id="dense_stack",
        title="Плотная укладка",
        layout=(
            (
                FruitType.APPLE,
                FruitType.BANANA,
                FruitType.CHERRY,
                FruitType.APPLE,
            ),
            (
                FruitType.BANANA,
                FruitType.CHERRY,
                FruitType.GRAPE,
                FruitType.GRAPE,
            ),
            (
                FruitType.ORANGE,
                FruitType.PEAR,
                FruitType.ORANGE,
                FruitType.PEAR,
            ),
        ),
        lower_capacity=8,
    ),
}

DEFAULT_LEVEL = LEVELS["tower_intro"]


def build_game(level: LevelDefinition = DEFAULT_LEVEL) -> FruitBlocksGame:
    return FruitBlocksGame.from_layout(level.layout, lower_capacity=level.lower_capacity)
