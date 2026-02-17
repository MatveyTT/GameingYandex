"""
ScoreManager — система подсчёта и хранения очков.

Управляет начислением очков, бонусами, рекордами
и статистикой игрока.
"""

from typing import Dict, Any, List


class ScoreManager:
    """
    Менеджер очков.

    Начисляет очки за совпадения, считает бонусы
    за цепные реакции и скорость, хранит рекорды.
    """

    def __init__(self, base_points: int = 100,
                 chain_multiplier: int = 2,
                 speed_bonus: int = 50,
                 speed_threshold: float = 3.0):
        """
        Args:
            base_points: Базовые очки за совпадение
            chain_multiplier: Множитель цепной реакции
            speed_bonus: Бонус за скорость
            speed_threshold: Порог скорости (секунды)
        """
        self.base_points = base_points
        self.chain_multiplier = chain_multiplier
        self.speed_bonus = speed_bonus
        self.speed_threshold = speed_threshold

        self.current_score: int = 0
        self.total_score: int = 0
        self.high_score: int = 0
        self.matches_count: int = 0
        self.max_chain: int = 0
        self.total_matches: int = 0

        self._score_history: List[Dict[str, Any]] = []

    def configure(self, config: Dict[str, Any]) -> None:
        """
        Настраивает систему очков из конфигурации.

        Args:
            config: Словарь scoring из game_config.json
        """
        self.base_points = config.get("match_points", 100)
        self.chain_multiplier = config.get("chain_multiplier_base", 2)
        self.speed_bonus = config.get("speed_bonus_points", 50)
        self.speed_threshold = config.get("speed_bonus_threshold_seconds", 3.0)

    def add_score(self, points: int, chain_count: int = 1) -> int:
        """
        Добавляет очки с учётом цепной реакции.

        Args:
            points: Базовые очки
            chain_count: Номер в цепочке (1 = первое совпадение)

        Returns:
            Итоговые начисленные очки
        """
        self.current_score += points
        self.matches_count += 1
        self.total_matches += 1

        if chain_count > self.max_chain:
            self.max_chain = chain_count

        self._score_history.append({
            "points": points,
            "chain": chain_count,
            "total": self.current_score
        })

        return points

    def calculate_match_points(self, chain_count: int = 1,
                                is_fast: bool = False) -> int:
        """
        Рассчитывает очки за совпадение.

        Args:
            chain_count: Номер в цепочке
            is_fast: Быстрое совпадение (скоростной бонус)

        Returns:
            Количество очков
        """
        points = self.base_points

        if chain_count > 1:
            points = int(points * (self.chain_multiplier ** (chain_count - 1)))

        if is_fast:
            points += self.speed_bonus

        return points

    def calculate_level_bonus(self, remaining_time: float,
                               time_multiplier: int = 10) -> int:
        """
        Рассчитывает бонус за оставшееся время.

        Args:
            remaining_time: Оставшееся время в секундах
            time_multiplier: Множитель времени

        Returns:
            Бонусные очки
        """
        if remaining_time <= 0:
            return 0
        return int(remaining_time * time_multiplier)

    def finalize_level(self) -> Dict[str, Any]:
        """
        Завершает уровень и возвращает статистику.

        Returns:
            Словарь со статистикой уровня
        """
        stats = {
            "score": self.current_score,
            "matches": self.matches_count,
            "max_chain": self.max_chain,
            "history": list(self._score_history)
        }

        self.total_score += self.current_score

        if self.current_score > self.high_score:
            self.high_score = self.current_score

        return stats

    def reset_level(self) -> None:
        """Сбрасывает очки для нового уровня."""
        self.current_score = 0
        self.matches_count = 0
        self.max_chain = 0
        self._score_history.clear()

    def reset_all(self) -> None:
        """Полный сброс системы очков."""
        self.current_score = 0
        self.total_score = 0
        self.matches_count = 0
        self.max_chain = 0
        self.total_matches = 0
        self._score_history.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает текущую статистику."""
        return {
            "current_score": self.current_score,
            "total_score": self.total_score,
            "high_score": self.high_score,
            "level_matches": self.matches_count,
            "total_matches": self.total_matches,
            "max_chain": self.max_chain
        }
