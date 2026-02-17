"""
BoardManager — менеджер игрового поля.

Управляет трёхмерной сеткой блоков, зоной сбора,
размещением и удалением блоков.

Прикрепляется к объекту игрового поля в Varwin XRMS.
"""

import math
from typing import Optional, List, Tuple, Dict, Any

from scripts.fruit_block import FruitBlock, BlockState


class BoardManager:
    """
    Менеджер игрового поля.

    Управляет 3D-сеткой блоков и зоной сбора (коллекционной зоной),
    куда падают активированные блоки.
    """

    BOARD_ORIGIN = (0.0, 1.2, 0.0)
    COLLECTION_ZONE_ORIGIN = (0.0, 0.0, 0.0)
    COLLECTION_ZONE_WIDTH = 2.0
    COLLECTION_ZONE_DEPTH = 2.0

    def __init__(self, block_size: float = 0.3, block_spacing: float = 0.05):
        """
        Args:
            block_size: Размер одного блока
            block_spacing: Расстояние между блоками
        """
        self.block_size = block_size
        self.block_spacing = block_spacing
        self.cell_size = block_size + block_spacing

        self.grid_width: int = 0
        self.grid_height: int = 0
        self.grid_depth: int = 0

        self.grid: Dict[Tuple[int, int, int], FruitBlock] = {}
        self.collection_zone_blocks: List[FruitBlock] = []
        self.all_blocks: List[FruitBlock] = []

        self.collection_zone_capacity: int = 10
        self.collection_zone_height_limit: float = 2.0

        self._next_block_id: int = 0
        self._settling_timer: float = 0.0
        self._settling_threshold: float = 0.5

    def setup_board(self, width: int, height: int, depth: int,
                    capacity: int = 10) -> None:
        """
        Настраивает игровое поле.

        Args:
            width: Ширина сетки (кол-во столбцов)
            height: Высота сетки (кол-во рядов)
            depth: Глубина сетки (кол-во слоёв)
            capacity: Вместимость зоны сбора
        """
        self.grid_width = width
        self.grid_height = height
        self.grid_depth = depth
        self.collection_zone_capacity = capacity

        self.grid.clear()
        self.collection_zone_blocks.clear()
        self.all_blocks.clear()
        self._next_block_id = 0
        self._settling_timer = 0.0

        print(f"[BoardManager] Поле настроено: {width}x{height}x{depth}, "
              f"вместимость зоны сбора: {capacity}")

    def place_blocks(self, blocks_data: List[Dict[str, Any]]) -> List[FruitBlock]:
        """
        Размещает блоки на игровом поле.

        Args:
            blocks_data: Список данных блоков из генератора уровней.
                Каждый элемент: {
                    "fruit_type_id": int,
                    "fruit_type_name": str,
                    "color": (r, g, b, a),
                    "grid_position": (x, y, z)
                }

        Returns:
            Список созданных объектов FruitBlock
        """
        created_blocks = []

        for data in blocks_data:
            grid_pos = tuple(data["grid_position"])
            fruit_id = data["fruit_type_id"]
            fruit_name = data["fruit_type_name"]
            color = tuple(data["color"])

            block = FruitBlock(
                fruit_type_id=fruit_id,
                fruit_type_name=fruit_name,
                color=color,
                grid_position=grid_pos,
                block_size=self.block_size
            )

            world_pos = self._grid_to_world(grid_pos)
            block.setup(world_pos, self._next_block_id)
            self._next_block_id += 1

            self.grid[grid_pos] = block
            self.all_blocks.append(block)
            created_blocks.append(block)

        print(f"[BoardManager] Размещено {len(created_blocks)} блоков")
        return created_blocks

    def _grid_to_world(self, grid_pos: Tuple[int, int, int]) -> Tuple[float, float, float]:
        """
        Конвертирует позицию в сетке в мировые координаты.

        Сетка центрирована относительно BOARD_ORIGIN.

        Args:
            grid_pos: Позиция в сетке (col, row, layer)

        Returns:
            Мировая позиция (x, y, z)
        """
        col, row, layer = grid_pos

        offset_x = (self.grid_width - 1) * self.cell_size / 2.0
        offset_z = (self.grid_depth - 1) * self.cell_size / 2.0

        x = self.BOARD_ORIGIN[0] + col * self.cell_size - offset_x
        y = self.BOARD_ORIGIN[1] + row * self.cell_size
        z = self.BOARD_ORIGIN[2] + layer * self.cell_size - offset_z

        return (x, y, z)

    def release_block(self, block: FruitBlock) -> None:
        """
        Освобождает блок из сетки (игрок активировал его).

        Блок удаляется из сетки и начинает падение.
        Блоки выше него также проверяются на устойчивость.

        Args:
            block: Активированный блок
        """
        grid_pos = block.grid_position
        if grid_pos in self.grid:
            del self.grid[grid_pos]

        block.activate()
        self._settling_timer = 0.0

        self._check_unsupported_blocks(grid_pos)

        print(f"[BoardManager] Блок освобождён из позиции {grid_pos}")

    def _check_unsupported_blocks(self, removed_pos: Tuple[int, int, int]) -> None:
        """
        Проверяет и обрабатывает блоки без поддержки после удаления.

        Args:
            removed_pos: Позиция удалённого блока
        """
        col, row, layer = removed_pos

        for r in range(row + 1, self.grid_height):
            above_pos = (col, r, layer)
            if above_pos in self.grid:
                above_block = self.grid[above_pos]

                if not self._has_support(above_pos):
                    new_pos = self._find_supported_position(col, r, layer)
                    if new_pos and new_pos != above_pos:
                        del self.grid[above_pos]
                        above_block.grid_position = new_pos
                        self.grid[new_pos] = above_block

                        new_world = self._grid_to_world(new_pos)
                        above_block._initial_y = new_world[1]

    def _has_support(self, grid_pos: Tuple[int, int, int]) -> bool:
        """
        Проверяет, есть ли у блока поддержка снизу.

        Args:
            grid_pos: Позиция блока

        Returns:
            True если блок поддерживается
        """
        col, row, layer = grid_pos

        if row == 0:
            return True

        below_pos = (col, row - 1, layer)
        return below_pos in self.grid

    def _find_supported_position(self, col: int, start_row: int,
                                  layer: int) -> Optional[Tuple[int, int, int]]:
        """
        Находит ближайшую поддерживаемую позицию ниже.

        Args:
            col: Столбец
            start_row: Начальный ряд
            layer: Слой

        Returns:
            Позиция с поддержкой или None
        """
        for row in range(start_row - 1, -1, -1):
            pos = (col, row, layer)
            if pos in self.grid:
                supported_pos = (col, row + 1, layer)
                if supported_pos not in self.grid:
                    return supported_pos
                return None

        return (col, 0, layer) if (col, 0, layer) not in self.grid else None

    def on_block_landed(self, block: FruitBlock) -> None:
        """
        Обработчик приземления блока в зоне сбора.

        Args:
            block: Приземлившийся блок
        """
        if block not in self.collection_zone_blocks:
            self.collection_zone_blocks.append(block)

        self._settling_timer = 0.0

        print(f"[BoardManager] Блок '{block.fruit_type_name}' "
              f"приземлился в зону сбора")

    def remove_block(self, block: FruitBlock) -> None:
        """
        Удаляет блок из игры (после совпадения).

        Args:
            block: Блок для удаления
        """
        block.start_destroy()

        if block in self.collection_zone_blocks:
            self.collection_zone_blocks.remove(block)

        grid_pos = block.grid_position
        if grid_pos in self.grid:
            del self.grid[grid_pos]

    def update(self, delta_time: float) -> None:
        """
        Обновление игрового поля.

        Args:
            delta_time: Время с предыдущего кадра
        """
        for block in self.all_blocks:
            if block.state != BlockState.DESTROYED:
                block.update(delta_time)

        self._settling_timer += delta_time

    def are_blocks_settled(self) -> bool:
        """
        Проверяет, успокоились ли все блоки (нет падающих).

        Returns:
            True если все блоки в стабильном состоянии
        """
        if self._settling_timer < self._settling_threshold:
            return False

        for block in self.all_blocks:
            if block.state in (BlockState.FALLING, BlockState.ACTIVATED):
                return False
        return True

    def get_collection_zone_blocks(self) -> List[FruitBlock]:
        """Возвращает список блоков в зоне сбора."""
        return [b for b in self.collection_zone_blocks
                if b.state not in (BlockState.DESTROYING, BlockState.DESTROYED)]

    def get_remaining_blocks(self) -> List[FruitBlock]:
        """Возвращает список оставшихся блоков в сетке."""
        return [b for b in self.grid.values()
                if b.state not in (BlockState.DESTROYING, BlockState.DESTROYED)]

    def get_remaining_block_count(self) -> int:
        """Возвращает количество оставшихся блоков."""
        count = 0
        for block in self.all_blocks:
            if block.state not in (BlockState.DESTROYING, BlockState.DESTROYED):
                count += 1
        return count

    def is_board_empty(self) -> bool:
        """Проверяет, очищено ли всё поле."""
        return (len(self.grid) == 0 and
                len(self.get_collection_zone_blocks()) == 0)

    def is_collection_zone_full(self) -> bool:
        """Проверяет, заполнена ли зона сбора."""
        active_blocks = self.get_collection_zone_blocks()
        return len(active_blocks) >= self.collection_zone_capacity

    def get_collection_zone_max_height(self) -> float:
        """Возвращает максимальную высоту блоков в зоне сбора."""
        max_y = 0.0
        for block in self.collection_zone_blocks:
            if block.state not in (BlockState.DESTROYING, BlockState.DESTROYED):
                max_y = max(max_y, block.position[1] + self.block_size)
        return max_y

    def get_block_at_grid(self, grid_pos: Tuple[int, int, int]) -> Optional[FruitBlock]:
        """
        Возвращает блок в указанной позиции сетки.

        Args:
            grid_pos: Позиция в сетке

        Returns:
            Блок или None
        """
        return self.grid.get(grid_pos)

    def get_neighbors(self, block: FruitBlock) -> List[FruitBlock]:
        """
        Возвращает соседние блоки в сетке.

        Args:
            block: Блок для поиска соседей

        Returns:
            Список соседних блоков
        """
        col, row, layer = block.grid_position
        neighbors = []

        directions = [
            (1, 0, 0), (-1, 0, 0),
            (0, 1, 0), (0, -1, 0),
            (0, 0, 1), (0, 0, -1)
        ]

        for dx, dy, dz in directions:
            neighbor_pos = (col + dx, row + dy, layer + dz)
            neighbor = self.grid.get(neighbor_pos)
            if neighbor and neighbor.state not in (BlockState.DESTROYING, BlockState.DESTROYED):
                neighbors.append(neighbor)

        return neighbors

    def get_board_info(self) -> Dict[str, Any]:
        """Возвращает информацию о текущем состоянии поля."""
        return {
            "grid_size": f"{self.grid_width}x{self.grid_height}x{self.grid_depth}",
            "total_blocks": len(self.all_blocks),
            "grid_blocks": len(self.grid),
            "collection_zone_blocks": len(self.get_collection_zone_blocks()),
            "collection_zone_capacity": self.collection_zone_capacity,
            "collection_zone_height": round(self.get_collection_zone_max_height(), 2),
            "is_board_empty": self.is_board_empty(),
            "is_zone_full": self.is_collection_zone_full()
        }
