#!/usr/bin/env node
/**
 * mermaid-verify.mjs — verify Mermaid diagrams embedded in Markdown.
 *
 * Goes beyond `mermaid.parse()` (which silently accepts things real renderers
 * reject): it PARSES and actually RENDERS every ```mermaid block in strict and
 * loose mode, and lint-checks the documented escaping gotchas — especially for
 * sequence diagrams, where a bare `;` (and the `;` inside HTML entities like
 * `&lt;`) terminates the statement.
 *   Ref: https://mermaid.js.org/syntax/sequenceDiagram.html#entity-codes-to-escape-characters
 *
 * Usage:
 *   npm i mermaid jsdom        # one-time, in this folder
 *   node mermaid-verify.mjs path/to/file.md [more.md ...]
 *
 * Exit code is non-zero if any block fails, so it can gate CI or a pre-commit hook.
 */
// Mermaid verifier — parse + actual render (loose & strict) + a lint pass for the
// documented gotchas that parse() accepts but renderers reject.
// Refs: https://mermaid.js.org/syntax/sequenceDiagram.html#entity-codes-to-escape-characters
import { JSDOM } from 'jsdom';
import fs from 'fs';

const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>', { pretendToBeVisual: true });
globalThis.window = dom.window;
globalThis.document = dom.window.document;
// expose constructors mermaid's renderer reaches for on the global scope
for (const k of ['CSSStyleSheet','Element','SVGElement','Node','DOMParser','XMLSerializer','NodeList','HTMLElement','MutationObserver','CSSStyleDeclaration','getComputedStyle']) {
  if (dom.window[k] && !globalThis[k]) globalThis[k] = dom.window[k];
}
// jsdom has no layout engine; stub the SVG measurement APIs so render() can complete.
const P = dom.window.SVGElement.prototype;
P.getBBox = function () { return { x: 0, y: 0, width: 80, height: 16 }; };
P.getComputedTextLength = function () { return 80; };
P.getPointAtLength = function () { return { x: 0, y: 0 }; };
P.getTotalLength = function () { return 80; };

const mermaid = (await import('mermaid')).default;

// ---- lint pass (the part parse() misses) -------------------------------------
// Apply to the *text* portions of a diagram: message text (after the first ':' on
// an arrow line), note text, and the labels of loop/alt/opt/par/critical/box/rect.
function lintSequence(code) {
  const issues = [];
  const lines = code.split('\n');
  const arrow = /^\s*[A-Za-z0-9_]+\s*(?:->>|-->>|->|-->|-x|--x|-\)|--\)|<<->>|<<-->>)\s*[+\-]?\s*[A-Za-z0-9_]+\s*:(.*)$/;
  const note = /^\s*Note\s+(?:left of|right of|over)\s+[^:]+:(.*)$/i;
  const blockLabel = /^\s*(?:loop|alt|opt|par|and|critical|option|break|box|rect|else)\b(.*)$/i;

  function checkText(text, lineNo, where) {
    const t = text.trim();
    if (!t) return;
    // HTML entities (&lt; &gt; &amp; &#123;) break sequence diagrams: the ';' ends the statement.
    if (/&[a-zA-Z]+;|&#\d+;/.test(t))
      issues.push(`L${lineNo} ${where}: HTML entity breaks sequence diagrams (the ; terminates the statement) — use a mermaid entity code: #60; for <, #62; for >, #38; for &`);
    // A bare ';' that is not part of a mermaid entity code (#123; or #name;).
    const noEnt = t.replace(/#\d+;/g, '').replace(/#[a-zA-Z]+;/g, '');
    if (/;/.test(noEnt))
      issues.push(`L${lineNo} ${where}: literal ';' — use #59; (a bare ; ends the statement)`);
    // '#<digits>' not terminated by ';' will be misread as an entity code.
    if (/#\d/.test(t.replace(/#\d+;/g, '')))
      issues.push(`L${lineNo} ${where}: '#<digits>' looks like an unterminated entity code — write #35; for a literal #`);
  }

  lines.forEach((ln, i) => {
    let m;
    if ((m = ln.match(arrow))) checkText(m[1], i + 1, 'message');
    else if ((m = ln.match(note))) checkText(m[1], i + 1, 'note');
    else if ((m = ln.match(blockLabel))) checkText(m[1], i + 1, 'block label');
  });
  return issues;
}

function extract(file) {
  const txt = fs.readFileSync(file, 'utf8'), out = [],
    re = /^[ \t]*```mermaid(?:[ \t][^\r\n]*)?\r?\n([\s\S]*?)^[ \t]*```/gm;
  let m, i = 0;
  while ((m = re.exec(txt))) out.push({ file, idx: ++i, code: m[1].trimEnd() });
  return out;
}

async function check(level, code, id) {
  mermaid.initialize({ startOnLoad: false, securityLevel: level });
  try { await mermaid.parse(code); } catch (e) { return `parse(${level}) FAILED: ${String(e.message).split('\n')[0]}`; }
  try { await mermaid.render(id + '_' + level, code); } catch (e) { return `render(${level}) FAILED: ${String(e.message).split('\n')[0].slice(0,140)}`; }
  return null;
}

const files = process.argv.slice(2);
let blocks = [];
for (const f of files) blocks = blocks.concat(extract(f));

if (blocks.length === 0) {
  console.log('no mermaid blocks found');
  process.exit(2);
}

let bad = 0;
for (const b of blocks) {
  const type = b.code.split('\n')[0].trim();
  const id = 'd' + b.idx;
  const probs = [];
  for (const lv of ['loose', 'strict']) { const r = await check(lv, b.code, id); if (r) probs.push('  ' + r); }
  if (/sequenceDiagram/.test(type)) probs.push(...lintSequence(b.code).map(s => '  lint: ' + s));
  if (probs.length) { bad++; console.log(`FAIL  ${b.file} #${b.idx} (${type})`); probs.forEach(p => console.log(p)); }
  else console.log(`PASS  ${b.file} #${b.idx} (${type})`);
}
console.log(`\n${blocks.length - bad}/${blocks.length} clean`);

process.exit(bad ? 1 : 0);
