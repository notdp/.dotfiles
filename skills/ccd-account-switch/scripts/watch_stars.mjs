// 常驻监听：环境 star 一变就快照（替代每 30 分钟轮询）。由 launchd（KeepAlive）拉起：
//   node watch_stars.mjs <python3> <env_stars.py>
//
// 为什么这么盯（2026-10-20 实测）：
// - fs.watch(dir, {recursive:true}) 走 FSEvents，点星时 .log 的修改时间变了，它却一个事件都没报；
// - 直接 fs.watch(那个 .log 文件) 走 kqueue，每次点星都有 change 事件。
// 所以盯「当前的 NNNNNN.log 文件」本身；它会被 LevelDB 轮换（rename），切号时整个目录会被删了重建，
// 因此再盯 leveldb 目录和上一级 IndexedDB 目录，出事件就重新挂；外加每 60 秒自检一次挂的是不是最新的 .log。
//
// 每次事件防抖 3 秒后，直接在原始文件里找 key（IndexedDB 的 key 是大端 UTF-16）后面那条
// {"state":{"starredIds":[...]},...,"updatedAt":N}，updatedAt 比上次新才调 env_stars.py snapshot。
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';

const [py, script] = process.argv.slice(2);
const IDB = path.join(process.env.HOME, 'Library/Application Support/Claude/IndexedDB');
const DIR = path.join(IDB, 'https_claude.ai_0.indexeddb.leveldb');
const KEY = Buffer.from('store:pin-state:epitaxy-starred-environments', 'utf16le').swap16();   // 大端
const REC = /\{"state":\{"starredIds":\[([^\]]*)\]\},"version":\d+,"updatedAt":(\d+)\}/;

let watchers = [], watchedLog = null, timer = null, lastSeen = 0;

function latestRecord() {
  let best = null;
  let names = [];
  try { names = fs.readdirSync(DIR); } catch { return null; }
  for (const n of names) {
    if (!/\.(log|ldb)$/.test(n)) continue;
    let b; try { b = fs.readFileSync(path.join(DIR, n)); } catch { continue; }
    for (let i = b.indexOf(KEY); i !== -1; i = b.indexOf(KEY, i + 1)) {
      const m = REC.exec(b.subarray(i + KEY.length, i + KEY.length + 800).toString('latin1'));
      if (m && (!best || +m[2] >= best)) best = +m[2];
    }
  }
  return best;
}

function check() {
  const t = latestRecord();
  if (t && t > lastSeen) {
    lastSeen = t;
    spawn(py, ['-B', script, 'snapshot'], { stdio: 'ignore' });
  }
}

function schedule() { clearTimeout(timer); timer = setTimeout(check, 3000); }

function currentLog() {
  try { return fs.readdirSync(DIR).filter(f => /^\d+\.log$/.test(f)).sort().pop() || null; } catch { return null; }
}

function attach() {
  for (const w of watchers) { try { w.close(); } catch {} }
  watchers = [];
  const add = (p, onEvent) => { try { const w = fs.watch(p, onEvent); w.on('error', () => setTimeout(attach, 1000)); watchers.push(w); } catch {} };
  add(IDB, () => setTimeout(attach, 1000));                       // 切号时 leveldb 目录被删了重建
  add(DIR, () => { schedule(); if (currentLog() !== watchedLog) attach(); });
  watchedLog = currentLog();
  if (watchedLog) add(path.join(DIR, watchedLog), (ev) => { schedule(); if (ev === 'rename') setTimeout(attach, 500); });
}

attach();
check();
setInterval(() => { if (currentLog() !== watchedLog) { attach(); schedule(); } }, 60000);
