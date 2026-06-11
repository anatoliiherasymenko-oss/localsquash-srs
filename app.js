/**
 * REST API-обгортка модуля ffmpegCommand для LocalSquash.
 * Самостійна робота з ОПІ, варіант 2: Render, Node.js + Express.
 *
 * Endpoints:
 *   GET  /health          — health check для платформи розгортання
 *   GET  /api/parameters  — список допустимих параметрів (вимога варіанту 2)
 *   POST /api/build-args  — основна бізнес-логіка: збирання команди FFmpeg
 *   POST /api/validate    — валідація вхідного файлу за іменем та розміром
 */

const express = require("express");
const m = require("./ffmpegCommand");

const app = express();
app.use(express.json());

// GET /health — індикатор працездатності для Render
app.get("/health", (req, res) => {
  res.json({ status: "ok" });
});

// GET /api/parameters — допустимі параметри API (додаткова вимога варіанту 2)
app.get("/api/parameters", (req, res) => {
  res.json({
    presets: m.PRESETS,
    crf: { min: m.CRF_MIN, max: m.CRF_MAX, default: 26 },
    scale: { min: m.SCALE_MIN, max: m.SCALE_MAX, default: 1.0 },
    audioBitrateKbps: { min: m.AUDIO_BITRATE_MIN, max: m.AUDIO_BITRATE_MAX, default: 128 },
    supportedExtensions: m.SUPPORTED_EXTENSIONS,
    maxFileSizeBytes: m.MAX_FILE_SIZE_BYTES,
    crfZones: m.CRF_ZONES.map(([upTo, label]) => ({ upTo, label })),
  });
});

// POST /api/build-args — основний endpoint бізнес-логіки
// Тіло: { "inputName": "clip.mov", "crf": 26, "preset": "slow",
//         "scale": 0.5, "audioBitrateKbps": 96 }
app.post("/api/build-args", (req, res) => {
  const { inputName, crf, preset, scale, audioBitrateKbps } = req.body || {};
  if (!inputName || typeof inputName !== "string") {
    return res.status(400).json({ error: "Поле inputName є обов'язковим рядком" });
  }
  try {
    const options = {};
    if (crf !== undefined) options.crf = crf;
    if (preset !== undefined) options.preset = preset;
    if (scale !== undefined) options.scale = scale;
    if (audioBitrateKbps !== undefined) options.audioBitrateKbps = audioBitrateKbps;

    const args = m.buildFfmpegArgs(inputName, options);
    return res.json({
      args,
      command: `ffmpeg ${args.join(" ")}`,
      outputFilename: m.outputFilename(inputName),
      qualityLabel: m.crfQualityLabel(options.crf ?? 26),
    });
  } catch (err) {
    return res.status(400).json({ error: err.message });
  }
});

// POST /api/validate — валідація вхідного файлу
// Тіло: { "filename": "clip.mp4", "sizeBytes": 1048576 }
app.post("/api/validate", (req, res) => {
  const { filename, sizeBytes } = req.body || {};
  if (!filename || typeof filename !== "string" || !Number.isInteger(sizeBytes)) {
    return res.status(400).json({
      error: "Потрібні поля: filename (рядок) та sizeBytes (ціле число)",
    });
  }
  const result = m.validateInputFile(filename, sizeBytes);
  return res.json({
    ...result,
    humanSize: sizeBytes >= 0 ? m.formatFileSize(sizeBytes) : null,
  });
});

module.exports = app;
