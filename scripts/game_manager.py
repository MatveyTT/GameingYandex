"""
GameManager — главный контроллер игры «Фруктовые Блоки VR».

Управляет состоянием игры, координирует работу всех подсистем:
BoardManager, MatchDetector, ScoreManager, UIController,
AudioController, EffectsController, OnboardingController, LevelGenerator.

Используется как скрипт на корневом объекте сцены в Varwin XRMS.
"""

import json
import math
import time
from enum import Enum, auto
from typing import Optional, List, Dict, Any


class GameState(Enum):
    """Состояния игры."""
    LOADING = auto()
    ONBOARDING = auto()
    PLAYING = auto()
    PAUSED = auto()
    CHECKING_MATCHES = auto()
    CHAIN_REACTION = auto()
    LEVEL_COMPLETE = auto()
    GAME_OVER = auto()
    GAME_WON = auto()


class GameManager:
    """
    Главный контроллер игры.

    Координирует все подсистемы и управляет игровым циклом.
    Прикрепляется к корневому объекту сцены Varwin.
    """

    def __init__(self):
        self.state: GameState = GameState.LOADING
        self.current_level: int = 1
        self.score: int = 0
        self.total_score: int = 0
        self.chain_count: int = 0
        self.moves_count: int = 0
        self.time_elapsed: float = 0.0
        self.time_limit: float = 0.0
        self.last_match_time: float = 0.0
        self.is_initialized: bool = False

        self.board_manager: Optional[Any] = None
        self.match_detector: Optional[Any] = None
        self.score_manager: Optional[Any] = None
        self.ui_controller: Optional[Any] = None
        self.audio_controller: Optional[Any] = None
        self.effects_controller: Optional[Any] = None
        self.onboarding_controller: Optional[Any] = None
        self.level_generator: Optional[Any] = None
        self.physics_controller: Optional[Any] = None

        self.config: Dict[str, Any] = {}
        self.levels_config: Dict[str, Any] = {}
        self.fruit_types_config: Dict[str, Any] = {}

    def load_config(self, config_path: str = "config/game_config.json",
                    levels_path: str = "config/levels.json",
                    fruits_path: str = "config/fruit_types.json") -> None:
        """Загружает конфигурацию игры из JSON-файлов."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            with open(levels_path, 'r', encoding='utf-8') as f:
                self.levels_config = json.load(f)
            with open(fruits_path, 'r', encoding='utf-8') as f:
                self.fruit_types_config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"[GameManager] Ошибка загрузки конфигурации: {e}")
            self._set_default_config()

    def _set_default_config(self) -> None:
        """Устанавливает конфигурацию по умолчанию."""
        self.config = {
            "gameplay": {
                "block_size": 0.3,
                "match_distance": 0.45,
                "fall_gravity_multiplier": 2.0,
                "match_delay_seconds": 0.3,
                "chain_bonus_multiplier": 2,
                "collection_zone_height_limit": 2.0,
                "block_hover_scale": 1.08,
                "match_check_interval": 0.2
            },
            "scoring": {
                "match_points": 100,
                "chain_multiplier_base": 2,
                "speed_bonus_threshold_seconds": 3.0,
                "speed_bonus_points": 50,
                "level_complete_time_multiplier": 10
            },
            "physics": {
                "gravity": -9.81,
                "block_mass": 1.0,
                "block_bounciness": 0.2,
                "block_friction": 0.6
            }
        }

    def initialize(self, board_manager, match_detector, score_manager,
                   ui_controller, audio_controller, effects_controller,
                   onboarding_controller, level_generator,
                   physics_controller) -> None:
        """
        Инициализирует все подсистемы игры.

        Args:
            board_manager: Менеджер игрового поля
            match_detector: Детектор совпадений
            score_manager: Менеджер очков
            ui_controller: Контроллер интерфейса
            audio_controller: Контроллер звука
            effects_controller: Контроллер эффектов
            onboarding_controller: Контроллер обучения
            level_generator: Генератор уровней
            physics_controller: Контроллер физики
        """
        self.board_manager = board_manager
        self.match_detector = match_detector
        self.score_manager = score_manager
        self.ui_controller = ui_controller
        self.audio_controller = audio_controller
        self.effects_controller = effects_controller
        self.onboarding_controller = onboarding_controller
        self.level_generator = level_generator
        self.physics_controller = physics_controller

        self.load_config()
        self.is_initialized = True
        print("[GameManager] Инициализация завершена.")

    def start_game(self) -> None:
        """Запускает новую игру с первого уровня."""
        if not self.is_initialized:
            print("[GameManager] ОШИБКА: Игра не инициализирована!")
            return

        self.total_score = 0
        self.current_level = 1
        self._start_level(self.current_level)

    def _start_level(self, level_id: int) -> None:
        """
        Запускает указанный уровень.

        Args:
            level_id: Номер уровня (1-based)
        """
        level_config = self._get_level_config(level_id)
        if level_config is None:
            self._set_state(GameState.GAME_WON)
            return

        self.score = 0
        self.chain_count = 0
        self.moves_count = 0
        self.time_elapsed = 0.0
        self.last_match_time = 0.0
        self.time_limit = level_config.get("time_limit_seconds", 0)

        fruit_count = level_config.get("fruit_type_count", 3)
        available_fruits = self.fruit_types_config.get("fruit_types", [])[:fruit_count]

        grid_w = level_config.get("grid_width", 3)
        grid_h = level_config.get("grid_height", 3)
        grid_d = level_config.get("grid_depth", 2)
        capacity = level_config.get("collection_zone_capacity", 10)

        if self.board_manager:
            self.board_manager.setup_board(grid_w, grid_h, grid_d, capacity)

        if self.level_generator:
            blocks = self.level_generator.generate_level(
                grid_w, grid_h, grid_d, available_fruits
            )
            if self.board_manager:
                self.board_manager.place_blocks(blocks)

        if self.physics_controller:
            physics_cfg = self.config.get("physics", {})
            self.physics_controller.configure(physics_cfg)

        if self.ui_controller:
            self.ui_controller.show_level_start(level_id, level_config.get("name", ""))
            self.ui_controller.update_score(self.score)
            self.ui_controller.update_level(level_id)

        if self.audio_controller:
            self.audio_controller.play_level_start()
            self.audio_controller.play_music()

        if level_config.get("show_onboarding", False) and self.onboarding_controller:
            self._set_state(GameState.ONBOARDING)
            self.onboarding_controller.start_onboarding()
        else:
            self._set_state(GameState.PLAYING)

        print(f"[GameManager] Уровень {level_id} запущен: "
              f"{grid_w}x{grid_h}x{grid_d}, {fruit_count} фруктов")

    def _get_level_config(self, level_id: int) -> Optional[Dict[str, Any]]:
        """Возвращает конфигурацию уровня по ID."""
        levels = self.levels_config.get("levels", [])
        for level in levels:
            if level.get("level_id") == level_id:
                return level
        return None

    def _set_state(self, new_state: GameState) -> None:
        """Изменяет состояние игры с логированием."""
        old_state = self.state
        self.state = new_state
        print(f"[GameManager] Состояние: {old_state.name} -> {new_state.name}")

    def update(self, delta_time: float) -> None:
        """
        Обновление игрового цикла. Вызывается каждый кадр.

        Args:
            delta_time: Время с предыдущего кадра в секундах
        """
        if self.state == GameState.PLAYING:
            self._update_playing(delta_time)
        elif self.state == GameState.ONBOARDING:
            self._update_onboarding(delta_time)
        elif self.state == GameState.CHECKING_MATCHES:
            self._update_checking_matches(delta_time)
        elif self.state == GameState.CHAIN_REACTION:
            self._update_chain_reaction(delta_time)

    def _update_playing(self, delta_time: float) -> None:
        """Обновление в состоянии игры."""
        self.time_elapsed += delta_time

        if self.time_limit > 0:
            remaining = self.time_limit - self.time_elapsed
            if self.ui_controller:
                self.ui_controller.update_timer(max(0, remaining))
            if remaining <= 0:
                self._on_game_over("Время вышло!")
                return

        if self.physics_controller:
            self.physics_controller.update(delta_time)

        if self.board_manager:
            self.board_manager.update(delta_time)

    def _update_onboarding(self, delta_time: float) -> None:
        """Обновление в состоянии обучения."""
        if self.onboarding_controller:
            self.onboarding_controller.update(delta_time)
            if self.onboarding_controller.is_complete:
                self._set_state(GameState.PLAYING)

    def _update_checking_matches(self, delta_time: float) -> None:
        """Обновление при проверке совпадений."""
        if self.match_detector and self.board_manager:
            matches = self.match_detector.find_matches(
                self.board_manager.get_collection_zone_blocks()
            )
            if matches:
                self._process_matches(matches)
            else:
                self.chain_count = 0
                self._check_game_state()
                self._set_state(GameState.PLAYING)

    def _update_chain_reaction(self, delta_time: float) -> None:
        """Обновление при цепной реакции."""
        if self.board_manager and self.board_manager.are_blocks_settled():
            self._set_state(GameState.CHECKING_MATCHES)

    def on_block_activated(self, block) -> None:
        """
        Обработчик активации блока игроком.

        Args:
            block: Активированный блок FruitBlock
        """
        if self.state not in (GameState.PLAYING, GameState.ONBOARDING):
            return

        if self.state == GameState.ONBOARDING:
            if self.onboarding_controller:
                self.onboarding_controller.on_first_action()
            self._set_state(GameState.PLAYING)

        self.moves_count += 1

        if self.board_manager:
            self.board_manager.release_block(block)

        if self.audio_controller:
            self.audio_controller.play_activate()

        if self.effects_controller:
            self.effects_controller.play_activation_flash(block.position)

        if self.ui_controller:
            self.ui_controller.update_moves(self.moves_count)

        print(f"[GameManager] Блок активирован: {block.fruit_type_name} "
              f"в позиции {block.grid_position}")

    def on_block_landed(self, block) -> None:
        """
        Обработчик приземления блока в зоне сбора.

        Args:
            block: Приземлившийся блок FruitBlock
        """
        if self.audio_controller:
            self.audio_controller.play_land()

        if self.effects_controller:
            self.effects_controller.play_land_dust(block.position)

        self._set_state(GameState.CHECKING_MATCHES)

    def _process_matches(self, matches: List[tuple]) -> None:
        """
        Обрабатывает найденные совпадения.

        Args:
            matches: Список пар совпавших блоков [(block_a, block_b), ...]
        """
        self.chain_count += 1
        current_time = self.time_elapsed

        for block_a, block_b in matches:
            match_position = (
                (block_a.position[0] + block_b.position[0]) / 2,
                (block_a.position[1] + block_b.position[1]) / 2,
                (block_a.position[2] + block_b.position[2]) / 2
            )

            points = self._calculate_points(current_time)

            if self.score_manager:
                self.score_manager.add_score(points, self.chain_count)
            self.score += points

            if self.audio_controller:
                self.audio_controller.play_match(self.chain_count)

            if self.effects_controller:
                self.effects_controller.play_match_explosion(
                    match_position, block_a.fruit_type_id
                )
                if self.chain_count > 1:
                    self.effects_controller.play_chain_flash(self.chain_count)

            if self.ui_controller:
                self.ui_controller.show_points_popup(points, match_position)
                self.ui_controller.update_score(self.score)

            if self.board_manager:
                self.board_manager.remove_block(block_a)
                self.board_manager.remove_block(block_b)

            self.last_match_time = current_time

            print(f"[GameManager] Совпадение! {block_a.fruit_type_name} "
                  f"x2, +{points} очков (цепочка: x{self.chain_count})")

        self._set_state(GameState.CHAIN_REACTION)

    def _calculate_points(self, current_time: float) -> int:
        """
        Рассчитывает очки за совпадение с учётом бонусов.

        Args:
            current_time: Текущее время в секундах

        Returns:
            Количество очков
        """
        scoring = self.config.get("scoring", {})
        base_points = scoring.get("match_points", 100)
        chain_mult = scoring.get("chain_multiplier_base", 2)
        speed_threshold = scoring.get("speed_bonus_threshold_seconds", 3.0)
        speed_bonus = scoring.get("speed_bonus_points", 50)

        points = base_points

        if self.chain_count > 1:
            points *= (chain_mult ** (self.chain_count - 1))
            points = int(points)

        if self.last_match_time > 0:
            time_since_last = current_time - self.last_match_time
            if time_since_last < speed_threshold:
                points += speed_bonus

        return points

    def _check_game_state(self) -> None:
        """Проверяет текущее состояние игры на завершение."""
        if self.board_manager:
            if self.board_manager.is_board_empty():
                self._on_level_complete()
                return

            if self.board_manager.is_collection_zone_full():
                remaining = self.board_manager.get_remaining_blocks()
                if not self._has_possible_matches(remaining):
                    self._on_game_over("Нет места для новых блоков!")
                    return

            remaining = self.board_manager.get_remaining_blocks()
            collection = self.board_manager.get_collection_zone_blocks()
            if not self._has_possible_matches(remaining + collection):
                if self.board_manager.are_blocks_settled():
                    self._on_game_over("Нет возможных совпадений!")

    def _has_possible_matches(self, blocks: list) -> bool:
        """
        Проверяет наличие возможных совпадений среди блоков.

        Args:
            blocks: Список блоков

        Returns:
            True если совпадения возможны
        """
        type_counts: Dict[int, int] = {}
        for block in blocks:
            ftype = block.fruit_type_id
            type_counts[ftype] = type_counts.get(ftype, 0) + 1

        for count in type_counts.values():
            if count >= 2:
                return True
        return False

    def _on_level_complete(self) -> None:
        """Обработка завершения уровня."""
        self._set_state(GameState.LEVEL_COMPLETE)

        time_bonus = 0
        if self.time_limit > 0:
            remaining_time = max(0, self.time_limit - self.time_elapsed)
            mult = self.config.get("scoring", {}).get("level_complete_time_multiplier", 10)
            time_bonus = int(remaining_time * mult)
            self.score += time_bonus

        self.total_score += self.score

        if self.audio_controller:
            self.audio_controller.play_win()

        if self.effects_controller:
            self.effects_controller.play_victory_fireworks()

        if self.ui_controller:
            self.ui_controller.show_level_complete(
                level=self.current_level,
                score=self.score,
                time_bonus=time_bonus,
                moves=self.moves_count,
                time_elapsed=self.time_elapsed
            )

        print(f"[GameManager] Уровень {self.current_level} пройден! "
              f"Очки: {self.score} (бонус времени: {time_bonus})")

    def _on_game_over(self, reason: str) -> None:
        """
        Обработка проигрыша.

        Args:
            reason: Причина проигрыша
        """
        self._set_state(GameState.GAME_OVER)

        if self.audio_controller:
            self.audio_controller.play_fail()

        if self.effects_controller:
            self.effects_controller.play_fail_effect()

        if self.ui_controller:
            self.ui_controller.show_game_over(
                reason=reason,
                score=self.score,
                moves=self.moves_count
            )

        print(f"[GameManager] Проигрыш: {reason}. Очки: {self.score}")

    def next_level(self) -> None:
        """Переход к следующему уровню."""
        self.current_level += 1
        self._start_level(self.current_level)

    def restart_level(self) -> None:
        """Перезапуск текущего уровня."""
        self._start_level(self.current_level)

    def restart_game(self) -> None:
        """Перезапуск всей игры."""
        self.total_score = 0
        self.current_level = 1
        self._start_level(1)

    def pause(self) -> None:
        """Пауза игры."""
        if self.state in (GameState.PLAYING, GameState.ONBOARDING):
            self._prev_state_before_pause = self.state
            self._set_state(GameState.PAUSED)
            if self.audio_controller:
                self.audio_controller.pause_music()
            if self.ui_controller:
                self.ui_controller.show_pause_menu()

    def resume(self) -> None:
        """Продолжение игры после паузы."""
        if self.state == GameState.PAUSED:
            restore_state = getattr(self, '_prev_state_before_pause', GameState.PLAYING)
            self._set_state(restore_state)
            if self.audio_controller:
                self.audio_controller.resume_music()
            if self.ui_controller:
                self.ui_controller.hide_pause_menu()

    def get_game_info(self) -> Dict[str, Any]:
        """Возвращает текущую информацию об игре."""
        return {
            "state": self.state.name,
            "level": self.current_level,
            "score": self.score,
            "total_score": self.total_score,
            "moves": self.moves_count,
            "time_elapsed": round(self.time_elapsed, 1),
            "chain_count": self.chain_count,
            "remaining_blocks": (
                self.board_manager.get_remaining_block_count()
                if self.board_manager else 0
            )
        }
