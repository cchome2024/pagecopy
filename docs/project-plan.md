# PageCopy Project Plan

## 项目目标 / Objectives
- 构建一个可重复使用的网页转存工具，处理普通页面与部分 JS-heavy 页面（如微信公众号）。
- 将结果保存为静态 HTML，生成可公开访问的 URL，方便长期归档与统一访问。
- 保持清晰的前后端结构，便于未来扩展并行处理、鉴权、多租户等能力。

## 项目范围 / Scope
- **Frontend**: React SPA，提供 URL 输入、选项开关、快照提交与结果展示。
- **Backend**: FastAPI 服务，统一处理快照任务、文件写入、访问 URL 构建；附带历史记录接口，方便追踪过往快照。
- **Browser rendering**: 使用 Playwright headless Chromium 渲染 JS-heavy 页面，并提供策略/参数控制。

## 开发阶段 / 里程碑
1. **阶段 1：项目骨架**
   - 初始化 `frontend/` (Vite + React + TS) 与 `backend/` (FastAPI) 结构。
   - 建立基础配置、运行脚本与健康检查接口。
2. **阶段 2：基础快照功能**
   - 实现 `POST /api/snapshots`，使用 httpx 抓取普通网页。
   - 生成 `<timestamp>_<hash>.html` 命名，并写入 `SNAPSHOT_ROOT`。
   - 基于 `SNAPSHOT_BASE_URL` 生成外部访问链接。
3. **阶段 3：浏览器渲染支持**
   - 集成 Playwright + `BrowserRenderer` 抽象。
   - 根据 hostname、客户端参数或抓取失败情况切换到浏览器渲染。
4. **阶段 4：前端交互与错误处理**
   - URL 文本区、多语言提示、强制渲染开关。
   - 结果列表、状态提示、网络/表单错误反馈。
   - 预留未来并发/队列的 UI 空间，并增加历史汇总视图/复制功能。
5. **阶段 5：部署与优化（可选）**
   - docker-compose、Nginx 反向代理示例。
   - Playwright 浏览器实例复用、并发限制与资源监控建议。

## 风险与注意事项 / Risks & Notes
- JS-heavy 网站常更改结构且可能有反爬策略，渲染成功率无法保证；需持续观察并更新策略。
- 微信公众号等内容受版权及平台协议限制，务必在合法、合规前提下使用。
- 浏览器渲染耗费资源，应限制并发、配置合理超时，并考虑队列/任务系统以保护主服务。
- 快照目录会持续增长，需规划存储扩容与定期清理/归档策略（例如生命周期任务或对象存储版本化）。
