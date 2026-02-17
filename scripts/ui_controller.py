"""
UIController — контроллер пользовательского интерфейса.

Управляет всеми UI-элементами игры: счёт, уровень, таймер,
экраны победы/поражения, всплывающие подсказки, паузу.

Прикрепляется к UI-объекту Canvas в Varwin XRMS.
"""

from typing import Tuple, Dict, Any, Optional


class UIElement:
    """Базовый UI-элемент."""

    def __init__(self, name: str, position: Tuple[float, float] = (0.0, 0.0),
                 is_visible: bool = True):
        self.name = name
        self.position = position
        self.is_visible = is_visible
        self.scene_object: Optional[Any] = None
        self.alpha: float = 1.0

    def show(self) -> None:
        """Показывает элемент."""
        self.is_visible = True
        self.alpha = 1.0
        self._update_visibility()

    def hide(self) -> None:
        """Скрывает элемент."""
        self.is_visible = False
        self.alpha = 0.0
        self._update_visibility()

    def _update_visibility(self) -> None:
        """Обновляет видимость в сцене."""
        if self.scene_object and hasattr(self.scene_object, 'set_active'):
            self.scene_object.set_active(self.is_visible)


class TextElement(UIElement):
    """Текстовый UI-элемент."""

    def __init__(self, name: str, text: str = "",
                 font_size: int = 24, color: Tuple[float, float, float, float] = (1, 1, 1, 1),
                 **kwargs):
        super().__init__(name, **kwargs)
        self.text = text
        self.font_size = font_size
        self.color = color

    def set_text(self, text: str) -> None:
        """Устанавливает текст."""
        self.text = text
        if self.scene_object and hasattr(self.scene_object, 'text'):
            self.scene_object.text = text

    def set_color(self, color: Tuple[float, float, float, float]) -> None:
        """Устанавливает цвет текста."""
        self.color = color


class PanelElement(UIElement):
    """Панель UI."""

    def __init__(self, name: str,
                 size: Tuple[float, float] = (1.0, 1.0),
                 background_color: Tuple[float, float, float, float] = (0, 0, 0, 0.7),
                 **kwargs):
        super().__init__(name, **kwargs)
        self.size = size
        self.background_color = background_color
        self.children: list = []

    def add_child(self, element: UIElement) -> None:
        """Добавляет дочерний элемент."""
        self.children.append(element)


class PointsPopup:
    """Всплывающий текст с очками."""

    FLOAT_SPEED = 0.5
    FADE_DURATION = 1.5
    SCALE_ANIMATION_DURATION = 0.3

    def __init__(self, points: int,
                 world_position: Tuple[float, float, float],
                 color: Tuple[float, float, float, float] = (1, 1, 0.3, 1)):
        self.points = points
        self.position = world_position
        self.color = color
        self.alpha = 1.0
        self.scale = 0.0
        self.time_alive = 0.0
        self.is_finished = False
        self.text = f"+{points}"

    def update(self, delta_time: float) -> None:
        """Обновление анимации всплывающего текста."""
        self.time_alive += delta_time

        self.position = (
            self.position[0],
            self.position[1] + self.FLOAT_SPEED * delta_time,
            self.position[2]
        )

        if self.time_alive < self.SCALE_ANIMATION_DURATION:
            progress = self.time_alive / self.SCALE_ANIMATION_DURATION
            self.scale = self._ease_out_back(progress)
        else:
            self.scale = 1.0

        fade_start = self.FADE_DURATION * 0.6
        if self.time_alive > fade_start:
            fade_progress = (self.time_alive - fade_start) / (self.FADE_DURATION - fade_start)
            self.alpha = max(0.0, 1.0 - fade_progress)

        if self.time_alive >= self.FADE_DURATION:
            self.is_finished = True

    @staticmethod
    def _ease_out_back(t: float) -> float:
        """Easing-функция с небольшим перелётом."""
        c1 = 1.70158
        c3 = c1 + 1.0
        return 1.0 + c3 * pow(t - 1.0, 3) + c1 * pow(t - 1.0, 2)


class UIController:
    """
    Контроллер пользовательского интерфейса.

    Управляет:
    - HUD (счёт, уровень, таймер, ходы)
    - Экран начала уровня
    - Экран завершения уровня
    - Экран проигрыша
    - Экран паузы
    - Всплывающие очки
    - Информационные подсказки
    """

    def __init__(self):
        self.score_text = TextElement("score_text", "Очки: 0", font_size=32)
        self.level_text = TextElement("level_text", "Уровень: 1", font_size=24)
        self.timer_text = TextElement("timer_text", "", font_size=28)
        self.moves_text = TextElement("moves_text", "Ходы: 0", font_size=20)

        self.level_start_panel = PanelElement("level_start_panel",
                                               size=(0.8, 0.4),
                                               background_color=(0.1, 0.1, 0.2, 0.9))
        self.level_start_title = TextElement("level_start_title", "", font_size=48)
        self.level_start_subtitle = TextElement("level_start_subtitle", "", font_size=24)
        self.level_start_panel.add_child(self.level_start_title)
        self.level_start_panel.add_child(self.level_start_subtitle)
        self.level_start_panel.hide()

        self.level_complete_panel = PanelElement("level_complete_panel",
                                                  size=(0.9, 0.6),
                                                  background_color=(0.05, 0.2, 0.05, 0.92))
        self.complete_title = TextElement("complete_title", "Уровень пройден!", font_size=48,
                                          color=(0.3, 1.0, 0.3, 1.0))
        self.complete_score = TextElement("complete_score", "", font_size=32)
        self.complete_stats = TextElement("complete_stats", "", font_size=22)
        self.complete_next_btn = TextElement("complete_next_btn", "[ Следующий уровень ]",
                                             font_size=28, color=(1, 1, 0.3, 1))
        self.level_complete_panel.add_child(self.complete_title)
        self.level_complete_panel.add_child(self.complete_score)
        self.level_complete_panel.add_child(self.complete_stats)
        self.level_complete_panel.add_child(self.complete_next_btn)
        self.level_complete_panel.hide()

        self.game_over_panel = PanelElement("game_over_panel",
                                             size=(0.9, 0.5),
                                             background_color=(0.3, 0.05, 0.05, 0.92))
        self.game_over_title = TextElement("game_over_title", "Игра окончена",
                                            font_size=48, color=(1, 0.3, 0.3, 1))
        self.game_over_reason = TextElement("game_over_reason", "", font_size=24)
        self.game_over_score = TextElement("game_over_score", "", font_size=28)
        self.game_over_retry = TextElement("game_over_retry", "[ Начать заново ]",
                                            font_size=28, color=(1, 1, 0.3, 1))
        self.game_over_panel.add_child(self.game_over_title)
        self.game_over_panel.add_child(self.game_over_reason)
        self.game_over_panel.add_child(self.game_over_score)
        self.game_over_panel.add_child(self.game_over_retry)
        self.game_over_panel.hide()

        self.pause_panel = PanelElement("pause_panel",
                                         size=(0.6, 0.5),
                                         background_color=(0.1, 0.1, 0.1, 0.85))
        self.pause_title = TextElement("pause_title", "Пауза", font_size=42)
        self.pause_resume = TextElement("pause_resume", "[ Продолжить ]",
                                         font_size=28, color=(0.3, 1, 0.3, 1))
        self.pause_restart = TextElement("pause_restart", "[ Начать заново ]",
                                          font_size=28, color=(1, 1, 0.3, 1))
        self.pause_panel.add_child(self.pause_title)
        self.pause_panel.add_child(self.pause_resume)
        self.pause_panel.add_child(self.pause_restart)
        self.pause_panel.hide()

        self.game_won_panel = PanelElement("game_won_panel",
                                            size=(1.0, 0.7),
                                            background_color=(0.1, 0.05, 0.2, 0.95))
        self.game_won_title = TextElement("game_won_title", "Победа!",
                                           font_size=64, color=(1, 0.85, 0.2, 1))
        self.game_won_score = TextElement("game_won_score", "", font_size=36)
        self.game_won_panel.add_child(self.game_won_title)
        self.game_won_panel.add_child(self.game_won_score)
        self.game_won_panel.hide()

        self._popups: list = []
        self._level_start_timer: float = 0.0
        self._level_start_duration: float = 2.5

    def update(self, delta_time: float) -> None:
        """
        Обновление UI-элементов.

        Args:
            delta_time: Время с предыдущего кадра
        """
        finished_popups = []
        for popup in self._popups:
            popup.update(delta_time)
            if popup.is_finished:
                finished_popups.append(popup)

        for popup in finished_popups:
            self._popups.remove(popup)

        if self.level_start_panel.is_visible:
            self._level_start_timer += delta_time
            if self._level_start_timer >= self._level_start_duration:
                self.level_start_panel.hide()

    def update_score(self, score: int) -> None:
        """Обновляет отображение счёта."""
        self.score_text.set_text(f"Очки: {score}")

    def update_level(self, level: int) -> None:
        """Обновляет отображение уровня."""
        self.level_text.set_text(f"Уровень: {level}")

    def update_timer(self, remaining_seconds: float) -> None:
        """Обновляет отображение таймера."""
        minutes = int(remaining_seconds) // 60
        seconds = int(remaining_seconds) % 60
        self.timer_text.set_text(f"{minutes:02d}:{seconds:02d}")

        if remaining_seconds <= 10:
            self.timer_text.set_color((1, 0.3, 0.3, 1))
        elif remaining_seconds <= 30:
            self.timer_text.set_color((1, 1, 0.3, 1))
        else:
            self.timer_text.set_color((1, 1, 1, 1))

    def update_moves(self, moves: int) -> None:
        """Обновляет отображение количества ходов."""
        self.moves_text.set_text(f"Ходы: {moves}")

    def show_level_start(self, level: int, name: str) -> None:
        """
        Показывает экран начала уровня.

        Args:
            level: Номер уровня
            name: Название уровня
        """
        self.level_start_title.set_text(f"Уровень {level}")
        self.level_start_subtitle.set_text(name)
        self.level_start_panel.show()
        self._level_start_timer = 0.0

        self._hide_all_panels_except(self.level_start_panel)

        print(f"[UIController] Показан экран начала уровня {level}: {name}")

    def show_level_complete(self, level: int, score: int, time_bonus: int,
                             moves: int, time_elapsed: float) -> None:
        """
        Показывает экран завершения уровня.

        Args:
            level: Номер уровня
            score: Набранные очки
            time_bonus: Бонус за время
            moves: Количество ходов
            time_elapsed: Время прохождения
        """
        self.complete_title.set_text(f"Уровень {level} пройден!")
        self.complete_score.set_text(f"Очки: {score}")

        minutes = int(time_elapsed) // 60
        seconds = int(time_elapsed) % 60
        stats = (f"Время: {minutes:02d}:{seconds:02d}\n"
                 f"Ходы: {moves}\n"
                 f"Бонус за время: +{time_bonus}")
        self.complete_stats.set_text(stats)

        self._hide_all_panels()
        self.level_complete_panel.show()

        print(f"[UIController] Уровень {level} завершён, очки: {score}")

    def show_game_over(self, reason: str, score: int, moves: int) -> None:
        """
        Показывает экран проигрыша.

        Args:
            reason: Причина проигрыша
            score: Набранные очки
            moves: Количество ходов
        """
        self.game_over_reason.set_text(reason)
        self.game_over_score.set_text(f"Очки: {score} | Ходы: {moves}")

        self._hide_all_panels()
        self.game_over_panel.show()

        print(f"[UIController] Проигрыш: {reason}")

    def show_game_won(self, total_score: int) -> None:
        """
        Показывает экран полной победы.

        Args:
            total_score: Общий счёт
        """
        self.game_won_score.set_text(f"Итоговый счёт: {total_score}")

        self._hide_all_panels()
        self.game_won_panel.show()

        print(f"[UIController] Полная победа! Счёт: {total_score}")

    def show_pause_menu(self) -> None:
        """Показывает меню паузы."""
        self.pause_panel.show()

    def hide_pause_menu(self) -> None:
        """Скрывает меню паузы."""
        self.pause_panel.hide()

    def show_points_popup(self, points: int,
                           world_position: Tuple[float, float, float]) -> None:
        """
        Показывает всплывающий текст с очками.

        Args:
            points: Количество очков
            world_position: Мировая позиция для отображения
        """
        color = (1.0, 1.0, 0.3, 1.0)
        if points >= 400:
            color = (1.0, 0.5, 0.0, 1.0)
        elif points >= 200:
            color = (0.3, 1.0, 0.3, 1.0)

        popup = PointsPopup(points, world_position, color)
        self._popups.append(popup)

    def show_hint(self, text: str, duration: float = 3.0) -> None:
        """
        Показывает подсказку.

        Args:
            text: Текст подсказки
            duration: Длительность показа в секундах
        """
        print(f"[UIController] Подсказка: {text} ({duration}с)")

    def _hide_all_panels(self) -> None:
        """Скрывает все панели."""
        self.level_start_panel.hide()
        self.level_complete_panel.hide()
        self.game_over_panel.hide()
        self.pause_panel.hide()
        self.game_won_panel.hide()

    def _hide_all_panels_except(self, except_panel: PanelElement) -> None:
        """Скрывает все панели кроме указанной."""
        panels = [
            self.level_start_panel, self.level_complete_panel,
            self.game_over_panel, self.pause_panel, self.game_won_panel
        ]
        for panel in panels:
            if panel is not except_panel:
                panel.hide()

    def get_active_popups(self) -> list:
        """Возвращает список активных всплывающих текстов."""
        return self._popups

    def reset(self) -> None:
        """Сбрасывает UI к начальному состоянию."""
        self._hide_all_panels()
        self._popups.clear()
        self.update_score(0)
        self.update_level(1)
        self.update_moves(0)
        self.timer_text.set_text("")
