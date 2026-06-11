/**
 * Тести JS-порту модуля та REST API (Jest + Supertest).
 * Кейси дзеркалять ключові TC з ЛР 03 (EP/BVA), щоб довести
 * еквівалентність порту, плюс інтеграційні тести endpoints.
 */

const request = require("supertest");
const app = require("../app");
const m = require("../ffmpegCommand");

describe("validateInputFile (EP/BVA, дзеркало TC-01..07)", () => {
  test("допустиме розширення — valid", () => {
    expect(m.validateInputFile("clip.mov", 300 * 1024 ** 2)).toEqual({ valid: true, message: "OK" });
  });
  test("недопустиме розширення — invalid", () => {
    expect(m.validateInputFile("notes.txt", 1024).valid).toBe(false);
  });
  test("BVA: розмір 0 — invalid; 1 — valid", () => {
    expect(m.validateInputFile("clip.mp4", 0).valid).toBe(false);
    expect(m.validateInputFile("clip.mp4", 1).valid).toBe(true);
  });
  test("BVA: MAX — valid; MAX+1 — invalid", () => {
    expect(m.validateInputFile("clip.mp4", m.MAX_FILE_SIZE_BYTES).valid).toBe(true);
    expect(m.validateInputFile("clip.mp4", m.MAX_FILE_SIZE_BYTES + 1).valid).toBe(false);
  });
});

describe("crfQualityLabel (BVA меж зон, дзеркало TC-08..10)", () => {
  test.each([
    [0, "lossless / archival"], [17, "lossless / archival"],
    [18, "near-lossless"], [22, "near-lossless"],
    [23, "balanced (recommended)"], [26, "balanced (recommended)"],
    [27, "maximum compression"], [35, "maximum compression"],
    [36, "preview only"], [51, "preview only"],
  ])("CRF %i → %s", (crf, label) => {
    expect(m.crfQualityLabel(crf)).toBe(label);
  });
  test("за межами діапазону — RangeError", () => {
    expect(() => m.crfQualityLabel(-1)).toThrow(RangeError);
    expect(() => m.crfQualityLabel(52)).toThrow(RangeError);
  });
});

describe("buildFfmpegArgs (дзеркало TC-12..16)", () => {
  test("повний набір валідних параметрів", () => {
    const args = m.buildFfmpegArgs("in.mov", { crf: 26, preset: "slow", scale: 0.5, audioBitrateKbps: 96 });
    expect(args.slice(0, 2)).toEqual(["-i", "in.mov"]);
    expect(args[args.indexOf("-crf") + 1]).toBe("26");
    expect(args.some((a) => a.startsWith("scale="))).toBe(true);
    expect(args[args.length - 1]).toBe("in_compressed.mp4");
  });
  test("BVA: scale=1.0 — без фільтра -vf", () => {
    expect(m.buildFfmpegArgs("in.mp4", { scale: 1.0 })).not.toContain("-vf");
  });
  test("невідомий пресет / межі бітрейту — RangeError", () => {
    expect(() => m.buildFfmpegArgs("in.mp4", { preset: "turbo" })).toThrow(RangeError);
    expect(() => m.buildFfmpegArgs("in.mp4", { audioBitrateKbps: 31 })).toThrow(RangeError);
    expect(() => m.buildFfmpegArgs("in.mp4", { audioBitrateKbps: 321 })).toThrow(RangeError);
    expect(m.buildFfmpegArgs("in.mp4", { audioBitrateKbps: 32 })).toContain("32k");
    expect(m.buildFfmpegArgs("in.mp4", { audioBitrateKbps: 320 })).toContain("320k");
  });
});

describe("formatFileSize (дзеркало TC-17..20)", () => {
  test.each([
    [0, "0 B"], [1023, "1023 B"], [1024, "1.0 KB"],
    [1536, "1.5 KB"], [1048576, "1.0 MB"],
    [2 * 1024 ** 3, "2.0 GB"], [3 * 1024 ** 4, "3.0 TB"],
  ])("%i → %s", (n, s) => {
    expect(m.formatFileSize(n)).toBe(s);
  });
  test("від'ємне / нецілий тип — помилка", () => {
    expect(() => m.formatFileSize(-1)).toThrow(RangeError);
    expect(() => m.formatFileSize("100")).toThrow(TypeError);
    expect(() => m.formatFileSize(1.5)).toThrow(TypeError);
  });
});

describe("REST API (supertest)", () => {
  test("GET /health → 200 {status:'ok'}", async () => {
    const res = await request(app).get("/health");
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: "ok" });
  });

  test("GET /api/parameters → перелік допустимих параметрів", async () => {
    const res = await request(app).get("/api/parameters");
    expect(res.status).toBe(200);
    expect(res.body.presets).toEqual(m.PRESETS);
    expect(res.body.crf).toEqual({ min: 0, max: 51, default: 26 });
    expect(res.body.supportedExtensions).toContain(".mp4");
  });

  test("POST /api/build-args — успіх", async () => {
    const res = await request(app)
      .post("/api/build-args")
      .send({ inputName: "vacation.mov", crf: 23, preset: "slow", scale: 0.5 });
    expect(res.status).toBe(200);
    expect(res.body.outputFilename).toBe("vacation_compressed.mp4");
    expect(res.body.command).toMatch(/^ffmpeg -i vacation\.mov/);
    expect(res.body.qualityLabel).toBe("balanced (recommended)");
  });

  test("POST /api/build-args — 400 на невалідних параметрах", async () => {
    const noName = await request(app).post("/api/build-args").send({ crf: 26 });
    expect(noName.status).toBe(400);
    const badCrf = await request(app).post("/api/build-args").send({ inputName: "a.mp4", crf: 99 });
    expect(badCrf.status).toBe(400);
    expect(badCrf.body.error).toMatch(/CRF/);
  });

  test("POST /api/validate — обидві гілки", async () => {
    const ok = await request(app).post("/api/validate").send({ filename: "clip.mp4", sizeBytes: 1048576 });
    expect(ok.status).toBe(200);
    expect(ok.body.valid).toBe(true);
    expect(ok.body.humanSize).toBe("1.0 MB");

    const bad = await request(app).post("/api/validate").send({ filename: "notes.txt", sizeBytes: 10 });
    expect(bad.body.valid).toBe(false);
  });
});
