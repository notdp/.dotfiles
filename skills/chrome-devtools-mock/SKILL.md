---
name: chrome-devtools-mock
description: 通过 Chrome DevTools 注入 XHR 拦截脚本来 mock 前端页面 API 数据，无需修改源码。当用户要求 mock 页面数据、前端没有后端可用、需要快速预览 UI 时触发。
---

# Chrome DevTools API Mock

通过 Chrome DevTools MCP 的 `navigate_page` + `initScript` 注入 XMLHttpRequest 拦截，在浏览器层面 mock API 响应，**不修改任何源码**。

## 禁止事项

- **禁止修改源码来 mock**：如在 API 文件中加 `MOCK_ENABLED = true`，会污染代码库，容易忘记删除导致提交到生产环境。
- **禁止拦截 `window.fetch`**：大多数项目用 axios，axios 底层走 `XMLHttpRequest` 而非 `fetch`，拦截 fetch 无效。
- **禁止用 `evaluate_script` 注入后再 reload**：reload 后注入的脚本会丢失。

## 正确方法

使用 `chrome-devtools___navigate_page` 工具的 `initScript` 参数。`initScript` 会在**页面加载前、任何其他脚本执行前**注入，确保 XHR 拦截在 API 请求之前生效。

## Instructions

### 1. 确认目标页面

用 `list_pages` + `select_page` 选中目标页面。

### 2. 分析需要 mock 的 API

根据用户需求和页面代码，确定：
- 需要 mock 的 API URL 路径
- 每个 API 的响应数据结构
- 项目的 API 响应包装格式（如 `{code: 1, message: 'success', data: {...}}`）

### 3. 构造 initScript 并注入

调用 `navigate_page` 时传入 `initScript`：

```
chrome-devtools___navigate_page({
  type: "reload",
  timeout: 15000,
  initScript: "<XHR拦截脚本>"
})
```

### 4. 验证

页面加载后用 `take_screenshot` 确认 mock 数据已生效。

## XHR 拦截模板

以下是完整的 XMLHttpRequest 拦截模板，**必须严格按此结构**：

```javascript
(function() {
  // === 1. 定义 mock 数据 ===
  var mockRoutes = {
    '/api/v1/some-endpoint': { key: 'value' },
    '/api/v1/another': { items: [] }
  };

  // === 2. 定义响应包装函数（根据项目 API 格式调整） ===
  var wrapResp = function(data) {
    // 常见格式，根据实际项目调整
    return JSON.stringify({ code: 1, message: 'success', data: data });
  };

  // === 3. 拦截 XMLHttpRequest ===
  var origOpen = XMLHttpRequest.prototype.open;
  var origSend = XMLHttpRequest.prototype.send;

  XMLHttpRequest.prototype.open = function(m, u) {
    this.__url = u;
    return origOpen.apply(this, arguments);
  };

  XMLHttpRequest.prototype.send = function(b) {
    var u = this.__url || '';
    var d = null;

    // === 4. URL 匹配（具体路径必须在泛路径之前） ===
    // 先匹配带 ID 的具体路径
    if (u.match(/\/api\/v1\/items\/[^/?]+/) && u.indexOf('delete') === -1) {
      d = { item: { id: '1', name: 'Mock Item' } };
    }
    // 再匹配列表路径
    else if (u.indexOf('/api/v1/items') !== -1) {
      d = { items: [{ id: '1', name: 'Mock Item' }] };
    }

    // === 5. 返回 mock 响应 ===
    if (d !== null) {
      var r = wrapResp(d);
      var self = this;
      // 必须用 Object.defineProperty 覆盖只读属性
      Object.defineProperty(self, 'readyState', { writable: true, value: 4 });
      Object.defineProperty(self, 'status', { writable: true, value: 200 });
      Object.defineProperty(self, 'statusText', { writable: true, value: 'OK' });
      Object.defineProperty(self, 'responseText', { writable: true, value: r });
      Object.defineProperty(self, 'response', { writable: true, value: r });
      // 必须异步触发回调，模拟真实网络行为
      setTimeout(function() {
        self.dispatchEvent(new Event('readystatechange'));
        self.dispatchEvent(new Event('load'));
        self.dispatchEvent(new Event('loadend'));
        if (self.onreadystatechange) self.onreadystatechange();
        if (self.onload) self.onload();
        if (self.onloadend) self.onloadend();
      }, 5);
      return; // 不调用原始 send
    }

    // 未匹配的请求走原始逻辑
    return origSend.apply(this, arguments);
  };
})();
```

## 关键注意事项

1. **URL 匹配顺序**：具体路径（如 `/items/123`）必须在泛路径（如 `/items`）之前匹配，否则泛路径会先命中
2. **`Object.defineProperty`**：XMLHttpRequest 的 `readyState`、`status`、`response` 等属性是只读的，必须用 `Object.defineProperty` 覆盖
3. **异步 `setTimeout`**：回调必须在 `setTimeout` 中触发，否则 axios 的拦截器可能还未注册
4. **同时触发事件和回调**：既要 `dispatchEvent` 也要直接调用 `onload` 等回调，因为 axios 可能用任一方式监听
5. **`initScript` 每次传入**：`initScript` 只在当次 `navigate_page` 调用时生效，后续刷新需要重新传入
6. **不要用正则中的命名组**：`initScript` 中的 JS 需要兼容各种环境，避免使用高级语法
