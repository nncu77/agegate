# Roadmap

5 週 MVP 規劃。每週結束都應該有可 demo 的成果。

## Week 1:基礎建設 + ML pipeline

**目標**:後端能接收一張圖,回傳年齡估測 + 決策結果。

- [ ] Supabase 專案建立,套用 `supabase/001_initial_schema.sql`
- [ ] 後端環境設定(virtualenv、`.env` 從 `.env.example` 複製)
- [ ] 安裝 InsightFace 並下載 `buffalo_l` 權重到 `model_cache_dir`
- [ ] 安裝 MiVOLO(從 GitHub source),下載預訓練 checkpoint
- [ ] `app/ml/pipeline.py` 把 TODO 標記處替換為真實實作
- [ ] 用 `httpx` 寫一個整合測試:本地圖片 → `/verify` → 預期決策
- [ ] **deliverable**:`pytest` 全綠,curl 打 `/verify` 有結果

## Week 2:前端攝影機與即時推論

**目標**:在瀏覽器開鏡頭、截圖、送後端、看到結果。

- [ ] 前端跑起來(`npm install && npm run dev`)
- [ ] `/verify` 頁面 + Camera 元件實測(本機 HTTPS 用 mkcert)
- [ ] 後端 CORS 確認與前端 origin 對齊
- [ ] 加 loading 狀態與錯誤處理,測試各種失敗情境:
  - 沒有人臉
  - 多張人臉(請另一個人入鏡測)
  - 攝影機被拒
  - 後端離線
- [ ] **deliverable**:錄一段 30 秒影片 demo,自己 + 家人測試

## Week 3:後台 Dashboard + Supabase Auth

**目標**:店家能登入、看自己的稽核紀錄、調整門檻。

- [ ] Supabase Auth(magic link 即可,不做密碼)
- [ ] 中介層:`/dashboard` 與 `/verify` 要求登入
- [ ] 稽核日誌表格:過濾(日期、決策類型)、分頁、匯出 CSV
- [ ] 統計卡片:今日驗證量、PASS/REJECT/MANUAL 比例、平均信心
- [ ] 門檻設定頁:修改 threshold/buffer/confidence,送 `/policy`
- [ ] **deliverable**:從註冊到調整門檻到看紀錄,完整流程可走

## Week 4:合規包裝

**目標**:從技術 demo 升級為「擬真產品」。

- [ ] 隱私權政策頁(模板 + 客製空白讓店家填)
- [ ] 「告示產生器」:輸入店名 → 產生印製用 A4 PDF 告示
- [ ] README 補上完整法律聲明
- [ ] Demo Mode:模擬資料 + 沒有後端也能跑(給面試官用)
- [ ] 錄一段 2-3 分鐘的 demo 影片放 README

## Week 5:部署 + portfolio 包裝

- [ ] 後端 Docker build 通過,部署 Railway
- [ ] 前端部署 Vercel,環境變數設好
- [ ] 自訂網域(選配)
- [ ] **履歷文案**:撰寫 1 段 + 3 點的技能 bullet
- [ ] **面試準備**:預想 5 個會被問的技術問題,寫好答案

## 不在 MVP 範圍內(但值得列在 README 的「Future Work」)

- 多幀融合
- A/B testing 不同模型(DeepFace vs MiVOLO)
- 邊緣裝置(Jetson Nano)部署
- Liveness detection(防止用照片詐騙)
- 多語系(英 / 日)
