const fs = require("node:fs/promises");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { PresentationFile, FileBlob } = require("@oai/artifact-tool");

const ROOT = path.resolve(__dirname, "..", "..");
const SKILL_DIR = "C:\\Users\\user\\.codex\\plugins\\cache\\openai-primary-runtime\\presentations\\26.1111.10930\\skills\\presentations";
const RUNTIME_PYTHON = "C:\\Users\\user\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe";
const SOURCE = path.join(__dirname, "source-r8-readonly-copy.pptx");
const BUILD_DIR = path.join(__dirname, "build");
const FINAL = path.join(ROOT, "docs", "취업준비", "해담-SOAR-포트폴리오-발표본-2026-11-12-r9.pptx");

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, Buffer.from(await blob.arrayBuffer()));
}

function caption(slide, text, left, top, width) {
  const box = slide.shapes.add({
    geometry: "textbox",
    position: { left, top, width, height: 22 },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  box.text = text;
  box.text.style = { fontSize: 12, bold: true, color: "#6A7B88", align: "center" };
}

async function slideElements(deck, index) {
  const result = await deck.inspect({
    select: `$.slides[${index}].elements[*]`,
    include: ["id", "kind", "text", "position"],
  });
  return result.records;
}

async function replaceText(deck, slideIndex, oldText, newText) {
  const result = await deck.inspect({
    select: `$.slides[${slideIndex}].elements[?(@.text == '${oldText}')]`,
    include: ["id", "text"],
  });
  if (result.recordCount !== 1) throw new Error(`Text anchor not unique: ${oldText}`);
  deck.resolve(result.records[0].id).text.replace(oldText, newText);
}

async function replaceNotes(deck, slideIndex, text) {
  const result = await deck.inspect({
    select: `$.slides[${slideIndex}].notes`,
    include: ["id", "text"],
  });
  if (result.recordCount !== 1) throw new Error(`Missing notes on slide ${slideIndex + 1}`);
  deck.resolve(result.records[0].id).text = text;
}

async function clearEvidenceArea(deck, slideIndex, top) {
  const targets = (await slideElements(deck, slideIndex))
    .filter((element) => element.position && element.position.top >= top && element.position.top < 660)
    .map((element) => element.id);
  if (targets.length) deck.delete(targets);
}

async function addScreenshot(slide, fileName, left, top, width, height, alt) {
  const blob = await fs.readFile(path.join(ROOT, "docs", "captures", fileName));
  slide.images.add({
    blob,
    contentType: "image/png",
    alt,
    fit: "contain",
    position: { left, top, width, height },
    geometry: "roundRect",
    borderRadius: "rounded-lg",
  });
}

async function main() {
  await fs.mkdir(BUILD_DIR, { recursive: true });
  await fs.mkdir(path.dirname(FINAL), { recursive: true });
  const deck = await PresentationFile.importPptx(await FileBlob.load(SOURCE));

  // Slides 6, 9 and 10 already have the evidence captions from r8.
  // Replace their blank screenshot frames with byte-embedded evidence.
  await clearEvidenceArea(deck, 5, 200);
  const s6 = deck.slides.getItem(5);
  await addScreenshot(s6, "h2-2-graylog-alerts-0002.png", 58, 205, 545, 410, "H2 Graylog alert showing count and group key");
  await addScreenshot(s6, "h2-3-n8n-executions-0002.png", 677, 205, 545, 410, "H2 n8n executions showing successful response workflows");
  caption(s6, "Graylog H2 경보: count()과 그룹 키", 58, 628, 545);
  caption(s6, "n8n 실행 이력: 대응·기록 워크플로 Success", 677, 628, 545);
  await replaceNotes(deck, 5, "H2 실측 화면이다. 왼쪽 Graylog에서 반복 조회 경보의 count()와 그룹 키를 확인하고, 오른쪽 n8n Executions에서 차단·기록 워크플로가 Success로 완료된 것을 확인한다. 이 캡처 묶음에는 Discord H2 카드가 포함되지 않아 슬라이드에는 넣지 않았다.");

  // Slide 9: retain the measured results and replace abstract verification cards with S7 evidence.
  await clearEvidenceArea(deck, 8, 340);
  const s9 = deck.slides.getItem(8);
  await addScreenshot(s9, "s7-2-ticket-restore.png", 130, 344, 440, 280, "S7 incident ticket with wazuh-ar restore applied");
  await addScreenshot(s9, "s7-3-panel-done.png", 710, 344, 440, 280, "S7 control panel with all six steps completed");
  caption(s9, "티켓: wazuh-ar restore applied", 130, 632, 440);
  caption(s9, "제어판: ①~⑥ 자동 복구 완료", 710, 632, 440);
  await replaceNotes(deck, 8, "왼쪽은 S7 티켓의 wazuh-ar restore applied 대응 기록이다. 오른쪽은 제어판의 기준 파일 변조부터 Wazuh FIM, Graylog 전환, n8n 복구, 기준 해시 검증까지 6단계 완료 화면이다. Discord 수신은 웹훅 미설정으로 여전히 미검증이다.");

  // Slide 10: retain the measured results and add the H4 applied and restored evidence.
  await clearEvidenceArea(deck, 9, 340);
  const s10 = deck.slides.getItem(9);
  await addScreenshot(s10, "h4-2-ticket-response-applied.png", 130, 344, 440, 280, "H4 incident ticket with portal lock applied");
  await addScreenshot(s10, "h4-3-panel-done.png", 710, 344, 440, 280, "H4 control panel after restoration");
  caption(s10, "티켓: portal lock applied 대응 적용", 130, 632, 440);
  caption(s10, "제어판: 해제까지 ①~⑥ 완료", 710, 632, 440);
  await replaceNotes(deck, 9, "왼쪽은 담당자 대량 조회 뒤 portal lock applied가 기록된 H4 티켓이다. 오른쪽은 관리자 해제까지 6단계가 모두 완료된 제어판 화면이다. 티켓의 restored 최종 화면도 별도 증적으로 보완할 수 있다.");

  const candidate = path.join(BUILD_DIR, "haedam-soar-r8-candidate.pptx");
  await (await PresentationFile.exportPptx(deck)).save(candidate);

  const { finalizePresentation } = await import(pathToFileURL(path.join(SKILL_DIR, "container_tools", "artifact_tool_utils.mjs")).href);
  await finalizePresentation({
    workspaceDir: ROOT,
    candidatePath: candidate,
    finalPath: FINAL,
    pythonExecutable: RUNTIME_PYTHON,
    integrityValidatorPath: path.join(SKILL_DIR, "container_tools", "inspect_presentation_package_integrity.py"),
    layoutValidatorPath: path.join(SKILL_DIR, "container_tools", "inspect_presentation_layout_geometry.py"),
    layoutArgs: ["--expected-slide-size-emu", "12192000,6858000", "--validate-bullet-geometry", "--validate-heading-fit"],
    requiredNativeTableOwnerSlides: [],
    requiredNativeChartOwnerSlides: [],
    verifyArtifactToolImport: true,
    receiptPath: path.join(BUILD_DIR, "haedam-soar-r9.validation.json"),
  });

  const finalDeck = await PresentationFile.importPptx(await FileBlob.load(FINAL));
  for (const index of [4, 5, 8, 9]) {
    await writeBlob(path.join(BUILD_DIR, `slide-${index + 1}-after.png`), await finalDeck.slides.getItem(index).export({ format: "png", scale: 1 }));
  }
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
