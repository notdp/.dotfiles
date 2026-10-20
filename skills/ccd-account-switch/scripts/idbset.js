// 用跟 CCD 同版本的 Electron 打开一份 userData 目录（只放 IndexedDB 副本），在 https://claude.ai 源下
// 读/写 keyval-store 里的一个 key。CCD 的 IndexedDB 用 Chromium 自定义排序规则 + V8 序列化，外部库打不开；
// 同版本 Electron 是唯一稳妥的读写方式（版本更高的 Chrome 可能把库格式升级掉）。
//
// 用法: Electron idbset.js <userData> get <key>
//       Electron idbset.js <userData> merge <key> <ids.json>   把 ids 并进 value.state.starredIds，已有的保留
// 输出一行 JSON：{"before": <原值字符串|null>, "after": <新值字符串|null>}
const { app, BrowserWindow, protocol } = require('electron');
const fs = require('fs');

const [userData, mode, key, idsFile] = process.argv.slice(2).filter(a => !a.startsWith('--'));
app.setPath('userData', userData);
app.commandLine.appendSwitch('disable-gpu');
app.whenReady().then(async () => {
  if (app.dock) app.dock.hide();
  protocol.handle('https', () => new Response('<html><body>stub</body></html>',
    { headers: { 'content-type': 'text/html' } }));
  const w = new BrowserWindow({ show: false });
  await w.loadURL('https://claude.ai/');
  const ids = mode === 'merge' ? JSON.parse(fs.readFileSync(idsFile, 'utf8')) : null;
  const res = await w.webContents.executeJavaScript(`(async () => {
    const db = await new Promise((ok, no) => {
      const r = indexedDB.open('keyval-store');
      r.onupgradeneeded = () => r.result.createObjectStore('keyval');
      r.onsuccess = () => ok(r.result); r.onerror = () => no(String(r.error));
    });
    const get = k => new Promise(ok => { const r = db.transaction('keyval').objectStore('keyval').get(k); r.onsuccess = () => ok(r.result ?? null); });
    const key = ${JSON.stringify(key)}, before = await get(key);
    if (${JSON.stringify(mode)} === 'merge') {
      const obj = before ? JSON.parse(before) : { state: { starredIds: [] }, version: 0 };
      const cur = obj.state.starredIds || [];
      obj.state.starredIds = cur.concat(${JSON.stringify(ids)}.filter(x => !cur.includes(x)));
      obj.updatedAt = Date.now();
      await new Promise((ok, no) => {
        const t = db.transaction('keyval', 'readwrite');
        t.objectStore('keyval').put(JSON.stringify(obj), key);
        t.oncomplete = ok; t.onerror = () => no(String(t.error));
      });
    }
    const after = await get(key); db.close();
    return { before, after };
  })()`);
  console.log(JSON.stringify(res));
  w.destroy();
  setTimeout(() => app.quit(), 500);
});
