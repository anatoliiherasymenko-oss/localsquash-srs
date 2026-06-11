/**
 * Модуль побудови команди FFmpeg для LocalSquash (порт із Python, ЛР 03–04).
 *
 * Логіка, константи та межі діапазонів ідентичні відрефакторенetій версії
 * lr03/ffmpeg_command.py (після ЛР 04): іменовані константи замість магічних
 * чисел, табличний пошук зон CRF, хелпер checkRange без дублювання.
 */

// Обмеження C-03 з SRS: практична межа розміру файлу ~2 ГБ (RAM пристрою)
const MAX_FILE_SIZE_BYTES = 2 * 1024 ** 3;

const SUPPORTED_EXTENSIONS = [".mp4", ".mov", ".mkv", ".webm", ".avi", ".wmv", ".flv"];

const PRESETS = [
  "ultrafast", "superfast", "veryfast", "fast",
  "medium", "slow", "slower", "veryslow",
];

// Межі параметрів кодування (FR-02, FR-04, FR-05)
const CRF_MIN = 0;
const CRF_MAX = 51;
const SCALE_MIN = 0.1;
const SCALE_MAX = 1.0;
const AUDIO_BITRATE_MIN = 32;
const AUDIO_BITRATE_MAX = 320;

// Зони якості CRF: [верхня межа зони включно, підказка]
const CRF_ZONES = [
  [17, "lossless / archival"],
  [22, "near-lossless"],
  [26, "balanced (recommended)"],
  [35, "maximum compression"],
  [CRF_MAX, "preview only"],
];

const BYTES_PER_UNIT = 1024;
const SIZE_UNITS = ["B", "KB", "MB", "GB", "TB"];

/** Перевіряє входження значення у діапазон [low, high], інакше кидає RangeError. */
function checkRange(value, low, high, message) {
  if (!(value >= low && value <= high)) {
    throw new RangeError(message);
  }
}

/** Витягує розширення файлу в нижньому регістрі (аналог Path().suffix). */
function fileExtension(filename) {
  const base = filename.split("/").pop();
  const dot = base.lastIndexOf(".");
  return dot > 0 ? base.slice(dot).toLowerCase() : "";
}

/**
 * Перевіряє вхідний файл за розширенням та розміром (FR-01, C-03).
 * Повертає { valid, message }.
 */
function validateInputFile(filename, sizeBytes) {
  const ext = fileExtension(filename);
  if (!SUPPORTED_EXTENSIONS.includes(ext)) {
    return { valid: false, message: `Непідтримуваний формат: ${ext || "(без розширення)"}` };
  }
  if (sizeBytes <= 0) {
    return { valid: false, message: "Файл порожній або розмір невідомий" };
  }
  if (sizeBytes > MAX_FILE_SIZE_BYTES) {
    return { valid: false, message: "Файл перевищує практичний ліміт 2 ГБ (обмеження пам'яті)" };
  }
  return { valid: true, message: "OK" };
}

/** Повертає текстову підказку зони якості для значення CRF (FR-02). */
function crfQualityLabel(crf) {
  checkRange(crf, CRF_MIN, CRF_MAX, `CRF має бути в діапазоні ${CRF_MIN}–${CRF_MAX}`);
  for (const [upperBound, label] of CRF_ZONES.slice(0, -1)) {
    if (crf <= upperBound) {
      return label;
    }
  }
  return CRF_ZONES[CRF_ZONES.length - 1][1];
}

/** Генерує ім'я результату з суфіксом _compressed та контейнером .mp4 (FR-10). */
function outputFilename(inputName) {
  const base = inputName.split("/").pop();
  const dot = base.lastIndexOf(".");
  const stem = dot > 0 ? base.slice(0, dot) : base;
  return `${stem}_compressed.mp4`;
}

/**
 * Збирає список аргументів FFmpeg для стиснення відео.
 * Покриває FR-02 (CRF), FR-03 (пресет), FR-04 (масштаб), FR-05 (бітрейт аудіо).
 * Вихід — завжди H.264 + AAC у MP4 (C-04).
 */
function buildFfmpegArgs(
  inputName,
  { crf = 26, preset = "medium", scale = 1.0, audioBitrateKbps = 128 } = {},
) {
  if (!PRESETS.includes(preset)) {
    throw new RangeError(`Невідомий пресет: ${preset}`);
  }
  checkRange(scale, SCALE_MIN, SCALE_MAX,
    `Масштаб має бути в діапазоні ${SCALE_MIN}–${SCALE_MAX}`);
  checkRange(audioBitrateKbps, AUDIO_BITRATE_MIN, AUDIO_BITRATE_MAX,
    `Бітрейт аудіо: ${AUDIO_BITRATE_MIN}–${AUDIO_BITRATE_MAX} kbps`);
  crfQualityLabel(crf); // валідація діапазону CRF

  const args = ["-i", inputName, "-c:v", "libx264", "-crf", String(crf), "-preset", preset];
  if (scale < SCALE_MAX) {
    args.push("-vf", `scale=trunc(iw*${scale}/2)*2:trunc(ih*${scale}/2)*2`);
  }
  args.push("-c:a", "aac", "-b:a", `${audioBitrateKbps}k`);
  args.push(outputFilename(inputName));
  return args;
}

/** Форматує значення з одиницею: байти — цілим числом, решта — з одним знаком. */
function formatWithUnit(value, unit) {
  if (unit === SIZE_UNITS[0]) {
    return `${Math.trunc(value)} ${unit}`;
  }
  return `${value.toFixed(1)} ${unit}`;
}

/**
 * Форматує розмір у байтах у людиночитний рядок (двійкові одиниці).
 * Реалізує допоміжну логіку DownloadService з UML-моделі (ЛР 02).
 */
function formatFileSize(sizeBytes) {
  if (!Number.isInteger(sizeBytes) || typeof sizeBytes === "boolean") {
    throw new TypeError("Розмір має бути цілим числом байтів");
  }
  if (sizeBytes < 0) {
    throw new RangeError("Розмір не може бути від'ємним");
  }

  let value = sizeBytes;
  for (const unit of SIZE_UNITS.slice(0, -1)) {
    if (value < BYTES_PER_UNIT) {
      return formatWithUnit(value, unit);
    }
    value /= BYTES_PER_UNIT;
  }
  return formatWithUnit(value, SIZE_UNITS[SIZE_UNITS.length - 1]);
}

module.exports = {
  MAX_FILE_SIZE_BYTES,
  SUPPORTED_EXTENSIONS,
  PRESETS,
  CRF_MIN, CRF_MAX,
  SCALE_MIN, SCALE_MAX,
  AUDIO_BITRATE_MIN, AUDIO_BITRATE_MAX,
  CRF_ZONES,
  validateInputFile,
  crfQualityLabel,
  outputFilename,
  buildFfmpegArgs,
  formatFileSize,
};
