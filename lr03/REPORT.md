# ЛР 03 — Модульне тестування програмного коду (Unit Testing)

**Студент:** Герасименко Анатолій Вячеславович, група ПЗПІ 25-2 (індивідуальне виконання)
**Проєкт:** LocalSquash — браузерний сервіс локального стиснення медіафайлів (ПЗ 01–02, ЛР 01–02)

## 1. Тема та мета

**Тема:** модульне тестування програмного модуля проєкту LocalSquash із застосуванням формальних технік проєктування тестів.

**Мета:** набуття практичних навичок написання модульних тестів із використанням pytest; оволодіння техніками еквівалентного розбиття (EP) та аналізу граничних значень (BVA); інтерпретація метрик покриття коду та досягнення line coverage ≥ 80 %.

## 2. Вихідний код реалізованого модуля

Модуль `ffmpeg_command.py` реалізує логіку, спроєктовану в UML-моделі ЛР 02: `validate_input_file` відповідає методу `MediaFile.validate()`, `build_ffmpeg_args` — `CompressionSettings.toFFmpegArgs()`, `crf_quality_label` — підказкам якості з UC-01, `output_filename` та `format_file_size` — допоміжній логіці `DownloadService`. П'ять функцій містять умовні конструкції, цикл (`format_file_size`) та обробку виняткових ситуацій (`ValueError`, `TypeError`).

```python
"""Модуль побудови команди FFmpeg для LocalSquash.

Реалізує перші функції проєкту, специфікованого у SRS (ПЗ 01)
та Sprint 1 (ПЗ 02): валідацію вхідного файлу (FR-01, C-03),
підказки якості CRF (FR-02), генерацію імені результату (FR-10)
та збирання аргументів команди кодування (FR-02, FR-03, FR-04, FR-05).
"""

from pathlib import Path

# Обмеження C-03 з SRS: практична межа розміру файлу ~2 ГБ (RAM пристрою)
MAX_FILE_SIZE_BYTES = 2 * 1024**3

SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".wmv", ".flv"}

PRESETS = (
    "ultrafast", "superfast", "veryfast", "fast",
    "medium", "slow", "slower", "veryslow",
)


def validate_input_file(filename: str, size_bytes: int) -> tuple[bool, str]:
    """Перевіряє вхідний файл за розширенням та розміром (FR-01, C-03).

    Повертає кортеж (валідний, повідомлення).
    """
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return False, f"Непідтримуваний формат: {ext or '(без розширення)'}"
    if size_bytes <= 0:
        return False, "Файл порожній або розмір невідомий"
    if size_bytes > MAX_FILE_SIZE_BYTES:
        return False, "Файл перевищує практичний ліміт 2 ГБ (обмеження пам'яті)"
    return True, "OK"


def crf_quality_label(crf: int) -> str:
    """Повертає текстову підказку зони якості для значення CRF (FR-02)."""
    if not 0 <= crf <= 51:
        raise ValueError("CRF має бути в діапазоні 0–51")
    if crf <= 17:
        return "lossless / archival"
    if crf <= 22:
        return "near-lossless"
    if crf <= 26:
        return "balanced (recommended)"
    if crf <= 35:
        return "maximum compression"
    return "preview only"


def output_filename(input_name: str) -> str:
    """Генерує ім'я результату з суфіксом _compressed та контейнером .mp4 (FR-10)."""
    return f"{Path(input_name).stem}_compressed.mp4"


def build_ffmpeg_args(
    input_name: str,
    crf: int = 26,
    preset: str = "medium",
    scale: float = 1.0,
    audio_bitrate_kbps: int = 128,
) -> list[str]:
    """Збирає список аргументів FFmpeg для стиснення відео.

    Покриває FR-02 (CRF), FR-03 (пресет), FR-04 (масштаб),
    FR-05 (бітрейт аудіо). Вихід — завжди H.264 + AAC у MP4 (C-04).
    """
    if preset not in PRESETS:
        raise ValueError(f"Невідомий пресет: {preset}")
    if not 0.1 <= scale <= 1.0:
        raise ValueError("Масштаб має бути в діапазоні 0.1–1.0")
    if not 32 <= audio_bitrate_kbps <= 320:
        raise ValueError("Бітрейт аудіо має бути в діапазоні 32–320 kbps")
    crf_quality_label(crf)  # валідація діапазону CRF

    args = ["-i", input_name, "-c:v", "libx264", "-crf", str(crf), "-preset", preset]
    if scale < 1.0:
        args += ["-vf", f"scale=trunc(iw*{scale}/2)*2:trunc(ih*{scale}/2)*2"]
    args += ["-c:a", "aac", "-b:a", f"{audio_bitrate_kbps}k", output_filename(input_name)]
    return args


def format_file_size(size_bytes: int) -> str:
    """Форматує розмір у байтах у людиночитний рядок (двійкові одиниці).

    Реалізує допоміжну логіку DownloadService з UML-моделі (ЛР 02):
    відображення розміру результату користувачу. Містить цикл
    послідовного ділення на 1024 та обробку виняткових ситуацій.
    """
    if not isinstance(size_bytes, int) or isinstance(size_bytes, bool):
        raise TypeError("Розмір має бути цілим числом байтів")
    if size_bytes < 0:
        raise ValueError("Розмір не може бути від'ємним")

    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size_bytes)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    raise AssertionError("unreachable")
```

## 3. Таблиця проєктування тестів

20 тест-кейсів (з урахуванням параметризації — 40 виконуваних тестів). Кожен метод покритий класами еквівалентності та граничними значеннями на обох межах кожного діапазону.

| Тест-кейс | Вхідні дані | Очікуваний результат | Техніка | Статус |
|---|---|---|---|---|
| TC-01 | `clip.mov`, 300 МБ | (True, "OK") | EP (допустимий клас), позитивний | pass |
| TC-02 | `notes.txt`, 1 КБ | (False, "Непідтримуваний формат…") | EP (недопустимий клас), негативний | pass |
| TC-03 | `videofile` (без розширення) | (False, …) | EP (недопустимий клас), негативний | pass |
| TC-04 | `clip.mp4`, розмір 0 | (False, "порожній…") | BVA (нижня межа), негативний | pass |
| TC-05 | `clip.mp4`, розмір 1 Б | (True, "OK") | BVA (межа+1), позитивний | pass |
| TC-06 | `clip.mp4`, розмір = 2 ГБ (MAX) | (True, "OK") | BVA (верхня межа), позитивний | pass |
| TC-07 | `clip.mp4`, MAX+1 | (False, "…2 ГБ…") | BVA (межа+1), негативний | pass |
| TC-08 | CRF ∈ {0,17,18,22,23,26,27,35,36,51} | відповідна зона якості (10 підкейсів) | BVA (межі всіх зон) | pass |
| TC-09 | CRF = −1 | ValueError | BVA (межа−1), негативний | pass |
| TC-10 | CRF = 52 | ValueError | BVA (межа+1), негативний | pass |
| TC-11 | `vacation.mov` | `vacation_compressed.mp4` | EP, позитивний | pass |
| TC-12 | повний набір валідних параметрів | коректний список аргументів FFmpeg | EP, позитивний | pass |
| TC-13 | scale = 1.0 | фільтр `-vf` відсутній | BVA (верхня межа scale) | pass |
| TC-14 | preset = "turbo" | ValueError | EP (недопустимий клас), негативний | pass |
| TC-15 | бітрейт ∈ {31, 32, 320, 321} | виняток / валідний аргумент (4 підкейси) | BVA (обидві межі ±1) | pass |
| TC-16 | scale = 0.09 | ValueError | BVA (нижня межа−крок), негативний | pass |
| TC-17 | розмір ∈ {0, 1023, 1024} | "0 B" / "1023 B" / "1.0 KB" (3 підкейси) | BVA (межа переходу одиниць) | pass |
| TC-18 | представники KB/MB/GB/TB | коректний рядок (4 підкейси) | EP (класи одиниць), позитивний | pass |
| TC-19 | розмір = −1 | ValueError | EP (недопустимий клас), негативний | pass |
| TC-20 | "100" / 1.5 / None / True | TypeError (4 підкейси) | EP (недопустимий тип), негативний | pass |

## 4. Вихідний код тестового набору

Кожен тест структурований за патерном AAA з явними коментарями фаз та зазначенням техніки.

```python
"""Модульні тести для ffmpeg_command (ЛР 03).

Кожен тест структуровано за патерном AAA (Arrange — Act — Assert)
і позначено застосованою технікою проєктування:
EP — еквівалентне розбиття, BVA — аналіз граничних значень,
позитивний / негативний сценарій.
"""

import pytest

from ffmpeg_command import (
    MAX_FILE_SIZE_BYTES,
    build_ffmpeg_args,
    crf_quality_label,
    format_file_size,
    output_filename,
    validate_input_file,
)

# ---------- validate_input_file: EP за розширенням, BVA за розміром ----------

# TC-01. EP: допустимий клас розширень, позитивний сценарій
def test_validate_supported_extension():
    # Arrange
    filename, size = "clip.mov", 300 * 1024**2
    # Act
    ok, msg = validate_input_file(filename, size)
    # Assert
    assert ok is True and msg == "OK"


# TC-02. EP: недопустимий клас розширень, негативний сценарій
def test_validate_unsupported_extension():
    # Arrange
    filename, size = "notes.txt", 1024
    # Act
    ok, msg = validate_input_file(filename, size)
    # Assert
    assert ok is False and "Непідтримуваний формат" in msg


# TC-03. EP: файл без розширення, негативний сценарій
def test_validate_no_extension():
    # Arrange
    filename, size = "videofile", 1024
    # Act
    ok, _ = validate_input_file(filename, size)
    # Assert
    assert ok is False


# TC-04. BVA: розмір = 0 (нижня межа), негативний сценарій
def test_validate_zero_size():
    # Arrange
    filename, size = "clip.mp4", 0
    # Act
    ok, msg = validate_input_file(filename, size)
    # Assert
    assert ok is False and "порожній" in msg


# TC-05. BVA: розмір = 1 байт (нижня межа + 1), позитивний сценарій
def test_validate_one_byte():
    # Arrange
    filename, size = "clip.mp4", 1
    # Act
    ok, _ = validate_input_file(filename, size)
    # Assert
    assert ok is True


# TC-06. BVA: розмір = MAX (верхня межа, включно), позитивний сценарій
def test_validate_exact_limit():
    # Arrange
    filename, size = "clip.mp4", MAX_FILE_SIZE_BYTES
    # Act
    ok, _ = validate_input_file(filename, size)
    # Assert
    assert ok is True


# TC-07. BVA: розмір = MAX + 1 (за верхньою межею), негативний сценарій
def test_validate_over_limit():
    # Arrange
    filename, size = "clip.mp4", MAX_FILE_SIZE_BYTES + 1
    # Act
    ok, msg = validate_input_file(filename, size)
    # Assert
    assert ok is False and "2 ГБ" in msg


# ---------- crf_quality_label: BVA на межах зон якості ----------

# TC-08. BVA: межі всіх п'яти класів еквівалентності CRF
@pytest.mark.parametrize(
    "crf, expected",
    [
        (0, "lossless / archival"),      # нижня межа діапазону
        (17, "lossless / archival"),     # верхня межа 1-ї зони
        (18, "near-lossless"),           # нижня межа 2-ї зони
        (22, "near-lossless"),
        (23, "balanced (recommended)"),
        (26, "balanced (recommended)"),
        (27, "maximum compression"),
        (35, "maximum compression"),
        (36, "preview only"),
        (51, "preview only"),            # верхня межа діапазону
    ],
)
def test_crf_zone_boundaries(crf, expected):
    # Arrange — значення CRF на межі зони (параметризація)
    # Act
    label = crf_quality_label(crf)
    # Assert
    assert label == expected


# TC-09. BVA: CRF = -1 (нижня межа - 1), негативний сценарій (виняток)
def test_crf_below_range():
    # Arrange
    crf = -1
    # Act / Assert
    with pytest.raises(ValueError):
        crf_quality_label(crf)


# TC-10. BVA: CRF = 52 (верхня межа + 1), негативний сценарій (виняток)
def test_crf_above_range():
    # Arrange
    crf = 52
    # Act / Assert
    with pytest.raises(ValueError):
        crf_quality_label(crf)


# ---------- output_filename: позитивний сценарій ----------

# TC-11. EP: типове ім'я з розширенням, позитивний сценарій
def test_output_filename_suffix_and_container():
    # Arrange
    name = "vacation.mov"
    # Act
    result = output_filename(name)
    # Assert
    assert result == "vacation_compressed.mp4"


# ---------- build_ffmpeg_args: EP/BVA за параметрами ----------

# TC-12. EP: усі параметри в допустимих класах, позитивний сценарій
def test_build_args_full_settings():
    # Arrange
    name, crf, preset, scale, abr = "in.mov", 26, "slow", 0.5, 96
    # Act
    args = build_ffmpeg_args(name, crf, preset, scale, abr)
    # Assert
    assert args[:2] == ["-i", "in.mov"]
    assert "-crf" in args and args[args.index("-crf") + 1] == "26"
    assert args[args.index("-preset") + 1] == "slow"
    assert any(a.startswith("scale=") for a in args)
    assert args[-1] == "in_compressed.mp4"


# TC-13. BVA: scale = 1.0 (верхня межа) — фільтр scale НЕ додається
def test_build_args_scale_one_no_filter():
    # Arrange
    scale = 1.0
    # Act
    args = build_ffmpeg_args("in.mp4", scale=scale)
    # Assert
    assert "-vf" not in args


# TC-14. EP: недопустимий пресет, негативний сценарій (виняток)
def test_build_args_invalid_preset():
    # Arrange
    preset = "turbo"
    # Act / Assert
    with pytest.raises(ValueError):
        build_ffmpeg_args("in.mp4", preset=preset)


# TC-15. BVA: бітрейт аудіо на межах 32/320 (валідні) та 31/321 (невалідні)
@pytest.mark.parametrize("abr, valid", [(31, False), (32, True), (320, True), (321, False)])
def test_build_args_audio_bitrate_boundaries(abr, valid):
    # Arrange — граничні значення бітрейту (параметризація)
    # Act / Assert
    if valid:
        args = build_ffmpeg_args("in.mp4", audio_bitrate_kbps=abr)
        assert f"{abr}k" in args
    else:
        with pytest.raises(ValueError):
            build_ffmpeg_args("in.mp4", audio_bitrate_kbps=abr)


# TC-16. BVA: scale = 0.09 (нижня межа - крок), негативний сценарій
def test_build_args_scale_below_min():
    # Arrange
    scale = 0.09
    # Act / Assert
    with pytest.raises(ValueError):
        build_ffmpeg_args("in.mp4", scale=scale)


# ---------- format_file_size: EP/BVA + цикл переходу одиниць ----------

# TC-17. BVA: межа переходу B → KB (1023 / 1024)
@pytest.mark.parametrize("n, expected", [(0, "0 B"), (1023, "1023 B"), (1024, "1.0 KB")])
def test_format_size_byte_boundary(n, expected):
    # Arrange — значення навколо межі 1024 (параметризація)
    # Act
    result = format_file_size(n)
    # Assert
    assert result == expected


# TC-18. EP: представники класів KB / MB / GB / TB, позитивний сценарій
@pytest.mark.parametrize(
    "n, expected",
    [(1536, "1.5 KB"), (1048576, "1.0 MB"), (2 * 1024**3, "2.0 GB"), (3 * 1024**4, "3.0 TB")],
)
def test_format_size_unit_classes(n, expected):
    # Arrange — представник кожного класу еквівалентності одиниць
    # Act
    result = format_file_size(n)
    # Assert
    assert result == expected


# TC-19. EP: від'ємне значення, негативний сценарій (виняток)
def test_format_size_negative():
    # Arrange
    n = -1
    # Act / Assert
    with pytest.raises(ValueError):
        format_file_size(n)


# TC-20. EP: недопустимий тип аргументу, негативний сценарій (виняток)
@pytest.mark.parametrize("bad", ["100", 1.5, None, True])
def test_format_size_wrong_type(bad):
    # Arrange — нечислові/неприпустимі типи (параметризація)
    # Act / Assert
    with pytest.raises(TypeError):
        format_file_size(bad)
```

## 5. Звіт покриття коду

Команда запуску та підсумок:

```
$ pytest --cov=ffmpeg_command --cov-report=html --cov-report=term

........................................                                 [100%]
================================ tests coverage ================================
_______________ coverage: platform linux, python 3.12.3-final-0 ________________

Name                Stmts   Miss  Cover
---------------------------------------
ffmpeg_command.py      54      1    98%
---------------------------------------
TOTAL                  54      1    98%
40 passed in 0.07s
```

**Line coverage: 98 %** (поріг 80 % перевищено). Повний HTML-звіт — у теці [`htmlcov/`](htmlcov/index.html) цього репозиторію (зелені рядки — покриті, червоні — ні).

## 6. Посилання на Git-репозиторій

https://github.com/anatoliiherasymenko-oss/localsquash-srs — код модуля, тестовий набір, HTML-звіт покриття та цей звіт розміщено в теці `lr03/`; конфігурація CI — у `.github/workflows/tests.yml`.

## 7. Висновки

Досягнуто line coverage 98 % при порозі 80 %. Єдиний непокритий рядок (104) — захисний `raise AssertionError("unreachable")` наприкінці `format_file_size`: він недосяжний за побудовою, оскільки цикл гарантовано повертає результат на останній одиниці виміру (TB). Це ілюструє принципову межу метрики line coverage: вона показує, що виконувалося, але не розрізняє свідомо мертвий захисний код і пропущену логіку — інтерпретація потребує аналізу, а не лише числа.

Виявлені проблеми та спостереження: (1) найбільше дефектоємних місць — на межах діапазонів (CRF 0/51, бітрейт 32/320, scale 0.1/1.0, перехід 1023/1024 байт), що підтверджує доцільність BVA як обов'язкової техніки; (2) у Python BVA для типів так само важлива, як для значень — кейс `format_file_size(True)` виявив, що `bool` є підтипом `int`, і без явної перевірки тип помилково проходив валідацію; цю перевірку додано в модуль за результатами тестування (ітеративний цикл п. 6 завдання).

Шляхи поліпшення: додати branch coverage як другу метрику (наразі логічні гілки покриті, але метрика не вимірювалася формально); застосувати mutation testing (mutmut) для оцінки якості самих тестів, а не лише факту виконання рядків; інтегрувати property-based тестування (hypothesis) для `format_file_size`, де інваріант (монотонність одиниць) перевірявся б на тисячах згенерованих входів.

Автоматичний запуск тестів налаштовано через GitHub Actions (бонусне завдання): при кожному push/pull request CI виконує тестовий набір із прапорцем `--cov-fail-under=80`, що блокує злиття за падіння покриття нижче порогу.
