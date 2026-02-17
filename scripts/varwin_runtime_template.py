"""Template of runtime wiring for a Varwin scene.

Replace TODO sections with concrete Varwin XRMS API calls.
"""

from __future__ import annotations

import os
import sys
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fruit_blocks_vr.levels import build_game
from fruit_blocks_vr.varwin_adapter import VarwinBridge, VarwinGameController


class TODOSceneBridge(VarwinBridge):
    """Example bridge for Varwin object API."""

    def set_block_dynamic(self, object_id: str) -> None:
        # TODO: enable rigidbody/physics for object_id
        pass

    def play_sound(self, sound_id: str, target_object_id: Optional[str] = None) -> None:
        # TODO: play 3D/2D sound by sound_id
        pass

    def spawn_vfx(self, effect_id: str, target_object_id: Optional[str] = None) -> None:
        # TODO: spawn particle effect
        pass

    def remove_object(self, object_id: str) -> None:
        # TODO: hide or destroy block object in scene
        pass

    def set_highlight(self, object_id: str, enabled: bool) -> None:
        # TODO: apply/remove outline material
        pass

    def show_message(self, text: str, duration_sec: float = 3.0) -> None:
        # TODO: display short onboarding/status text in UI
        pass

    def finish_game(self, won: bool, reason: str) -> None:
        # TODO: display final state and restart button
        pass


def bootstrap_controller(object_to_block: dict[str, str]) -> VarwinGameController:
    """Create game controller for the current Varwin scene."""
    game = build_game()
    bridge = TODOSceneBridge()
    controller = VarwinGameController(
        game=game,
        bridge=bridge,
        object_to_block=object_to_block,
    )
    controller.start()
    return controller


def on_player_interaction(controller: VarwinGameController, scene_object_id: str) -> None:
    """Call this from block click/impact callback in Varwin."""
    controller.on_object_interacted(scene_object_id)
