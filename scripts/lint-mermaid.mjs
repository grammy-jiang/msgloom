#!/usr/bin/env node

import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";

const files = process.argv.slice(2);

if (files.length === 0) {
  process.exit(0);
}

function openingFence(line) {
  const match = line.match(/^ {0,3}((`{3,})|(~{3,}))[ \t]*(.*)$/);
  if (match === null) {
    return null;
  }

  const fence = match[1];
  const info = match[4].trim();

  // CommonMark does not allow a backtick in the info string of a backtick
  // fence. Treat such a line as ordinary text.
  if (fence[0] === "`" && info.includes("`")) {
    return null;
  }

  return {
    character: fence[0],
    info,
    length: fence.length,
  };
}

function isClosingFence(line, fence) {
  const expression =
    fence.character === "`"
      ? /^ {0,3}(`{3,})[ \t]*$/
      : /^ {0,3}(~{3,})[ \t]*$/;
  const match = line.match(expression);

  return match !== null && match[1].length >= fence.length;
}

function extractDiagrams(source) {
  const diagrams = [];
  const lines = source.split(/\r?\n/);
  let active = null;

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];

    if (active === null) {
      const fence = openingFence(line);
      if (fence === null) {
        continue;
      }

      const language = fence.info.split(/[ \t]+/, 1)[0].toLowerCase();
      active = {
        ...fence,
        content: [],
        isMermaid: language === "mermaid",
        line: index + 1,
      };
      continue;
    }

    if (isClosingFence(line, active)) {
      if (active.isMermaid) {
        diagrams.push({ code: active.content.join("\n"), line: active.line });
      }
      active = null;
      continue;
    }

    if (active.isMermaid) {
      active.content.push(line);
    }
  }

  if (active?.isMermaid) {
    const error = new Error(`unclosed Mermaid fence at line ${active.line}`);
    error.line = active.line;
    throw error;
  }

  return diagrams;
}

function conciseError(error) {
  const message = error instanceof Error ? error.message : String(error);
  return message.split(/\n\s+at\s/)[0].trim();
}

let failures = 0;
const targets = [];

for (const file of files) {
  let diagrams;

  try {
    const source = await readFile(file, "utf8");
    diagrams = extractDiagrams(source);
  } catch (error) {
    failures += 1;
    console.error(`\n${file}: ${conciseError(error)}`);
    continue;
  }

  for (const diagram of diagrams) {
    targets.push({ ...diagram, file });
  }
}

if (targets.length === 0) {
  if (failures > 0) {
    console.error(`\nmermaid-parse: ${failures} failure(s); no diagrams parsed.`);
    process.exit(1);
  }

  console.log("mermaid-parse: no Mermaid diagrams found.");
  process.exit(0);
}

// Mermaid sanitizes diagram text while parsing. Give it a small DOM without
// starting a browser. LinkeDOM does not execute scripts from diagram text.
// createRequire honors the NODE_PATH that pre-commit's Node shim provides.
const require = createRequire(import.meta.url);
const { parseHTML } = require("linkedom");
const { window } = parseHTML("<!doctype html><html><body></body></html>");
globalThis.window = window;
globalThis.document = window.document;

const mermaidUrl = pathToFileURL(require.resolve("mermaid")).href;
const { default: mermaid } = await import(mermaidUrl);
mermaid.initialize({ securityLevel: "strict", startOnLoad: false });

for (const target of targets) {
  try {
    await mermaid.parse(target.code);
  } catch (error) {
    failures += 1;
    console.error(`\n${target.file}:${target.line}: invalid Mermaid diagram`);
    console.error(conciseError(error));
  }
}

if (failures > 0) {
  console.error(
    `\nmermaid-parse: ${failures} failure(s) across ${targets.length} diagram(s).`,
  );
  process.exit(1);
}

console.log(`mermaid-parse: ${targets.length} diagram(s) valid.`);
