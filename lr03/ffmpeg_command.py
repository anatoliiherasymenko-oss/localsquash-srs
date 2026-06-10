"""Модуль побудови команди FFmpeg для LocalSquash.

Реалізує перші функції проєкту, специфікованого у SRS (ПЗ 01)
та Sprint 1 (ПЗ 02): валідацію вхідного файлу (FR-01, C-03),
підказки якості CRF (FR-02), генерацію імені результату (FR-10)
та збирання аргументів команди кодування (FR-02, FR-03, FR-04, FR-05).

Рефакторинг у межах ЛР 04: усунено магічні числа (іменовані константи),
if-ланцюжок зон CRF замінено табличним пошуком, видалено мертвий код,
дубльовану перевірку діапазонів винесено у хелпер _check_range
"""

from pathlib import Path

# Обмеження C-03 з SRS: практична межа розміру файлу ~2 ГБ (RAM пристрою)
MAX_FILE_SIZE_BYTES = 2 * 1024**3

SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".wmv", ".flv"}

PRESETS = (
    "ultrafast", "superfast", "veryfast", "fast",
    "medium", "slow", "slower", "veryslow",
)

# Межі параметрів кодування (FR-02, FR-04, FR-05)
CRF_MIN, CRF_MAX = 0, 51
SCALE_MIN, SCALE_MAX = 0.1, 1.0
AUDIO_BITRATE_MIN, AUDIO_BITRATE_MAX = 32, 320

# Зони якості CRF: (верхня межа зони включно, підказка)
_CRF_ZONES = (
    (17, "lossless / archival"),
    (22, "near-lossless"),
    (26, "balanced (recommended)"),
    (35, "maximum compression"),
    (CRF_MAX, "preview only"),
)

BYTES_PER_UNIT = 1024
_SIZE_UNITS = ("B", "KB", "MB", "GB", "TB")


def _check_range(value: float, low: float, high: float, message: str) -> None:
    """Перевіряє входження значення у діапазон [low, high], інакше ValueError."""
    if not low <= value <= high:
        raise ValueError(message)


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
    _check_range(crf, CRF_MIN, CRF_MAX, f"CRF має бути в діапазоні {CRF_MIN}–{CRF_MAX}")
    for upper_bound, label in _CRF_ZONES[:-1]:
        if crf <= upper_bound:
            return label
    return _CRF_ZONES[-1][1]


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
    _check_range(
        scale, SCALE_MIN, SCALE_MAX,
        f"Масштаб має бути в діапазоні {SCALE_MIN}–{SCALE_MAX}",
    )
    _check_range(
        audio_bitrate_kbps, AUDIO_BITRATE_MIN, AUDIO_BITRATE_MAX,
        f"Бітрейт аудіо: {AUDIO_BITRATE_MIN}–{AUDIO_BITRATE_MAX} kbps",
    )
    crf_quality_label(crf)  # валідація діапазону CRF

    args = ["-i", input_name, "-c:v", "libx264", "-crf", str(crf), "-preset", preset]
    if scale < SCALE_MAX:
        args += ["-vf", f"scale=trunc(iw*{scale}/2)*2:trunc(ih*{scale}/2)*2"]
    args += ["-c:a", "aac", "-b:a", f"{audio_bitrate_kbps}k"]
    args.append(output_filename(input_name))
    return args


def _format_with_unit(value: float, unit: str) -> str:
    """Форматує значення з одиницею: байти — цілим числом, решта — з одним знаком."""
    if unit == _SIZE_UNITS[0]:
        return f"{int(value)} {unit}"
    return f"{value:.1f} {unit}"


def format_file_size(size_bytes: int) -> str:
    """Форматує розмір у байтах у людиночитний рядок (двійкові одиниці).

    Реалізує допоміжну логіку DownloadService з UML-моделі (ЛР 02).
    """
    if not isinstance(size_bytes, int) or isinstance(size_bytes, bool):
        raise TypeError("Розмір має бути цілим числом байтів")
    if size_bytes < 0:
        raise ValueError("Розмір не може бути від'ємним")

    value = float(size_bytes)
    for unit in _SIZE_UNITS[:-1]:
        if value < BYTES_PER_UNIT:
            return _format_with_unit(value, unit)
        value /= BYTES_PER_UNIT
    return _format_with_unit(value, _SIZE_UNITS[-1])
