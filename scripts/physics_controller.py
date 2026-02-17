"""
PhysicsController — контроллер физики.

Управляет физическим поведением блоков: гравитация,
столкновения, отскоки, трение.

Работает совместно с физическим движком Varwin (Unity Physics).
"""

import math
from typing import Dict, Any, Tuple, List, Optional

from scripts.fruit_block import FruitBlock, BlockState


class PhysicsController:
    """
    Контроллер физики для управления поведением блоков.

    В Varwin XRMS физика обрабатывается движком Unity,
    этот контроллер управляет параметрами и дополнительной логикой.
    """

    DEFAULT_GRAVITY = -9.81
    DEFAULT_MASS = 1.0
    DEFAULT_DRAG = 0.1
    DEFAULT_ANGULAR_DRAG = 0.5
    DEFAULT_BOUNCINESS = 0.2
    DEFAULT_FRICTION = 0.6

    def __init__(self):
        self.gravity: float = self.DEFAULT_GRAVITY
        self.gravity_multiplier: float = 2.0
        self.block_mass: float = self.DEFAULT_MASS
        self.block_drag: float = self.DEFAULT_DRAG
        self.block_angular_drag: float = self.DEFAULT_ANGULAR_DRAG
        self.block_bounciness: float = self.DEFAULT_BOUNCINESS
        self.block_friction: float = self.DEFAULT_FRICTION

        self.collection_zone_floor_y: float = 0.0
        self.collection_zone_walls: Dict[str, float] = {
            "left": -1.0,
            "right": 1.0,
            "front": -1.0,
            "back": 1.0
        }

        self._active_falling_blocks: List[FruitBlock] = []
        self._velocity_threshold: float = 0.05
        self._settled_time_required: float = 0.3
        self._block_settled_timers: Dict[int, float] = {}

    def configure(self, config: Dict[str, Any]) -> None:
        """
        Настраивает параметры физики из конфигурации.

        Args:
            config: Словарь с параметрами физики
        """
        self.gravity = config.get("gravity", self.DEFAULT_GRAVITY)
        self.block_mass = config.get("block_mass", self.DEFAULT_MASS)
        self.block_drag = config.get("block_drag", self.DEFAULT_DRAG)
        self.block_angular_drag = config.get("block_angular_drag", self.DEFAULT_ANGULAR_DRAG)
        self.block_bounciness = config.get("block_bounciness", self.DEFAULT_BOUNCINESS)
        self.block_friction = config.get("block_friction", self.DEFAULT_FRICTION)

        gravity_mult = config.get("fall_gravity_multiplier", 2.0)
        self.gravity_multiplier = gravity_mult

        print(f"[PhysicsController] Настроен: gravity={self.gravity}, "
              f"mass={self.block_mass}, bounce={self.block_bounciness}")

    def setup_collection_zone(self, width: float, depth: float,
                               floor_y: float = 0.0) -> None:
        """
        Настраивает зону сбора (физические границы).

        Args:
            width: Ширина зоны
            depth: Глубина зоны
            floor_y: Высота пола
        """
        half_w = width / 2.0
        half_d = depth / 2.0
        self.collection_zone_floor_y = floor_y
        self.collection_zone_walls = {
            "left": -half_w,
            "right": half_w,
            "front": -half_d,
            "back": half_d
        }

    def apply_physics_to_block(self, block: FruitBlock,
                                scene_object: Any = None) -> None:
        """
        Применяет физические параметры к блоку.

        В Varwin это настраивает Rigidbody и Collider объекта.

        Args:
            block: Блок для настройки
            scene_object: Объект Varwin-сцены
        """
        if scene_object is None:
            scene_object = block.scene_object

        if scene_object is None:
            return

        try:
            rb = getattr(scene_object, 'rigidbody', None)
            if rb:
                rb.mass = self.block_mass
                rb.drag = self.block_drag
                rb.angular_drag = self.block_angular_drag

            collider = getattr(scene_object, 'collider', None)
            if collider:
                if hasattr(collider, 'material'):
                    collider.material.bounciness = self.block_bounciness
                    collider.material.dynamic_friction = self.block_friction
                    collider.material.static_friction = self.block_friction * 1.2

        except Exception as e:
            print(f"[PhysicsController] Ошибка настройки физики: {e}")

    def enable_block_physics(self, block: FruitBlock) -> None:
        """
        Включает физику для блока (начало падения).

        Args:
            block: Блок для активации физики
        """
        block.is_kinematic = False
        block.use_gravity = True

        if block not in self._active_falling_blocks:
            self._active_falling_blocks.append(block)

        if block.scene_object:
            try:
                rb = getattr(block.scene_object, 'rigidbody', None)
                if rb:
                    rb.is_kinematic = False
                    rb.use_gravity = True
            except Exception as e:
                print(f"[PhysicsController] Ошибка включения физики: {e}")

        print(f"[PhysicsController] Физика включена для блока {block.block_id}")

    def disable_block_physics(self, block: FruitBlock) -> None:
        """
        Отключает физику для блока (блок приземлился).

        Args:
            block: Блок для деактивации физики
        """
        block.is_kinematic = True
        block.use_gravity = False

        if block in self._active_falling_blocks:
            self._active_falling_blocks.remove(block)

        if block.block_id in self._block_settled_timers:
            del self._block_settled_timers[block.block_id]

    def update(self, delta_time: float) -> None:
        """
        Обновление физики. Вызывается каждый кадр.

        Args:
            delta_time: Время с предыдущего кадра
        """
        blocks_to_land = []

        for block in list(self._active_falling_blocks):
            if block.state == BlockState.DESTROYED:
                self._active_falling_blocks.remove(block)
                continue

            if self._is_block_settled(block, delta_time):
                blocks_to_land.append(block)

        for block in blocks_to_land:
            self._on_block_settled(block)

    def _is_block_settled(self, block: FruitBlock, delta_time: float) -> bool:
        """
        Проверяет, успокоился ли блок (перестал двигаться).

        Args:
            block: Блок для проверки
            delta_time: Время с предыдущего кадра

        Returns:
            True если блок неподвижен достаточно долго
        """
        velocity_magnitude = math.sqrt(
            block.velocity[0] ** 2 +
            block.velocity[1] ** 2 +
            block.velocity[2] ** 2
        )

        if velocity_magnitude < self._velocity_threshold:
            timer = self._block_settled_timers.get(block.block_id, 0.0)
            timer += delta_time
            self._block_settled_timers[block.block_id] = timer

            return timer >= self._settled_time_required
        else:
            self._block_settled_timers[block.block_id] = 0.0
            return False

    def _on_block_settled(self, block: FruitBlock) -> None:
        """
        Обработка приземления блока.

        Args:
            block: Приземлившийся блок
        """
        block.on_collision()
        self.disable_block_physics(block)

    def simulate_fall(self, block: FruitBlock, delta_time: float) -> None:
        """
        Упрощённая симуляция падения (для preview/тестирования).

        Используется когда физический движок недоступен.

        Args:
            block: Падающий блок
            delta_time: Время с предыдущего кадра
        """
        if not block.use_gravity:
            return

        effective_gravity = self.gravity * self.gravity_multiplier
        vy = block.velocity[1] + effective_gravity * delta_time
        block.velocity = (block.velocity[0], vy, block.velocity[2])

        new_x = block.position[0] + block.velocity[0] * delta_time
        new_y = block.position[1] + block.velocity[1] * delta_time
        new_z = block.position[2] + block.velocity[2] * delta_time

        half_size = block.block_size / 2.0
        if new_y - half_size <= self.collection_zone_floor_y:
            new_y = self.collection_zone_floor_y + half_size
            vy = -block.velocity[1] * self.block_bounciness
            if abs(vy) < 0.1:
                vy = 0.0
            block.velocity = (block.velocity[0] * 0.8, vy, block.velocity[2] * 0.8)

        walls = self.collection_zone_walls
        new_x = max(walls["left"] + half_size, min(walls["right"] - half_size, new_x))
        new_z = max(walls["front"] + half_size, min(walls["back"] - half_size, new_z))

        block.position = (new_x, new_y, new_z)

    def get_falling_block_count(self) -> int:
        """Возвращает количество падающих блоков."""
        return len(self._active_falling_blocks)

    def are_all_settled(self) -> bool:
        """Проверяет, все ли блоки успокоились."""
        return len(self._active_falling_blocks) == 0

    def reset(self) -> None:
        """Сбрасывает состояние контроллера."""
        self._active_falling_blocks.clear()
        self._block_settled_timers.clear()
