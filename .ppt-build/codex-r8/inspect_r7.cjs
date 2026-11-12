const fs = require("node:fs/promises");
const path = require("node:path");
const { Presentation, PresentationFile, FileBlob } = require("@oai/artifact-tool");

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, Buffer.from(await blob.arrayBuffer()));
}

async function main() {
  const root = path.resolve(__dirname, "..", "..");
  const deckPath = path.join(root, "docs", "취업준비", "해담-SOAR-포트폴리오-발표본-2026-11-12-r7.pptx");
  const out = path.join(__dirname, "inspection");
  await fs.mkdir(out, { recursive: true });

  const deck = await PresentationFile.importPptx(await FileBlob.load(deckPath));
  const summary = await deck.inspect({
    select: "$.slides[4,5,8,9]",
    include: ["id", "index", "elements.id", "elements.kind", "elements.text", "elements.position", "notes.text"],
  });
  await fs.writeFile(path.join(out, "slides-5-6-9-10.ndjson"), summary.ndjson, "utf8");
  for (const index of [4, 5, 8, 9]) {
    const slide = deck.slides.getItem(index);
    await writeBlob(path.join(out, `slide-${index + 1}-before.png`), await slide.export({ format: "png", scale: 1 }));
    await writeBlob(path.join(out, `slide-${index + 1}-before.layout.json`), await slide.export({ format: "layout" }));
  }
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
