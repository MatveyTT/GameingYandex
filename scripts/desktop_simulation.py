"""Desktop simulation of Fruit Blocks VR puzzle logic."""

from __future__ import annotations

import os
import sys
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fruit_blocks_vr.core import FruitBlocksGame
from fruit_blocks_vr.levels import DEFAULT_LEVEL, build_game
from fruit_blocks_vr.varwin_adapter import VarwinBridge, VarwinGameController


class ConsoleBridge(VarwinBridge):
    def set_block_dynamic(self, object_id: str) -> None:
        print(f"[physics] {object_id} -> dynamic")

    def play_sound(self, sound_id: str, target_object_id: Optional[str] = None) -> None:
        target = f" @ {target_object_id}" if target_object_id else ""
        print(f"[sound] {sound_id}{target}")

    def spawn_vfx(self, effect_id: str, target_object_id: Optional[str] = None) -> None:
        target = f" @ {target_object_id}" if target_object_id else ""
        print(f"[vfx] {effect_id}{target}")

    def remove_object(self, object_id: str) -> None:
        print(f"[scene] remove {object_id}")

    def set_highlight(self, object_id: str, enabled: bool) -> None:
        state = "on" if enabled else "off"
        print(f"[hint] {object_id} highlight {state}")

    def show_message(self, text: str, duration_sec: float = 3.0) -> None:
        print(f"[ui:{duration_sec:.1f}s] {text}")

    def finish_game(self, won: bool, reason: str) -> None:
        result = "WIN" if won else "FAIL"
        print(f"[{result}] {reason}")


def print_help() -> None:
    print("Команды:")
    print("  list             - показать доступные блоки")
    print("  pick <block_id>  - активировать блок")
    print("  state            - показать снимок состояния")
    print("  auto             - активировать предложенный блок")
    print("  quit             - выход")


def print_blocks(game: FruitBlocksGame) -> None:
    for block_id in sorted(game.blocks):
        block = game.blocks[block_id]
        status = "removed" if block.removed else "active" if block.activated else "idle"
        print(f"  {block_id}: {block.fruit.value:<7} {status}")


def main() -> None:
    game = build_game(DEFAULT_LEVEL)
    object_to_block = {block_id: block_id for block_id in game.blocks}
    controller = VarwinGameController(
        game=game,
        bridge=ConsoleBridge(),
        object_to_block=object_to_block,
    )
    controller.start()

    print(
        f"Уровень: {DEFAULT_LEVEL.title} | блоков: {len(game.blocks)} | "
        f"capacity: {game.lower_capacity}"
    )
    print_help()
    print_blocks(game)

    while True:
        raw = input(">> ").strip()
        if not raw:
            continue

        if raw == "quit":
            break
        if raw == "help":
            print_help()
            continue
        if raw == "list":
            print_blocks(game)
            continue
        if raw == "state":
            print(game.snapshot())
            continue
        if raw == "auto":
            block_id = game.suggested_block_id()
            if block_id is None:
                print("Подсказка недоступна.")
                continue
            accepted = controller.on_object_interacted(block_id)
            print(f"auto -> {block_id} ({'ok' if accepted else 'skip'})")
            continue
        if raw.startswith("pick "):
            block_id = raw.split(" ", 1)[1].strip()
            accepted = controller.on_object_interacted(block_id)
            print("ok" if accepted else "Нельзя активировать этот блок.")
            continue

        print("Неизвестная команда. Введите help.")


if __name__ == "__main__":
    main()
