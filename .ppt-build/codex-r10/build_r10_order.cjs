const fs = require("node:fs/promises");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { PresentationFile, FileBlob } = require("@oai/artifact-tool");

const ROOT = path.resolve(__dirname, "..", "..");
const SKILL_DIR = "C:\\Users\\user\\.codex\\plugins\\cache\\openai-primary-runtime\\presentations\\26.1111.10930\\skills\\presentations";
const RUNTIME_PYTHON = "C:\\Users\\user\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe";
const SOURCE = path.join(__dirname, "source-r9-readonly-copy.pptx");
const BUILD_DIR = path.join(__dirname, "build");
const FINAL = path.join(ROOT, "docs", "취업준비", "해담-SOAR-포트폴리오-발표본-2026-11-12-r10.pptx");

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, Buffer.from(await blob.arrayBuffer()));
}

async function slideElements(deck, index) {
  const result = await deck.inspect({
    select: `$.slides[${index}].elements[*]`,
    include: ["id", "kind", "text", "position"],
  });
  return result.records;
}

function sortByPosition(elements) {
  return elements.sort((a, b) => a.position.top - b.position.top || a.position.left - b.position.left);
}

async function main() {
  await fs.mkdir(BUILD_DIR, { recursive: true });
  const deck = await PresentationFile.importPptx(await FileBlob.load(SOURCE));

  // Slide 4: make the scenario cards match the control-panel tab sequence.
  const cards = [
    ["H1", "민원 반복 등록", "작성 제한과 원복"],
    ["H2", "타인 민원 반복 조회", "IP 차단·계정 잠금"],
    ["H3", "민원 처리 결과 조작", "잠금·스냅샷 복원"],
    ["H4", "담당자 대량 조회", "담당자 잠금·세션 회수"],
    ["S1", "로그인 무차별 대입", "포털 차단과 원복"],
    ["S4", "실패 뒤 성공 로그인", "계정 잠금·세션 회수"],
    ["S7", "홈페이지 변조", "Wazuh 자동 복구"],
    ["S8", "포털 스캔·로그인 실패", "포털 차단"],
    ["S10", "경계 신호·스캔·로그인", "pfSense와 포털 차단"],
    ["S12", "요청 폭주", "요청 수 기준 포털 차단"],
  ];
  const elements = await slideElements(deck, 3);
  const roleText = (top) => sortByPosition(elements.filter((item) => item.kind === "textbox" && Math.abs(item.position.top - top) < 1));
  const codes = roleText(220.8).concat(roleText(417.6));
  const scenarios = roleText(286.08).concat(roleText(482.88));
  const responses = roleText(322.56).concat(roleText(519.36));
  if ([codes, scenarios, responses].some((items) => items.length !== 10)) throw new Error("Scenario card anchors changed");
  cards.forEach(([code, scenario, response], index) => {
    deck.resolve(codes[index].id).text = code;
    deck.resolve(scenarios[index].id).text = scenario;
    deck.resolve(responses[index].id).text = response;
  });

  // Featured case slides follow the same H then S sequence: H2, H4, S7.
  const slides = await deck.inspect({ select: "$.slides[*]", include: ["id"] });
  const order = slides.records.map((record) => record.id);
  [order[8], order[9]] = [order[9], order[8]];
  deck.slides.reorder(order);

  const h4Elements = await slideElements(deck, 8);
  const s7Elements = await slideElements(deck, 9);
  const text = (elements, oldValue, newValue) => {
    const match = elements.find((item) => item.kind === "textbox" && item.text === oldValue);
    if (!match) throw new Error(`Missing text: ${oldValue}`);
    deck.resolve(match.id).text = newValue;
  };
  text(h4Elements, "10  H4", "09  H4");
  text(h4Elements, "10", "9");
  text(s7Elements, "09  S7", "10  S7");
  text(s7Elements, "9", "10");

  const candidate = path.join(BUILD_DIR, "haedam-soar-r10-candidate.pptx");
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
    receiptPath: path.join(BUILD_DIR, "haedam-soar-r10.validation.json"),
  });

  const finalDeck = await PresentationFile.importPptx(await FileBlob.load(FINAL));
  for (const index of [3, 8, 9]) {
    await writeBlob(path.join(BUILD_DIR, `slide-${index + 1}-after.png`), await finalDeck.slides.getItem(index).export({ format: "png", scale: 1 }));
  }
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
