# AGENTS.md

工程慣例與品質規範。Claude Code 與人類開發者都需遵守。

## Python (backend/)

### 風格
- Python 3.11+
- 所有函式參數與回傳值都要有 type hints
- 用 `from __future__ import annotations` 取得更乾淨的型別語法
- 模組內 import 順序:標準函式庫 → 第三方 → 本專案,各組之間空行
- 用 `ruff` 格式化與 lint。設定見 `backend/pyproject.toml`
- docstring 用 Google 或 NumPy 風格擇一,本專案用 Google 風格
- 私有函式以底線開頭(`_helper`)

### 模組設計
- 業務邏輯與 I/O 分離:`core/` 是純函式,`db/`、`api/`、`ml/` 處理 I/O
- 任何模組都不應該直接依賴 FastAPI 物件,API 層才碰 `Request`、`Response`
- ML pipeline 是 stateful singleton,透過 FastAPI dependency injection 取得
- 不要在 import time 做任何重操作(讀檔、連線、載入模型)

### 錯誤處理
- 預期內的錯誤(使用者輸入錯)→ raise `HTTPException` 在 API 層
- 預期外的錯誤(程式 bug)→ 讓它冒上來,FastAPI 會回 500 並由 middleware logging
- 不要 `except Exception: pass`,等同於把 bug 藏起來
- DB 寫入失敗(例如 audit log)應該 log 但不中斷使用者請求 —— 看 `audit_repo.write_log` 註解

### 測試
- 用 `pytest`,不用 `unittest`
- 純邏輯(`core/`)必須有單元測試,目標 90%+ 覆蓋率
- I/O 層(`db/`、`api/`)用整合測試,可以打真實 Supabase 測試資料庫
- 測試命名:`test_<被測函式>_<情境>_<預期>`,例如 `test_decide_low_confidence_returns_manual`
- 一個 test function 只測一件事,不要塞五個 assert 在裡面

## TypeScript / React (frontend/)

### 風格
- `strict: true` 開啟,不關
- **禁用 `any`**。真的需要動態型別用 `unknown` 配合 type guard
- 用 function components + hooks,不用 class components
- 元件檔案以 PascalCase 命名(`Camera.tsx`),hooks 與 utils 用 camelCase(`api.ts`)
- 用 `import type { ... }` 區分型別 import
- 不寫不必要的 `useEffect` —— 能在 render 時算出來的就不要放 effect

### 元件設計
- props 用 `interface` 定義在元件上方,以 `<ComponentName>Props` 命名
- 副作用(setTimeout、fetch、addEventListener)一定要在 cleanup function 裡解除
- 攝影機 stream 的解除特別重要 —— 看 `Camera.tsx` 的 useEffect cleanup
- 共用樣式提取成 utility class 或 `clsx` 條件樣式,不要 inline style

### 資料流
- 暫時的 UI state 用 `useState`
- 跨頁面的 state 之後會用 Supabase + URL params,不要引入 Redux/Zustand
- API 呼叫集中在 `lib/api.ts`,元件不直接 fetch

## 資料庫 (supabase/)

- migration 檔案編號遞增不重用:`001_initial_schema.sql`、`002_add_xxx.sql`
- 一個 migration 一個邏輯變更,不要塞太多進一個檔案
- 永遠提供 `down` 邏輯(註解寫清楚怎麼回滾)
- 所有表都要開 RLS,例外要在 task 中明確說明
- 索引命名:`<table>_<columns>_idx`

## Commit Messages

格式:
```
<type>(<scope>): <subject>

<body>
```

- type:`feat` | `fix` | `refactor` | `test` | `docs` | `chore`
- scope:`backend` | `frontend` | `db` | `ml` | `docs` | `infra`
- subject 用祈使句、小寫開頭、不加句點,< 60 字

範例:
```
feat(ml): wire insightface buffalo_l for face detection

Replace TODO placeholder in pipeline.detect_faces with real
InsightFace FaceAnalysis call. Min confidence threshold reads
from settings so tests can override.
```

## 不要做的事

- 不要把 `console.log` / `print` 留在程式碼裡(debug 用完刪掉,長期 logging 用 logger)
- 不要為了通過測試而修改測試 —— 改程式
- 不要 commit `node_modules/`、`.venv/`、`.env`、模型權重
- 不要在 PR 一次混合 refactor 與 feature
- 不要用「魔法數字」—— 取個常數放在 `config.py` 或檔案頂端
