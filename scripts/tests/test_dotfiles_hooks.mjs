// 契约测试: 验证 kilo/opencode plugin 的 chat.message 钩子把 capsule 注入用户消息。
// 真的 spawn context_capsule.py, 验证完整注入链(不需要 LLM)。
// 关键: runtime 要求 part 带完整 schema(id/messageID/sessionID), 缺字段会崩 session,
//      所以注入是追加到既有 text part 的 text 字段, 不新增 part(已端到端实测)。
// 运行: node scripts/tests/test_dotfiles_hooks.mjs
import assert from "node:assert";
import { DotfilesHooksPlugin } from "../opencode/dotfiles_hooks.mjs";

const MARKER = "<!-- dotfiles-context-capsule -->";
const hooks = await DotfilesHooksPlugin({ directory: process.cwd() });
const chatMessage = hooks["chat.message"];
assert.ok(typeof chatMessage === "function", "plugin must expose chat.message hook");

// 模拟 runtime 真实 part 形态(带 id/messageID/sessionID)
function userPart(text) {
  return { type: "text", text, messageID: "msg_x", sessionID: "ses_x", id: "prt_x" };
}

// case 1: 变更意图 → scope capsule 追加进 text, 不新增 part(防 runtime schema 崩)
{
  const output = { parts: [userPart("帮我加个缓存")] };
  await chatMessage({ sessionID: "t1" }, output);
  assert.strictEqual(output.parts.length, 1, "must NOT add new parts (runtime requires full part schema)");
  assert.ok(output.parts[0].text.includes("Scope Alignment Capsule"), "scope capsule injected into text");
  assert.ok(output.parts[0].text.includes(MARKER), "marker present");
  console.log("case1 ok: scope capsule appended to text, no new part");
}

// case 2: 无关 prompt → text 原样不动
{
  const output = { parts: [userPart("谢谢")] };
  const before = output.parts[0].text;
  await chatMessage({ sessionID: "t2" }, output);
  assert.strictEqual(output.parts[0].text, before, "unrelated prompt must be untouched");
  console.log("case2 ok: no injection for unrelated prompt");
}

// case 3: 已含 marker → 不重复注入(防自激循环)
{
  const output = { parts: [userPart(`帮我加个缓存\n\n${MARKER}\n# Scope Alignment Capsule ...`)] };
  const before = output.parts[0].text;
  await chatMessage({ sessionID: "t3" }, output);
  assert.strictEqual(output.parts[0].text, before, "already-injected text must not double-inject");
  console.log("case3 ok: marker prevents double injection");
}

// case 4: scope+planning 共现, 顺序 scope→planning
{
  const output = { parts: [userPart("优化这个模块，给我一个重构方案")] };
  await chatMessage({ sessionID: "t4" }, output);
  const text = output.parts[0].text;
  assert.ok(text.includes("Scope Alignment Capsule"), "scope present");
  assert.ok(text.includes("Planning Task Capsule"), "planning present");
  assert.ok(
    text.indexOf("Scope Alignment Capsule") < text.indexOf("Planning Task Capsule"),
    "scope must precede planning",
  );
  console.log("case4 ok: scope+planning co-occur in scope→planning order");
}

console.log("ALL PASS");
