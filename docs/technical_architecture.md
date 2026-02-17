# Техническая архитектура: Фруктовые Блоки VR

## Обзор

Проект построен на модульной архитектуре с чётким разделением ответственности.
Каждый модуль (скрипт) отвечает за одну область игровой логики и взаимодействует
с другими через определённые интерфейсы.

---

## Диаграмма компонентов

```
┌─────────────────────────────────────────────────────────────┐
│                    VarwinIntegration                         │
│                  (Точка входа, Varwin API)                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                     GameManager                              │
│              (Состояния, координация)                        │
├─────────┬─────────┬─────────┬──────────┬────────────────────┤
│         │         │         │          │                    │
▼         ▼         ▼         ▼          ▼                    ▼
┌───────┐ ┌───────┐ ┌──────┐ ┌────────┐ ┌──────────┐ ┌──────────────┐
│Board  │ │Match  │ │Score │ │Physics │ │Level     │ │Onboarding    │
│Manager│ │Detect.│ │Mgr   │ │Control.│ │Generator │ │Controller    │
└───┬───┘ └───────┘ └──────┘ └────────┘ └──────────┘ └──────────────┘
    │
    ▼
┌──────────┐
│FruitBlock│ (множество экземпляров)
└──────────┘

┌────────────────────────────────────────────┐
│          Подсистемы обратной связи          │
├────────────────┬───────────────────────────┤
│ UIController   │ AudioController           │
│ EffectsControl.│                           │
└────────────────┴───────────────────────────┘
```

---

## Описание модулей

### VarwinIntegration (`varwin_integration.py`)
- **Роль**: Точка входа, мост между Varwin XRMS и игровой логикой
- **Ответственность**: Инициализация подсистем, обработка событий Varwin,
  синхронизация объектов сцены
- **Зависимости**: Все модули

### GameManager (`game_manager.py`)
- **Роль**: Главный контроллер состояний
- **Ответственность**: Управление состояниями (GameState), координация
  игрового цикла, обработка событий блоков
- **Паттерн**: State Machine + Mediator
- **Состояния**: LOADING → ONBOARDING → PLAYING ⇄ CHECKING_MATCHES ⇄
  CHAIN_REACTION → LEVEL_COMPLETE | GAME_OVER

### FruitBlock (`fruit_block.py`)
- **Роль**: Игровой объект — фруктовый блок
- **Ответственность**: Состояние блока, анимации, взаимодействие
- **Паттерн**: State Machine (BlockState)
- **Состояния**: IDLE → HOVERED → ACTIVATED → FALLING → LANDED →
  MATCHED → DESTROYING → DESTROYED

### BoardManager (`board_manager.py`)
- **Роль**: Управление игровым полем
- **Ответственность**: 3D-сетка блоков, зона сбора, размещение/удаление
- **Данные**: grid (Dict[Tuple, FruitBlock]), collection_zone (List[FruitBlock])

### MatchDetector (`match_detector.py`)
- **Роль**: Поиск совпадений
- **Ответственность**: Нахождение пар одинаковых блоков рядом
- **Алгоритм**: Группировка по типу → попарная проверка расстояний →
  жадный выбор ближайших пар

### PhysicsController (`physics_controller.py`)
- **Роль**: Управление физикой
- **Ответственность**: Параметры Rigidbody, границы зоны сбора,
  определение «приземления» блоков

### ScoreManager (`score_manager.py`)
- **Роль**: Система очков
- **Ответственность**: Начисление, бонусы, статистика, рекорды

### UIController (`ui_controller.py`)
- **Роль**: Пользовательский интерфейс
- **Ответственность**: HUD, панели, всплывающие очки

### AudioController (`audio_controller.py`)
- **Роль**: Звуковое сопровождение
- **Ответственность**: SFX, музыка, пространственный звук

### EffectsController (`effects_controller.py`)
- **Роль**: Визуальные эффекты
- **Ответственность**: Частицы, вспышки, фейерверки

### OnboardingController (`onboarding_controller.py`)
- **Роль**: Обучение игрока
- **Ответственность**: 10-секундный онбординг, подсказки

### LevelGenerator (`level_generator.py`)
- **Роль**: Генерация уровней
- **Ответственность**: Создание сбалансированных расположений блоков

---

## Поток данных

### Активация блока
```
Игрок кликает/нажимает триггер
    │
    ▼
VarwinIntegration.on_block_click(block_id)
    │
    ▼
FruitBlock.on_pointer_click()
    │
    ▼
FruitBlock.activate()
    │  └── callback → VarwinIntegration._on_block_activated()
    │
    ▼
GameManager.on_block_activated(block)
    ├── BoardManager.release_block(block)
    ├── PhysicsController.enable_block_physics(block)
    ├── AudioController.play_activate()
    ├── EffectsController.play_activation_flash()
    └── UIController.update_moves()
```

### Совпадение блоков
```
Блок приземлился → GameManager.on_block_landed()
    │
    ▼
GameState → CHECKING_MATCHES
    │
    ▼
MatchDetector.find_matches(collection_zone_blocks)
    │
    ▼ [совпадения найдены]
GameManager._process_matches(matches)
    ├── ScoreManager.add_score()
    ├── AudioController.play_match(chain_count)
    ├── EffectsController.play_match_explosion()
    ├── UIController.show_points_popup()
    ├── BoardManager.remove_block(block_a)
    └── BoardManager.remove_block(block_b)
    │
    ▼
GameState → CHAIN_REACTION (ждём стабилизации)
    │
    ▼ [блоки успокоились]
GameState → CHECKING_MATCHES (проверяем ещё раз)
    │
    ▼ [нет совпадений]
GameManager._check_game_state()
    ├── board_empty? → LEVEL_COMPLETE
    ├── zone_full & no_matches? → GAME_OVER
    └── else → PLAYING
```

---

## Конфигурация

Все числовые параметры вынесены в JSON-файлы в папке `config/`:

| Файл | Содержимое |
|------|-----------|
| `game_config.json` | Параметры геймплея, физики, UI, аудио, эффектов |
| `levels.json` | Конфигурация 8 уровней |
| `fruit_types.json` | 6 типов фруктов с цветами и ассетами |

Это позволяет настраивать баланс без изменения кода.

---

## Производительность

### Оптимизации
- Блоки проверяются на совпадения только после приземления
- Группировка по типу фрукта перед попарной проверкой
- Эффекты имеют пул объектов (object pooling)
- UI обновляется только при изменении значений

### Ограничения
- Максимум ~125 блоков (5x5x5) на экране одновременно
- Максимум 22 блока в зоне сбора
- До 50 частиц на один эффект совпадения
- До 5 одновременных эффектов
