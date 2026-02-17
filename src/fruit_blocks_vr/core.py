"""Core puzzle mechanics for Fruit Blocks VR."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence


class FruitType(str, Enum):
    APPLE = "apple"
    BANANA = "banana"
    CHERRY = "cherry"
    GRAPE = "grape"
    ORANGE = "orange"
    PEAR = "pear"


class GameStatus(str, Enum):
    RUNNING = "running"
    WON = "won"
    LOST = "lost"


@dataclass
class GameEvent:
    kind: str
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FruitBlock:
    block_id: str
    fruit: FruitType
    layer: int
    sector: int
    activated: bool = False
    removed: bool = False

    @property
    def interactable(self) -> bool:
        return not self.activated and not self.removed


class FruitBlocksGame:
    """Single-action puzzle logic for the VR adaptation."""

    def __init__(self, blocks: Sequence[FruitBlock], lower_capacity: int) -> None:
        if lower_capacity < 2:
            raise ValueError("lower_capacity must be >= 2")
        if not blocks:
            raise ValueError("Game must contain at least one block")

        self.blocks: Dict[str, FruitBlock] = {block.block_id: block for block in blocks}
        if len(self.blocks) != len(list(blocks)):
            raise ValueError("Block ids must be unique")

        self.lower_capacity = lower_capacity
        self.lower_zone: List[str] = []
        self.status = GameStatus.RUNNING
        self.fail_reason: Optional[str] = None
        self.score_pairs = 0
        self.activations = 0
        self._event_queue: List[GameEvent] = []

    @classmethod
    def from_layout(
        cls,
        layout: Sequence[Sequence[FruitType | str]],
        lower_capacity: int = 8,
    ) -> "FruitBlocksGame":
        blocks: List[FruitBlock] = []
        for layer_idx, row in enumerate(layout):
            if not row:
                raise ValueError("Every layer must contain at least one block")
            for sector_idx, fruit in enumerate(row):
                fruit_type = _coerce_fruit(fruit)
                block_id = f"L{layer_idx:02d}S{sector_idx:02d}"
                blocks.append(
                    FruitBlock(
                        block_id=block_id,
                        fruit=fruit_type,
                        layer=layer_idx,
                        sector=sector_idx,
                    )
                )
        return cls(blocks=blocks, lower_capacity=lower_capacity)

    @staticmethod
    def onboarding_text() -> str:
        return "Активируйте блок: одинаковые фрукты внизу исчезают попарно."

    def list_interactable(self) -> List[str]:
        ids = [block.block_id for block in self.blocks.values() if block.interactable]
        return sorted(ids)

    def suggested_block_id(self) -> Optional[str]:
        if self.status != GameStatus.RUNNING:
            return None

        interactable = self.list_interactable()
        if not interactable:
            return None

        if self.lower_zone:
            last_fruit = self.blocks[self.lower_zone[-1]].fruit
            for block_id in interactable:
                if self.blocks[block_id].fruit == last_fruit:
                    return block_id

        return interactable[0]

    def activate_block(self, block_id: str) -> bool:
        if self.status != GameStatus.RUNNING:
            return False

        block = self.blocks.get(block_id)
        if block is None or not block.interactable:
            return False

        block.activated = True
        self.activations += 1
        self._emit(
            "activate",
            block_id=block_id,
            fruit=block.fruit.value,
            sfx="block_hit",
            vfx="block_pulse",
        )

        self.lower_zone.append(block_id)
        self._emit("drop", block_id=block_id, lower_zone_size=len(self.lower_zone))

        self._resolve_matches()
        self._refresh_status()
        self._emit_hint()
        return True

    def drain_events(self) -> List[GameEvent]:
        events = list(self._event_queue)
        self._event_queue.clear()
        return events

    def snapshot(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "fail_reason": self.fail_reason,
            "activations": self.activations,
            "score_pairs": self.score_pairs,
            "lower_zone": list(self.lower_zone),
            "interactable": self.list_interactable(),
            "removed": sorted(
                block.block_id for block in self.blocks.values() if block.removed
            ),
        }

    def _resolve_matches(self) -> None:
        made_match = True
        while made_match:
            made_match = False
            idx = 0
            while idx < len(self.lower_zone) - 1:
                left_id = self.lower_zone[idx]
                right_id = self.lower_zone[idx + 1]
                left = self.blocks[left_id]
                right = self.blocks[right_id]

                if left.fruit == right.fruit:
                    left.removed = True
                    right.removed = True
                    del self.lower_zone[idx : idx + 2]
                    self.score_pairs += 1
                    self._emit(
                        "match",
                        pair=[left_id, right_id],
                        fruit=left.fruit.value,
                        sfx="pair_destroy",
                        vfx="fruit_shards",
                    )
                    made_match = True
                    continue
                idx += 1

    def _refresh_status(self) -> None:
        if self.status != GameStatus.RUNNING:
            return

        all_removed = all(block.removed for block in self.blocks.values())
        if all_removed:
            self.status = GameStatus.WON
            self._emit("win", sfx="win_chime", vfx="confetti", pairs=self.score_pairs)
            return

        no_interactable_left = not any(
            block.interactable for block in self.blocks.values()
        )
        if no_interactable_left and self.lower_zone:
            self.status = GameStatus.LOST
            self.fail_reason = "Нет доступных активаций, внизу остались блоки."
            self._emit("fail", reason=self.fail_reason, sfx="fail_buzzer", vfx="red_flash")
            return

        if len(self.lower_zone) >= self.lower_capacity:
            self.status = GameStatus.LOST
            self.fail_reason = "Нижняя зона переполнена."
            self._emit("fail", reason=self.fail_reason, sfx="fail_buzzer", vfx="red_flash")

    def _emit_hint(self) -> None:
        if self.status != GameStatus.RUNNING:
            return
        suggestion = self.suggested_block_id()
        if suggestion is None:
            return
        self._emit("hint", block_id=suggestion, ui="outline")

    def _emit(self, kind: str, **payload: Any) -> None:
        self._event_queue.append(GameEvent(kind=kind, payload=payload))


def _coerce_fruit(value: FruitType | str) -> FruitType:
    if isinstance(value, FruitType):
        return value
    return FruitType(value)
