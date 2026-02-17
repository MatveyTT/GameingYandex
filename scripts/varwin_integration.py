"""
VarwinIntegration — точка входа и интеграция с Varwin XRMS.

Этот модуль является главным скриптом, который прикрепляется
к корневому объекту сцены в Varwin XRMS. Он инициализирует
все подсистемы игры и обрабатывает события Varwin.

В Varwin XRMS этот скрипт привязывается к пустому GameObject
в корне сцены через систему Object Logic.
"""

import json
import time
from typing import Any, Dict, List, Optional

from scripts.game_manager import GameManager, GameState
from scripts.fruit_block import FruitBlock, BlockState
from scripts.board_manager import BoardManager
from scripts.match_detector import MatchDetector
from scripts.score_manager import ScoreManager
from scripts.ui_controller import UIController
from scripts.audio_controller import AudioController
from scripts.effects_controller import EffectsController
from scripts.onboarding_controller import OnboardingController
from scripts.level_generator import LevelGenerator
from scripts.physics_controller import PhysicsController


class FruitBlocksVR:
    """
    Главный класс игры «Фруктовые Блоки VR».

    Инициализирует все подсистемы, управляет жизненным циклом
    и обрабатывает взаимодействие с Varwin XRMS API.

    Использование в Varwin:
        Прикрепите этот скрипт к пустому объекту GameController
        в корне сцены. Скрипт автоматически создаст и настроит
        все необходимые подсистемы.
    """

    def __init__(self):
        self.game_manager = GameManager()
        self.board_manager = BoardManager()
        self.match_detector = MatchDetector()
        self.score_manager = ScoreManager()
        self.ui_controller = UIController()
        self.audio_controller = AudioController()
        self.effects_controller = EffectsController()
        self.onboarding_controller = OnboardingController()
        self.level_generator = LevelGenerator()
        self.physics_controller = PhysicsController()

        self._scene: Optional[Any] = None
        self._block_objects: Dict[int, Any] = {}
        self._is_running: bool = False
        self._last_time: float = 0.0

        self._input_handler: Optional[Any] = None
        self._raycast_system: Optional[Any] = None
        self._hovered_block: Optional[FruitBlock] = None

    def on_start(self, scene: Any = None) -> None:
        """
        Вызывается при запуске сцены в Varwin.

        Инициализирует все подсистемы и запускает игру.

        Args:
            scene: Ссылка на Varwin-сцену
        """
        self._scene = scene
        self._last_time = time.time()

        self.game_manager.initialize(
            board_manager=self.board_manager,
            match_detector=self.match_detector,
            score_manager=self.score_manager,
            ui_controller=self.ui_controller,
            audio_controller=self.audio_controller,
            effects_controller=self.effects_controller,
            onboarding_controller=self.onboarding_controller,
            level_generator=self.level_generator,
            physics_controller=self.physics_controller
        )

        self._setup_scene_objects()

        gameplay_config = self.game_manager.config.get("gameplay", {})
        self.match_detector.configure(
            gameplay_config.get("match_distance", 0.45)
        )

        scoring_config = self.game_manager.config.get("scoring", {})
        self.score_manager.configure(scoring_config)

        audio_config = self.game_manager.config.get("audio", {})
        self.audio_controller.configure(audio_config)

        effects_config = self.game_manager.config.get("effects", {})
        self.effects_controller.configure(effects_config)

        self.physics_controller.setup_collection_zone(
            width=2.0, depth=2.0, floor_y=0.0
        )

        for block in self.board_manager.all_blocks:
            block.set_callbacks(
                on_activated=self._on_block_activated,
                on_landed=self._on_block_landed,
                on_destroyed=self._on_block_destroyed
            )

        self._is_running = True

        self.game_manager.start_game()
        print("[FruitBlocksVR] Игра запущена!")

    def on_update(self) -> None:
        """
        Вызывается каждый кадр в Varwin.

        Обновляет все подсистемы и обрабатывает ввод.
        """
        if not self._is_running:
            return

        current_time = time.time()
        delta_time = current_time - self._last_time
        self._last_time = current_time

        delta_time = min(delta_time, 0.1)

        self._handle_input()

        self.game_manager.update(delta_time)
        self.ui_controller.update(delta_time)
        self.audio_controller.update(delta_time)
        self.effects_controller.update(delta_time)

        self._sync_scene_objects()

    def on_destroy(self) -> None:
        """Вызывается при уничтожении сцены."""
        self._is_running = False
        self.effects_controller.clear_all_effects()
        self.audio_controller.stop_music()
        print("[FruitBlocksVR] Игра остановлена")

    def _setup_scene_objects(self) -> None:
        """
        Настраивает объекты Varwin-сцены.

        Находит или создаёт необходимые объекты:
        - Блоки (FruitBlock prefabs)
        - Зону сбора (CollectionZone)
        - UI Canvas
        - Audio Sources
        - Particle Systems
        """
        if self._scene is None:
            print("[FruitBlocksVR] Работа без Varwin-сцены (тестовый режим)")
            return

        try:
            if hasattr(self._scene, 'find'):
                collection_zone = self._scene.find("CollectionZone")
                if collection_zone:
                    print("[FruitBlocksVR] Зона сбора найдена")

                ui_canvas = self._scene.find("UICanvas")
                if ui_canvas:
                    self._setup_ui_bindings(ui_canvas)

                audio_source = self._scene.find("AudioSource")
                if audio_source:
                    self._setup_audio_bindings(audio_source)

        except Exception as e:
            print(f"[FruitBlocksVR] Ошибка настройки сцены: {e}")

    def _setup_ui_bindings(self, canvas: Any) -> None:
        """Привязывает UI-элементы к объектам сцены."""
        try:
            score_obj = canvas.find_child("ScoreText") if hasattr(canvas, 'find_child') else None
            if score_obj:
                self.ui_controller.score_text.scene_object = score_obj

            level_obj = canvas.find_child("LevelText") if hasattr(canvas, 'find_child') else None
            if level_obj:
                self.ui_controller.level_text.scene_object = level_obj

            timer_obj = canvas.find_child("TimerText") if hasattr(canvas, 'find_child') else None
            if timer_obj:
                self.ui_controller.timer_text.scene_object = timer_obj

        except Exception as e:
            print(f"[FruitBlocksVR] Ошибка привязки UI: {e}")

    def _setup_audio_bindings(self, audio_source: Any) -> None:
        """Привязывает аудио-источники к контроллеру."""
        pass

    def _handle_input(self) -> None:
        """
        Обрабатывает ввод игрока.

        Desktop: мышь + клавиатура
        VR: контроллер + триггер
        """
        if self.game_manager.state == GameState.PAUSED:
            return

        if self.game_manager.state in (GameState.LEVEL_COMPLETE, GameState.GAME_OVER):
            return

    def on_block_pointer_enter(self, block_id: int) -> None:
        """
        Обработчик наведения на блок (от Varwin raycast).

        Args:
            block_id: ID блока
        """
        block = self._find_block_by_id(block_id)
        if block and block.is_interactable:
            if self._hovered_block and self._hovered_block != block:
                self._hovered_block.on_pointer_exit()

            block.on_pointer_enter()
            self._hovered_block = block
            self.audio_controller.play_hover()

    def on_block_pointer_exit(self, block_id: int) -> None:
        """
        Обработчик ухода курсора с блока.

        Args:
            block_id: ID блока
        """
        block = self._find_block_by_id(block_id)
        if block:
            block.on_pointer_exit()
            if self._hovered_block == block:
                self._hovered_block = None

    def on_block_click(self, block_id: int) -> None:
        """
        Обработчик клика/нажатия на блок.

        Args:
            block_id: ID блока
        """
        block = self._find_block_by_id(block_id)
        if block and block.is_interactable:
            block.on_pointer_click()

    def on_next_level_click(self) -> None:
        """Обработчик кнопки «Следующий уровень»."""
        self.audio_controller.play_button()
        self.game_manager.next_level()

    def on_restart_click(self) -> None:
        """Обработчик кнопки «Начать заново»."""
        self.audio_controller.play_button()
        self.game_manager.restart_level()

    def on_pause_click(self) -> None:
        """Обработчик кнопки паузы."""
        self.audio_controller.play_button()
        if self.game_manager.state == GameState.PAUSED:
            self.game_manager.resume()
        else:
            self.game_manager.pause()

    def _on_block_activated(self, block: FruitBlock) -> None:
        """Callback: блок активирован игроком."""
        self.game_manager.on_block_activated(block)
        self.physics_controller.enable_block_physics(block)

    def _on_block_landed(self, block: FruitBlock) -> None:
        """Callback: блок приземлился."""
        self.board_manager.on_block_landed(block)
        self.game_manager.on_block_landed(block)

    def _on_block_destroyed(self, block: FruitBlock) -> None:
        """Callback: блок уничтожен (после анимации)."""
        if block.block_id in self._block_objects:
            scene_obj = self._block_objects[block.block_id]
            if scene_obj and hasattr(scene_obj, 'set_active'):
                scene_obj.set_active(False)

    def _find_block_by_id(self, block_id: int) -> Optional[FruitBlock]:
        """Находит блок по его ID."""
        for block in self.board_manager.all_blocks:
            if block.block_id == block_id:
                return block
        return None

    def _sync_scene_objects(self) -> None:
        """Синхронизирует состояние блоков с объектами Varwin-сцены."""
        for block in self.board_manager.all_blocks:
            if block.state == BlockState.DESTROYED:
                continue

            if block.scene_object:
                try:
                    obj = block.scene_object
                    if hasattr(obj, 'transform'):
                        obj.transform.position = block.position
                        obj.transform.local_scale = (
                            block.block_size * block.scale[0],
                            block.block_size * block.scale[1],
                            block.block_size * block.scale[2]
                        )
                except Exception:
                    pass

    def get_debug_info(self) -> Dict[str, Any]:
        """Возвращает отладочную информацию."""
        return {
            "game": self.game_manager.get_game_info(),
            "board": self.board_manager.get_board_info(),
            "score": self.score_manager.get_stats(),
            "physics_falling": self.physics_controller.get_falling_block_count(),
            "active_effects": self.effects_controller.get_active_effect_count(),
            "match_total": self.match_detector.get_match_count()
        }


def create_game() -> FruitBlocksVR:
    """
    Фабричная функция для создания экземпляра игры.

    Вызывается из Varwin XRMS при загрузке сцены.

    Returns:
        Экземпляр FruitBlocksVR
    """
    game = FruitBlocksVR()
    return game


if __name__ == "__main__":
    print("=" * 60)
    print("  Фруктовые Блоки VR — Fruit Blocks VR")
    print("  Varwin XRMS Game")
    print("=" * 60)
    print()

    game = create_game()
    game.on_start(scene=None)

    print()
    print("Отладочная информация:")
    debug = game.get_debug_info()
    for section, data in debug.items():
        print(f"\n  [{section}]")
        if isinstance(data, dict):
            for key, value in data.items():
                print(f"    {key}: {value}")
        else:
            print(f"    {data}")

    print()
    print("Симуляция 5 кадров обновления:")
    for i in range(5):
        game.on_update()
        info = game.game_manager.get_game_info()
        print(f"  Кадр {i+1}: state={info['state']}, "
              f"score={info['score']}, "
              f"blocks={info['remaining_blocks']}")

    print()
    print("Игра готова к работе в Varwin XRMS!")
