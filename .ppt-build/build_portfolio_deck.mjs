import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const workspaceDir = "C:/SR/final_project";
const skillDir = "C:/Users/user/.codex/plugins/cache/openai-primary-runtime/presentations/26.1105.12137/skills/presentations";
const buildDir = path.join(workspaceDir, ".ppt-build");
const outputDir = path.join(workspaceDir, "docs", "취업준비");
const finalPath = path.join(outputDir, "해담-SOAR-포트폴리오-발표본-2026-11-11-r2.pptx");
const candidatePath = path.join(buildDir, "haedam-portfolio-candidate.pptx");

const C = {
  navy: "#123047",
  teal: "#27CDBE",
  ink: "#173B50",
  muted: "#648092",
  pale: "#EAF3F7",
  mint: "#DDF7F2",
  white: "#FFFFFF",
  bg: "#F7FAFC",
  amber: "#D47A15",
  amberPale: "#FFF1D9",
  green: "#12836D",
  line: "#C9D9E2",
};
const FONT = "Malgun Gothic";

function shape(slide, geometry, left, top, width, height, fill = "none", lineFill = "none", lineWidth = 0) {
  return slide.shapes.add({
    geometry,
    position: { left, top, width, height },
    fill,
    line: { style: "solid", fill: lineFill, width: lineWidth },
  });
}

function rect(slide, left, top, width, height, fill, radius = false) {
  return shape(slide, radius ? "roundRect" : "rect", left, top, width, height, fill, "none", 0);
}

function text(slide, value, left, top, width, height, opts = {}) {
  const box = shape(slide, "textbox", left, top, width, height, "none", "none", 0);
  box.text = value;
  box.text.style = {
    fontFamily: FONT,
    fontSize: opts.size ?? 22,
    bold: opts.bold ?? false,
    color: opts.color ?? C.ink,
    alignment: opts.align ?? "left",
    verticalAlignment: opts.vAlign ?? "top",
  };
  return box;
}

function base(slide, number, section, title, subtitle = "") {
  slide.background.fill = C.bg;
  rect(slide, 0, 0, 24, 720, C.teal);
  text(slide, `${String(number).padStart(2, "0")}  ${section.toUpperCase()}`, 70, 46, 400, 28, {
    size: 17, bold: true, color: C.teal,
  });
  text(slide, title, 70, 94, 1110, 58, { size: 38, bold: true, color: C.navy });
  if (subtitle) text(slide, subtitle, 70, 158, 1080, 42, { size: 18, color: C.muted });
  rect(slide, 70, 211, 1140, 3, C.navy);
  text(slide, "해담시청 SOAR 실습 환경  |  실측 근거만 기재", 70, 682, 700, 18, { size: 11, color: C.muted });
  text(slide, String(number), 1160, 678, 50, 20, { size: 12, color: C.muted, align: "right" });
}

function metric(slide, x, value, label, note, color = C.teal) {
  text(slide, value, x, 315, 230, 70, { size: 48, bold: true, color });
  text(slide, label, x, 388, 260, 30, { size: 20, bold: true, color: C.navy });
  text(slide, note, x, 425, 270, 48, { size: 14, color: C.muted });
}

function step(slide, x, number, label, detail, isDark = false) {
  const fill = isDark ? C.navy : C.white;
  const main = isDark ? C.white : C.navy;
  rect(slide, x, 330, 232, 148, fill, true);
  text(slide, String(number).padStart(2, "0"), x + 22, 350, 50, 24, { size: 15, bold: true, color: C.teal });
  text(slide, label, x + 22, 387, 188, 30, { size: 21, bold: true, color: main });
  text(slide, detail, x + 22, 424, 188, 34, { size: 13, color: isDark ? "#DDEAF1" : C.muted });
}

async function imageBytes(filePath) {
  const bytes = await fs.readFile(filePath);
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
}

async function addImage(slide, filePath, left, top, width, height, alt) {
  slide.images.add({
    blob: await imageBytes(filePath),
    contentType: "image/png",
    alt,
    fit: "contain",
    position: { left, top, width, height },
    geometry: "roundRect",
    borderRadius: "rounded-xl",
  });
}

async function build() {
  await fs.mkdir(buildDir, { recursive: true });
  await fs.mkdir(outputDir, { recursive: true });
  const presentation = Presentation.create({ slideSize: { width: 1280, height: 720 } });

  // 1. Cover
  {
    const s = presentation.slides.add();
    s.background.fill = C.navy;
    rect(s, 0, 0, 28, 720, C.teal);
    text(s, "HAEDAM SOAR", 90, 104, 330, 30, { size: 18, bold: true, color: C.teal });
    text(s, "민원 포털 보안 자동 대응", 90, 180, 850, 70, { size: 48, bold: true, color: C.white });
    text(s, "탐지 · 차단 · 티켓 · 원복을 하나의 실습 흐름으로 검증", 94, 267, 860, 38, { size: 23, color: "#DCEAF2" });
    rect(s, 90, 372, 186, 4, C.teal);
    text(s, "Graylog  /  n8n  /  pfSense  /  Wazuh  /  민원 포털", 90, 406, 900, 36, { size: 21, color: C.white });
    text(s, "발표자: [이름 입력]     2026. 11. 11", 90, 596, 650, 28, { size: 16, color: "#BFD3DF" });
    text(s, "실습 환경의 로컬 검증 결과", 90, 630, 520, 24, { size: 14, color: "#8EABB9" });
  }

  // 2. Problem and scope
  {
    const s = presentation.slides.add();
    base(s, 2, "Project", "문제와 목표", "반복 공격을 탐지하고, 안전한 자동 조치와 원복 기록을 남긴다");
    text(s, "기존 상황", 100, 280, 260, 28, { size: 19, bold: true, color: C.teal });
    text(s, "탐지 화면, 대응 도구, 처리 이력이 분리되면\n운영자가 사건의 전후 상태를 한 번에 확인하기 어렵다.", 100, 326, 420, 105, { size: 23, color: C.navy });
    rect(s, 596, 272, 4, 230, C.teal);
    text(s, "검증 범위", 650, 280, 260, 28, { size: 19, bold: true, color: C.teal });
    text(s, "민원 포털 로그를 Graylog가 탐지한다.\nn8n이 차단과 티켓 기록을 실행한다.\n담당자는 원복 뒤 정상 기능을 다시 확인한다.", 650, 326, 450, 130, { size: 23, color: C.navy });
  }

  // 3. Architecture
  {
    const s = presentation.slides.add();
    base(s, 3, "Architecture", "보안 관제 구성", "포털의 보안 이벤트가 탐지, 대응, 알림과 티켓 기록으로 이어진다");
    step(s, 75, 1, "민원 포털", "접근·로그인 이벤트", true);
    text(s, "→", 323, 376, 58, 46, { size: 35, bold: true, color: C.teal, align: "center" });
    step(s, 392, 2, "Graylog", "규칙·이벤트 정의");
    text(s, "→", 640, 376, 58, 46, { size: 35, bold: true, color: C.teal, align: "center" });
    step(s, 709, 3, "n8n", "차단·티켓·알림", true);
    text(s, "→", 957, 376, 58, 46, { size: 35, bold: true, color: C.teal, align: "center" });
    step(s, 1026, 4, "보호 조치", "포털·pfSense 원복");
    text(s, "Wazuh는 정적 파일 무결성 감시 경로로 별도 연계한다.", 75, 545, 930, 30, { size: 18, color: C.muted });
  }

  // 4. Cases
  {
    const s = presentation.slides.add();
    base(s, 4, "Coverage", "검증한 시나리오", "가용성·기밀성·인증 공격을 실제 실행기와 티켓으로 확인했다");
    const rows = [
      ["S10", "경계 신호·스캔·로그인", "pfSense와 포털 차단", "완료"],
      ["S8", "포털 스캔과 로그인 실패", "포털 차단", "완료"],
      ["S1", "로그인 무차별 대입", "포털 차단과 원복", "완료"],
      ["H1", "민원 반복 등록", "작성 제한과 원복", "완료"],
      ["H2", "타인 민원 반복 조회", "IP 차단·계정 잠금·원복", "완료"],
      ["H3", "민원 처리 결과 조작", "변경 이력 기반 원복", "진행 중"],
    ];
    const y0 = 270;
    ["CASE", "시나리오", "대응", "상태"].forEach((h, i) => text(s, h, [96, 246, 600, 1030][i], 242, [100, 320, 350, 100][i], 24, { size: 15, bold: true, color: C.teal }));
    rows.forEach((r, i) => {
      const y = y0 + i * 55;
      rect(s, 92, y + 43, 1090, 1, C.line);
      text(s, r[0], 96, y, 100, 28, { size: 18, bold: true, color: C.navy });
      text(s, r[1], 246, y, 320, 28, { size: 17, color: C.ink });
      text(s, r[2], 600, y, 350, 28, { size: 17, color: C.ink });
      text(s, r[3], 1030, y, 100, 28, { size: 16, bold: true, color: r[3] === "완료" ? C.green : C.amber });
    });
  }

  // 5. H2 detect flow
  {
    const s = presentation.slides.add();
    base(s, 5, "H2", "타인 민원 반복 조회 탐지", "기밀성 침해 시도를 계정과 출발지 IP 조합으로 묶어 판단한다");
    step(s, 85, 1, "403 반복", "타인 민원 상세 3건 이상", true);
    text(s, "→", 329, 377, 58, 46, { size: 35, bold: true, color: C.teal, align: "center" });
    step(s, 405, 2, "Graylog 경보", "5분 창, count() > 2");
    text(s, "→", 649, 377, 58, 46, { size: 35, bold: true, color: C.teal, align: "center" });
    step(s, 725, 3, "자동 대응", "IP 차단·계정 잠금", true);
    text(s, "→", 969, 377, 58, 46, { size: 35, bold: true, color: C.teal, align: "center" });
    step(s, 1045, 4, "원복 확인", "계정 정상·권한 유지");
    text(s, "공격 출발지 203.0.113.11  |  H2 티켓 T-20261111-0009", 85, 550, 800, 30, { size: 18, bold: true, color: C.navy });
  }

  // 6. Evidence
  {
    const s = presentation.slides.add();
    base(s, 6, "Evidence", "탐지부터 원복까지의 증적", "H2는 Graylog·n8n·Discord에 같은 티켓 ID로 남는다");
    text(s, "T-20261111-0009", 80, 276, 440, 48, { size: 33, bold: true, color: C.navy });
    text(s, "Graylog: H2 타인 민원 상세 반복 조회\nn8n: 포털 IP 차단·계정 잠금·해제 성공\nDiscord: 자동 차단 처리 후 복원 완료", 80, 349, 475, 132, { size: 21, color: C.ink });
    rect(s, 80, 516, 467, 68, C.amberPale, true);
    text(s, "발표 시 H2 Discord·Graylog·n8n 원본 캡처 3장을 순서대로 교체", 104, 536, 420, 25, { size: 14, bold: true, color: C.amber });
    const evidence = [
      ["Graylog", "H2 반복 조회 경보\n그룹 키: 계정 + 203.0.113.11\ncount()=4.0"],
      ["n8n", "포털 IP 차단·계정 잠금\n결과 기록·복원 워크플로\n모두 Success"],
      ["Discord", "T-20261111-0009\n계정 잠금·IP 차단\n이어서 복원 완료"],
    ];
    evidence.forEach((item, i) => {
      const y = 258 + i * 116;
      rect(s, 644, y, 430, 94, i === 1 ? C.navy : C.white, true);
      text(s, item[0], 670, y + 16, 100, 24, { size: 16, bold: true, color: C.teal });
      text(s, item[1], 790, y + 14, 250, 60, { size: 15, color: i === 1 ? C.white : C.ink });
    });
    text(s, "원본 캡처 3장을 확보하면 같은 위치에 교체한다.", 644, 611, 450, 22, { size: 13, color: C.muted });
  }

  // 7. Aggregate results
  {
    const s = presentation.slides.add();
    base(s, 7, "Results", "수정 후 실측 결과", "S10·S8·S1·H1·H2의 성공 회차만 집계했다");
    metric(s, 100, "16/16", "자동 대응", "수정 후 모든 실측 회차 성공");
    metric(s, 400, "16/16", "원복", "조치 후 정상 기능 복구");
    metric(s, 700, "0회", "정상 사용자 영향", "대응 중 normal 요청 확인", C.green);
    metric(s, 1000, "0/5", "기준선 오탐", "각 케이스 정상 입력", C.green);
    rect(s, 100, 518, 1060, 1, C.line);
    text(s, "입력부터 차단까지 중앙값", 100, 548, 330, 30, { size: 20, color: C.muted });
    text(s, "37.391초", 450, 535, 260, 52, { size: 37, bold: true, color: C.navy });
    text(s, "Graylog 내부 처리 기준 MTTD 중앙값 0.466초", 730, 551, 400, 26, { size: 17, color: C.muted });
  }

  // 8. H2 validation
  {
    const s = presentation.slides.add();
    base(s, 8, "H2", "H2 검증 결과", "차단 뒤에도 타인 민원 권한은 계속 거부되는지 확인했다");
    const columns = [100, 365, 620, 875];
    const heads = ["자동 대응", "원복", "기준선 오탐", "입력→차단 중앙값"];
    const vals = ["3/3", "3/3", "0/1", "46.907초"];
    heads.forEach((h, i) => text(s, h, columns[i], 280, 240, 28, { size: 16, bold: true, color: C.teal }));
    vals.forEach((v, i) => text(s, v, columns[i], 320, 240, 50, { size: 34, bold: true, color: C.navy }));
    rect(s, 100, 417, 1040, 3, C.teal);
    text(s, "원복 후 확인", 100, 455, 250, 30, { size: 20, bold: true, color: C.navy });
    text(s, "공격 계정 로그인 200", 100, 500, 300, 30, { size: 19, color: C.ink });
    text(s, "타인 민원 상세 조회 403", 470, 500, 330, 30, { size: 19, color: C.ink });
    text(s, "미인증 해제 요청 403", 860, 500, 290, 30, { size: 19, color: C.ink });
    text(s, "계정은 복구하되, 타인 민원 접근 권한은 복구하지 않는다.", 100, 576, 820, 34, { size: 23, bold: true, color: C.green });
  }

  // 9. Contribution
  {
    const s = presentation.slides.add();
    base(s, 9, "Contribution", "담당 기여와 해결한 문제", "포털 대응 API와 이벤트 경로를 실측 가능한 시나리오로 연결했다");
    text(s, "담당 영역", 100, 280, 240, 26, { size: 19, bold: true, color: C.teal });
    text(s, "포털 대응 API\nGELF TCP 로그 경로\nS1·S4 대응 흐름\nH1·H2 시나리오", 100, 328, 340, 170, { size: 23, color: C.navy });
    rect(s, 560, 270, 4, 260, C.teal);
    text(s, "해결 사례", 620, 280, 240, 26, { size: 19, bold: true, color: C.teal });
    text(s, "H1에서 탐지와 n8n 호출은 성공했지만\n티켓 저장소의 허용 목록 누락으로 기록이 400으로 거부됐다.\n목록을 보완한 뒤 수정 후 실측 3/3에서\n작성 제한·정상 사용자·원복을 모두 확인했다.", 620, 328, 475, 160, { size: 21, color: C.navy });
  }

  // 10. Limits
  {
    const s = presentation.slides.add();
    base(s, 10, "Next", "한계와 다음 단계", "현재 결과의 범위와 남은 검증을 구분한다");
    text(s, "현재 한계", 100, 285, 270, 28, { size: 20, bold: true, color: C.teal });
    text(s, "케이스별 실측은 3회라 경향만 판단할 수 있다.\n한 PC Docker 환경이므로 다중 PC 환경의 지연과 직접 같지 않다.", 100, 338, 440, 105, { size: 22, color: C.navy });
    rect(s, 620, 272, 4, 245, C.teal);
    text(s, "다음 검증", 680, 285, 270, 28, { size: 20, bold: true, color: C.teal });
    text(s, "H3 실측·원복 완료\nS4·S7·S12 시나리오 검증\n다중 PC 환경에서 재측정", 680, 338, 390, 120, { size: 22, color: C.navy });
    text(s, "실습 검증 결과와 한계를 함께 제시해 재현 가능한 발표 자료로 마무리한다.", 100, 585, 1000, 34, { size: 20, bold: true, color: C.green });
  }

  await (await PresentationFile.exportPptx(presentation)).save(candidatePath);
  const { finalizePresentation } = await import(pathToFileURL(path.join(skillDir, "container_tools", "artifact_tool_utils.mjs")).href);
  const result = await finalizePresentation({
    explicitTotalSlideCount: 10,
    requiredNativeTableOwnerSlides: [],
    requiredNativeChartOwnerSlides: [],
    workspaceDir,
    candidatePath,
    finalPath,
    pythonExecutable: process.env.RUNTIME_PYTHON,
    integrityValidatorPath: path.join(skillDir, "container_tools", "inspect_presentation_package_integrity.py"),
    layoutValidatorPath: path.join(skillDir, "container_tools", "inspect_presentation_layout_geometry.py"),
    layoutArgs: ["--expected-slide-size-emu", "12192000,6858000", "--validate-bullet-geometry", "--validate-heading-fit"],
    fontPolicy: { basis: "design", families: [FONT, "Arial"] },
    verifyArtifactToolImport: true,
    receiptPath: path.join(buildDir, "haedam-portfolio-r2.validation.json"),
  });
  console.log(JSON.stringify({ finalPath, result }, null, 2));
}

build().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
