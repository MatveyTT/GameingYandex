"""Tests for Varwin adapter behavior."""

from __future__ import annotations

import os
import sys
import unittest
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fruit_blocks_vr.core import FruitBlocksGame, FruitType
from fruit_blocks_vr.varwin_adapter import VarwinGameController


@dataclass
class RecordingBridge:
    calls: List[Tuple[str, tuple]] = field(default_factory=list)

    def set_block_dynamic(self, object_id: str) -> None:
        self.calls.append(("set_block_dynamic", (object_id,)))

    def play_sound(self, sound_id: str, target_object_id: Optional[str] = None) -> None:
        self.calls.append(("play_sound", (sound_id, target_object_id)))

    def spawn_vfx(self, effect_id: str, target_object_id: Optional[str] = None) -> None:
        self.calls.append(("spawn_vfx", (effect_id, target_object_id)))

    def remove_object(self, object_id: str) -> None:
        self.calls.append(("remove_object", (object_id,)))

    def set_highlight(self, object_id: str, enabled: bool) -> None:
        self.calls.append(("set_highlight", (object_id, enabled)))

    def show_message(self, text: str, duration_sec: float = 3.0) -> None:
        self.calls.append(("show_message", (text, duration_sec)))

    def finish_game(self, won: bool, reason: str) -> None:
        self.calls.append(("finish_game", (won, reason)))


class VarwinAdapterTests(unittest.TestCase):
    def test_controller_maps_events_to_bridge_calls(self) -> None:
        game = FruitBlocksGame.from_layout(
            [[FruitType.APPLE, FruitType.APPLE]],
            lower_capacity=4,
        )
        bridge = RecordingBridge()
        controller = VarwinGameController(
            game=game,
            bridge=bridge,
            object_to_block={"obj0": "L00S00", "obj1": "L00S01"},
        )

        controller.start()
        self.assertIn(("show_message", (game.onboarding_text(), 6.0)), bridge.calls)

        accepted = controller.on_object_interacted("obj0")
        self.assertTrue(accepted)
        self.assertIn(("set_block_dynamic", ("obj0",)), bridge.calls)

        accepted = controller.on_object_interacted("obj1")
        self.assertTrue(accepted)

        finish_calls = [c for c in bridge.calls if c[0] == "finish_game"]
        self.assertEqual(len(finish_calls), 1)
        self.assertTrue(finish_calls[0][1][0])


if __name__ == "__main__":
    unittest.main()
