"""Tests for core Fruit Blocks VR mechanics."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fruit_blocks_vr.core import FruitBlocksGame, FruitType, GameStatus


class FruitBlocksGameTests(unittest.TestCase):
    def test_pair_is_removed_and_game_is_won(self) -> None:
        game = FruitBlocksGame.from_layout(
            [[FruitType.APPLE, FruitType.APPLE]],
            lower_capacity=4,
        )

        self.assertTrue(game.activate_block("L00S00"))
        self.assertTrue(game.activate_block("L00S01"))

        self.assertEqual(game.status, GameStatus.WON)
        self.assertEqual(game.lower_zone, [])
        self.assertEqual(game.score_pairs, 1)
        self.assertTrue(all(block.removed for block in game.blocks.values()))

        event_kinds = [event.kind for event in game.drain_events()]
        self.assertIn("match", event_kinds)
        self.assertIn("win", event_kinds)

    def test_invalid_or_duplicate_activation_is_rejected(self) -> None:
        game = FruitBlocksGame.from_layout(
            [[FruitType.BANANA, FruitType.APPLE]],
            lower_capacity=4,
        )

        self.assertFalse(game.activate_block("UNKNOWN"))
        self.assertTrue(game.activate_block("L00S00"))
        self.assertFalse(game.activate_block("L00S00"))

    def test_fail_when_lower_zone_overflows(self) -> None:
        game = FruitBlocksGame.from_layout(
            [[FruitType.APPLE, FruitType.BANANA, FruitType.CHERRY]],
            lower_capacity=2,
        )

        self.assertTrue(game.activate_block("L00S00"))
        self.assertEqual(game.status, GameStatus.RUNNING)
        self.assertTrue(game.activate_block("L00S01"))

        self.assertEqual(game.status, GameStatus.LOST)
        self.assertEqual(game.fail_reason, "Нижняя зона переполнена.")
        self.assertEqual(game.lower_zone, ["L00S00", "L00S01"])

    def test_hint_prefers_block_matching_last_fruit(self) -> None:
        game = FruitBlocksGame.from_layout(
            [[FruitType.APPLE, FruitType.BANANA, FruitType.APPLE]],
            lower_capacity=4,
        )
        self.assertEqual(game.suggested_block_id(), "L00S00")

        game.activate_block("L00S00")
        self.assertEqual(game.suggested_block_id(), "L00S02")


if __name__ == "__main__":
    unittest.main()
