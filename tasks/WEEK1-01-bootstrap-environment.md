# WEEK1-01: Bootstrap Environment

## 目標
讓後端的 Python 環境可以跑起來,所有依賴安裝完成,測試指令能執行。
**這個 task 完成後,任何人 clone 專案應該都能跑測試。**

## 前置條件
- 機器上有 Python 3.11(`python3.11 --version` 確認)
- 機器上有 Node.js 20+ 與 npm

## 步驟

1. 跑 `scripts/bootstrap.sh`,確認:
   - `backend/.venv` 被建立
   - `backend/requirements.txt` 安裝完成
   - **暫不安裝 MiVOLO**(它要從 GitHub 抓,留到 WEEK1-04)
2. 跑 `frontend/`:
   - `cd frontend && npm install`
3. 從 `backend/.env.example` 複製出 `backend/.env`,但保持 Supabase 欄位為空(WEEK1-06 才填)

## 驗收條件

- [ ] `cd backend && source .venv/bin/activate && PYTHONPATH=. python -m pytest -q` 全綠
- [ ] `cd frontend && npm run typecheck` 通過(可能有 warning,但不能 error)
- [ ] `backend/.env` 存在但**沒有被 commit**(在 `.gitignore` 中)
- [ ] `scripts/bootstrap.sh` 可重複執行而不爆錯(idempotent)

## 不要做的事
- 不要安裝 InsightFace、MiVOLO、torch —— 這些留到 WEEK1-03/04
- 不要修改 `requirements.txt`(若依賴版本有衝突,先停下來問人類)

## Completion Log

**完成時間**:2026-05-18

**結果**:驗收條件 1–3 通過;條件 4(bootstrap.sh idempotent)在 Windows 環境無法直接驗證,見「偏離原計畫」。

**驗證**:
- `cd backend && PYTHONPATH=. .venv/Scripts/python.exe -m pytest -q` → `18 passed in 0.08s`
- `cd frontend && npm run typecheck` → 零錯誤
- `backend/.env` 存在,`.gitignore` 已排除 `.env` / `.env.local` / `.venv/` / `node_modules/`

**偏離原計畫**:

1. **bypass `scripts/bootstrap.sh`,手動執行等效步驟**。
   原因:腳本對 Windows 有兩個結構性不相容:
   - 第 17 行 `command -v python3.11` — Windows 官方 installer 不會把 `python3.11` 加到 PATH(只有 `py -3.11`)
   - 第 49 行 `source .venv/bin/activate` — Windows 的 `python -m venv` 建出來的是 `.venv\Scripts\activate`,不會有 `bin/`

   採用步驟(對應腳本邏輯):
   ```bash
   cd backend
   py -3.11 -m venv .venv
   .venv/Scripts/python.exe -m pip install --upgrade pip
   grep -vE '^(insightface|onnxruntime|torch)' requirements.txt > /tmp/agegate-light.txt
   .venv/Scripts/python.exe -m pip install -r /tmp/agegate-light.txt
   cp .env.example .env
   PYTHONPATH=. .venv/Scripts/python.exe -m pytest -q
   cd ../frontend
   cp .env.example .env.local
   npm install --no-fund --no-audit
   npm run typecheck
   ```

2. **修改 `requirements.txt`:`pytest==9.0.3` → `pytest==8.3.3`**(經人類批准)。
   原因:`pytest==9.0.3` 這個版本在 PyPI 不存在(pytest 目前 stable 是 8.3.x;9.0.0 只有 alpha);且 `pytest-asyncio==0.24.0` 要求 `pytest<9`,結構性衝突。
   修改後組合通過 pip resolver。

3. **修改 `frontend/package.json`:`eslint==9.12.0` → `eslint==8.57.1`**(經人類批准)。
   原因:`eslint-config-next@14.2.15` 要求 `eslint ^7.23.0 || ^8.0.0`,跟 eslint 9 互斥。降到 eslint 8 最終版可在不動 Next.js 框架版本的情況下解決。

**對後續 task / 維護者的建議**(不直接改,提出來給人類審視):

- **bootstrap.sh 跨平台化**:目前腳本只在 Linux/macOS 可用。若要支援 Windows,可考慮:
  (a) 加入 `python3.11 || py -3.11` fallback 偵測;
  (b) 用 `[ -f .venv/bin/python ] && VPY=.venv/bin/python || VPY=.venv/Scripts/python.exe` 抽象 venv python 路徑;
  (c) 或單獨提供 `scripts/bootstrap.ps1`。
  這對未來的 maintainer 與 CI(若跑 Windows runner)有意義,但屬於額外工作,本 task 沒做。

- **`next@14.2.15` 有 security advisory**(npm install 警告 2025-12-11 公告)。建議升到最新 14.2.x patch 版。屬於安全議題,但本 task 不修改 dependency 範圍,先記錄。

- **`pytest-asyncio` deprecation warning**:`asyncio_default_fixture_loop_scope` 未設定。未來版本會改 default。建議在 `pyproject.toml` 加 `[tool.pytest.ini_options] asyncio_default_fixture_loop_scope = "function"` — 但屬於小幅 config 改動,留到後續 task。

**未踩雷**:
- 沒 commit 任何檔案(人類掌控 git)
- `.env` 沒被加入 stage
- 沒安裝 InsightFace / MiVOLO / torch / onnxruntime(留到 WEEK1-03/04)
- 沒修改測試斷言

