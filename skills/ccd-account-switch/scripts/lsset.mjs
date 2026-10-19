// 直接改 CCD 页面 localStorage（Chromium LevelDB）里某个账号的环境列表。只能在 CCD 完全退出后跑：
// CCD 开着时 LevelDB 有 LOCK，open 会失败，这本身就是保险。
//
// 用法: node lsset.mjs <classic-level 所在目录> <Local Storage/leveldb> <账号 uuid> <presets.json>
//
// Chromium localStorage 编码（2026-10-19 在副本上读写、再用独立 Chrome 读回验证过）：
//   key   = "_" + origin + "\x00\x01" + key 名（latin1）
//   value = "\x01" + latin1      （全部字符 <= 0xFF）
//         | "\x00" + UTF-16LE    （否则）
// 只替换值里第一个 presets 数组（通常是 .state.presets），别的字段原样保留。
// 退出码: 0 写好并读回一致；2 打不开（多半 CCD 还开着）；3 没有这个 key；4 值里没有 presets；5 读回不一致
import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';

const [depDir, lsDir, acct, presetsFile] = process.argv.slice(2);
const { ClassicLevel } = createRequire(path.join(depDir, 'package.json'))('classic-level');
const ORIGIN = 'https://claude.ai';
const NAME = 'persisted.ccd-session-presets.' + acct;

const key = Buffer.concat([Buffer.from('_' + ORIGIN, 'latin1'), Buffer.from([0, 1]), Buffer.from(NAME, 'latin1')]);
const dec = b => (b[0] === 1 ? b.subarray(1).toString('latin1') : b.subarray(1).toString('utf16le'));
const enc = s => ([...s].every(c => c.codePointAt(0) <= 0xff)
  ? Buffer.concat([Buffer.from([1]), Buffer.from(s, 'latin1')])
  : Buffer.concat([Buffer.from([0]), Buffer.from(s, 'utf16le')]));
const out = (code, msg) => { console.log(JSON.stringify({ code, ...msg })); process.exit(code); };

const presets = JSON.parse(fs.readFileSync(presetsFile, 'utf8'));
const db = new ClassicLevel(lsDir, { keyEncoding: 'buffer', valueEncoding: 'buffer', createIfMissing: false });
try { await db.open(); } catch (e) { out(2, { error: 'open failed: ' + (e.cause?.message || e.message) }); }

let raw;
try { raw = await db.get(key); } catch { raw = undefined; }
if (raw === undefined) { await db.close(); out(3, { error: 'no key ' + NAME }); }
const obj = JSON.parse(dec(raw));
let target = null;
(function walk(o) {
  if (!o || typeof o !== 'object' || target) return;
  if (Array.isArray(o.presets)) { target = o; return; }
  for (const v of Object.values(o)) walk(v);
})(obj);
if (!target) { await db.close(); out(4, { error: 'no presets array in value' }); }

const before = target.presets.length;
target.presets = presets;
const str = JSON.stringify(obj);
await db.put(key, enc(str));
const back = await db.get(key);
await db.close();
if (dec(back) !== str) out(5, { error: 'readback mismatch' });
out(0, { key: NAME, before, after: presets.length });
