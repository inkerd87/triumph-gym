"""Каталог тренажёров зала и связанные группы мышц."""

# id мышц совпадают с data-muscle в SVG-схеме тела
MUSCLE_LABELS = {
    "chest": "Грудные",
    "back": "Спина",
    "shoulders": "Плечи",
    "arms": "Руки",
    "abs": "Пресс",
    "glutes": "Ягодицы",
    "quads": "Квадрицепс",
    "hamstrings": "Бицепс бедра",
    "calves": "Икры",
}

EQUIPMENT_ZONES = {
    "all": "Все",
    "upper": "Верх",
    "lower": "Низ",
    "core": "Кор",
    "cardio": "Кардио",
}

GYM_EQUIPMENT = [
    {
        "id": "bench-press",
        "name": "Жим лёжа",
        "hint": "Горизонтальная скамья",
        "muscles": ["chest", "shoulders", "arms"],
        "icon": "bench",
        "zone": "upper",
    },
    {
        "id": "leg-press",
        "name": "Жим ногами",
        "hint": "Платформа 45°",
        "muscles": ["quads", "glutes"],
        "icon": "legs",
        "zone": "lower",
    },
    {
        "id": "lat-pulldown",
        "name": "Тяга верхнего блока",
        "hint": "Кроссовер",
        "muscles": ["back", "arms"],
        "icon": "cable",
        "zone": "upper",
    },
    {
        "id": "smith-squat",
        "name": "Присед в Смите",
        "hint": "Машина Смита",
        "muscles": ["quads", "glutes", "abs"],
        "icon": "squat",
        "zone": "lower",
    },
    {
        "id": "leg-extension",
        "name": "Разгибание ног",
        "hint": "Сидя",
        "muscles": ["quads"],
        "icon": "legs",
        "zone": "lower",
    },
    {
        "id": "leg-curl",
        "name": "Сгибание ног",
        "hint": "Лёжа",
        "muscles": ["hamstrings"],
        "icon": "legs",
        "zone": "lower",
    },
    {
        "id": "pec-deck",
        "name": "Бабочка",
        "hint": "Сведение рук",
        "muscles": ["chest"],
        "icon": "chest",
        "zone": "upper",
    },
    {
        "id": "shoulder-press",
        "name": "Жим плеч",
        "hint": "Сидя",
        "muscles": ["shoulders", "arms"],
        "icon": "press",
        "zone": "upper",
    },
    {
        "id": "cable-row",
        "name": "Горизонтальная тяга",
        "hint": "Блок",
        "muscles": ["back", "arms"],
        "icon": "cable",
        "zone": "upper",
    },
    {
        "id": "hyperextension",
        "name": "Гиперэкстензия",
        "hint": "Разгибание спины",
        "muscles": ["back", "glutes", "hamstrings"],
        "icon": "back",
        "zone": "core",
    },
    {
        "id": "calf-raise",
        "name": "Икры стоя",
        "hint": "Станок",
        "muscles": ["calves"],
        "icon": "legs",
        "zone": "lower",
    },
    {
        "id": "treadmill",
        "name": "Беговая дорожка",
        "hint": "Кардио",
        "muscles": ["quads", "calves", "glutes"],
        "icon": "cardio",
        "zone": "cardio",
    },
]


def equipment_with_labels():
    items = []
    for eq in GYM_EQUIPMENT:
        row = dict(eq)
        row["muscle_labels"] = [MUSCLE_LABELS[m] for m in eq["muscles"]]
        items.append(row)
    return items


def equipment_zones():
    return EQUIPMENT_ZONES
