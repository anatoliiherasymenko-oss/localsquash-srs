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
