# Read methods

## 第一版路由

- GitHub 页面：统一走 reader proxy
- PDF：统一走 reader proxy
- 通用网页：统一走 reader proxy

## 当前脚本边界

- 只负责把 URL 拉成文本
- 不负责登录、点击、滚动、截图
- 不负责内容真实性判断

## 升级方向

- 加入 PDF 专项后处理
- 加入站点级 routing 表
- 对需要交互的站点自动提示切换到 `agent-browser`
