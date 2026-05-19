# AgeGate

AI 輔助年齡驗證系統 — 為年齡管制零售場景設計的合規工具

> ⚠️ **聲明**：本專案為個人 portfolio 作品，展示 ML 系統設計與合規工程思維。雖然系統按照可上線標準設計，但 **AI 年齡估測不能取代法定身分證件查驗**。任何實際場域使用都需經過完整法律審查與保險規劃。

---

## 專案定位

針對菸酒銷售、夜店、電子煙等具有年齡管制需求的零售場景，AgeGate 透過攝影機即時擷取顧客人臉，使用本地推論的 ML pipeline 估測年齡區間，並透過**保守決策邏輯**輔助現場人員判斷是否需要進一步查驗證件。

系統核心設計理念：**AI 是減少疏忽的輔助層，不是責任轉移層。**

## 為何選擇本地推論而非雲端 API

評估初期曾考量 AWS Rekognition、Azure Face API 等雲端方案，最終選擇本地推論架構，原因如下：

1. **個資合規**：人臉影像屬於《個人資料保護法》中的特種個資。雲端 API 將影像傳輸至境外伺服器，臺灣商家適用上存在告知義務與跨境傳輸合規負擔
2. **可控性**：本地推論不依賴第三方服務可用性，無 API 月費，可離線運作
3. **技術深度**：自行 serve ML 模型可完整掌握 pipeline 每一階段，便於後續優化

## 技術棧

| 層 | 技術 |
|---|---|
| 前端 | Next.js 14, TypeScript, Tailwind CSS, WebRTC |
| 後端 | FastAPI, Python 3.11, Pydantic v2 |
| ML | InsightFace（人臉偵測與對齊）, MiVOLO（年齡估測） |
| 資料庫 | Supabase Postgres |
| 認證 | Supabase Auth (JWT) |
| 部署 | Vercel (前端) + Railway (後端 + ML 模型) |

## 系統架構

```
┌─────────────────────────────────────────────────────┐
│  Operator UI（店員操作介面）                          │
│  - 攝影機即時預覽                                     │
│  - 紅黃綠燈判斷顯示                                   │
│  - 人工複核紀錄                                       │
└──────────────┬──────────────────────────────────────┘
               │ HTTPS / JSON
               ▼
┌─────────────────────────────────────────────────────┐
│  FastAPI Service                                    │
│                                                     │
│  POST /verify   → 即時年齡估測                       │
│  GET  /audit    → 稽核日誌查詢                       │
│  POST /policy   → 門檻設定                          │
│                                                     │
│  ML Pipeline:                                       │
│  Image → InsightFace (detect+align)                 │
│        → MiVOLO (age estimation)                    │
│        → Conservative Decision Policy               │
│        → Decision + Audit Log                       │
└──────────────┬──────────────────────────────────────┘
               │
               ▼
        Supabase Postgres
        - audit_logs（不含影像、不含人臉特徵）
        - stores（店家設定）
        - policies（門檻配置）
```

## 核心技術亮點

### 1. 保守決策邏輯（Conservative Decision Policy）

年齡估測模型輸出的是「點估計 + 信心區間」。直接用點估計做合規判斷會造成嚴重的 false negative（漏放未成年）。

AgeGate 將判斷區分為三類：

| 判斷 | 條件 | 行動 |
|---|---|---|
| 🟢 PASS | `age_low ≥ threshold + buffer` | 直接通過 |
| 🔴 REJECT | `age_high < threshold` | 明確拒絕 |
| 🟡 MANUAL | 其他所有情況 | 強制人工查證件 |

`buffer` 預設值 3 歲，可由店家依風險偏好調整。設計理由詳見 `docs/decision-policy.md`。

### 2. 個資最小化

- 影像在後端記憶體處理後**立即丟棄**，不寫入磁碟
- 不儲存人臉特徵向量
- 稽核日誌僅記錄判斷結果摘要，無法反向識別個人

### 3. 可稽核性

每次判斷產生不可變的稽核紀錄，包含：時間戳、店家 ID、判斷類別、估測年齡區間、模型信心、使用的門檻設定、操作員的最終決定（人工複核時）。

商家被主管機關稽查時可提供完整使用紀錄。

### 4. 多場景門檻設定

支援多個法定年齡門檻（18 / 20）與緩衝區寬度調整，適應菸酒、夜店、電子煙等不同場景。

## 開發進度

- [ ] Phase 1: 基礎建設與 ML pipeline
- [ ] Phase 2: 前端攝影機與即時推論
- [ ] Phase 3: 後台 Dashboard 與稽核查詢
- [ ] Phase 4: 合規包裝與部署

詳細規劃見 `docs/roadmap.md`。

## 本地開發

```bash
# 一鍵初始化(idempotent)
./scripts/bootstrap.sh

# 後端
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload

# 前端
cd frontend && npm run dev
```

詳細設定見 `docs/setup.md`。

## 用 Claude Code 開發

本專案規劃為「人類主導 + AI agent 執行」的開發模式。

- **AI agent 讀**:`CLAUDE.md`(規矩)、`AGENTS.md`(慣例)、`tasks/INDEX.md`(待辦)
- **人類讀**:`docs/claude-code-prompts.md`(怎麼指揮 AI)、`docs/roadmap.md`(策略)

第一次啟動:
```bash
claude
> 請讀完 CLAUDE.md、AGENTS.md、tasks/INDEX.md,然後告訴我你的理解。
```

詳細工作流見 `docs/claude-code-prompts.md`。

## 法律與限制聲明

本系統的年齡估測為**機率性輸出**，存在固有誤差（業界一般 API 平均誤差 ±3–5 歲，邊界年齡誤差更大）。本系統設計上將所有邊界情況導向人工查驗證件，**不可作為唯一的年齡驗證依據**。

任何欲將本系統部署於實際零售場域者，須自行確認符合：

- 《個人資料保護法》告知與同意義務
- 《菸害防制法》《兒少權益法》或相關法規的查驗責任歸屬
- 場域內的隱私權告示要求

作者不對任何因使用本系統導致的法律責任、罰則或損失負責。

## 授權

MIT License
