const fs = require("node:fs/promises");
const path = require("node:path");
const { Presentation, PresentationFile } = require("@oai/artifact-tool");

async function main() {
  const root = path.resolve(__dirname, "..", "..");
  const source = path.join(root, "docs", "captures", "h2-2-graylog-alerts-0002.png");
  const bytes = await fs.readFile(source);
  const presentation = Presentation.create({ slideSize: { width: 1280, height: 720 } });
  const slide = presentation.slides.add();
  slide.images.add({
    blob: bytes,
    contentType: "image/png",
    alt: "Embedding probe",
    position: { left: 40, top: 40, width: 600, height: 600 },
    fit: "contain",
  });
  const out = path.join(__dirname, "image-embedding-probe.pptx");
  await (await PresentationFile.exportPptx(presentation)).save(out);
  console.log(out);
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
