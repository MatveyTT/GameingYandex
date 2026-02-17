"""Bridge between core puzzle logic and a Varwin scene."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Optional, Protocol

from .core import FruitBlocksGame, GameEvent


class VarwinBridge(Protocol):
    """Abstraction layer over Varwin API calls."""

    def set_block_dynamic(self, object_id: str) -> None:
        ...

    def play_sound(self, sound_id: str, target_object_id: Optional[str] = None) -> None:
        ...

    def spawn_vfx(self, effect_id: str, target_object_id: Optional[str] = None) -> None:
        ...

    def remove_object(self, object_id: str) -> None:
        ...

    def set_highlight(self, object_id: str, enabled: bool) -> None:
        ...

    def show_message(self, text: str, duration_sec: float = 3.0) -> None:
        ...

    def finish_game(self, won: bool, reason: str) -> None:
        ...


@dataclass
class VarwinGameController:
    """Controller to connect one-action puzzle gameplay to scene interaction."""

    game: FruitBlocksGame
    bridge: VarwinBridge
    object_to_block: Mapping[str, str]

    def __post_init__(self) -> None:
        self.block_to_object: Dict[str, str] = {
            block_id: object_id for object_id, block_id in self.object_to_block.items()
        }
        self.highlighted_object: Optional[str] = None

    def start(self) -> None:
        self.bridge.show_message(self.game.onboarding_text(), duration_sec=6.0)
        self._highlight_suggestion()

    def on_object_interacted(self, object_id: str) -> bool:
        block_id = self.object_to_block.get(object_id)
        if block_id is None:
            return False

        accepted = self.game.activate_block(block_id)
        self._flush_events()
        return accepted

    def _flush_events(self) -> None:
        for event in self.game.drain_events():
            self._apply_event(event)

    def _apply_event(self, event: GameEvent) -> None:
        kind = event.kind
        payload = event.payload
        if kind == "activate":
            block_id = payload["block_id"]
            object_id = self.block_to_object.get(block_id)
            if object_id:
                self.bridge.set_block_dynamic(object_id)
                self.bridge.play_sound(payload.get("sfx", "block_hit"), object_id)
                self.bridge.spawn_vfx(payload.get("vfx", "block_pulse"), object_id)
            return

        if kind == "match":
            for block_id in payload.get("pair", []):
                object_id = self.block_to_object.get(block_id)
                if object_id:
                    self.bridge.spawn_vfx(payload.get("vfx", "fruit_shards"), object_id)
                    self.bridge.remove_object(object_id)
            self.bridge.play_sound(payload.get("sfx", "pair_destroy"))
            return

        if kind == "hint":
            self._highlight_suggestion(payload.get("block_id"))
            return

        if kind == "win":
            self._clear_highlight()
            self.bridge.play_sound(payload.get("sfx", "win_chime"))
            self.bridge.spawn_vfx(payload.get("vfx", "confetti"))
            self.bridge.finish_game(True, "Победа! Все блоки очищены.")
            return

        if kind == "fail":
            self._clear_highlight()
            reason = payload.get("reason", "Попытка завершена.")
            self.bridge.play_sound(payload.get("sfx", "fail_buzzer"))
            self.bridge.spawn_vfx(payload.get("vfx", "red_flash"))
            self.bridge.finish_game(False, reason)

    def _highlight_suggestion(self, suggested_block_id: Optional[str] = None) -> None:
        self._clear_highlight()
        if suggested_block_id is None:
            suggested_block_id = self.game.suggested_block_id()
        if suggested_block_id is None:
            return

        object_id = self.block_to_object.get(suggested_block_id)
        if object_id is None:
            return
        self.bridge.set_highlight(object_id, True)
        self.highlighted_object = object_id

    def _clear_highlight(self) -> None:
        if self.highlighted_object is not None:
            self.bridge.set_highlight(self.highlighted_object, False)
            self.highlighted_object = None
