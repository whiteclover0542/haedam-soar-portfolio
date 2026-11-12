// r7: r6 content + H4 gaps filled. Run: NODE_PATH=<dir with pptxgenjs, react-icons, react, react-dom, sharp> node build_deck_r7.cjs
const path = require("path");
const pptxgen = require("pptxgenjs");
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa");
const { applyTheme } = require(process.env.APPLY_THEME);

const OUT = path.join(__dirname, "..", "docs", "취업준비", "해담-SOAR-포트폴리오-발표본-2026-11-12-r7.pptx");
const THEME = {
  name: "Haedam SOC",
  headFontFace: "Malgun Gothic",
  bodyFontFace: "Malgun Gothic",
  colors: {
    dk1: "14232F", lt1: "FFFFFF", dk2: "0B1A26", lt2: "EEF2F5",
    accent1: "FF6B2C", accent2: "17A673", accent3: "2E86AB", accent4: "E9A23B", accent5: "6A7B88", accent6: "D6DEE4",
    hlink: "2E86AB", folHlink: "6A7B88",
  },
};
const H = THEME.colors; // hex, only for images and shadows
const MONO = "Consolas";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "해담 SOAR 포트폴리오";
const C = pres.SchemeColor;
const S = pres.shapes;

const shadow = () => ({ type: "outer", color: H.dk2, opacity: 0.1, blur: 10, offset: 2, angle: 90 });

async function icon(Comp, hex) {
  const svg = renderToStaticMarkup(React.createElement(Comp, { color: "#" + hex, size: 256 }));
  return "image/png;base64," + (await sharp(Buffer.from(svg)).png().toBuffer()).toString("base64");
}

// ---------- layouts ----------
const footer = (color) => [
  { text: { text: "해담시청 SOAR 실습 환경  |  실측 근거만 기재",
    options: { x: 0.6, y: 6.98, w: 7, h: 0.3, fontSize: 10, color, margin: 0 } } },
];
const heads = (dark) => [
  { placeholder: { options: { name: "kicker", type: "body", x: 0.6, y: 0.42, w: 9, h: 0.3, fontSize: 12, bold: true,
    color: C.accent1, charSpacing: 2, margin: 0, valign: "top" }, text: "" } },
  { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.74, w: 12.1, h: 0.7, fontSize: 32, bold: true,
    color: dark ? C.background1 : C.text2, margin: 0, valign: "top", align: "left" }, text: "" } },
  { placeholder: { options: { name: "sub", type: "body", x: 0.6, y: 1.42, w: 12.1, h: 0.4, fontSize: 15,
    color: dark ? C.accent6 : C.accent5, margin: 0, valign: "top" }, text: "" } },
];
pres.defineSlideMaster({ title: "LIGHT", background: { color: C.background1 },
  objects: [...heads(false), ...footer(C.accent5)],
  slideNumber: { x: 12.23, y: 6.98, w: 0.5, h: 0.3, fontSize: 10, color: C.accent5, align: "right" } });
pres.defineSlideMaster({ title: "DARK", background: { color: C.text2 },
  objects: [...heads(true), ...footer(C.accent5)],
  slideNumber: { x: 12.23, y: 6.98, w: 0.5, h: 0.3, fontSize: 10, color: C.accent5, align: "right" } });
pres.defineSlideMaster({ title: "COVER", background: { color: C.text2 }, objects: [] });

function page(master, section, kicker, title, sub) {
  const s = pres.addSlide({ masterName: master, sectionTitle: section });
  s.addText(kicker, { placeholder: "kicker" });
  s.addText(title, { placeholder: "title" });
  if (sub) s.addText(sub, { placeholder: "sub" });
  return s;
}
const T = (s, text, o) => s.addText(text, { isTextBox: true, margin: 0, valign: "top", ...o });
const box = (s, o) => s.addShape(S.ROUNDED_RECTANGLE, { rectRadius: 0.08, line: { type: "none" }, ...o });
function iconTile(s, data, x, y, d, fill, transparency = 0, shape = "circle") {
  s.addShape(shape === "circle" ? S.OVAL : S.ROUNDED_RECTANGLE,
    { x, y, w: d, h: d, fill: { color: fill, transparency }, line: { type: "none" }, ...(shape === "circle" ? {} : { rectRadius: 0.1 }) });
  const p = d * 0.27;
  s.addImage({ data, x: x + p, y: y + p, w: d - 2 * p, h: d - 2 * p });
}
const chip = (s, text, x, y, w, o = {}) => {
  box(s, { x, y, w, h: 0.42, rectRadius: 0.21, fill: { color: o.fill ?? C.background2, transparency: o.t ?? 0 } });
  T(s, text, { x, y, w, h: 0.42, align: "center", valign: "middle", fontSize: o.size ?? 13, bold: o.bold ?? false,
    color: o.color ?? C.text1, fontFace: o.mono ? MONO : undefined });
};
const arrow = (s, x1, y, x2, color = C.accent6) =>
  s.addShape(S.LINE, { x: x1, y, w: x2 - x1, h: 0, line: { color, width: 2, endArrowType: "triangle" } });

async function build() {
  const I = {};
  const want = {
    globe: [fa.FaGlobeAsia, H.lt1], search: [fa.FaSearch, H.lt1], cogs: [fa.FaCogs, H.lt1], shield: [fa.FaShieldAlt, H.lt1],
    ticket: [fa.FaTicketAlt, H.lt1], undo: [fa.FaUndoAlt, H.lt1], ban: [fa.FaBan, H.lt1], bell: [fa.FaBell, H.lt1],
    eye: [fa.FaEye, H.accent5], warn: [fa.FaExclamationTriangle, H.lt1], check: [fa.FaCheck, H.lt1],
    code: [fa.FaCode, H.lt1], stream: [fa.FaStream, H.lt1], flow: [fa.FaProjectDiagram, H.lt1], flask: [fa.FaFlask, H.lt1],
    lock: [fa.FaUserLock, H.lt1], discord: [fa.FaDiscord, H.lt1], key: [fa.FaKey, H.lt1], chart: [fa.FaChartLine, H.lt1],
    bigShield: [fa.FaShieldAlt, "1A3346"], monitor: [fa.FaDesktop, H.lt1], layers: [fa.FaLayerGroup, H.lt1],
    eyeW: [fa.FaEye, H.lt1], wrench: [fa.FaWrench, H.lt1], server: [fa.FaServer, H.lt1],
  };
  for (const [k, [comp, hex]] of Object.entries(want)) I[k] = await icon(comp, hex);

  // ---------- 1. cover ----------
  {
    pres.addSection({ title: "소개" });
    const s = pres.addSlide({ masterName: "COVER", sectionTitle: "소개" });
    s.addImage({ data: I.bigShield, x: 8.9, y: 0.7, w: 4.0, h: 4.0 });
    T(s, "HAEDAM SOAR", { x: 0.8, y: 1.05, w: 6, h: 0.35, fontSize: 14, bold: true, color: C.accent1, charSpacing: 4 });
    T(s, "민원 포털 보안 자동 대응", { x: 0.8, y: 1.5, w: 9, h: 0.95, fontSize: 46, bold: true, color: C.background1 });
    T(s, "탐지 · 차단 · 티켓 · 원복을 하나의 실습 흐름으로 검증", { x: 0.8, y: 2.5, w: 9, h: 0.5, fontSize: 20, color: C.accent6 });
    // lifecycle hero
    const steps = [["탐지", I.search, C.accent1], ["차단", I.ban, C.accent1], ["티켓", I.ticket, C.accent3], ["원복", I.undo, C.accent2]];
    steps.forEach(([label, ic, col], i) => {
      const x = 0.8 + i * 2.1;
      if (i) arrow(s, x - 1.1, 4.12, x - 0.12, C.accent5);
      iconTile(s, ic, x, 3.7, 0.84, col);
      T(s, label, { x: x - 0.3, y: 4.68, w: 1.44, h: 0.4, align: "center", fontSize: 15, bold: true, color: C.background1 });
    });
    ["Graylog", "n8n", "pfSense", "Wazuh", "민원 포털"].forEach((t, i) =>
      chip(s, t, 0.8 + i * 1.42, 5.45, 1.28, { fill: C.background1, t: 90, color: C.accent6, size: 12 }));
    T(s, "발표자: [이름 입력]     2026. 11. 12", { x: 0.8, y: 6.45, w: 7, h: 0.35, fontSize: 14, color: C.accent6 });
    T(s, "실습 환경의 로컬 검증 결과", { x: 0.8, y: 6.82, w: 7, h: 0.3, fontSize: 11, color: C.accent5 });
    s.addNotes("제목은 짧게. 탐지부터 차단·티켓·원복까지 하나의 흐름을 실습 환경에서 검증한 프로젝트라고 소개한다.");
  }

  // ---------- 2. problem ----------
  {
    const s = page("LIGHT", "소개", "02  PROJECT", "문제와 목표", "반복 공격을 탐지하고, 안전한 자동 조치와 원복 기록을 남긴다");
    box(s, { x: 0.6, y: 2.15, w: 5.85, h: 4.45, fill: { color: C.background2 } });
    iconTile(s, I.warn, 0.95, 2.45, 0.6, C.accent1);
    T(s, "기존 상황", { x: 1.75, y: 2.55, w: 4, h: 0.45, fontSize: 20, bold: true, color: C.text2 });
    [["탐지 화면", 1.0, 3.45], ["대응 도구", 3.15, 3.85], ["처리 이력", 1.75, 4.45]].forEach(([t, x, y]) => {
      box(s, { x, y, w: 2.0, h: 0.55, fill: { color: C.background1 }, line: { color: C.accent6, width: 1, dashType: "dash" } });
      T(s, t, { x, y, w: 2.0, h: 0.55, align: "center", valign: "middle", fontSize: 14, color: C.accent5 });
    });
    T(s, "탐지 화면, 대응 도구, 처리 이력이 분리되면 운영자가 사건의 전후 상태를 한 번에 확인하기 어렵다.",
      { x: 0.95, y: 5.35, w: 5.2, h: 1.0, fontSize: 15, color: C.text1 });

    box(s, { x: 6.85, y: 2.15, w: 5.88, h: 4.45, fill: { color: C.background1 }, line: { color: C.accent6, width: 1 }, shadow: shadow() });
    iconTile(s, I.check, 7.2, 2.45, 0.6, C.accent2);
    T(s, "검증 범위", { x: 8.0, y: 2.55, w: 4, h: 0.45, fontSize: 20, bold: true, color: C.text2 });
    ["민원 포털 로그를 Graylog가 탐지한다", "n8n이 차단과 티켓 기록을 실행한다", "담당자는 원복 뒤 정상 기능을 다시 확인한다"].forEach((t, i) => {
      const y = 3.45 + i * 0.95;
      s.addShape(S.OVAL, { x: 7.2, y, w: 0.5, h: 0.5, fill: { color: C.text2 }, line: { type: "none" } });
      T(s, String(i + 1), { x: 7.2, y, w: 0.5, h: 0.5, align: "center", valign: "middle", fontSize: 14, bold: true, color: C.background1 });
      T(s, t, { x: 7.95, y, w: 4.5, h: 0.5, valign: "middle", fontSize: 16, color: C.text1 });
    });
    s.addNotes("주장보다 시연 범위를 분명히 설명한다. 수동 관제는 탐지·대응·기록이 분리된다는 점에서 출발한다.");
  }

  // 8~11장 공통: 수치 4개 → 확인 타일 3개 → 핵심 문장
  function verdict(s, stats, label, tiles, banner) {
    stats.forEach(([v, l], i) => {
      const x = 0.6 + i * 3.09;
      T(s, l, { x, y: 2.15, w: 2.85, h: 0.35, fontSize: 13, bold: true, color: C.accent5 });
      T(s, v, { x, y: 2.5, w: 2.85, h: 0.75, fontSize: 34, bold: true, color: C.text2 });
    });
    T(s, label, { x: 0.6, y: 3.6, w: 4, h: 0.4, fontSize: 16, bold: true, color: C.text2 });
    tiles.forEach(([code, what, tag, col], i) => {
      const x = 0.6 + i * 4.14;
      box(s, { x, y: 4.1, w: 3.84, h: 1.3, fill: { color: C.background1 }, line: { color: C.accent6, width: 1 }, shadow: shadow() });
      T(s, code, { x: x + 0.3, y: 4.3, w: 1.3, h: 0.85, valign: "middle", fontSize: 36, bold: true, color: col, fontFace: /^[0-9A-Z]+$/.test(code) ? MONO : undefined });
      T(s, what, { x: x + 1.65, y: 4.38, w: 2.1, h: 0.4, fontSize: 14, bold: true, color: C.text1, fontFace: what.startsWith("T-") ? MONO : undefined });
      T(s, tag, { x: x + 1.65, y: 4.78, w: 2.1, h: 0.35, fontSize: 12, color: col });
    });
    box(s, { x: 0.6, y: 5.7, w: 12.13, h: 0.8, fill: { color: C.accent2, transparency: 88 } });
    iconTile(s, I.key, 0.85, 5.82, 0.56, C.accent2);
    T(s, banner, { x: 1.65, y: 5.7, w: 10.8, h: 0.8, valign: "middle", fontSize: 19, bold: true, color: C.text2 });
  }

  // ---------- 3. architecture ----------
  {
    const s = page("LIGHT", "소개", "03  ARCHITECTURE", "보안 관제 구성", "포털의 보안 이벤트가 탐지, 대응, 알림과 티켓 기록으로 이어진다");
    const nodes = [["민원 포털", "로그인·민원 이벤트", I.globe, C.accent3],
      ["Graylog", "규칙·이벤트 정의", I.search, C.accent1],
      ["n8n", "차단·잠금·티켓·알림", I.cogs, C.accent1],
      ["보호 조치", "포털·pfSense 원복", I.shield, C.accent2]];
    nodes.forEach(([name, detail, ic, col], i) => {
      const x = 0.6 + i * 3.15, hub = i === 2;
      box(s, { x, y: 2.3, w: 2.55, h: 2.1, fill: { color: hub ? C.text2 : C.background1 },
        line: hub ? { type: "none" } : { color: C.accent6, width: 1 }, shadow: shadow() });
      iconTile(s, ic, x + 0.3, 2.6, 0.62, col);
      T(s, name, { x: x + 0.3, y: 3.35, w: 2.1, h: 0.45, fontSize: 20, bold: true, color: hub ? C.background1 : C.text2 });
      T(s, detail, { x: x + 0.3, y: 3.82, w: 2.1, h: 0.4, fontSize: 13, color: hub ? C.accent6 : C.accent5 });
      if (i) arrow(s, x - 0.52, 3.35, x - 0.08, C.accent5);
    });
    s.addShape(S.LINE, { x: 8.175, y: 4.4, w: 0, h: 0.45, line: { color: C.accent5, width: 2, endArrowType: "triangle" } });
    box(s, { x: 6.9, y: 4.9, w: 2.55, h: 0.75, fill: { color: C.accent3, transparency: 88 } });
    iconTile(s, I.ticket, 7.05, 5.02, 0.5, C.accent3);
    T(s, "티켓 대시보드\nDiscord 알림", { x: 7.68, y: 4.95, w: 1.7, h: 0.65, valign: "middle", fontSize: 12, bold: true, color: C.text2 });

    box(s, { x: 0.6, y: 4.9, w: 5.7, h: 0.75, fill: { color: C.background1 }, line: { color: C.accent5, width: 1, dashType: "dash" } });
    s.addImage({ data: I.eye, x: 0.85, y: 5.08, w: 0.4, h: 0.4 });
    T(s, [{ text: "Wazuh", options: { bold: true, color: C.text2 } }, { text: "  파일 변조 감시 → 자동 복구(S7)", options: { color: C.accent5 } }],
      { x: 1.4, y: 4.9, w: 4.8, h: 0.75, valign: "middle", fontSize: 14 });
    T(s, "실습 환경 구성 · 실제 운영망과 연결하지 않음", { x: 0.6, y: 6.2, w: 8, h: 0.3, fontSize: 11, color: C.accent5 });
    s.addNotes("민원 포털 → Graylog → n8n → 포털·pfSense → 티켓 대시보드·Discord. 포털은 로그인뿐 아니라 민원 등록·조회·처리 변경도 이벤트로 남긴다(H1~H4). S7만 경로가 달라 Wazuh FIM → Graylog → n8n → Wazuh Active Response로 기준본을 되돌린다. 실습 환경임을 밝힌다.");
  }

  // ---------- 4. cases ----------
  {
    pres.addSection({ title: "검증" });
    const s = page("LIGHT", "검증", "04  COVERAGE", "검증한 시나리오", "가용성·기밀성·무결성·인증 공격 10종을 실제 실행기와 티켓으로 확인했다");
    const rows = [
      ["S10", "경계 신호·스캔·로그인", "pfSense와 포털 차단"],
      ["S8", "포털 스캔·로그인 실패", "포털 차단"],
      ["S1", "로그인 무차별 대입", "포털 차단과 원복"],
      ["S4", "실패 뒤 성공 로그인", "계정 잠금·세션 회수"],
      ["S12", "요청 폭주", "요청 수 기준 포털 차단"],
      ["S7", "홈페이지 변조", "Wazuh 자동 복구"],
      ["H1", "민원 반복 등록", "작성 제한과 원복"],
      ["H2", "타인 민원 반복 조회", "IP 차단·계정 잠금"],
      ["H3", "민원 처리 결과 조작", "잠금·스냅샷 복원"],
      ["H4", "담당자 대량 조회", "담당자 잠금·세션 회수"],
    ];
    const W = 2.25, G = 0.22;
    rows.forEach(([id, scen, resp], i) => {
      const x = 0.6 + (i % 5) * (W + G), y = 2.1 + Math.floor(i / 5) * 2.05;
      box(s, { x, y, w: W, h: 1.8, fill: { color: C.background1 }, line: { color: C.accent6, width: 1 }, shadow: shadow() });
      T(s, id, { x: x + 0.22, y: y + 0.2, w: 1.1, h: 0.5, fontSize: 24, bold: true, color: C.text2, fontFace: MONO, valign: "middle" });
      box(s, { x: x + W - 0.9, y: y + 0.27, w: 0.68, h: 0.34, rectRadius: 0.17, fill: { color: C.accent2, transparency: 85 } });
      T(s, "완료", { x: x + W - 0.9, y: y + 0.27, w: 0.68, h: 0.34, align: "center", valign: "middle", fontSize: 10, bold: true, color: C.accent2 });
      T(s, scen, { x: x + 0.22, y: y + 0.88, w: W - 0.35, h: 0.36, fontSize: 13, bold: true, color: C.text1 });
      T(s, resp, { x: x + 0.22, y: y + 1.26, w: W - 0.35, h: 0.32, fontSize: 11, color: C.accent5 });
    });
    T(s, "S = 외부 공격(인증·가용성·변조)  ·  H = 민원 업무 악용(시민·담당자)  ·  10종 모두 수정 후 31/31, 기준선 오탐 0/11",
      { x: 0.6, y: 6.3, w: 12.1, h: 0.3, fontSize: 11, color: C.accent5 });
    s.addNotes("10종 모두 수정 후 실측 3회 이상과 기준선까지 완료해 정량평가에 반영했다. 8종은 Graylog→n8n→포털/pfSense, S7은 Wazuh FIM→Active Response, H4는 담당자 조회 건수→계정 잠금. raw 명령·스크립트·제어판 세 진입점으로도 같은 결과를 확인했다(11장).");
  }

  // ---------- 5. H2 detect ----------
  {
    const s = page("LIGHT", "검증", "05  H2", "타인 민원 반복 조회 탐지", "기밀성 침해 시도를 계정과 출발지 IP 조합으로 묶어 판단한다");
    const steps = [["403 반복", "타인 민원 상세 3건 이상", I.lock, C.accent1], ["Graylog 경보", "5분 창, count() > 2", I.bell, C.accent1],
      ["자동 대응", "IP 차단·계정 잠금", I.ban, C.accent1], ["원복 확인", "계정 정상·권한 유지", I.undo, C.accent2]];
    s.addShape(S.LINE, { x: 1.9, y: 2.75, w: 9.3, h: 0, line: { color: C.accent6, width: 2 } });
    steps.forEach(([t, d, ic, col], i) => {
      const cx = 1.9 + i * 3.1;
      iconTile(s, ic, cx - 0.4, 2.35, 0.8, col);
      T(s, `0${i + 1}  ${t}`, { x: cx - 1.4, y: 3.35, w: 2.8, h: 0.42, align: "center", fontSize: 18, bold: true, color: C.text2 });
      T(s, d, { x: cx - 1.4, y: 3.8, w: 2.8, h: 0.4, align: "center", fontSize: 13, color: C.accent5 });
    });
    box(s, { x: 0.6, y: 4.75, w: 12.13, h: 1.75, fill: { color: C.text2 } });
    T(s, "GRAYLOG 이벤트 조건", { x: 1.0, y: 5.0, w: 4, h: 0.3, fontSize: 11, bold: true, color: C.accent5, charSpacing: 2 });
    T(s, "count() > 2", { x: 1.0, y: 5.32, w: 4.5, h: 0.65, fontSize: 34, bold: true, color: C.accent1, fontFace: MONO });
    T(s, "5분 창 · 계정 + 출발지 IP 기준", { x: 1.0, y: 6.0, w: 5, h: 0.32, fontSize: 13, color: C.accent6 });
    [["공격 출발지", "203.0.113.11"], ["H2 티켓", "T-20261111-0009"]].forEach(([k, v], i) => {
      const y = 5.12 + i * 0.6;
      T(s, k, { x: 7.0, y, w: 1.5, h: 0.42, valign: "middle", fontSize: 13, color: C.accent6 });
      chip(s, v, 8.6, y, 3.7, { fill: C.background1, t: 88, color: C.background1, mono: true, size: 15, bold: true });
    });
    s.addNotes("Graylog 경보 캡처(h2-2-graylog-alerts-0009.png)를 띄워 count()=4.0, 그룹 키, H2 이벤트 정의를 짚는다. 이 회차는 출발지를 케이스별로 나누기 전이라 .11이다(지금 H2는 .15).");
  }

  // ---------- 6. evidence ----------
  {
    const s = page("LIGHT", "검증", "06  EVIDENCE", "탐지부터 원복까지의 증적", "H2는 Graylog·n8n·Discord에 같은 티켓 ID로 남는다");
    box(s, { x: 0.6, y: 2.15, w: 4.95, h: 4.45, fill: { color: C.text2 } });
    T(s, "INCIDENT TICKET", { x: 0.95, y: 2.5, w: 4, h: 0.3, fontSize: 11, bold: true, color: C.accent1, charSpacing: 3 });
    T(s, "T-20261111-0009", { x: 0.95, y: 2.85, w: 4.4, h: 0.6, fontSize: 28, bold: true, color: C.background1, fontFace: MONO });
    T(s, "같은 티켓 ID로 세 시스템에 기록된다", { x: 0.95, y: 3.5, w: 4.3, h: 0.35, fontSize: 14, color: C.accent6 });
    chip(s, "계정 잠금·IP 차단", 0.95, 4.5, 2.0, { fill: C.accent1, t: 0, color: C.background1, bold: true, size: 12 });
    arrow(s, 3.02, 4.71, 3.35, C.accent5);
    chip(s, "복원 완료", 3.42, 4.5, 1.8, { fill: C.accent2, t: 0, color: C.background1, bold: true, size: 12 });
    T(s, "Discord 카드가 차단에서 복원까지", { x: 0.95, y: 5.25, w: 4.3, h: 0.32, fontSize: 13, color: C.accent6 });
    T(s, "같은 티켓으로 이어진다", { x: 0.95, y: 5.57, w: 4.3, h: 0.32, fontSize: 13, color: C.accent6 });
    const ev = [["Graylog", I.search, C.accent1, "H2 반복 조회 경보", "그룹 키: 계정 + 203.0.113.11  ·  count()=4.0"],
      ["n8n", I.cogs, C.text2, "포털 IP 차단·계정 잠금", "결과 기록·복원 워크플로 모두 Success"],
      ["Discord", I.discord, C.accent3, "T-20261111-0009", "계정 잠금·IP 차단, 이어서 복원 완료"]];
    ev.forEach(([name, ic, col, head, body], i) => {
      const y = 2.15 + i * 1.55;
      box(s, { x: 5.9, y, w: 6.83, h: 1.35, fill: { color: C.background1 }, line: { color: C.accent6, width: 1 }, shadow: shadow() });
      iconTile(s, ic, 6.2, y + 0.33, 0.7, col, 0, "square");
      T(s, name, { x: 7.15, y: y + 0.22, w: 1.6, h: 0.4, fontSize: 13, bold: true, color: C.accent5 });
      T(s, head, { x: 7.15, y: y + 0.52, w: 5.3, h: 0.4, fontSize: 17, bold: true, color: C.text2, fontFace: head.startsWith("T-") ? MONO : undefined });
      T(s, body, { x: 7.15, y: y + 0.9, w: 5.4, h: 0.35, fontSize: 13, color: C.accent5 });
    });
    s.addNotes("발표 시 H2 Discord·Graylog·n8n 원본 캡처 3장을 순서대로 보여준다(h2-1-discord-ticket-0009, h2-2-graylog-alerts-0009, h2-3-n8n-executions-0009). 원본 캡처를 확보하면 오른쪽 카드 자리에 교체한다.");
  }

  // ---------- 7. results ----------
  {
    const s = page("LIGHT", "검증", "07  RESULTS", "수정 후 실측 결과", "10종(S10·S8·S1·S4·S7·S12·H1~H4) 수정 후 31회를 집계했다");
    const stats = [["31/31", "자동 대응", "수정 후 모든 실측 회차 성공", C.text2], ["31/31", "원복", "조치 후 정상 기능 복구", C.text2],
      ["0회", "정상 사용자 영향", "대응 중 normal 요청 확인", C.accent2], ["0/11", "기준선 오탐", "각 케이스 정상 입력", C.accent2]];
    stats.forEach(([v, l, n, col], i) => {
      const x = 0.6 + i * 3.09;
      box(s, { x, y: 2.15, w: 2.85, h: 2.3, fill: { color: C.background2 } });
      T(s, v, { x: x + 0.3, y: 2.4, w: 2.4, h: 0.9, fontSize: 44, bold: true, color: col });
      T(s, l, { x: x + 0.3, y: 3.38, w: 2.4, h: 0.4, fontSize: 16, bold: true, color: C.text2 });
      T(s, n, { x: x + 0.3, y: 3.8, w: 2.4, h: 0.4, fontSize: 12, color: C.accent5 });
    });
    box(s, { x: 0.6, y: 4.75, w: 12.13, h: 1.75, fill: { color: C.text2 } });
    iconTile(s, I.chart, 1.0, 5.25, 0.75, C.accent1);
    T(s, "입력부터 차단까지 중앙값", { x: 2.0, y: 5.08, w: 4, h: 0.35, fontSize: 14, color: C.accent6 });
    T(s, "33.65초", { x: 2.0, y: 5.42, w: 4, h: 0.85, fontSize: 40, bold: true, color: C.background1 });
    s.addShape(S.LINE, { x: 7.2, y: 5.1, w: 0, h: 1.05, line: { color: C.accent5, width: 1 } });
    T(s, "MTTD 중앙값", { x: 7.6, y: 5.08, w: 4, h: 0.35, fontSize: 14, color: C.accent6 });
    T(s, "0.58초", { x: 7.6, y: 5.42, w: 2.4, h: 0.85, fontSize: 32, bold: true, color: C.accent1 });
    T(s, "Graylog 내부 처리 기준", { x: 9.9, y: 5.62, w: 2.6, h: 0.4, fontSize: 12, color: C.accent6 });
    s.addNotes("정량평가 표를 간결하게 재구성한 값. 10종 31회, 기준선 11회에서 오탐 없음. MTTD 0.58초는 Graylog 내부 처리 기준이고, 체감 지연은 입력→차단 중앙값 33.65초(1분 평가 주기 포함)로 설명한다. 수정 전 실패 회차는 정량평가 문서에 원인과 함께 따로 둔다.");
  }

  // ---------- 8. H2 validation ----------
  {
    const s = page("LIGHT", "검증", "08  H2", "H2 검증 결과", "차단 뒤에도 타인 민원 권한은 계속 거부되는지 확인했다");
    verdict(s, [["3/3", "자동 대응"], ["3/3", "원복"], ["0/1", "기준선 오탐"], ["46.907초", "입력→차단 중앙값"]], "원복 후 확인",
      [["200", "공격 계정 로그인", "복구", C.accent2], ["403", "타인 민원 상세 조회", "거부 유지", C.accent1], ["403", "미인증 해제 요청", "거부 유지", C.accent1]],
      "계정은 복구하되, 타인 민원 접근 권한은 복구하지 않는다.");
    s.addNotes("계정 원복과 권한 우회는 다르다. 원복 뒤에도 타인 민원 조회는 403으로 막혀 권한 경계가 유지됐다.");
  }

  // ---------- 9. S7 ----------
  {
    const s = page("LIGHT", "검증", "09  S7", "S7 홈페이지 변조 검증", "Wazuh FIM이 잡은 변조를 n8n이 Active Response로 기준본에 되돌렸다");
    verdict(s, [["3/3", "자동 복구"], ["3/3", "기준 해시 일치"], ["0/1", "기준선 오탐"], ["43.256초", "입력→복구 중앙값"]], "복구 후 확인",
      [["200", "포털 첫 화면", "정상 서비스", C.accent2], ["403", "키 없는 대응 웹훅", "인증 필요", C.accent1], ["거부", "웹 루트 밖 복구 요청", "범위 밖 경로 차단", C.accent1]],
      "같은 내용 재배포는 거르고, 바뀐 해시만 사람 손 없이 되돌린다.");
    s.addNotes("S7은 포털 컨테이너 안 Wazuh Agent가 /app/dist를 감시한다. 기준 파일 끝에 주석 한 줄(화면 영향 없음)을 붙이면 FIM 규칙 550 → Graylog가 기준 해시 표에 없는 해시만 신호로 → n8n haedam-33이 티켓을 만들고 Wazuh API로 복구 명령 → 에이전트가 기준본으로 되돌린다. 3회(favicon·CSS·JS) 모두 브라우저가 받는 파일이 기준 해시와 같아졌다. 같은 내용 재배포(기준선)는 Wazuh 경보가 나도 티켓이 없었다. 웹 루트 밖 경로 복구 요청은 path_outside_web_root로 거부된다. Discord 수신은 웹훅 미설정으로 확인하지 못했다고 솔직히 말한다.");
  }

  // ---------- 10. H4 ----------
  {
    const s = page("LIGHT", "검증", "10  H4", "H4 담당자 대량 조회 검증", "권한 안의 과도한 조회를 건수로 잡아 담당자 계정을 잠갔다");
    verdict(s, [["3/3", "자동 잠금"], ["3/3", "원복"], ["0/1", "기준선 오탐"], ["23.762초", "입력→잠금 중앙값"]], "잠금 중 확인",
      [["200", "시민 자기 민원", "정상 서비스", C.accent2], ["401", "잠긴 담당자 새 로그인", "거부", C.accent1], ["401", "쥐고 있던 세션", "세션 회수", C.accent1]],
      "권한이 있어도 비정상적인 양이면 멈추고, 판단은 관리자가 한다.");
    s.addNotes("H4는 내부자 시나리오다. 담당자는 민원을 볼 권한이 있어 403 같은 거부 신호가 없다. 그래서 담당자의 민원 상세 조회가 10분에 20건을 넘으면 n8n(haedam-38)이 계정을 잠그고 세션을 회수한다. 기준선(상세 조회 8건)은 티켓이 없었다. 3회 모두 새 로그인·쥐고 있던 세션 401, 시민 200, 관리자 해제 뒤 200·티켓 restored. 첫 회차는 잠금은 됐지만 티켓 기록이 멱등키 길이(7자)로 거부됐다. 새 n8n에서 실행 번호가 작아 생긴 버그로 H3도 같이 고쳤다. 설계 초안의 역할 강등 대신 검증된 계정 잠금을 썼고, 강등은 후속이다. Discord 수신은 미검증.");
  }

  // ---------- 11. reproduction ----------
  {
    const s = page("LIGHT", "검증", "11  REPRODUCTION", "세 진입점 독립 재현", "제어판 전용 시연이 아니라 같은 방어 경로가 도는지 확인했다");
    verdict(s, [["10/10", "① raw 명령"], ["10/10", "② 스크립트"], ["10/10", "③ 제어판"], ["0/11", "기준선 오탐"]], "raw 재현 예시",
      [["S4", "T-20261111-0041", "401×5 + 성공 → 잠금", C.accent3], ["H2", "T-20261111-0042", "403×3 → 차단+잠금", C.accent3], ["S7", "T-20261111-0007", "파일 변조 → 자동 복구", C.accent3]],
      "제어판은 ②에 UI만 씌운 것. 가장 강한 증거는 ① raw 재현이다.");
    s.addNotes("리뷰어 지적: 제어판에서만 되면 실제 방어인지 알 수 없다. 그래서 같은 케이스를 ① 프로젝트 코드 없는 raw curl·docker exec, ② 실행 스크립트, ③ 제어판으로 각각 공격했고 10종 모두 같은 탐지→대응→원복이 돌았다. 제어판은 ②와 같은 요청을 보내므로 ①이 가장 강한 증거다. 티켓 번호는 검증 체크리스트에 있다.");
  }

  // ---------- 12. contribution ----------
  {
    pres.addSection({ title: "정리" });
    const s = page("LIGHT", "정리", "12  CONTRIBUTION", "담당 기여와 해결한 문제", "포털 대응 API와 이벤트 경로를 실측 가능한 시나리오로 연결했다");
    T(s, "담당 영역", { x: 0.6, y: 2.15, w: 4, h: 0.4, fontSize: 16, bold: true, color: C.text2 });
    [["포털 대응 API", I.code], ["GELF TCP 로그 경로", I.stream], ["S1·S4 대응 흐름", I.flow], ["H1~H4·S12·S7 실측 연결", I.flask]].forEach(([t, ic], i) => {
      const y = 2.7 + i * 0.95;
      iconTile(s, ic, 0.6, y, 0.65, C.text2, 0, "square");
      T(s, t, { x: 1.45, y, w: 3.8, h: 0.65, valign: "middle", fontSize: 17, color: C.text1 });
    });
    box(s, { x: 5.55, y: 2.15, w: 7.18, h: 4.45, fill: { color: C.background2 } });
    T(s, "실측하며 찾아 고친 문제", { x: 5.9, y: 2.38, w: 6.5, h: 0.4, fontSize: 16, bold: true, color: C.text2 });
    [["H1", "티켓 저장소 허용 목록 누락 → 기록 400 거부", C.accent1],
      ["H3", "민원 3건 중 1건만 복원되던 문제", C.accent1],
      ["H3·H4", "멱등키 길이(7자) 버그 → 티켓 기록 거부", C.accent1],
      ["H2", "제어판 해제가 잠긴 계정에서 멈추던 문제", C.accent3],
      ["S12", "health 기준 → 요청 수 기준으로 전환", C.accent3],
      ["S7", "제어판을 실제 자동 복구 경로로 교체", C.accent3]].forEach(([k, v, col], i) => {
      const y = 2.95 + i * 0.6;
      box(s, { x: 5.9, y, w: 1.05, h: 0.4, rectRadius: 0.2, fill: { color: col } });
      T(s, k, { x: 5.9, y, w: 1.05, h: 0.4, align: "center", valign: "middle", fontSize: 12, bold: true, color: C.background1, fontFace: MONO });
      T(s, v, { x: 7.15, y: y - 0.05, w: 5.4, h: 0.5, valign: "middle", fontSize: 14, color: C.text1 });
    });
    s.addNotes("본인이 직접 확인·수정한 것만 말한다. 위 세 줄(주황)은 대응은 됐지만 기록·복원이 틀어지던 결함, 아래 세 줄(파랑)은 실습 도구·탐지 기준을 실제 경로에 맞춘 것. 가장 이야기하기 좋은 사례는 H1: 탐지와 n8n 호출은 성공했는데 티켓 저장소 허용 목록에 H1이 없어 기록이 400으로 거부됐고, 목록을 보완한 뒤 수정 후 실측 3/3. H4 첫 회차의 멱등키 버그는 새 n8n에서 실행 번호가 작아 키가 7자가 된 것으로, H3도 같이 고쳤다.");
  }

  // ---------- 13. limits ----------
  {
    const s = page("DARK", "정리", "13  NEXT", "한계와 다음 단계", "현재 결과의 범위와 남은 검증을 구분한다");
    const col = (x, head, ic, color, items) => {
      box(s, { x, y: 2.15, w: 5.9, h: 3.0, fill: { color: C.background1, transparency: 93 } });
      iconTile(s, ic, x + 0.35, 2.45, 0.6, color);
      T(s, head, { x: x + 1.15, y: 2.53, w: 4, h: 0.45, fontSize: 19, bold: true, color: C.background1 });
      T(s, items.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < items.length - 1 } })),
        { x: x + 0.35, y: 3.3, w: 5.3, h: 2.1, fontSize: 15, color: C.accent6, paraSpaceAfter: 8 });
    };
    col(0.6, "현재 한계", I.warn, C.accent4, ["케이스별 실측은 3~5회라 경향만 판단할 수 있다", "한 PC Docker 환경이라 다중 PC 지연과 같지 않다",
      "S7·H4 Discord 수신은 웹훅 미설정으로 미검증"]);
    col(6.83, "다음 검증", I.flask, C.accent2, ["Discord 웹훅 설정 뒤 S7·H4 알림 확인", "H4 역할 강등 API(지금은 계정 잠금)",
      "세 진입점 재현 화면 증적 보강", "다중 PC 환경에서 재측정"]);
    T(s, "실습 검증 결과와 한계를 함께 제시해 재현 가능한 발표 자료로 마무리한다.", { x: 0.6, y: 5.6, w: 12, h: 0.5, fontSize: 18, bold: true, color: C.background1 });
    s.addNotes("과장 없이 실제 남은 범위를 말한다. 표본은 케이스별 3~5회, 한 PC Docker 환경. S7·H4 Discord 수신은 웹훅을 설정한 뒤 확인한다. H4는 설계 초안의 역할 강등 대신 계정 잠금을 썼고, 강등 API와 근무 외 가중치는 후속. 저장소·시연 URL은 발표 환경에서 입력한다.");
  }


  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log(OUT);
}

build().catch((e) => { console.error(e); process.exit(1); });
