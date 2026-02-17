"""
FruitBlock — логика фруктового блока.

Каждый блок представляет собой игровой объект с типом фрукта,
физическим поведением и визуальной обратной связью.

Прикрепляется к каждому объекту-блоку на сцене Varwin XRMS.
"""

import math
from enum import Enum, auto
from typing import Optional, Tuple, Dict, Any, Callable


class BlockState(Enum):
    """Состояния блока."""
    IDLE = auto()
    HOVERED = auto()
    ACTIVATED = auto()
    FALLING = auto()
    LANDED = auto()
    MATCHED = auto()
    DESTROYING = auto()
    DESTROYED = auto()


class FruitBlock:
    """
    Фруктовый блок — основной игровой объект.

    Атрибуты:
        fruit_type_id: Числовой ID типа фрукта (0-5)
        fruit_type_name: Название фрукта (яблоко, апельсин, ...)
        grid_position: Позиция в сетке (x, y, z)
        position: Мировая позиция (x, y, z)
        state: Текущее состояние блока
        color: Цвет блока (r, g, b, a)
    """

    IDLE_BOB_SPEED = 1.5
    IDLE_BOB_AMPLITUDE = 0.02
    HOVER_SCALE_TARGET = 1.08
    HOVER_OUTLINE_COLOR = (1.0, 1.0, 1.0, 0.8)
    ACTIVATION_FLASH_DURATION = 0.15
    DESTROY_DURATION = 0.4
    DESTROY_SHRINK_SCALE = 0.01

    def __init__(self, fruit_type_id: int, fruit_type_name: str,
                 color: Tuple[float, float, float, float],
                 grid_position: Tuple[int, int, int],
                 block_size: float = 0.3):
        """
        Args:
            fruit_type_id: ID типа фрукта
            fruit_type_name: Название типа фрукта
            color: Цвет (R, G, B, A) от 0.0 до 1.0
            grid_position: Позиция в сетке (col, row, layer)
            block_size: Размер блока в мировых единицах
        """
        self.fruit_type_id = fruit_type_id
        self.fruit_type_name = fruit_type_name
        self.color = color
        self.grid_position = grid_position
        self.block_size = block_size

        self.state = BlockState.IDLE
        self.position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self.rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self.scale: Tuple[float, float, float] = (1.0, 1.0, 1.0)
        self.velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)

        self.is_kinematic: bool = True
        self.use_gravity: bool = False
        self.is_interactable: bool = True

        self.block_id: int = -1
        self.scene_object: Optional[Any] = None

        self._time_alive: float = 0.0
        self._hover_lerp: float = 0.0
        self._activation_timer: float = 0.0
        self._destroy_timer: float = 0.0
        self._initial_y: float = 0.0
        self._on_landed_callback: Optional[Callable] = None
        self._on_destroyed_callback: Optional[Callable] = None
        self._on_activated_callback: Optional[Callable] = None

    def setup(self, world_position: Tuple[float, float, float],
              block_id: int, scene_object: Any = None) -> None:
        """
        Инициализирует блок в мире.

        Args:
            world_position: Мировая позиция (x, y, z)
            block_id: Уникальный ID блока в сцене
            scene_object: Ссылка на объект Varwin-сцены
        """
        self.position = world_position
        self._initial_y = world_position[1]
        self.block_id = block_id
        self.scene_object = scene_object
        self.state = BlockState.IDLE
        self.is_interactable = True
        self._apply_to_scene_object()

    def set_callbacks(self, on_activated: Optional[Callable] = None,
                      on_landed: Optional[Callable] = None,
                      on_destroyed: Optional[Callable] = None) -> None:
        """Устанавливает callback-функции для событий блока."""
        self._on_activated_callback = on_activated
        self._on_landed_callback = on_landed
        self._on_destroyed_callback = on_destroyed

    def update(self, delta_time: float) -> None:
        """
        Обновление логики блока. Вызывается каждый кадр.

        Args:
            delta_time: Время с предыдущего кадра в секундах
        """
        self._time_alive += delta_time

        if self.state == BlockState.IDLE:
            self._update_idle(delta_time)
        elif self.state == BlockState.HOVERED:
            self._update_hovered(delta_time)
        elif self.state == BlockState.ACTIVATED:
            self._update_activated(delta_time)
        elif self.state == BlockState.FALLING:
            self._update_falling(delta_time)
        elif self.state == BlockState.DESTROYING:
            self._update_destroying(delta_time)

    def _update_idle(self, delta_time: float) -> None:
        """Обновление в состоянии покоя — мягкое покачивание."""
        bob_offset = math.sin(self._time_alive * self.IDLE_BOB_SPEED) * self.IDLE_BOB_AMPLITUDE
        self.position = (
            self.position[0],
            self._initial_y + bob_offset,
            self.position[2]
        )
        self._hover_lerp = max(0.0, self._hover_lerp - delta_time * 5.0)
        self._apply_scale_from_hover()

    def _update_hovered(self, delta_time: float) -> None:
        """Обновление при наведении — плавное увеличение."""
        self._hover_lerp = min(1.0, self._hover_lerp + delta_time * 8.0)
        self._apply_scale_from_hover()

        bob_offset = math.sin(self._time_alive * self.IDLE_BOB_SPEED * 1.5) * self.IDLE_BOB_AMPLITUDE
        self.position = (
            self.position[0],
            self._initial_y + bob_offset,
            self.position[2]
        )

    def _update_activated(self, delta_time: float) -> None:
        """Обновление при активации — вспышка перед падением."""
        self._activation_timer += delta_time
        if self._activation_timer >= self.ACTIVATION_FLASH_DURATION:
            self._start_falling()

    def _update_falling(self, delta_time: float) -> None:
        """Обновление при падении (если физика не через Varwin)."""
        pass

    def _update_destroying(self, delta_time: float) -> None:
        """Обновление при уничтожении — сжатие и исчезновение."""
        self._destroy_timer += delta_time
        progress = min(1.0, self._destroy_timer / self.DESTROY_DURATION)

        eased = 1.0 - (1.0 - progress) * (1.0 - progress)

        current_scale = 1.0 - eased * (1.0 - self.DESTROY_SHRINK_SCALE)
        self.scale = (current_scale, current_scale, current_scale)

        spin_speed = 720.0 * progress
        self.rotation = (
            self.rotation[0],
            self.rotation[1] + spin_speed * delta_time,
            self.rotation[2]
        )

        if progress >= 1.0:
            self._on_destroy_complete()

    def _apply_scale_from_hover(self) -> None:
        """Рассчитывает масштаб на основе hover-состояния."""
        target = self.HOVER_SCALE_TARGET
        current = 1.0 + (target - 1.0) * self._hover_lerp
        self.scale = (current, current, current)

    def on_pointer_enter(self) -> None:
        """Вызывается при наведении курсора/луча на блок."""
        if self.state == BlockState.IDLE and self.is_interactable:
            self.state = BlockState.HOVERED

    def on_pointer_exit(self) -> None:
        """Вызывается при уходе курсора/луча с блока."""
        if self.state == BlockState.HOVERED:
            self.state = BlockState.IDLE

    def on_pointer_click(self) -> None:
        """Вызывается при клике/нажатии триггера на блоке."""
        if self.state in (BlockState.IDLE, BlockState.HOVERED) and self.is_interactable:
            self.activate()

    def activate(self) -> None:
        """Активирует блок — запускает процесс падения."""
        if self.state in (BlockState.ACTIVATED, BlockState.FALLING,
                          BlockState.DESTROYING, BlockState.DESTROYED):
            return

        self.state = BlockState.ACTIVATED
        self.is_interactable = False
        self._activation_timer = 0.0

        if self._on_activated_callback:
            self._on_activated_callback(self)

        print(f"[FruitBlock] Блок '{self.fruit_type_name}' "
              f"(ID:{self.block_id}) активирован")

    def _start_falling(self) -> None:
        """Запускает падение блока."""
        self.state = BlockState.FALLING
        self.is_kinematic = False
        self.use_gravity = True
        self._apply_physics_to_scene()

    def on_collision(self, other_object: Any = None,
                     collision_point: Tuple[float, float, float] = (0, 0, 0)) -> None:
        """
        Обработчик столкновения блока с другим объектом.

        Args:
            other_object: Объект столкновения
            collision_point: Точка столкновения
        """
        if self.state == BlockState.FALLING:
            self.state = BlockState.LANDED
            self.is_kinematic = True
            self.use_gravity = False

            if self._on_landed_callback:
                self._on_landed_callback(self)

    def start_destroy(self) -> None:
        """Запускает анимацию уничтожения блока."""
        if self.state == BlockState.DESTROYING or self.state == BlockState.DESTROYED:
            return

        self.state = BlockState.DESTROYING
        self.is_interactable = False
        self._destroy_timer = 0.0

    def _on_destroy_complete(self) -> None:
        """Завершает уничтожение блока."""
        self.state = BlockState.DESTROYED
        self.scale = (0.0, 0.0, 0.0)

        if self._on_destroyed_callback:
            self._on_destroyed_callback(self)

        if self.scene_object:
            pass

        print(f"[FruitBlock] Блок '{self.fruit_type_name}' "
              f"(ID:{self.block_id}) уничтожен")

    def _apply_to_scene_object(self) -> None:
        """Применяет параметры блока к объекту Varwin-сцены."""
        if self.scene_object is None:
            return

        try:
            obj = self.scene_object
            if hasattr(obj, 'transform'):
                obj.transform.position = self.position
                obj.transform.rotation = self.rotation
                obj.transform.local_scale = (
                    self.block_size * self.scale[0],
                    self.block_size * self.scale[1],
                    self.block_size * self.scale[2]
                )
        except Exception as e:
            print(f"[FruitBlock] Ошибка применения параметров: {e}")

    def _apply_physics_to_scene(self) -> None:
        """Применяет физические параметры к объекту Varwin-сцены."""
        if self.scene_object is None:
            return

        try:
            obj = self.scene_object
            if hasattr(obj, 'rigidbody'):
                obj.rigidbody.is_kinematic = self.is_kinematic
                obj.rigidbody.use_gravity = self.use_gravity
        except Exception as e:
            print(f"[FruitBlock] Ошибка применения физики: {e}")

    def get_distance_to(self, other: 'FruitBlock') -> float:
        """
        Рассчитывает расстояние до другого блока.

        Args:
            other: Другой блок

        Returns:
            Расстояние между центрами блоков
        """
        dx = self.position[0] - other.position[0]
        dy = self.position[1] - other.position[1]
        dz = self.position[2] - other.position[2]
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def matches_with(self, other: 'FruitBlock') -> bool:
        """
        Проверяет, совпадает ли этот блок с другим по типу.

        Args:
            other: Другой блок

        Returns:
            True если типы фруктов совпадают
        """
        return self.fruit_type_id == other.fruit_type_id

    def to_dict(self) -> Dict[str, Any]:
        """Сериализует блок в словарь."""
        return {
            "block_id": self.block_id,
            "fruit_type_id": self.fruit_type_id,
            "fruit_type_name": self.fruit_type_name,
            "grid_position": self.grid_position,
            "position": self.position,
            "state": self.state.name,
            "is_interactable": self.is_interactable
        }

    def __repr__(self) -> str:
        return (f"FruitBlock(id={self.block_id}, "
                f"fruit='{self.fruit_type_name}', "
                f"state={self.state.name}, "
                f"pos={self.grid_position})")
