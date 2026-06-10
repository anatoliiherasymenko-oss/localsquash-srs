# ЛР 02 — Моделювання системи LocalSquash засобами UML

**Студент:** Герасименко Анатолій Вячеславович, група ПЗПІ 25-2 (індивідуальне виконання)
**Проєкт:** LocalSquash — браузерний сервіс локального стиснення та конвертації медіафайлів (ПЗ 01–02)
**Інструмент:** PlantUML (code-as-diagram); джерела діаграм — у цьому документі та в цій теці поруч із зображеннями

---

## 1. Функціональні вимоги

Сім вимог відібрано з SRS, розробленого на ПЗ 01 (ідентифікатори збережено для наскрізної трасовності).

| ID | Функціональна вимога | Пріоритет |
|---|---|---|
| FR-01 | Система має дозволяти відкрити локальний медіафайл через drag&drop або діалог вибору без передачі його на сервер | Високий |
| FR-02 | Система має виконувати стиснення відео у H.264/MP4 з налаштовуваним CRF у діапазоні 0–51 | Високий |
| FR-03 | Система має надавати вибір швидкісного пресета кодування (ultrafast–veryslow) | Високий |
| FR-07 | Система має стискати зображення з вибором формату (WebP/JPEG/PNG) та якості 1–100 | Високий |
| FR-08 | Система має стискати аудіо з вибором кодека (AAC/MP3/Opus) та бітрейту 32–320 kbps | Високий |
| FR-09 | Система має конвертувати вхідні відеоформати (MOV/MKV/WebM та ін.) у сумісний MP4 | Високий |
| FR-10 | Система має відображати прогрес кодування та автоматично завантажувати результат | Середній |

Кожна вимога однозначна (одна дія системи), перевірювана (критерії перевірки визначені в матриці відстежуваності SRS) і трасована (див. розділ 5).

## 2. Діаграма прецедентів (Use Case Diagram)

Актори: **Користувач** (анонімний — система працює без реєстрації), **Адміністратор** (публікація матеріалів блогу), **Платіжний сервіс Buy Me a Coffee** (зовнішня система, що обробляє донати). Дев'ять прецедентів у межах системи; зв'язки include (валідація файлу обов'язкова для всіх сценаріїв стиснення) та extend (обрізання/кадрування — необов'язкове розширення стиснення відео).

![Діаграма прецедентів](usecase.png)

<details><summary>Джерело PlantUML</summary>

```plantuml
@startuml
left to right direction
skinparam shadowing false
skinparam actorStyle stickman

actor "Користувач" as User
actor "Адміністратор" as Admin
actor "Платіжний сервіс\n(Buy Me a Coffee)" as Pay <<external system>>

rectangle "LocalSquash — браузерний компресор медіафайлів" {
  usecase "UC-01\nСтиснути відео\n(CRF, пресет)" as UC01
  usecase "UC-02\nСтиснути зображення" as UC02
  usecase "UC-03\nСтиснути аудіо" as UC03
  usecase "UC-04\nКонвертувати відео у MP4" as UC04
  usecase "UC-05\nВідкрити та валідувати\nлокальний файл" as UC05
  usecase "UC-06\nЗавантажити результат" as UC06
  usecase "UC-07\nОбрізати / кадрувати відео" as UC07
  usecase "UC-08\nЗробити донат" as UC08
  usecase "UC-09\nОпублікувати матеріал блогу" as UC09
}

User --> UC01
User --> UC02
User --> UC03
User --> UC04
User --> UC08
Admin --> UC09
UC08 --> Pay

UC01 ..> UC05 : <<include>>
UC02 ..> UC05 : <<include>>
UC03 ..> UC05 : <<include>>
UC04 ..> UC05 : <<include>>
UC01 ..> UC06 : <<include>>
UC07 ..> UC01 : <<extend>>
@enduml
```
</details>

## 3. Діаграма класів (Class Diagram)

Дев'ять елементів моделі: абстрактний `MediaFile` з трьома нащадками (наслідування), `CompressionJob` як центральний клас сценарію — **композиція** з `CompressionSettings` (налаштування не існують поза задачею), **агрегація** `MediaFile` (файл існує незалежно від задачі), асоціація з `FFmpegEngine` з кратностями, залежність від `DownloadService`, перелік `JobStatus`.

![Діаграма класів](class.png)

<details><summary>Джерело PlantUML</summary>

```plantuml
@startuml
skinparam shadowing false
skinparam classAttributeIconSize 0

abstract class MediaFile {
  # name : String
  # sizeBytes : long
  # mimeType : String
  + validate() : ValidationResult
  + getExtension() : String
}

class VideoFile {
  - durationSec : float
  - width : int
  - height : int
  + getResolution() : String
}

class ImageFile {
  - width : int
  - height : int
  + hasExif() : boolean
}

class AudioFile {
  - durationSec : float
  - sourceCodec : String
}

class CompressionSettings {
  - crf : int = 26
  - preset : String = "medium"
  - scale : float = 1.0
  - audioBitrateKbps : int = 128
  + toFFmpegArgs(input : MediaFile) : List<String>
  + validate() : boolean
}

class CompressionJob {
  - jobId : String
  - status : JobStatus
  - progress : float
  + start() : void
  + cancel() : void
  + onProgress(handler : Callback) : void
}

class FFmpegEngine {
  - loaded : boolean
  + load() : Promise<void>
  + run(args : List<String>) : Blob
  + onProgress(cb : Callback) : void
}

class DownloadService {
  + createObjectUrl(data : Blob) : String
  + triggerDownload(url : String, filename : String) : void
}

enum JobStatus {
  READY
  ENCODING
  DONE
  FAILED
}

MediaFile <|-- VideoFile
MediaFile <|-- ImageFile
MediaFile <|-- AudioFile

CompressionJob "1" *-- "1" CompressionSettings : налаштування >
CompressionJob "0..*" o-- "1" MediaFile : вхідний файл >
FFmpegEngine "1" -- "0..*" CompressionJob : виконує <
CompressionJob ..> DownloadService : використовує
CompressionJob -> JobStatus
@enduml
```
</details>

## 4. Діаграма послідовності (Sequence Diagram)

SD-01 — ключовий сценарій **«Стиснути відео» (UC-01, вимоги FR-01, FR-02, FR-10)**. Містить лінії життя, смуги активації, синхронні та зворотні повідомлення, комбіновані фрагменти: `alt` (валідний/невалідний файл), `opt` (ледаче завантаження WASM-модуля), `loop` (progress-події кодування).

![Діаграма послідовності](sequence.png)

<details><summary>Джерело PlantUML</summary>

```plantuml
@startuml
skinparam shadowing false
actor "Користувач" as U
participant ":CompressorPage" as UI
participant ":VideoFile" as VF
participant ":CompressionJob" as Job
participant ":FFmpegEngine" as Eng
participant ":DownloadService" as DL

U -> UI : dropFile(file)
activate UI
UI -> VF : validate()
activate VF
VF --> UI : result : ValidationResult
deactivate VF

alt файл невалідний (формат / розмір > 2 ГБ)
  UI --> U : повідомлення про помилку
else файл валідний
  UI --> U : метадані файлу та налаштування
  U -> UI : setCrf(26), setPreset("slow")
  U -> UI : натиснути "Compress"
  UI -> Job : start()
  activate Job

  opt WASM-модуль ще не завантажений
    Job -> Eng : load()
    activate Eng
    Eng --> Job : ready
    deactivate Eng
  end

  Job -> Eng : run(settings.toFFmpegArgs(file))
  activate Eng

  loop кожна progress-подія кодування
    Eng --> Job : progress(p)
    Job --> UI : updateProgress(p)
    UI --> U : прогрес-бар (p%)
  end

  Eng --> Job : output : Blob
  deactivate Eng

  Job -> DL : createObjectUrl(output)
  activate DL
  DL --> Job : url
  Job -> DL : triggerDownload(url, "video_compressed.mp4")
  DL --> U : файл збережено на пристрій
  deactivate DL
  Job --> UI : status = DONE
  deactivate Job
end
deactivate UI
@enduml
```
</details>

## 5. Матриця трасовності

| Вимога | Use Case | Класи | Sequence |
|---|---|---|---|
| FR-01 | UC-05 | MediaFile, VideoFile, ImageFile, AudioFile | SD-01 (фрагмент валідації) |
| FR-02 | UC-01 | CompressionJob, CompressionSettings, FFmpegEngine, VideoFile | SD-01 |
| FR-03 | UC-01 | CompressionSettings | SD-01 (параметри run) |
| FR-07 | UC-02 | ImageFile, CompressionJob, CompressionSettings | — |
| FR-08 | UC-03 | AudioFile, CompressionJob, CompressionSettings | — |
| FR-09 | UC-04 | FFmpegEngine, CompressionSettings | — |
| FR-10 | UC-01, UC-06 | CompressionJob, FFmpegEngine, DownloadService | SD-01 (loop прогресу та завантаження) |

Прогалин у покритті немає: кожна вимога відображена щонайменше одним прецедентом і одним класом; ключовий сценарій FR-02 деталізовано діаграмою послідовності SD-01.
