"""
OnboardingController — контроллер обучения игрока.

Управляет процессом быстрого введения в игру за первые 10 секунд.
Показывает визуальные подсказки и направляет игрока через первые действия.
"""

from typing import Tuple, Optional, Any, List
from enum import Enum, auto


class OnboardingStep(Enum):
    """Шаги обучения."""
    WELCOME_TEXT = auto()
    HIGHLIGHT_BLOCK = auto()
    SHOW_ACTION_HINT = auto()
    WAIT_FIRST_ACTION = auto()
    SHOW_MATCH_HINT = auto()
    COMPLETE = auto()


class HintElement:
    """Визуальная подсказка."""

    def __init__(self, hint_type: str, text: str = "",
                 position: Tuple[float, float, float] = (0, 0, 0),
                 target_block: Optional[Any] = None,
                 duration: float = 3.0):
        self.hint_type = hint_type
        self.text = text
        self.position = position
        self.target_block = target_block
        self.duration = duration
        self.time_alive: float = 0.0
        self.is_visible: bool = True
        self.alpha: float = 1.0
        self.pulse_time: float = 0.0
        self.scene_object: Optional[Any] = None

    def update(self, delta_time: float) -> None:
        """Обновление подсказки."""
        self.time_alive += delta_time
        self.pulse_time += delta_time

        import math
        self.alpha = 0.7 + 0.3 * math.sin(self.pulse_time * 3.0)

        if self.duration > 0 and self.time_alive >= self.duration:
            self.is_visible = False

    def show(self) -> None:
        """Показывает подсказку."""
        self.is_visible = True
        self.time_alive = 0.0

    def hide(self) -> None:
        """Скрывает подсказку."""
        self.is_visible = False


class OnboardingController:
    """
    Контроллер обучения.

    Сценарий обучения (10 секунд):
    1. (0-3 сек) Приветственный текст: «Активируй фруктовые блоки!»
    2. (3-6 сек) Один блок подсвечивается пульсирующим светом
    3. (6-10 сек) Стрелка и текст «Нажми» рядом с блоком
    4. После первого действия: «Одинаковые фрукты исчезают!»

    Обучение автоматически завершается после первого действия
    или по истечении времени.
    """

    TOTAL_DURATION = 12.0
    WELCOME_DURATION = 3.0
    HIGHLIGHT_START = 3.0
    ACTION_HINT_START = 5.0
    POST_ACTION_HINT_DURATION = 3.0

    def __init__(self):
        self.current_step: OnboardingStep = OnboardingStep.WELCOME_TEXT
        self.is_complete: bool = False
        self.is_active: bool = False

        self._time_elapsed: float = 0.0
        self._hints: List[HintElement] = []
        self._target_block: Optional[Any] = None
        self._post_action_timer: float = 0.0
        self._first_action_done: bool = False

        self._welcome_hint: Optional[HintElement] = None
        self._highlight_hint: Optional[HintElement] = None
        self._action_hint: Optional[HintElement] = None
        self._match_hint: Optional[HintElement] = None

    def start_onboarding(self, target_block: Optional[Any] = None) -> None:
        """
        Запускает обучение.

        Args:
            target_block: Рекомендуемый блок для первой активации
        """
        self.is_active = True
        self.is_complete = False
        self._time_elapsed = 0.0
        self._first_action_done = False
        self._post_action_timer = 0.0
        self._target_block = target_block
        self._hints.clear()

        self._welcome_hint = HintElement(
            hint_type="text",
            text="Активируй фруктовые блоки!",
            position=(0.0, 2.0, 1.0),
            duration=self.WELCOME_DURATION
        )
        self._hints.append(self._welcome_hint)

        self._highlight_hint = HintElement(
            hint_type="highlight",
            text="",
            target_block=target_block,
            duration=0
        )
        self._highlight_hint.is_visible = False
        self._hints.append(self._highlight_hint)

        self._action_hint = HintElement(
            hint_type="arrow_text",
            text="Нажми!",
            target_block=target_block,
            duration=0
        )
        self._action_hint.is_visible = False
        self._hints.append(self._action_hint)

        self._match_hint = HintElement(
            hint_type="text",
            text="Одинаковые фрукты исчезают!",
            position=(0.0, 2.0, 1.0),
            duration=self.POST_ACTION_HINT_DURATION
        )
        self._match_hint.is_visible = False
        self._hints.append(self._match_hint)

        self.current_step = OnboardingStep.WELCOME_TEXT

        print("[OnboardingController] Обучение запущено")

    def update(self, delta_time: float) -> None:
        """
        Обновление обучения.

        Args:
            delta_time: Время с предыдущего кадра
        """
        if not self.is_active or self.is_complete:
            return

        self._time_elapsed += delta_time

        for hint in self._hints:
            if hint.is_visible:
                hint.update(delta_time)

        if self._first_action_done:
            self._update_post_action(delta_time)
            return

        if self.current_step == OnboardingStep.WELCOME_TEXT:
            if self._time_elapsed >= self.HIGHLIGHT_START:
                self._transition_to_highlight()

        elif self.current_step == OnboardingStep.HIGHLIGHT_BLOCK:
            if self._time_elapsed >= self.ACTION_HINT_START:
                self._transition_to_action_hint()

        elif self.current_step == OnboardingStep.SHOW_ACTION_HINT:
            if self._time_elapsed >= self.TOTAL_DURATION:
                self._complete_onboarding()

    def _transition_to_highlight(self) -> None:
        """Переход к шагу подсветки блока."""
        self.current_step = OnboardingStep.HIGHLIGHT_BLOCK

        if self._welcome_hint:
            self._welcome_hint.hide()

        if self._highlight_hint:
            self._highlight_hint.show()

        print("[OnboardingController] Шаг: подсветка блока")

    def _transition_to_action_hint(self) -> None:
        """Переход к шагу подсказки действия."""
        self.current_step = OnboardingStep.SHOW_ACTION_HINT

        if self._action_hint:
            self._action_hint.show()

        print("[OnboardingController] Шаг: подсказка действия")

    def on_first_action(self) -> None:
        """Обработчик первого действия игрока."""
        if self._first_action_done:
            return

        self._first_action_done = True
        self._post_action_timer = 0.0

        if self._welcome_hint:
            self._welcome_hint.hide()
        if self._highlight_hint:
            self._highlight_hint.hide()
        if self._action_hint:
            self._action_hint.hide()

        if self._match_hint:
            self._match_hint.show()

        self.current_step = OnboardingStep.SHOW_MATCH_HINT

        print("[OnboardingController] Первое действие выполнено!")

    def _update_post_action(self, delta_time: float) -> None:
        """Обновление после первого действия."""
        self._post_action_timer += delta_time

        if self._post_action_timer >= self.POST_ACTION_HINT_DURATION:
            self._complete_onboarding()

    def _complete_onboarding(self) -> None:
        """Завершает обучение."""
        self.is_complete = True
        self.is_active = False
        self.current_step = OnboardingStep.COMPLETE

        for hint in self._hints:
            hint.hide()

        print("[OnboardingController] Обучение завершено!")

    def skip(self) -> None:
        """Пропускает обучение."""
        self._complete_onboarding()

    def get_visible_hints(self) -> List[HintElement]:
        """Возвращает видимые подсказки."""
        return [h for h in self._hints if h.is_visible]

    def get_progress(self) -> float:
        """Возвращает прогресс обучения (0.0 - 1.0)."""
        if self.is_complete:
            return 1.0
        return min(1.0, self._time_elapsed / self.TOTAL_DURATION)

    def reset(self) -> None:
        """Сбрасывает обучение."""
        self.is_active = False
        self.is_complete = False
        self._time_elapsed = 0.0
        self._first_action_done = False
        self._hints.clear()
        self._target_block = None
        self.current_step = OnboardingStep.WELCOME_TEXT
