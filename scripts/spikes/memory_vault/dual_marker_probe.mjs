#!/usr/bin/env node
import assert from "node:assert";

const CAPSULE_MARKER = "<!-- dotfiles-context-capsule -->";
const MEMORY_MARKER = "<!-- dotfiles-memory-context -->";
const MAX_CONTEXT_CHARS = 2200;

function userPart(text) {
  return { type: "text", text, messageID: "msg_spike", sessionID: "ses_spike", id: "prt_spike" };
}

function injectSegment(output, marker, context) {
  const parts = output?.parts;
  if (!Array.isArray(parts)) return false;
  const textPart = parts.find((part) => part && part.type === "text" && typeof part.text === "string" && part.text.trim());
  if (!textPart || textPart.text.includes(marker)) return false;
  if (typeof context === "string" && context.trim()) {
    textPart.text = `${textPart.text}\n\n${marker}\n${context.trim()}`;
    return true;
  }
  return false;
}

function injectDualMarkers(output) {
  injectSegment(output, CAPSULE_MARKER, "Capsule spike context");
  injectSegment(output, MEMORY_MARKER, "Memory spike context");
}

function markerCount(text, marker) {
  return Array.from(text.matchAll(new RegExp(marker, "g"))).length;
}

function runCase(name, initialText) {
  const output = { parts: [userPart(initialText)] };
  const initialPartCount = output.parts.length;

  injectDualMarkers(output);
  injectDualMarkers(output);

  const text = output.parts[0].text;
  const capsuleCount = markerCount(text, CAPSULE_MARKER);
  const memoryCount = markerCount(text, MEMORY_MARKER);
  const appendedLength = text.length - initialText.length;

  assert.strictEqual(output.parts.length, initialPartCount, `${name}: must not push a new runtime part`);
  assert.strictEqual(capsuleCount, 1, `${name}: capsule marker must be independently idempotent`);
  assert.strictEqual(memoryCount, 1, `${name}: memory marker must be independently idempotent`);

  return {
    name,
    initialPartCount,
    finalPartCount: output.parts.length,
    capsuleCount,
    memoryCount,
    appendedLength,
  };
}

const cases = [
  runCase("empty", "phase01 dual marker probe"),
  runCase("capsule-preexisting", `phase01 dual marker probe\n\n${CAPSULE_MARKER}\nCapsule spike context`),
  runCase("memory-preexisting", `phase01 dual marker probe\n\n${MEMORY_MARKER}\nMemory spike context`),
];

const appendedLength = cases.reduce((max, item) => Math.max(max, item.appendedLength), 0);

assert.ok(appendedLength <= MAX_CONTEXT_CHARS, "synthetic appended context must fit budget");

console.log(JSON.stringify({
  ok: true,
  initialPartCount: cases[0].initialPartCount,
  finalPartCount: cases[0].finalPartCount,
  capsuleCount: cases[0].capsuleCount,
  memoryCount: cases[0].memoryCount,
  appendedLength,
  maxContextChars: MAX_CONTEXT_CHARS,
  cases,
}));
