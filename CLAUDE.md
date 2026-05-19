# CLAUDE.md

> 這個檔案是給 Claude Code 看的。請在開始任何工作前完整讀完。
> 人類開發者也歡迎讀,但主要受眾是 AI agent。

## 專案是什麼

AgeGate 是一個 AI 輔助年齡驗證系統,給菸酒、夜店、電子煙等年齡管制場景的零售商使用。

**重要定位**:這是一個 **portfolio / 學習專案**,不會真的部署到生產環境。
但設計與程式碼品質要做到「彷彿準備上線」的水準,因為主要目的是展示工程能力給面試官看。

技術棧:
- 後端:FastAPI + Python 3.11 + InsightFace + MiVOLO
- 前端:Next.js 14 + TypeScript + Tailwind
- 資料庫:Supabase Postgres
- 部署:Vercel(前端)+ Railway(後端)

完整背景請讀 `README.md`。

## 你的工作模式

任務都在 `tasks/` 資料夾,以 `WEEK{n}-{nn}-{slug}.md` 命名,例如 `WEEK1-01-supabase-setup.md`。

**做事順序**:
1. 開始前先看 `tasks/INDEX.md` 確認當前優先順序
2. 一次處理**一個 task**,不要平行做多個
3. 每個 task 檔案內都有「驗收條件 (Acceptance Criteria)」,完成後逐項確認
4. 完成後,在 task 檔案末尾加一個 `## Completion Log` section,記錄:
   - 完成時間
   - 實際遇到的問題與決策
   - 任何偏離原計畫的地方與理由
5. 把對應的 INDEX.md 條目標記為 `[x]`

**不要做的事**:
- 不要主動修改 `CLAUDE.md`、`AGENTS.md`、`README.md`(這些是策略文件,需人類確認)
- 不要主動新增 task 檔案(發現新工作要做時,在當前 task 的 Completion Log 提出建議,讓人類審視)
- 不要刪檔案,除非 task 明確要求
- 不要為了通過測試而修改測試斷言 —— 改程式,不是改測試
- 不要 commit 或 push(人類掌控 git)

## 工程慣例

詳細的程式碼風格、依賴管理、commit message 規範請讀 `AGENTS.md`。
摘要:
- Python:type hints 必填、用 `ruff` 格式化、測試用 `pytest`
- TypeScript:`strict: true`、不用 `any`、元件用 function components + hooks
- 不增加 dependency 除非必要,要加先在 task 完成時提出
- 每一個 commit 應該對應一個邏輯單位(通常是一個 task 或 task 的一個 sub-step)

## 環境

- 後端 venv 在 `backend/.venv`(若不存在,跑 `scripts/bootstrap.sh` 建立)
- 前端 deps 用 `npm install` 在 `frontend/` 安裝
- 環境變數讀 `.env.example` 範本,**不要把實際 secrets 寫進任何 commit 的檔案**
- Supabase 連線資訊請問人類(不要假造 URL 或 key)

## 測試

開始任何修改前,先確認測試是綠的:
```bash
cd backend && PYTHONPATH=. python -m pytest -q
```

如果測試一開始就紅,**停下來告訴人類**,不要為了讓它變綠而修改測試。

## ML 模型狀態

`backend/app/ml/pipeline.py` 中 InsightFace 與 MiVOLO 的真實推論程式碼**還沒接上**,
所有實作位置都有 `# TODO(week-1)` 標記。第一個 ML 相關的 task 就是把這些填起來。

在那之前,`/verify` 端點會在呼叫 `pipeline.estimate_age()` 時拋 `NotImplementedError`。
這是預期行為,不是 bug。

## 何時暫停問人類

下列情況 **必須** 暫停並問人類,不要自行決定:

1. 需要修改 schema(`supabase/*.sql`)的結構
2. 需要新增或更換 npm/pip 套件
3. 任何牽涉到 secrets、API key、認證設定的步驟
4. task 描述與你的觀察矛盾(可能是 task 寫錯了,人類要修)
5. 完成 task 時發現原本的設計有更好的做法 —— 提出來,不要直接改

## 不要踩的地雷

- **個資**:audit_logs 表絕對不可以加任何能識別個人的欄位(姓名、影像、人臉特徵向量)。
  這是這個專案的核心合規承諾。
- **影像存留**:`/verify` 端點處理完影像後,影像必須立刻離開記憶體。
  不要為了 debug 把它寫到磁碟。
- **決策邏輯**:`backend/app/core/decision.py` 是系統最重要的檔案。
  任何修改都要同步更新 `backend/tests/test_decision.py` 與 `docs/decision-policy.md`。
- **CORS / Auth**:不要為了方便開發把 CORS 設成 `*`,或停用 Supabase RLS。
- **直接 commit `.env`**:絕對不行。

## 常用指令速查

```bash
# 後端啟動
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload

# 後端測試
cd backend && PYTHONPATH=. python -m pytest -v

# 後端 lint
cd backend && ruff check app/

# 前端啟動
cd frontend && npm run dev

# 前端型別檢查
cd frontend && npm run typecheck
```
