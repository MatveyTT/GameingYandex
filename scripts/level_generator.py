"""
LevelGenerator — генератор уровней.

Создаёт расположение фруктовых блоков для каждого уровня,
гарантируя решаемость (каждый тип фрукта имеет чётное количество).
"""

import random
import math
from typing import List, Dict, Any, Tuple, Optional


class LevelGenerator:
    """
    Генератор уровней.

    Создаёт сбалансированные уровни с гарантией:
    - Чётное количество каждого типа фрукта (для возможности совпадений)
    - Минимум 2 блока каждого используемого типа
    - Рандомизированное, но сбалансированное размещение
    - Начальное расположение, гарантирующее решаемость
    """

    MIN_BLOCKS_PER_TYPE = 2
    MAX_GENERATION_ATTEMPTS = 100

    def __init__(self, seed: Optional[int] = None):
        """
        Args:
            seed: Сид для генератора случайных чисел (для воспроизводимости)
        """
        self.seed = seed
        if seed is not None:
            random.seed(seed)

        self._generation_count: int = 0

    def generate_level(self, grid_width: int, grid_height: int,
                        grid_depth: int,
                        available_fruits: List[Dict[str, Any]],
                        difficulty: float = 1.0) -> List[Dict[str, Any]]:
        """
        Генерирует расположение блоков для уровня.

        Args:
            grid_width: Ширина сетки
            grid_height: Высота сетки
            grid_depth: Глубина сетки
            available_fruits: Доступные типы фруктов
            difficulty: Модификатор сложности (0.5 - 2.0)

        Returns:
            Список данных блоков для BoardManager.place_blocks()
        """
        self._generation_count += 1

        total_cells = grid_width * grid_height * grid_depth
        fruit_count = len(available_fruits)

        if fruit_count == 0:
            print("[LevelGenerator] ОШИБКА: нет доступных фруктов!")
            return []

        if total_cells < fruit_count * self.MIN_BLOCKS_PER_TYPE:
            print("[LevelGenerator] ПРЕДУПРЕЖДЕНИЕ: мало ячеек для всех типов фруктов")

        type_distribution = self._calculate_distribution(
            total_cells, fruit_count, difficulty
        )

        positions = self._generate_positions(grid_width, grid_height, grid_depth)

        block_types = self._create_block_sequence(type_distribution)

        random.shuffle(block_types)

        blocks_data = self._assign_blocks_to_positions(
            block_types, positions, available_fruits
        )

        if not self._validate_level(blocks_data):
            print("[LevelGenerator] ПРЕДУПРЕЖДЕНИЕ: уровень может быть нерешаемым")

        print(f"[LevelGenerator] Уровень #{self._generation_count} сгенерирован: "
              f"{len(blocks_data)} блоков, {fruit_count} типов фруктов, "
              f"сетка {grid_width}x{grid_height}x{grid_depth}")

        return blocks_data

    def _calculate_distribution(self, total_cells: int,
                                 fruit_count: int,
                                 difficulty: float) -> List[int]:
        """
        Рассчитывает распределение типов фруктов.

        Гарантирует чётное количество каждого типа.

        Args:
            total_cells: Общее количество ячеек
            fruit_count: Количество типов фруктов
            difficulty: Модификатор сложности

        Returns:
            Список количеств для каждого типа [count_type_0, count_type_1, ...]
        """
        total_even = total_cells if total_cells % 2 == 0 else total_cells - 1

        base_per_type = total_even // fruit_count
        if base_per_type % 2 != 0:
            base_per_type -= 1
        base_per_type = max(self.MIN_BLOCKS_PER_TYPE, base_per_type)

        distribution = [base_per_type] * fruit_count
        total_assigned = sum(distribution)
        remaining = total_even - total_assigned

        while remaining >= 2:
            type_idx = random.randint(0, fruit_count - 1)
            distribution[type_idx] += 2
            remaining -= 2

        if difficulty > 1.0:
            variance = int((difficulty - 1.0) * 4)
            for _ in range(variance):
                if fruit_count < 2:
                    break
                src = random.randint(0, fruit_count - 1)
                dst = random.randint(0, fruit_count - 1)
                if src != dst and distribution[src] >= self.MIN_BLOCKS_PER_TYPE + 2:
                    distribution[src] -= 2
                    distribution[dst] += 2

        for i in range(len(distribution)):
            if distribution[i] % 2 != 0:
                distribution[i] -= 1
            distribution[i] = max(self.MIN_BLOCKS_PER_TYPE, distribution[i])

        return distribution

    def _generate_positions(self, width: int, height: int,
                             depth: int) -> List[Tuple[int, int, int]]:
        """
        Генерирует все позиции в сетке.

        Args:
            width: Ширина
            height: Высота
            depth: Глубина

        Returns:
            Список позиций (col, row, layer)
        """
        positions = []
        for layer in range(depth):
            for row in range(height):
                for col in range(width):
                    positions.append((col, row, layer))
        return positions

    def _create_block_sequence(self, distribution: List[int]) -> List[int]:
        """
        Создаёт последовательность ID типов фруктов.

        Args:
            distribution: Количества каждого типа

        Returns:
            Список ID типов (не перемешанный)
        """
        sequence = []
        for type_id, count in enumerate(distribution):
            sequence.extend([type_id] * count)
        return sequence

    def _assign_blocks_to_positions(self, block_types: List[int],
                                      positions: List[Tuple[int, int, int]],
                                      available_fruits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Привязывает типы блоков к позициям.

        Args:
            block_types: Перемешанная последовательность ID типов
            positions: Список позиций в сетке
            available_fruits: Данные о типах фруктов

        Returns:
            Список данных блоков
        """
        blocks_data = []

        count = min(len(block_types), len(positions))

        for i in range(count):
            type_id = block_types[i]
            pos = positions[i]

            fruit_data = available_fruits[type_id] if type_id < len(available_fruits) else available_fruits[0]

            block_data = {
                "fruit_type_id": fruit_data.get("id", type_id),
                "fruit_type_name": fruit_data.get("display_name",
                                                    fruit_data.get("name", f"fruit_{type_id}")),
                "color": tuple(fruit_data.get("color", [1.0, 1.0, 1.0, 1.0])),
                "grid_position": list(pos),
                "model": fruit_data.get("model", "default_block"),
                "texture": fruit_data.get("texture", "default_texture")
            }
            blocks_data.append(block_data)

        return blocks_data

    def _validate_level(self, blocks_data: List[Dict[str, Any]]) -> bool:
        """
        Проверяет решаемость уровня.

        Базовая проверка: каждый тип фрукта имеет чётное количество.

        Args:
            blocks_data: Данные блоков

        Returns:
            True если уровень валиден
        """
        type_counts: Dict[int, int] = {}
        for block in blocks_data:
            ftype = block["fruit_type_id"]
            type_counts[ftype] = type_counts.get(ftype, 0) + 1

        for ftype, count in type_counts.items():
            if count % 2 != 0:
                print(f"[LevelGenerator] Нечётное количество типа {ftype}: {count}")
                return False
            if count < self.MIN_BLOCKS_PER_TYPE:
                print(f"[LevelGenerator] Слишком мало типа {ftype}: {count}")
                return False

        return True

    def generate_tutorial_level(self, available_fruits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Генерирует специальный обучающий уровень.

        Маленький, с очевидными совпадениями для быстрого понимания.

        Args:
            available_fruits: Доступные типы фруктов (нужно минимум 2)

        Returns:
            Список данных блоков
        """
        if len(available_fruits) < 2:
            available_fruits = available_fruits * 2

        blocks_data = []

        tutorial_layout = [
            ((0, 0, 0), 0), ((1, 0, 0), 1),
            ((0, 1, 0), 1), ((1, 1, 0), 0),
            ((0, 0, 1), 0), ((1, 0, 1), 1),
            ((0, 1, 1), 1), ((1, 1, 1), 0),
        ]

        for pos, type_idx in tutorial_layout:
            type_idx = type_idx % len(available_fruits)
            fruit_data = available_fruits[type_idx]

            block_data = {
                "fruit_type_id": fruit_data.get("id", type_idx),
                "fruit_type_name": fruit_data.get("display_name",
                                                    fruit_data.get("name", f"fruit_{type_idx}")),
                "color": tuple(fruit_data.get("color", [1.0, 1.0, 1.0, 1.0])),
                "grid_position": list(pos),
                "model": fruit_data.get("model", "default_block"),
                "texture": fruit_data.get("texture", "default_texture")
            }
            blocks_data.append(block_data)

        return blocks_data

    def set_seed(self, seed: int) -> None:
        """Устанавливает сид генератора."""
        self.seed = seed
        random.seed(seed)

    def get_generation_count(self) -> int:
        """Возвращает количество сгенерированных уровней."""
        return self._generation_count
