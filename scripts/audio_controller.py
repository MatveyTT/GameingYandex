"""
AudioController — контроллер звукового сопровождения.

Управляет воспроизведением звуковых эффектов и фоновой музыки.
Обеспечивает звуковую обратную связь для всех игровых действий.

Прикрепляется к AudioSource-объекту в Varwin XRMS.
"""

from typing import Dict, Any, Optional, Tuple
from enum import Enum, auto


class SoundType(Enum):
    """Типы звуковых эффектов."""
    HOVER = auto()
    ACTIVATE = auto()
    LAND = auto()
    MATCH = auto()
    CHAIN = auto()
    FAIL = auto()
    WIN = auto()
    LEVEL_START = auto()
    BUTTON_CLICK = auto()
    TIMER_WARNING = auto()
    COMBO_1 = auto()
    COMBO_2 = auto()
    COMBO_3 = auto()


class SoundEntry:
    """Описание звукового ресурса."""

    def __init__(self, name: str, file_path: str, volume: float = 1.0,
                 pitch: float = 1.0, spatial_blend: float = 0.0,
                 loop: bool = False):
        """
        Args:
            name: Имя звука
            file_path: Путь к аудиофайлу
            volume: Громкость (0.0 - 1.0)
            pitch: Высота тона (0.5 - 2.0)
            spatial_blend: 3D-звук (0.0 = 2D, 1.0 = полный 3D)
            loop: Зацикливание
        """
        self.name = name
        self.file_path = file_path
        self.volume = volume
        self.pitch = pitch
        self.spatial_blend = spatial_blend
        self.loop = loop
        self.audio_source: Optional[Any] = None


class AudioController:
    """
    Контроллер звукового сопровождения.

    Управляет:
    - Фоновая музыка (с плавными переходами)
    - Звуки взаимодействия (наведение, активация, падение)
    - Звуки совпадений (с нарастанием для цепочек)
    - Звуки UI (кнопки, уведомления)
    - Звуки состояний (победа, поражение, начало уровня)
    """

    CHAIN_PITCH_STEP = 0.15
    MAX_CHAIN_PITCH = 2.0
    MUSIC_CROSSFADE_DURATION = 1.0
    TIMER_WARNING_THRESHOLD = 10.0

    def __init__(self):
        self.master_volume: float = 1.0
        self.music_volume: float = 0.3
        self.sfx_volume: float = 0.7

        self.is_music_playing: bool = False
        self.is_muted: bool = False

        self._sounds: Dict[SoundType, SoundEntry] = {}
        self._music_entry: Optional[SoundEntry] = None
        self._tension_music_entry: Optional[SoundEntry] = None
        self._current_music_volume: float = 0.3
        self._target_music_volume: float = 0.3

        self._setup_default_sounds()

    def _setup_default_sounds(self) -> None:
        """Настраивает звуки по умолчанию."""
        default_sounds = {
            SoundType.HOVER: SoundEntry(
                "hover", "assets/sounds/hover.wav",
                volume=0.2, pitch=1.2, spatial_blend=0.5
            ),
            SoundType.ACTIVATE: SoundEntry(
                "activate", "assets/sounds/activate.wav",
                volume=0.6, pitch=1.0, spatial_blend=0.8
            ),
            SoundType.LAND: SoundEntry(
                "land", "assets/sounds/land.wav",
                volume=0.5, pitch=0.9, spatial_blend=1.0
            ),
            SoundType.MATCH: SoundEntry(
                "match", "assets/sounds/match.wav",
                volume=0.8, pitch=1.0, spatial_blend=0.7
            ),
            SoundType.CHAIN: SoundEntry(
                "chain", "assets/sounds/chain.wav",
                volume=0.9, pitch=1.0, spatial_blend=0.5
            ),
            SoundType.FAIL: SoundEntry(
                "fail", "assets/sounds/fail.wav",
                volume=0.9, pitch=1.0, spatial_blend=0.0
            ),
            SoundType.WIN: SoundEntry(
                "win", "assets/sounds/win.wav",
                volume=1.0, pitch=1.0, spatial_blend=0.0
            ),
            SoundType.LEVEL_START: SoundEntry(
                "level_start", "assets/sounds/level_start.wav",
                volume=0.7, pitch=1.0, spatial_blend=0.0
            ),
            SoundType.BUTTON_CLICK: SoundEntry(
                "button_click", "assets/sounds/button_click.wav",
                volume=0.5, pitch=1.1, spatial_blend=0.0
            ),
            SoundType.TIMER_WARNING: SoundEntry(
                "timer_warning", "assets/sounds/timer_warning.wav",
                volume=0.6, pitch=1.0, spatial_blend=0.0
            ),
        }

        self._sounds = default_sounds

        self._music_entry = SoundEntry(
            "background_music", "assets/sounds/music_main.ogg",
            volume=0.3, pitch=1.0, loop=True
        )
        self._tension_music_entry = SoundEntry(
            "tension_music", "assets/sounds/music_tension.ogg",
            volume=0.3, pitch=1.0, loop=True
        )

    def configure(self, config: Dict[str, Any]) -> None:
        """
        Настраивает параметры звука из конфигурации.

        Args:
            config: Словарь audio из game_config.json
        """
        self.music_volume = config.get("music_volume", 0.3)
        self.sfx_volume = config.get("sfx_volume", 0.7)
        self._current_music_volume = self.music_volume
        self._target_music_volume = self.music_volume

        volume_map = {
            SoundType.HOVER: config.get("hover_volume", 0.2),
            SoundType.ACTIVATE: config.get("activate_volume", 0.6),
            SoundType.MATCH: config.get("match_volume", 0.8),
            SoundType.FAIL: config.get("fail_volume", 0.9),
            SoundType.WIN: config.get("win_volume", 1.0),
        }

        for sound_type, volume in volume_map.items():
            if sound_type in self._sounds:
                self._sounds[sound_type].volume = volume

    def play_sound(self, sound_type: SoundType,
                   position: Optional[Tuple[float, float, float]] = None,
                   pitch_override: Optional[float] = None) -> None:
        """
        Воспроизводит звуковой эффект.

        Args:
            sound_type: Тип звука
            position: 3D-позиция для пространственного звука
            pitch_override: Переопределение высоты тона
        """
        if self.is_muted:
            return

        sound = self._sounds.get(sound_type)
        if sound is None:
            return

        effective_volume = sound.volume * self.sfx_volume * self.master_volume
        effective_pitch = pitch_override if pitch_override else sound.pitch

        self._play_audio(sound, effective_volume, effective_pitch, position)

    def play_hover(self) -> None:
        """Воспроизводит звук наведения на блок."""
        self.play_sound(SoundType.HOVER)

    def play_activate(self) -> None:
        """Воспроизводит звук активации блока."""
        self.play_sound(SoundType.ACTIVATE)

    def play_land(self) -> None:
        """Воспроизводит звук приземления блока."""
        self.play_sound(SoundType.LAND)

    def play_match(self, chain_count: int = 1) -> None:
        """
        Воспроизводит звук совпадения.

        Высота тона повышается с каждым звеном цепочки.

        Args:
            chain_count: Номер в цепочке (1+)
        """
        pitch = 1.0 + (chain_count - 1) * self.CHAIN_PITCH_STEP
        pitch = min(pitch, self.MAX_CHAIN_PITCH)

        if chain_count > 1:
            self.play_sound(SoundType.CHAIN, pitch_override=pitch)
        else:
            self.play_sound(SoundType.MATCH, pitch_override=pitch)

    def play_fail(self) -> None:
        """Воспроизводит звук проигрыша."""
        self.play_sound(SoundType.FAIL)

    def play_win(self) -> None:
        """Воспроизводит звук победы."""
        self.play_sound(SoundType.WIN)

    def play_level_start(self) -> None:
        """Воспроизводит звук начала уровня."""
        self.play_sound(SoundType.LEVEL_START)

    def play_button(self) -> None:
        """Воспроизводит звук нажатия кнопки."""
        self.play_sound(SoundType.BUTTON_CLICK)

    def play_timer_warning(self) -> None:
        """Воспроизводит звук предупреждения таймера."""
        self.play_sound(SoundType.TIMER_WARNING)

    def play_music(self) -> None:
        """Запускает фоновую музыку."""
        if self.is_muted or self._music_entry is None:
            return

        self.is_music_playing = True
        self._target_music_volume = self.music_volume

        self._play_music_internal(self._music_entry)
        print("[AudioController] Фоновая музыка запущена")

    def pause_music(self) -> None:
        """Приостанавливает фоновую музыку."""
        self._target_music_volume = 0.0
        print("[AudioController] Музыка приостановлена")

    def resume_music(self) -> None:
        """Возобновляет фоновую музыку."""
        self._target_music_volume = self.music_volume
        print("[AudioController] Музыка возобновлена")

    def stop_music(self) -> None:
        """Останавливает фоновую музыку."""
        self.is_music_playing = False
        self._target_music_volume = 0.0
        print("[AudioController] Музыка остановлена")

    def set_tension_mode(self, enabled: bool) -> None:
        """
        Переключает режим напряжения (при приближении к проигрышу).

        Args:
            enabled: Включить/выключить
        """
        if enabled:
            self._play_music_internal(self._tension_music_entry)
        else:
            self._play_music_internal(self._music_entry)

    def update(self, delta_time: float) -> None:
        """
        Обновление аудио-системы (crossfade и т.д.).

        Args:
            delta_time: Время с предыдущего кадра
        """
        if abs(self._current_music_volume - self._target_music_volume) > 0.01:
            fade_speed = 1.0 / max(self.MUSIC_CROSSFADE_DURATION, 0.01)
            if self._current_music_volume < self._target_music_volume:
                self._current_music_volume = min(
                    self._target_music_volume,
                    self._current_music_volume + fade_speed * delta_time
                )
            else:
                self._current_music_volume = max(
                    self._target_music_volume,
                    self._current_music_volume - fade_speed * delta_time
                )

    def set_master_volume(self, volume: float) -> None:
        """Устанавливает общую громкость (0.0 - 1.0)."""
        self.master_volume = max(0.0, min(1.0, volume))

    def set_music_volume(self, volume: float) -> None:
        """Устанавливает громкость музыки (0.0 - 1.0)."""
        self.music_volume = max(0.0, min(1.0, volume))
        self._target_music_volume = self.music_volume

    def set_sfx_volume(self, volume: float) -> None:
        """Устанавливает громкость эффектов (0.0 - 1.0)."""
        self.sfx_volume = max(0.0, min(1.0, volume))

    def toggle_mute(self) -> bool:
        """Переключает отключение звука."""
        self.is_muted = not self.is_muted
        if self.is_muted:
            self._target_music_volume = 0.0
        else:
            self._target_music_volume = self.music_volume
        return self.is_muted

    def _play_audio(self, sound: SoundEntry, volume: float, pitch: float,
                    position: Optional[Tuple[float, float, float]] = None) -> None:
        """
        Внутренний метод воспроизведения через Varwin API.

        Args:
            sound: Звуковой ресурс
            volume: Громкость
            pitch: Высота тона
            position: 3D-позиция (для пространственного звука)
        """
        if sound.audio_source is not None:
            try:
                src = sound.audio_source
                if hasattr(src, 'volume'):
                    src.volume = volume
                if hasattr(src, 'pitch'):
                    src.pitch = pitch
                if position and hasattr(src, 'transform'):
                    src.transform.position = position
                if hasattr(src, 'play'):
                    src.play()
            except Exception as e:
                print(f"[AudioController] Ошибка воспроизведения '{sound.name}': {e}")
        else:
            print(f"[AudioController] Звук: '{sound.name}' "
                  f"(vol={volume:.2f}, pitch={pitch:.2f})")

    def _play_music_internal(self, music: Optional[SoundEntry]) -> None:
        """Внутренний метод запуска музыки."""
        if music and music.audio_source:
            try:
                src = music.audio_source
                if hasattr(src, 'loop'):
                    src.loop = True
                if hasattr(src, 'volume'):
                    src.volume = self._current_music_volume * self.master_volume
                if hasattr(src, 'play'):
                    src.play()
            except Exception as e:
                print(f"[AudioController] Ошибка музыки: {e}")
