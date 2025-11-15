# PageCopy 网页转存 / PageCopy Snapshot

## 项目简介 / Introduction
- **中文**：PageCopy 是一个帮助团队把网页转存为静态 HTML 的小工具，支持普通页面和部分需要浏览器渲染的 JS-heavy 页面（例如微信公众号文章），方便归档与长期访问。
- **English**: PageCopy is a lightweight archiving tool that captures web pages (including some JS-heavy sites) as static HTML snapshots for consistent access and preservation.

## 技术栈 / Tech Stack
- **Frontend**: Vite + React + TypeScript (located in `frontend/`)
- **Backend**: FastAPI + httpx (located in `backend/`)
- **Browser Rendering**: Playwright + headless Chromium for JS-heavy pages
- **Snapshot summary**: history stored in `data/history.jsonl` (relative snapshot links for portable deployments)
- **Session capture**: optional Playwright storage state JSON (`data/sessions/<host>.json`) for login-only sites

## 环境准备 / Prerequisites
- Node.js 20 LTS (or newer) and npm / pnpm
- Python 3.10+ (recommended 3.11)
- Playwright runtime: `npx playwright install` or `playwright install` to download Chromium and system deps
- Optional: A static web server (Nginx/Apache) to expose the snapshot directory

## Quickstart / 快速开始

### 1. Clone & enter
```bash
git clone <repo-url>
cd pagecopy
```

### 2. Backend
```bash
cd backend
python -m venv .venv && .venv\Scripts\activate  # 可选 / optional
pip install -r requirements.txt
```

Create `.env` (or export the variables) to configure storage and base URL:
```bash
SNAPSHOT_ROOT=./data/snapshots
SNAPSHOT_BASE_URL=http://localhost:8000/snapshots
PLAYWRIGHT_HEADLESS=true
PLAYWRIGHT_SESSION_DIR=./data/sessions   # 可选：用于存放登录态 JSON
```

Install Playwright browsers (only once per environment):
```bash
playwright install
```

Run the API server **from the project root** (i.e., the directory that contains the `backend/` folder). Staying inside `backend/` will make `backend.main` unreachable.
```bash
cd ..
uvicorn backend.main:app --reload --port 8000
```
The backend automatically exposes the snapshot directory at `http://localhost:8000/snapshots/...`, so the links returned in the API response are immediately accessible after the file is written. Snapshot links are stored as relative paths (e.g. `/snapshots/<file>.html`) to keep archives portable across environments.

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```

The Vite dev server runs on `http://localhost:5173` and proxies `/api` to `http://localhost:8000`.  
If your backend runs elsewhere, set `VITE_API_BASE_URL=<backend-url>` before `npm run dev`.

### 4. 使用说明 / Usage
1. 打开前端页面，输入一条或多条 URL（每行一条）。
2. 可选：勾选 “对 JS 动态页面强制使用浏览器渲染” 来强制 Playwright 渲染。
3. 若目标页面需登录，可在浏览器 DevTools 的 Network 请求里复制 `Cookie` 头粘贴到「可选：Cookie Header」文本框；服务器将在访问时附带该登录态（不存储到磁盘）。
4. 点击「开始转存」，等待结果。
5. 结果列表中可查看每条 URL 的状态，并打开生成的静态快照链接。
6. 历史记录区域会展示最近的抓取结果，支持单条/多选/全选复制相对路径，也可删除选中记录，方便批量粘贴或迁移到其它服务器后继续访问。

## 部署说明 / Deployment Notes
- **Snapshots hosting**: expose `SNAPSHOT_ROOT` via Nginx/Apache or object storage (configure `SNAPSHOT_BASE_URL` accordingly).
- **Backend**: run with `uvicorn`/`gunicorn` + Supervisor/systemd, or build a Docker image. Ensure Playwright browsers are installed in the runtime image/VM.
- **Frontend**: `npm run build` produces static assets in `frontend/dist`; deploy them to any static host (Netlify, Vercel, S3 + CDN, etc.).
- **Security & housekeeping**: restrict access to the API if necessary, and implement lifecycle policies (e.g., cron jobs) to clean old snapshots as the storage grows.
- **History store**: `data/history.jsonl` keeps newline-delimited JSON entries of all runs; copy/backup it together with `data/snapshots` when migrating environments.
- **Session files**: `data/sessions/<hostname>.json` store Playwright `storage_state` for login-only sites; regenerate via the helper script whenever credentials change.

### Handling login-only pages / 登录态页面
部分站点（如企业内网、公众号后台）需要登录态才能访问。本项目提供两种方案：

#### A. 临时粘贴 Cookie（无需服务器登录）
1. 在浏览器里先访问目标站点并完成登录。
2. 打开 DevTools → Network，选择任意已登录请求，复制 Request Headers 中的 `Cookie` 字段。
3. 回到 PageCopy 前端，把 `Cookie` 粘贴到「可选：Cookie Header」文本框再发起转存。
4. 后端只在该次请求里附带 Cookie，不会保存到磁盘，适合一次性操作或不方便在服务器登录的场景。

#### B. 在服务器上预存 Session（长期复用）
利用 Playwright 保存一次会话，然后在抓取时自动带上 Cookie：

1. 在有图形界面的环境执行：
   ```bash
   cd backend
   python -m backend.scripts.capture_session https://example.com/login \
     --output ../data/sessions/example.com.json
   ```
2. 浏览器会打开相应页面，手动完成登录后回到终端按下 Enter。
3. `data/sessions/<host>.json` 会保存当前的 storage_state，FastAPI 会在访问对应 hostname 时自动加载。
4. 若登录过期，重复上述步骤即可更新；需要多个账号/站点时，可在 `data/sessions/` 下为不同的 host 维护多份 JSON。
