"""
Тесты игровой логики «Фруктовые Блоки VR».

Проверяет корректность работы всех подсистем:
- Генерация уровней
- Совпадения блоков
- Система очков
- Состояния игры
- Обучение
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.fruit_block import FruitBlock, BlockState
from scripts.board_manager import BoardManager
from scripts.match_detector import MatchDetector
from scripts.score_manager import ScoreManager
from scripts.level_generator import LevelGenerator
from scripts.physics_controller import PhysicsController
from scripts.ui_controller import UIController, PointsPopup
from scripts.audio_controller import AudioController
from scripts.effects_controller import EffectsController
from scripts.onboarding_controller import OnboardingController
from scripts.game_manager import GameManager, GameState


def test_fruit_block():
    """Тестирует создание и поведение фруктового блока."""
    print("=== Тест: FruitBlock ===")

    block = FruitBlock(
        fruit_type_id=0,
        fruit_type_name="Яблоко",
        color=(0.9, 0.3, 0.2, 1.0),
        grid_position=(1, 2, 0),
        block_size=0.3
    )

    assert block.fruit_type_id == 0
    assert block.fruit_type_name == "Яблоко"
    assert block.grid_position == (1, 2, 0)
    assert block.state == BlockState.IDLE
    assert block.is_interactable is True
    print("  [OK] Создание блока")

    block.setup((0.5, 1.0, 0.0), block_id=42)
    assert block.block_id == 42
    assert block.position == (0.5, 1.0, 0.0)
    print("  [OK] Настройка блока")

    block.on_pointer_enter()
    assert block.state == BlockState.HOVERED
    print("  [OK] Наведение (HOVERED)")

    block.on_pointer_exit()
    assert block.state == BlockState.IDLE
    print("  [OK] Уход курсора (IDLE)")

    activated = False
    def on_activate(b):
        nonlocal activated
        activated = True

    block.set_callbacks(on_activated=on_activate)
    block.on_pointer_click()
    assert block.state == BlockState.ACTIVATED
    assert activated is True
    assert block.is_interactable is False
    print("  [OK] Активация блока")

    for _ in range(10):
        block.update(0.02)
    assert block.state == BlockState.FALLING
    print("  [OK] Переход в FALLING")

    block2 = FruitBlock(0, "Яблоко", (0.9, 0.3, 0.2, 1.0), (0, 0, 0))
    assert block.matches_with(block2) is True

    block3 = FruitBlock(1, "Апельсин", (0.9, 0.5, 0.1, 1.0), (0, 0, 0))
    assert block.matches_with(block3) is False
    print("  [OK] Проверка совпадений типов")

    block_a = FruitBlock(0, "Яблоко", (1, 0, 0, 1), (0, 0, 0))
    block_a.setup((0.0, 0.0, 0.0), 100)
    block_b = FruitBlock(0, "Яблоко", (1, 0, 0, 1), (0, 0, 0))
    block_b.setup((0.3, 0.0, 0.0), 101)

    dist = block_a.get_distance_to(block_b)
    assert abs(dist - 0.3) < 0.001
    print("  [OK] Расчёт расстояния")

    destroy_block = FruitBlock(0, "Яблоко", (1, 0, 0, 1), (0, 0, 0))
    destroy_block.setup((0, 0, 0), 200)
    destroy_block.start_destroy()
    assert destroy_block.state == BlockState.DESTROYING

    for _ in range(30):
        destroy_block.update(0.02)
    assert destroy_block.state == BlockState.DESTROYED
    print("  [OK] Анимация уничтожения")

    print("  PASSED\n")


def test_match_detector():
    """Тестирует детектор совпадений."""
    print("=== Тест: MatchDetector ===")

    detector = MatchDetector(match_distance=0.45)

    block_a = FruitBlock(0, "Яблоко", (1, 0, 0, 1), (0, 0, 0))
    block_a.setup((0.0, 0.0, 0.0), 1)
    block_a.state = BlockState.LANDED

    block_b = FruitBlock(0, "Яблоко", (1, 0, 0, 1), (1, 0, 0))
    block_b.setup((0.3, 0.0, 0.0), 2)
    block_b.state = BlockState.LANDED

    matches = detector.find_matches([block_a, block_b])
    assert len(matches) == 1
    assert matches[0] == (block_a, block_b) or matches[0] == (block_b, block_a)
    print("  [OK] Совпадение близких блоков")

    block_c = FruitBlock(0, "Яблоко", (1, 0, 0, 1), (2, 0, 0))
    block_c.setup((2.0, 0.0, 0.0), 3)
    block_c.state = BlockState.LANDED

    matches = detector.find_matches([block_a, block_c])
    assert len(matches) == 0
    print("  [OK] Нет совпадения для далёких блоков")

    block_d = FruitBlock(1, "Апельсин", (1, 0.5, 0, 1), (0, 1, 0))
    block_d.setup((0.1, 0.0, 0.0), 4)
    block_d.state = BlockState.LANDED

    matches = detector.find_matches([block_a, block_d])
    assert len(matches) == 0
    print("  [OK] Нет совпадения для разных типов")

    blocks = []
    for i in range(4):
        b = FruitBlock(0, "Яблоко", (1, 0, 0, 1), (i, 0, 0))
        b.setup((i * 0.3, 0.0, 0.0), 10 + i)
        b.state = BlockState.LANDED
        blocks.append(b)

    matches = detector.find_matches(blocks)
    assert len(matches) == 2
    print("  [OK] Множественные совпадения (4 блока → 2 пары)")

    potential = detector.find_potential_matches(blocks, [])
    assert potential == 2
    print("  [OK] Потенциальные совпадения")

    print("  PASSED\n")


def test_level_generator():
    """Тестирует генератор уровней."""
    print("=== Тест: LevelGenerator ===")

    generator = LevelGenerator(seed=42)

    fruits = [
        {"id": 0, "name": "apple", "display_name": "Яблоко", "color": [1, 0, 0, 1]},
        {"id": 1, "name": "orange", "display_name": "Апельсин", "color": [1, 0.5, 0, 1]},
        {"id": 2, "name": "banana", "display_name": "Банан", "color": [1, 1, 0, 1]},
    ]

    blocks = generator.generate_level(3, 3, 2, fruits)
    assert len(blocks) == 18
    print(f"  [OK] Генерация уровня 3x3x2: {len(blocks)} блоков")

    type_counts = {}
    for block in blocks:
        ftype = block["fruit_type_id"]
        type_counts[ftype] = type_counts.get(ftype, 0) + 1

    for ftype, count in type_counts.items():
        assert count % 2 == 0, f"Тип {ftype} имеет нечётное количество: {count}"
        assert count >= 2, f"Тип {ftype} имеет менее 2 блоков: {count}"
    print("  [OK] Чётное количество каждого типа (решаемость)")

    positions = set()
    for block in blocks:
        pos = tuple(block["grid_position"])
        assert pos not in positions, f"Дублирование позиции: {pos}"
        positions.add(pos)
    print("  [OK] Уникальные позиции")

    tutorial = generator.generate_tutorial_level(fruits[:2])
    assert len(tutorial) == 8
    print(f"  [OK] Обучающий уровень: {len(tutorial)} блоков")

    big_blocks = generator.generate_level(5, 5, 5, fruits)
    assert len(big_blocks) == 124  # 125 ячеек, но чётное число = 124
    print(f"  [OK] Большой уровень 5x5x5: {len(big_blocks)} блоков (чётное)")

    print("  PASSED\n")


def test_board_manager():
    """Тестирует менеджер игрового поля."""
    print("=== Тест: BoardManager ===")

    board = BoardManager(block_size=0.3, block_spacing=0.05)
    board.setup_board(3, 3, 2, capacity=10)

    assert board.grid_width == 3
    assert board.grid_height == 3
    assert board.grid_depth == 2
    print("  [OK] Настройка поля")

    blocks_data = [
        {"fruit_type_id": 0, "fruit_type_name": "Яблоко",
         "color": [1, 0, 0, 1], "grid_position": [0, 0, 0]},
        {"fruit_type_id": 1, "fruit_type_name": "Апельсин",
         "color": [1, 0.5, 0, 1], "grid_position": [1, 0, 0]},
        {"fruit_type_id": 0, "fruit_type_name": "Яблоко",
         "color": [1, 0, 0, 1], "grid_position": [0, 1, 0]},
        {"fruit_type_id": 1, "fruit_type_name": "Апельсин",
         "color": [1, 0.5, 0, 1], "grid_position": [1, 1, 0]},
    ]

    created = board.place_blocks(blocks_data)
    assert len(created) == 4
    assert len(board.grid) == 4
    print("  [OK] Размещение блоков")

    block = board.get_block_at_grid((0, 0, 0))
    assert block is not None
    assert block.fruit_type_name == "Яблоко"
    print("  [OK] Получение блока по позиции")

    neighbors = board.get_neighbors(block)
    assert len(neighbors) >= 1
    print(f"  [OK] Поиск соседей: {len(neighbors)} найдено")

    assert not board.is_board_empty()
    assert not board.is_collection_zone_full()
    print("  [OK] Проверки состояния поля")

    info = board.get_board_info()
    assert info["total_blocks"] == 4
    assert info["grid_blocks"] == 4
    print(f"  [OK] Информация о поле: {info}")

    print("  PASSED\n")


def test_score_manager():
    """Тестирует систему очков."""
    print("=== Тест: ScoreManager ===")

    score_mgr = ScoreManager(
        base_points=100, chain_multiplier=2,
        speed_bonus=50, speed_threshold=3.0
    )

    score_mgr.add_score(100, chain_count=1)
    assert score_mgr.current_score == 100
    print("  [OK] Базовое начисление очков")

    score_mgr.add_score(200, chain_count=2)
    assert score_mgr.current_score == 300
    assert score_mgr.max_chain == 2
    print("  [OK] Начисление с цепной реакцией")

    points = score_mgr.calculate_match_points(chain_count=3, is_fast=True)
    assert points == 100 * 4 + 50  # base * 2^2 + speed_bonus
    print(f"  [OK] Расчёт очков: chain=3, fast=true → {points}")

    bonus = score_mgr.calculate_level_bonus(remaining_time=30.0, time_multiplier=10)
    assert bonus == 300
    print(f"  [OK] Бонус за время: 30с × 10 = {bonus}")

    stats = score_mgr.finalize_level()
    assert stats["score"] == 300
    assert stats["matches"] == 2
    print(f"  [OK] Финализация уровня: {stats}")

    score_mgr.reset_level()
    assert score_mgr.current_score == 0
    assert score_mgr.total_score == 300
    print("  [OK] Сброс уровня (total сохраняется)")

    print("  PASSED\n")


def test_physics_controller():
    """Тестирует контроллер физики."""
    print("=== Тест: PhysicsController ===")

    physics = PhysicsController()
    physics.configure({
        "gravity": -9.81,
        "block_mass": 1.0,
        "block_bounciness": 0.2,
        "block_friction": 0.6,
        "fall_gravity_multiplier": 2.0
    })

    assert physics.gravity == -9.81
    assert physics.gravity_multiplier == 2.0
    print("  [OK] Настройка физики")

    physics.setup_collection_zone(width=2.0, depth=2.0, floor_y=0.0)
    assert physics.collection_zone_floor_y == 0.0
    assert physics.collection_zone_walls["left"] == -1.0
    print("  [OK] Настройка зоны сбора")

    block = FruitBlock(0, "Яблоко", (1, 0, 0, 1), (0, 0, 0))
    block.setup((0.0, 2.0, 0.0), 1)

    physics.enable_block_physics(block)
    assert block.is_kinematic is False
    assert block.use_gravity is True
    print("  [OK] Включение физики блока")

    initial_y = block.position[1]
    for _ in range(50):
        physics.simulate_fall(block, 0.016)
    assert block.position[1] < initial_y
    print(f"  [OK] Симуляция падения: {initial_y:.1f} → {block.position[1]:.3f}")

    assert physics.get_falling_block_count() == 1
    physics.disable_block_physics(block)
    assert physics.get_falling_block_count() == 0
    print("  [OK] Отключение физики")

    print("  PASSED\n")


def test_onboarding_controller():
    """Тестирует контроллер обучения."""
    print("=== Тест: OnboardingController ===")

    onboarding = OnboardingController()
    assert not onboarding.is_active
    assert not onboarding.is_complete
    print("  [OK] Начальное состояние")

    onboarding.start_onboarding()
    assert onboarding.is_active
    assert not onboarding.is_complete
    print("  [OK] Запуск обучения")

    for _ in range(150):
        onboarding.update(0.02)
    hints = onboarding.get_visible_hints()
    print(f"  [OK] Обновление: прогресс={onboarding.get_progress():.1%}, "
          f"видимых подсказок: {len(hints)}")

    onboarding.on_first_action()
    print(f"  [OK] Первое действие обработано")

    for _ in range(200):
        onboarding.update(0.02)
    assert onboarding.is_complete
    print("  [OK] Обучение завершено")

    print("  PASSED\n")


def test_ui_controller():
    """Тестирует контроллер интерфейса."""
    print("=== Тест: UIController ===")

    ui = UIController()

    ui.update_score(500)
    assert ui.score_text.text == "Очки: 500"
    print("  [OK] Обновление счёта")

    ui.update_level(3)
    assert ui.level_text.text == "Уровень: 3"
    print("  [OK] Обновление уровня")

    ui.update_timer(95.0)
    assert ui.timer_text.text == "01:35"
    print("  [OK] Обновление таймера")

    ui.show_points_popup(200, (0.5, 1.0, 0.3))
    assert len(ui.get_active_popups()) == 1
    print("  [OK] Всплывающие очки")

    for _ in range(100):
        ui.update(0.02)
    remaining = len(ui.get_active_popups())
    print(f"  [OK] Обновление: осталось попапов: {remaining}")

    ui.show_game_over("Нет места!", 1500, 20)
    assert ui.game_over_panel.is_visible
    print("  [OK] Экран проигрыша")

    ui.reset()
    assert not ui.game_over_panel.is_visible
    print("  [OK] Сброс UI")

    print("  PASSED\n")


def test_effects_controller():
    """Тестирует контроллер эффектов."""
    print("=== Тест: EffectsController ===")

    effects = EffectsController()

    effects.play_activation_flash((0.5, 1.0, 0.0))
    assert effects.get_active_effect_count() == 1
    print("  [OK] Вспышка активации")

    effects.play_match_explosion((0.0, 0.5, 0.0), fruit_type_id=2)
    assert effects.get_active_effect_count() == 2
    print("  [OK] Взрыв совпадения")

    effects.play_chain_flash(chain_count=3)
    flash = effects.get_screen_flash_state()
    assert flash["alpha"] > 0
    print(f"  [OK] Вспышка цепочки: alpha={flash['alpha']:.3f}")

    for _ in range(100):
        effects.update(0.016)
    print(f"  [OK] Обновление: активных эффектов: {effects.get_active_effect_count()}")

    effects.play_victory_fireworks()
    assert effects.get_active_effect_count() > 0
    print(f"  [OK] Фейерверки: {effects.get_active_effect_count()} эффектов")

    effects.clear_all_effects()
    assert effects.get_active_effect_count() == 0
    print("  [OK] Очистка эффектов")

    print("  PASSED\n")


def test_game_manager_integration():
    """Интеграционный тест GameManager."""
    print("=== Тест: GameManager (интеграционный) ===")

    gm = GameManager()
    board = BoardManager()
    match_det = MatchDetector()
    score_mgr = ScoreManager()
    ui = UIController()
    audio = AudioController()
    effects = EffectsController()
    onboarding = OnboardingController()
    level_gen = LevelGenerator(seed=42)
    physics = PhysicsController()

    gm.initialize(
        board_manager=board,
        match_detector=match_det,
        score_manager=score_mgr,
        ui_controller=ui,
        audio_controller=audio,
        effects_controller=effects,
        onboarding_controller=onboarding,
        level_generator=level_gen,
        physics_controller=physics
    )
    assert gm.is_initialized
    print("  [OK] Инициализация")

    gm.start_game()
    assert gm.state in (GameState.ONBOARDING, GameState.PLAYING)
    assert gm.current_level == 1
    print(f"  [OK] Запуск игры: state={gm.state.name}")

    for _ in range(10):
        gm.update(0.016)
    print(f"  [OK] Обновление: state={gm.state.name}")

    info = gm.get_game_info()
    assert info["level"] == 1
    assert info["remaining_blocks"] > 0
    print(f"  [OK] Информация: {info}")

    gm.pause()
    assert gm.state == GameState.PAUSED
    gm.resume()
    assert gm.state in (GameState.PLAYING, GameState.ONBOARDING)
    print("  [OK] Пауза/Возобновление")

    gm.restart_level()
    assert gm.current_level == 1
    print("  [OK] Перезапуск уровня")

    gm.restart_game()
    assert gm.current_level == 1
    assert gm.total_score == 0
    print("  [OK] Перезапуск игры")

    print("  PASSED\n")


def run_all_tests():
    """Запускает все тесты."""
    print("=" * 60)
    print("  Тесты: Фруктовые Блоки VR")
    print("=" * 60)
    print()

    tests = [
        test_fruit_block,
        test_match_detector,
        test_level_generator,
        test_board_manager,
        test_score_manager,
        test_physics_controller,
        test_onboarding_controller,
        test_ui_controller,
        test_effects_controller,
        test_game_manager_integration,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"  FAILED: {e}")
            import traceback
            traceback.print_exc()
            print()

    print("=" * 60)
    print(f"  Результаты: {passed} пройдено, {failed} провалено")
    print(f"  Итого: {passed}/{passed + failed}")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
