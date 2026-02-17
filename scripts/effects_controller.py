"""
EffectsController — контроллер визуальных эффектов.

Управляет частицами, вспышками, анимациями разрушения
и другими визуальными эффектами.

Работает с системой частиц Varwin (Unity Particle System).
"""

import math
from typing import Tuple, Dict, Any, Optional, List
from enum import Enum, auto


class EffectType(Enum):
    """Типы визуальных эффектов."""
    ACTIVATION_FLASH = auto()
    MATCH_EXPLOSION = auto()
    LAND_DUST = auto()
    CHAIN_SCREEN_FLASH = auto()
    VICTORY_FIREWORKS = auto()
    FAIL_EFFECT = auto()
    HOVER_GLOW = auto()
    BLOCK_TRAIL = auto()


class ParticleConfig:
    """Конфигурация системы частиц."""

    def __init__(self, count: int = 30, lifetime: float = 1.5,
                 speed: float = 3.0, size: float = 0.05,
                 color: Tuple[float, float, float, float] = (1, 1, 1, 1),
                 gravity_modifier: float = 0.5,
                 shape: str = "sphere"):
        self.count = count
        self.lifetime = lifetime
        self.speed = speed
        self.size = size
        self.color = color
        self.gravity_modifier = gravity_modifier
        self.shape = shape


FRUIT_PARTICLE_CONFIGS = {
    0: ParticleConfig(count=35, color=(1.0, 0.3, 0.3, 1.0), speed=3.5, shape="sphere"),
    1: ParticleConfig(count=35, color=(1.0, 0.6, 0.2, 1.0), speed=3.0, shape="sphere"),
    2: ParticleConfig(count=30, color=(1.0, 0.9, 0.3, 1.0), speed=4.0, shape="star"),
    3: ParticleConfig(count=40, color=(0.7, 0.4, 0.9, 1.0), speed=2.5, shape="sphere"),
    4: ParticleConfig(count=30, color=(1.0, 0.4, 0.6, 1.0), speed=3.0, shape="heart"),
    5: ParticleConfig(count=35, color=(0.3, 0.9, 0.5, 1.0), speed=3.5, shape="sphere"),
}


class ActiveEffect:
    """Активный эффект с временем жизни."""

    def __init__(self, effect_type: EffectType, position: Tuple[float, float, float],
                 duration: float, scene_object: Any = None):
        self.effect_type = effect_type
        self.position = position
        self.duration = duration
        self.scene_object = scene_object
        self.time_alive: float = 0.0
        self.is_finished: bool = False
        self.progress: float = 0.0

    def update(self, delta_time: float) -> None:
        """Обновление эффекта."""
        self.time_alive += delta_time
        self.progress = min(1.0, self.time_alive / max(self.duration, 0.001))
        if self.time_alive >= self.duration:
            self.is_finished = True


class EffectsController:
    """
    Контроллер визуальных эффектов.

    Управляет:
    - Вспышки активации блоков
    - Взрывы частиц при совпадении (цвет зависит от фрукта)
    - Пылевые облака при приземлении
    - Вспышки экрана при цепных реакциях
    - Фейерверки при победе
    - Красный overlay при проигрыше
    - Свечение при наведении
    """

    def __init__(self):
        self._active_effects: List[ActiveEffect] = []
        self._screen_flash_alpha: float = 0.0
        self._screen_flash_color: Tuple[float, float, float] = (1.0, 1.0, 1.0)
        self._screen_flash_decay: float = 3.0

        self.config: Dict[str, Any] = {
            "match_particle_count": 30,
            "match_particle_lifetime": 1.5,
            "match_particle_speed": 3.0,
            "activation_flash_intensity": 2.0,
            "chain_screen_flash_alpha": 0.15,
            "fail_screen_red_alpha": 0.4
        }

    def configure(self, config: Dict[str, Any]) -> None:
        """
        Настраивает параметры эффектов.

        Args:
            config: Словарь effects из game_config.json
        """
        self.config.update(config)

    def update(self, delta_time: float) -> None:
        """
        Обновление всех активных эффектов.

        Args:
            delta_time: Время с предыдущего кадра
        """
        finished = []
        for effect in self._active_effects:
            effect.update(delta_time)
            if effect.is_finished:
                finished.append(effect)
                self._cleanup_effect(effect)

        for effect in finished:
            self._active_effects.remove(effect)

        if self._screen_flash_alpha > 0.001:
            self._screen_flash_alpha *= math.exp(-self._screen_flash_decay * delta_time)
            if self._screen_flash_alpha < 0.001:
                self._screen_flash_alpha = 0.0

    def play_activation_flash(self, position: Tuple[float, float, float]) -> None:
        """
        Воспроизводит вспышку при активации блока.

        Яркая кратковременная вспышка в позиции блока.

        Args:
            position: Мировая позиция блока
        """
        effect = ActiveEffect(
            EffectType.ACTIVATION_FLASH, position,
            duration=0.15
        )
        self._active_effects.append(effect)

        self._spawn_particles(
            position=position,
            config=ParticleConfig(
                count=8, lifetime=0.3, speed=2.0,
                size=0.03, color=(1.0, 1.0, 0.8, 1.0),
                gravity_modifier=0.0
            )
        )

        print(f"[EffectsController] Вспышка активации в {position}")

    def play_match_explosion(self, position: Tuple[float, float, float],
                              fruit_type_id: int) -> None:
        """
        Воспроизводит взрыв частиц при совпадении.

        Цвет и форма частиц зависят от типа фрукта.

        Args:
            position: Позиция взрыва
            fruit_type_id: ID типа фрукта (для цвета)
        """
        particle_config = FRUIT_PARTICLE_CONFIGS.get(
            fruit_type_id,
            ParticleConfig(count=30, color=(1, 1, 1, 1))
        )

        particle_config.count = self.config.get("match_particle_count", 30)
        particle_config.lifetime = self.config.get("match_particle_lifetime", 1.5)

        effect = ActiveEffect(
            EffectType.MATCH_EXPLOSION, position,
            duration=particle_config.lifetime
        )
        self._active_effects.append(effect)

        self._spawn_particles(position, particle_config)

        self._spawn_shards(position, fruit_type_id)

        print(f"[EffectsController] Взрыв совпадения (фрукт {fruit_type_id}) в {position}")

    def play_land_dust(self, position: Tuple[float, float, float]) -> None:
        """
        Воспроизводит пылевое облако при приземлении.

        Args:
            position: Позиция приземления
        """
        effect = ActiveEffect(
            EffectType.LAND_DUST, position,
            duration=0.8
        )
        self._active_effects.append(effect)

        self._spawn_particles(
            position=position,
            config=ParticleConfig(
                count=12, lifetime=0.8, speed=1.0,
                size=0.04, color=(0.8, 0.8, 0.7, 0.6),
                gravity_modifier=0.1, shape="ring"
            )
        )

    def play_chain_flash(self, chain_count: int) -> None:
        """
        Воспроизводит вспышку экрана при цепной реакции.

        Интенсивность зависит от длины цепочки.

        Args:
            chain_count: Номер в цепочке
        """
        base_alpha = self.config.get("chain_screen_flash_alpha", 0.15)
        intensity = min(base_alpha * chain_count, 0.6)

        if chain_count <= 2:
            self._screen_flash_color = (1.0, 1.0, 0.3)
        elif chain_count <= 4:
            self._screen_flash_color = (1.0, 0.5, 0.0)
        else:
            self._screen_flash_color = (1.0, 0.2, 0.8)

        self._screen_flash_alpha = intensity
        self._screen_flash_decay = 3.0

        print(f"[EffectsController] Вспышка цепочки x{chain_count}")

    def play_victory_fireworks(self) -> None:
        """Воспроизводит фейерверки победы."""
        positions = [
            (-1.0, 2.0, 0.0),
            (0.0, 2.5, 0.5),
            (1.0, 2.0, -0.3),
            (-0.5, 3.0, 0.2),
            (0.5, 2.8, -0.2),
        ]

        colors = [
            (1.0, 0.3, 0.3, 1.0),
            (0.3, 1.0, 0.3, 1.0),
            (0.3, 0.3, 1.0, 1.0),
            (1.0, 1.0, 0.3, 1.0),
            (1.0, 0.5, 0.0, 1.0),
        ]

        for i, (pos, color) in enumerate(zip(positions, colors)):
            effect = ActiveEffect(
                EffectType.VICTORY_FIREWORKS, pos,
                duration=3.0 + i * 0.5
            )
            self._active_effects.append(effect)

            self._spawn_particles(
                position=pos,
                config=ParticleConfig(
                    count=50, lifetime=2.0, speed=5.0,
                    size=0.04, color=color,
                    gravity_modifier=0.8, shape="sphere"
                )
            )

        print("[EffectsController] Фейерверки победы!")

    def play_fail_effect(self) -> None:
        """Воспроизводит эффект проигрыша (красный overlay)."""
        fail_alpha = self.config.get("fail_screen_red_alpha", 0.4)
        self._screen_flash_color = (0.8, 0.1, 0.1)
        self._screen_flash_alpha = fail_alpha
        self._screen_flash_decay = 0.5

        print("[EffectsController] Эффект проигрыша")

    def play_hover_glow(self, position: Tuple[float, float, float],
                         color: Tuple[float, float, float, float]) -> ActiveEffect:
        """
        Создаёт свечение при наведении на блок.

        Args:
            position: Позиция блока
            color: Цвет свечения

        Returns:
            Активный эффект (для возможности отмены)
        """
        effect = ActiveEffect(
            EffectType.HOVER_GLOW, position,
            duration=float('inf')
        )
        self._active_effects.append(effect)
        return effect

    def stop_hover_glow(self, effect: ActiveEffect) -> None:
        """
        Останавливает свечение наведения.

        Args:
            effect: Эффект для остановки
        """
        effect.is_finished = True

    def _spawn_particles(self, position: Tuple[float, float, float],
                          config: ParticleConfig) -> None:
        """
        Создаёт систему частиц в указанной позиции.

        В Varwin это создаёт или активирует ParticleSystem.

        Args:
            position: Мировая позиция
            config: Конфигурация частиц
        """
        pass

    def _spawn_shards(self, position: Tuple[float, float, float],
                       fruit_type_id: int) -> None:
        """
        Создаёт осколки блока при разрушении.

        Args:
            position: Позиция разрушения
            fruit_type_id: ID фрукта (для цвета осколков)
        """
        pass

    def _cleanup_effect(self, effect: ActiveEffect) -> None:
        """
        Очищает ресурсы завершённого эффекта.

        Args:
            effect: Завершённый эффект
        """
        if effect.scene_object:
            try:
                if hasattr(effect.scene_object, 'destroy'):
                    effect.scene_object.destroy()
                elif hasattr(effect.scene_object, 'set_active'):
                    effect.scene_object.set_active(False)
            except Exception:
                pass

    def get_screen_flash_state(self) -> Dict[str, Any]:
        """Возвращает состояние вспышки экрана."""
        return {
            "alpha": self._screen_flash_alpha,
            "color": self._screen_flash_color
        }

    def get_active_effect_count(self) -> int:
        """Возвращает количество активных эффектов."""
        return len(self._active_effects)

    def clear_all_effects(self) -> None:
        """Очищает все активные эффекты."""
        for effect in self._active_effects:
            self._cleanup_effect(effect)
        self._active_effects.clear()
        self._screen_flash_alpha = 0.0
