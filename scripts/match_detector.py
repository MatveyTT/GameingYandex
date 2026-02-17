"""
MatchDetector — детектор совпадений фруктовых блоков.

Находит пары одинаковых блоков, находящихся рядом друг с другом
в зоне сбора, и отмечает их для удаления.
"""

import math
from typing import List, Tuple, Dict, Set, Optional

from scripts.fruit_block import FruitBlock, BlockState


class MatchDetector:
    """
    Детектор совпадений.

    Сканирует блоки в зоне сбора и находит пары одинаковых
    блоков, расстояние между которыми меньше порогового значения.
    """

    def __init__(self, match_distance: float = 0.45):
        """
        Args:
            match_distance: Максимальное расстояние для совпадения
        """
        self.match_distance = match_distance
        self._last_matches: List[Tuple[FruitBlock, FruitBlock]] = []
        self._match_history: List[Dict] = []

    def configure(self, match_distance: float) -> None:
        """
        Обновляет параметры детектора.

        Args:
            match_distance: Новое пороговое расстояние
        """
        self.match_distance = match_distance

    def find_matches(self, blocks: List[FruitBlock]) -> List[Tuple[FruitBlock, FruitBlock]]:
        """
        Находит все пары совпадающих блоков.

        Алгоритм:
        1. Группирует блоки по типу фрукта
        2. Для каждой группы проверяет пары на расстояние
        3. Каждый блок может участвовать только в одном совпадении
        4. Приоритет: ближайшие пары

        Args:
            blocks: Список блоков для проверки (обычно из зоны сбора)

        Returns:
            Список пар совпавших блоков
        """
        active_blocks = [
            b for b in blocks
            if b.state in (BlockState.LANDED, BlockState.IDLE)
        ]

        if len(active_blocks) < 2:
            self._last_matches = []
            return []

        groups = self._group_by_type(active_blocks)

        all_candidates: List[Tuple[float, FruitBlock, FruitBlock]] = []

        for fruit_type_id, group_blocks in groups.items():
            if len(group_blocks) < 2:
                continue

            for i in range(len(group_blocks)):
                for j in range(i + 1, len(group_blocks)):
                    block_a = group_blocks[i]
                    block_b = group_blocks[j]

                    distance = block_a.get_distance_to(block_b)

                    if distance <= self.match_distance:
                        all_candidates.append((distance, block_a, block_b))

        all_candidates.sort(key=lambda x: x[0])

        matched_ids: Set[int] = set()
        result: List[Tuple[FruitBlock, FruitBlock]] = []

        for distance, block_a, block_b in all_candidates:
            if block_a.block_id in matched_ids or block_b.block_id in matched_ids:
                continue

            result.append((block_a, block_b))
            matched_ids.add(block_a.block_id)
            matched_ids.add(block_b.block_id)

        self._last_matches = result

        if result:
            self._record_match_history(result)

        return result

    def find_potential_matches(self, grid_blocks: List[FruitBlock],
                                collection_blocks: List[FruitBlock]) -> int:
        """
        Подсчитывает потенциальные совпадения (для подсказок или проверки фейл-стейта).

        Проверяет, сколько пар одинаковых блоков существует
        среди всех оставшихся блоков (в сетке и зоне сбора).

        Args:
            grid_blocks: Блоки в сетке
            collection_blocks: Блоки в зоне сбора

        Returns:
            Количество возможных пар
        """
        all_blocks = grid_blocks + collection_blocks
        type_counts: Dict[int, int] = {}

        for block in all_blocks:
            if block.state not in (BlockState.DESTROYING, BlockState.DESTROYED):
                ftype = block.fruit_type_id
                type_counts[ftype] = type_counts.get(ftype, 0) + 1

        potential_pairs = 0
        for count in type_counts.values():
            potential_pairs += count // 2

        return potential_pairs

    def check_immediate_matches(self, blocks: List[FruitBlock],
                                 new_block: FruitBlock) -> Optional[FruitBlock]:
        """
        Быстрая проверка совпадения для нового блока.

        Проверяет, есть ли рядом с новым блоком
        блок того же типа.

        Args:
            blocks: Существующие блоки в зоне сбора
            new_block: Новый блок

        Returns:
            Блок-партнёр или None
        """
        closest_match: Optional[FruitBlock] = None
        closest_distance = float('inf')

        for block in blocks:
            if block.block_id == new_block.block_id:
                continue

            if block.state not in (BlockState.LANDED, BlockState.IDLE):
                continue

            if block.fruit_type_id != new_block.fruit_type_id:
                continue

            distance = new_block.get_distance_to(block)
            if distance <= self.match_distance and distance < closest_distance:
                closest_match = block
                closest_distance = distance

        return closest_match

    def _group_by_type(self, blocks: List[FruitBlock]) -> Dict[int, List[FruitBlock]]:
        """
        Группирует блоки по типу фрукта.

        Args:
            blocks: Список блоков

        Returns:
            Словарь {fruit_type_id: [блоки]}
        """
        groups: Dict[int, List[FruitBlock]] = {}
        for block in blocks:
            ftype = block.fruit_type_id
            if ftype not in groups:
                groups[ftype] = []
            groups[ftype].append(block)
        return groups

    def _record_match_history(self, matches: List[Tuple[FruitBlock, FruitBlock]]) -> None:
        """Записывает совпадения в историю."""
        for block_a, block_b in matches:
            record = {
                "fruit_type": block_a.fruit_type_name,
                "block_a_id": block_a.block_id,
                "block_b_id": block_b.block_id,
                "distance": round(block_a.get_distance_to(block_b), 3)
            }
            self._match_history.append(record)

    def get_match_count(self) -> int:
        """Возвращает общее количество совпадений за игру."""
        return len(self._match_history)

    def get_last_matches(self) -> List[Tuple[FruitBlock, FruitBlock]]:
        """Возвращает последние найденные совпадения."""
        return self._last_matches

    def reset(self) -> None:
        """Сбрасывает состояние детектора."""
        self._last_matches = []
        self._match_history = []
