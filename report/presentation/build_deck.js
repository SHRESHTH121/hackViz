// Builds hackViz_EST_presentation.pptx (10 slides) from the report figures.
// Run: node build_deck.js
const pptxgen = require("pptxgenjs");
const path = require("path");
const { applyTheme } = require(
  "C:/Users/admin/.claude/skills/synced/34eb69d6-a609-47e7-956f-2deabda86400_cfba0e6e-3c4d-43b9-afde-e84241673c92/pptx/scripts/apply_theme.js");

const FIG = (n) => path.join(__dirname, "..", "figures", n);
const OUT = path.join(__dirname, process.env.DECK_NAME || "hackViz_EST_presentation.pptx");

const THEME = {
  name: "hackViz Slate",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1C2331", lt1: "FFFFFF", dk2: "3A475C", lt2: "EEF1F5",
    accent1: "E8A33D", accent2: "3E7C87", accent3: "C0504D", accent4: "6B7A8F",
    accent5: "9FB4C7", accent6: "F4D58D", hlink: "3E7C87", folHlink: "6B7A8F",
  },
};
const HEX = THEME.colors;

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9"; // 10 x 5.625 in
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "hackViz: Explainable Insider-Threat Detection";
pres.author = "Shreshth Garg, Geetansh Bansal, Lakshit Goyal";
const C = pres.SchemeColor;

// ------------------------------------------------------------------ layouts
pres.defineSlideMaster({
  title: "TITLE_DARK",
  background: { color: C.text1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 1.25, w: 5.2, h: 1.1,
      fontSize: 44, bold: true, color: C.background1, valign: "bottom", align: "left", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.5, y: 2.45, w: 5.2, h: 0.9,
      fontSize: 18, color: C.accent1, valign: "top", margin: 0 }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: C.background1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.28, w: 9.0, h: 0.62,
      fontSize: 28, bold: true, color: C.text1, valign: "middle", align: "left", margin: 0 }, text: "" } },
    { text: { text: "hackViz  |  UCS503 End-Semester Evaluation", options: {
      x: 0.5, y: 5.22, w: 6, h: 0.25, fontSize: 10, color: C.accent4, margin: 0 } } },
  ],
  slideNumber: { x: 9.1, y: 5.22, w: 0.4, h: 0.25, fontSize: 10, color: C.accent4, align: "right" },
});
pres.defineSlideMaster({
  title: "CLOSING_DARK",
  background: { color: C.text1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.35, w: 9.0, h: 0.7,
      fontSize: 32, bold: true, color: C.background1, valign: "middle", align: "left", margin: 0 }, text: "" } },
  ],
  slideNumber: { x: 9.1, y: 5.22, w: 0.4, h: 0.25, fontSize: 10, color: C.accent5, align: "right" },
});

// ------------------------------------------------------------------ helpers
function numCircle(slide, n, x, y, d = 0.42) {
  slide.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: C.accent1 }, line: { color: C.accent1 },
    objectName: `Step ${n} marker` });
  slide.addText(String(n), { x, y, w: d, h: d, fontSize: 15, bold: true, color: C.text1, align: "center",
    valign: "middle", margin: 0, isTextBox: true });
}
function caption(slide, text, x, y, w) {
  slide.addText(text, { x, y, w, h: 0.28, fontSize: 11, italic: true, color: C.text2, align: "center",
    margin: 0, isTextBox: true });
}
function jpegSize(file) {
  const b = require("fs").readFileSync(file);
  let i = 2;
  while (i < b.length) {
    if (b[i] !== 0xff) { i++; continue; }
    const m = b[i + 1], L = b.readUInt16BE(i + 2);
    if (m >= 0xc0 && m <= 0xc3) return [b.readUInt16BE(i + 7), b.readUInt16BE(i + 5)];
    i += 2 + L;
  }
  throw new Error("no JPEG size in " + file);
}
function fitImage(slide, file, _pw, _ph, box, name) {
  // place the image inside box {x,y,w,h}, centred, aspect ratio read from the file itself
  const [pw, ph] = jpegSize(FIG(file));
  const r = Math.min(box.w / pw, box.h / ph);
  const w = pw * r, h = ph * r;
  slide.addImage({ path: FIG(file), x: box.x + (box.w - w) / 2, y: box.y + (box.h - h) / 2, w, h,
    altText: name, objectName: name });
  return { x: box.x + (box.w - w) / 2, y: box.y + (box.h - h) / 2, w, h };
}

// ================================================================== 1. Title
pres.addSection({ title: "Introduction" });
let s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Introduction" });
s.addText("hackViz", { placeholder: "title" });
s.addText("Explainable insider-threat detection with a local Transformer model", { placeholder: "body" });
s.addText([
  { text: "UCS503 Software Engineering Lab  ·  End-Semester Evaluation  ·  Group 3C25", options: { breakLine: true, bold: true } },
  { text: "Shreshth Garg (1024030380)", options: { breakLine: true } },
  { text: "Geetansh Bansal (1024030954)", options: { breakLine: true } },
  { text: "Lakshit Goyal (1024030383)", options: { breakLine: true } },
  { text: "Submitted to Dr. Stuti Chug  ·  CSED, TIET Patiala  ·  November 2026" },
], { x: 0.5, y: 3.55, w: 5.3, h: 1.6, fontSize: 12, color: C.accent5, valign: "top", margin: 0,
  paraSpaceAfter: 4, isTextBox: true });
fitImage(s, "ui_dashboard.jpg", 1400, 1505, { x: 5.9, y: 0.5, w: 3.6, h: 4.6 }, "hackViz dashboard screenshot");
s.addNotes("Introduce the team and the one-line idea: hackViz finds unusual employee activity and explains every alert with records an analyst can check.");

// ================================================================== 2. Problem and approach
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Introduction" });
s.addText("Insider threats hide inside normal work", { placeholder: "title" });
const probs = [
  ["Legitimate access", "Insiders use their own credentials and tools, so single actions look normal."],
  ["Too many false alarms", "Rule-based SIEM thresholds flag routine work and miss new patterns."],
  ["Scores without reasons", "ML detectors give an anomaly score but not why the activity is unusual."],
];
s.addText("The problem", { x: 0.5, y: 1.1, w: 4.3, h: 0.35, fontSize: 18, bold: true, color: C.accent3, margin: 0, isTextBox: true });
probs.forEach(([h, d], i) => {
  const y = 1.6 + i * 1.12;
  numCircle(s, i + 1, 0.5, y);
  s.addText([{ text: h, options: { bold: true, fontSize: 15, breakLine: true } },
             { text: d, options: { fontSize: 14 } }],
    { x: 1.1, y: y - 0.06, w: 3.7, h: 0.95, color: C.text1, valign: "top", margin: 0, isTextBox: true });
});
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 5.2, y: 1.1, w: 4.3, h: 3.85, rectRadius: 0.08,
  fill: { color: C.background2 }, line: { color: C.background2 }, objectName: "Approach card" });
s.addText("Our approach", { x: 5.45, y: 1.25, w: 3.8, h: 0.35, fontSize: 18, bold: true, color: C.accent2, margin: 0, isTextBox: true });
s.addText([
  { text: "Collect browser activity with consent (metadata only)", options: { bullet: true, breakLine: true } },
  { text: "Give a local LLM the employee's role, baseline and recent events", options: { bullet: true, breakLine: true } },
  { text: "Get back a risk level, a reason and the IDs of supporting records", options: { bullet: true, breakLine: true } },
  { text: "Verify every cited record before the alert is shown", options: { bullet: true, breakLine: true } },
  { text: "Runs on one laptop CPU; no data leaves the machine", options: { bullet: true } },
], { x: 5.45, y: 1.72, w: 3.85, h: 3.1, fontSize: 14, color: C.text1, valign: "top", paraSpaceAfter: 8, margin: 0, isTextBox: true });
s.addNotes("Context matters more than single actions. Our answer is an explainable assessment whose evidence is checked against the database.");

// ================================================================== 3. Use case diagram
pres.addSection({ title: "Analysis" });
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Analysis" });
s.addText("Use case diagram", { placeholder: "title" });
fitImage(s, "uc_diagram.jpg", 0, 0, { x: 0.5, y: 0.95, w: 4.6, h: 4.15 }, "Use case diagram");
const ucPts = [
  ["Primary actors", "Employee and Security Analyst use the main functions."],
  ["Secondary actors", "Administrator; LLM (Qwen2.5); Transformer decoder (planned, dashed)."],
  ["<<includes>> / <<extends>>", "Analyze Now includes Assess Activity; Export CSV and Score with Transformer decoder are extensions."],
];
ucPts.forEach(([h, d], i) => {
  const y = 1.15 + i * 1.3;
  numCircle(s, i + 1, 5.45, y);
  s.addText([{ text: h, options: { bold: true, fontSize: 15, breakLine: true } }, { text: d, options: { fontSize: 14 } }],
    { x: 6.0, y: y - 0.06, w: 3.5, h: 1.15, color: C.text1, valign: "top", margin: 0, isTextBox: true });
});
s.addNotes("Primary actors on the left, the other system on the right, all use cases inside the system boundary.");

// ================================================================== 4. Activity + swimlane
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Analysis" });
s.addText("Activity and swimlane diagrams", { placeholder: "title" });
let b1 = { x: 0.5, y: 0.95, w: 3.6, h: 3.95 }, b2 = { x: 4.4, y: 0.95, w: 5.1, h: 3.95 };
fitImage(s, "activity_diagram.jpg", 0, 0, b1, "Activity diagram");
fitImage(s, "swimlane_diagram.jpg", 0, 0, b2, "Swimlane diagram");
caption(s, "Activity: LLM step, Transformer decoder step (dashed)", b1.x, 4.95, b1.w);
caption(s, "Swimlane: who performs each action", b2.x, 4.95, b2.w);
s.addNotes("Guards in square brackets, loops re-enter through merge diamonds, fork/join saves the alert and cursor together.");

// ================================================================== 5. DFD level 0 + 1
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Analysis" });
s.addText("Data flow diagrams: level 0 and level 1", { placeholder: "title" });
b1 = { x: 0.5, y: 1.0, w: 3.5, h: 3.8 }; b2 = { x: 4.2, y: 1.0, w: 5.3, h: 3.8 };
fitImage(s, "dfd_level0.jpg", 0, 0, b1, "DFD level 0");
fitImage(s, "dfd_level1.jpg", 0, 0, b2, "DFD level 1");
caption(s, "Level 0: context diagram", b1.x, 4.9, b1.w);
caption(s, "Level 1: LLM entity, Transformer decoder process 6.0", b2.x, 4.9, b2.w);
s.addNotes("Processes are circles, entities rectangles, data stores two parallel lines. Level 1 keeps exactly the inputs and outputs of the context diagram.");

// ================================================================== 6. DFD level 2
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Analysis" });
s.addText("Data flow diagram: level 2 of process 4.0", { placeholder: "title" });
fitImage(s, "dfd_level2.jpg", 0, 0, { x: 0.5, y: 1.0, w: 5.6, h: 3.9 }, "DFD level 2");
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 6.4, y: 1.15, w: 3.1, h: 3.7, rectRadius: 0.08,
  fill: { color: C.background2 }, line: { color: C.background2 }, objectName: "Balancing card" });
s.addText([
  { text: "Balanced DFDs", options: { bold: true, fontSize: 16, color: C.accent2, breakLine: true } },
  { text: "Level 0 inputs: activity, employee details, Analyze Now request", options: { bullet: true, breakLine: true } },
  { text: "Level 1 keeps the same inputs and outputs", options: { bullet: true, breakLine: true } },
  { text: "Level 2 keeps the flows of 4.0: behaviour context and assessment JSON in, prompt and verified assessment out", options: { bullet: true } },
], { x: 6.6, y: 1.3, w: 2.75, h: 3.45, fontSize: 13, color: C.text1, valign: "top", paraSpaceAfter: 6, margin: 0, isTextBox: true });
s.addNotes("Process 4.0 is decomposed into compose prompt, parse response, verify evidence and save assessment.");

// ================================================================== 7. User stories and story cards
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Analysis" });
s.addText("User stories and story cards", { placeholder: "title" });
const cards = [
  ["US-01", "High · 3 pts", "As a Security Analyst, I want a ranked list of suspicious activity so that I can prioritise triage.", "Partial"],
  ["US-02", "High · 5 pts", "As a Security Analyst, I want to see why an alert was raised so that I can judge the risk.", "Implemented"],
  ["US-03", "High · 2 pts", "As a Security Analyst, I want to open the record behind any evidence ID so that I can verify it.", "Implemented"],
  ["US-04", "High · 3 pts", "As an Employee, I want to know what is collected and to stop it so that my privacy is respected.", "Implemented"],
  ["US-06", "Medium · 2 pts", "As an Administrator, I want to add employees from the dashboard so that they are monitored at once.", "Implemented"],
  ["US-07", "High · 2 pts", "As a Security Analyst, I want to confirm or dismiss an alert so that my decision is recorded.", "Not implemented"],
];
cards.forEach(([id, pr, story, st], i) => {
  const x = 0.5 + (i % 3) * 3.05, y = 1.0 + Math.floor(i / 3) * 2.05;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 2.85, h: 1.9, rectRadius: 0.06,
    fill: { color: C.background2 }, line: { color: C.background2 }, objectName: `Story card ${id}` });
  s.addText([{ text: id, options: { bold: true, color: C.accent2 } }, { text: "   " + pr, options: { color: C.text2 } }],
    { x: x + 0.15, y: y + 0.1, w: 2.55, h: 0.3, fontSize: 12, margin: 0, isTextBox: true });
  s.addText(story, { x: x + 0.15, y: y + 0.45, w: 2.55, h: 1.05, fontSize: 12, color: C.text1, valign: "top", margin: 0, isTextBox: true });
  s.addText("Status: " + st, { x: x + 0.15, y: y + 1.5, w: 2.55, h: 0.3, fontSize: 11, bold: true, color: C.text2, margin: 0, isTextBox: true });
});
s.addNotes("Each card has the story, priority, story points and status; the report lists all eight cards with acceptance criteria.");

// ================================================================== 8. Class diagrams
pres.addSection({ title: "Design" });
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Design" });
s.addText("Class diagrams", { placeholder: "title" });
b1 = { x: 0.5, y: 1.0, w: 4.4, h: 3.85 }; b2 = { x: 5.1, y: 1.0, w: 4.4, h: 3.85 };
fitImage(s, "class_domain.jpg", 0, 0, b1, "Domain class diagram");
fitImage(s, "class_analysis.jpg", 0, 0, b2, "Analysis class diagram");
caption(s, "Domain classes: composition and association", b1.x, 4.9, b1.w);
caption(s, "LLM and Transformer decoder inherit AnomalyModel", b2.x, 4.9, b2.w);
s.addNotes("Employee is composed of its records; the worker runs the analyzer, which uses the Ollama client; errors inherit from OllamaError.");

// ================================================================== 9. Sequence diagrams
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Design" });
s.addText("Sequence diagrams", { placeholder: "title" });
fitImage(s, "sequence_diagram.jpg", 0, 0, b1, "Pairing sequence diagram");
fitImage(s, "sequence_analyze.jpg", 0, 0, b2, "Analyze Now sequence diagram");
caption(s, "Pairing and sending activity", b1.x, 4.9, b1.w);
caption(s, "Analyze Now: Transformer decoder and LLM", b2.x, 4.9, b2.w);
s.addNotes("Solid arrows are requests, dashed arrows are replies.");

// ================================================================== 10. Results and conclusion
pres.addSection({ title: "Results" });
s = pres.addSlide({ masterName: "CLOSING_DARK", sectionTitle: "Results" });
s.addText("Results and conclusion", { placeholder: "title" });
const big = [["54 / 54", "automated tests pass"], ["26 / 26", "end-to-end steps in Chrome"],
             ["100%", "cited evidence verified"], ["61–134 s", "per analysis on CPU"]];
big.forEach(([v, l], i) => {
  const x = 0.5 + i * 2.3;
  s.addText(v, { x, y: 1.2, w: 2.1, h: 0.6, fontSize: 28, bold: true, color: C.accent1, fontFace: THEME.headFontFace,
    margin: 0, isTextBox: true });
  s.addText(l, { x, y: 1.8, w: 2.1, h: 0.35, fontSize: 12, color: C.accent5, margin: 0, isTextBox: true });
});
s.addText([
  { text: "A local Transformer model gives role-aware alerts whose evidence is checked against real records", options: { bullet: true, breakLine: true } },
  { text: "Next: Transformer decoder, labelled evaluation (precision, recall, F1), login and analyst feedback", options: { bullet: true } },
], { x: 0.5, y: 2.5, w: 9.0, h: 1.5, fontSize: 15, color: C.background1, valign: "top", paraSpaceAfter: 10, margin: 0, isTextBox: true });
s.addText("Thank you  ·  Questions?", { x: 0.5, y: 4.55, w: 9.0, h: 0.45, fontSize: 20, bold: true, color: C.accent5,
  fontFace: THEME.headFontFace, margin: 0, isTextBox: true });
s.addNotes("All tests ran with real components; no model response was mocked.");

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("written", OUT);
})();
