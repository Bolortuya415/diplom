# Render-ийн Тэмдэглэл (PNG / SVG)

**Огноо:** 2026-04-30

## Render оролдлогын төлөв

PNG / SVG render хийх оролдлого **амжилтгүй болсон**. Шалтгаан:

```
$ df -h /c
C:  238G  235G  3.1G  99% /c
```

C: диск нь 99% дүүрсэн (зөвхөн 3.1 GB чөлөөтэй) учир `@mermaid-js/mermaid-cli` болон түүний хамтын `puppeteer` (~300 MB Chromium-ийн хамт) суулгахад `npm install` алдаа өгсөн:

```
npm install @mermaid-js/mermaid-cli
→ Exit code 1
→ tail: write error: No space left on device
```

`plantuml.jar` файл орчин дунд бэлэн биш бөгөөд татан авахад мөн ижил диск-зайн асуудал тулгарна.

## Гар аргаар render хийх алхам

Дараах хэдэн арга гар аргаар render хийхэд бэлэн:

### Сонголт А — VS Code extension
1. VS Code-д `bierner.markdown-mermaid` болон `jebbs.plantuml` extension суулгана.
2. `docs/diagrams/source/*.mmd` болон `*.puml` файлуудыг нээж preview-р PNG/SVG export-хийнэ.

### Сонголт Б — Online render
1. **Mermaid:** https://mermaid.live/ дээр `.mmd` агуулгыг paste → "Actions" → Download PNG/SVG.
2. **PlantUML:** https://www.plantuml.com/plantuml/uml/ дээр `.puml` агуулгыг paste → PNG/SVG татна.

### Сонголт В — Локалд CLI ажиллуулах (диск чөлөөлсний дараа)
```powershell
# Disk зайг ядаж 5 GB чөлөөлсний дараа
npm install -g @mermaid-js/mermaid-cli
mmdc -i docs/diagrams/source/01_system_architecture.mmd `
     -o docs/diagrams/rendered/01_system_architecture.png

# PlantUML татаж ажиллуулах:
curl -L -o plantuml.jar `
  https://github.com/plantuml/plantuml/releases/latest/download/plantuml.jar
java -jar plantuml.jar -tpng -o docs/diagrams/rendered `
     docs/diagrams/source/*.puml
```

### Сонголт Г — Bulk render скрипт (`scripts/render_diagrams.ps1`)
```powershell
# Та энэ скриптийг кодлож тавьсны дараа нэг удаагаар бүх диаграмыг render хийх боломжтой.
$source = "docs/diagrams/source"
$target = "docs/diagrams/rendered"

# Mermaid
Get-ChildItem -Path $source -Filter "*.mmd" | ForEach-Object {
    $out = Join-Path $target ($_.BaseName + ".png")
    mmdc -i $_.FullName -o $out -t default -b white
}

# PlantUML (plantuml.jar нь project root-д байх ёстой)
java -jar plantuml.jar -tpng -o ../../$target $source/*.puml
```

## Хүлээгдэж буй PNG нэрийн жагсаалт

`docs/diagrams/rendered/` дотор дараах 9 файл оршин гарах ёстой (диск чөлөөлсний дараа):

| Файл | Source |
|------|--------|
| 01_system_architecture.png | 01_system_architecture.mmd / .puml |
| 02_er_diagram.png | 02_er_diagram.mmd / .puml |
| 03_class_diagram.png | 03_class_diagram.mmd / .puml |
| 04_sequence_chat_flow.png | 04_sequence_chat_flow.mmd / .puml |
| 05_sequence_ingest_flow.png | 05_sequence_ingest_flow.mmd / .puml |
| 06_activity_rag_flow.png | 06_activity_rag_flow.mmd / .puml |
| 07_data_flow_diagram.png | 07_data_flow_diagram.mmd / .puml |
| 08_deployment_diagram.png | 08_deployment_diagram.mmd / .puml |
| 09_use_case_diagram.png | 09_use_case_diagram.mmd / .puml |

## Cyrillic (Монгол) фонтын анхааруулга

Mermaid CLI болон PlantUML default фонтоор Cyrillic тэмдэгтийг render хийхэд асуудалгүй. Гэхдээ:
- **PlantUML** — `Arial Unicode MS` фонтыг тогтоосон (`skinparam defaultFontName`-д). Хэрэв system дээр энэ фонт байхгүй бол `Noto Sans CJK` эсвэл `DejaVu Sans` болгож солих.
- **Mermaid CLI** — pupeteer-ийн Chromium font fallback-аар Cyrillic ажиллана.

Final дипломын тайланд оруулахын өмнө render хийсний дараа Cyrillic тэмдэгтүүд цэвэр гарч байгаа эсэхийг шалгахыг зөвлөж байна.
