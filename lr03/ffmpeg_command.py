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
