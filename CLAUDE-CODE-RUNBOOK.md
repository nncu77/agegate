# AgeGate × Claude Code:一次跑完 Week 1 的完整 Prompt 包

> 這份是你要照順序貼給 Claude Code 的指令集。
> **一次貼一段**,看完 Claude Code 的回應、確認對勁,再貼下一段。
> 不要全部複製貼上 —— 那會讓它在沒檢查點的情況下亂跑。

## 準備動作(你自己做,不是 Claude Code 做)

1. 解壓 `agegate-claude-code.zip`
2. 開 terminal:
   ```bash
   cd agegate-cc
   git init
   git add .
   git commit -m "chore: initial scaffold"
   ```
3. 開 Supabase 帳號、建立一個新專案(免費方案就夠)
4. 把 Supabase 專案的 URL、service_role key、JWT secret 抄下來備用
5. 啟動 Claude Code:
   ```bash
   claude
   ```

準備好後,開始下面的 prompt 序列。

---

## ✅ Step 0 — 對齊理解(必做,不要跳過)

**貼這段:**

```
請先讀完這幾個檔案,不要動手做任何事:
- CLAUDE.md
- AGENTS.md
- README.md
- tasks/INDEX.md
- docs/decision-policy.md

讀完後,用你自己的話告訴我:
1. 這個專案在做什麼、誰用、為什麼
2. 你的工作模式是什麼(怎麼挑 task、怎麼完成、什麼時候該問我)
3. 三件「不能踩的地雷」
4. 第一個要做的 task 是哪個檔案,目標是什麼

回答完停下來等我確認,不要開始實作。
```

**檢查點**:
- 它有沒有正確說出「portfolio 專案、不真的營運」?
- 有沒有點出「個資、影像不落地、決策邏輯」這幾個地雷?
- 有沒有說會從 `WEEK1-01` 開始?

✅ 對的話,貼 Step 1。
❌ 錯的話,叫它「再讀一次 CLAUDE.md,你漏掉了什麼」。

---

## ✅ Step 1 — 環境初始化 (WEEK1-01)

**貼這段:**

```
開始執行 tasks/WEEK1-01-bootstrap-environment.md。

注意:
- 跑 scripts/bootstrap.sh 之前,先用 cat 看一遍腳本內容,確認你了解它要做什麼
- 如果腳本中有任何步驟失敗,停下來告訴我,不要自己嘗試修
- 完成後請逐項勾選驗收條件,並在 task 檔案末尾加 Completion Log
- 完成後不要繼續做下一個 task,等我確認
```

**檢查點**:
- `backend/.venv` 是否被建立
- `frontend/node_modules` 是否安裝完成
- `cd backend && PYTHONPATH=. python -m pytest -q tests/test_decision.py` 是否 18 passed
- task 檔案末尾是否有 Completion Log

**你親自跑一次**:
```bash
cd backend && source .venv/bin/activate && PYTHONPATH=. python -m pytest -q
```
看到 18 passed 才算成功。

✅ 過了再貼 Step 2。

---

## ✅ Step 2 — Commit 進度

**貼這段:**

```
請把目前的修改整理成一個 commit message 給我,
我會自己執行 git commit。格式遵照 AGENTS.md 的規範。
```

**你自己做**:
```bash
git status              # 看改了什麼
git diff                # 看細節
git add -A
git commit -m "<貼它給的 message>"
```

---

## ✅ Step 3 — 驗證決策邏輯 (WEEK1-02)

**貼這段:**

```
執行 tasks/WEEK1-02-verify-decision-tests-pass.md。
所有 18 個測試應該已經是綠的(在 WEEK1-01 中跑過),
這個 task 的重點是補上覆蓋率檢查與報告。

完成後一樣加 Completion Log,等我確認。
```

**檢查點**:
- `decision.py` 覆蓋率報告應該 ≥ 95%
- 如果不到 95%,看它有沒有補測試(這是 task 中明確要求的)

✅ 過了再貼 Step 4(同時 commit)。

---

## ⚠️ Step 4 — 在做 InsightFace 前的重要停頓

**先不要貼 prompt,先做這件事**:

`WEEK1-03` 會要 Claude Code 下載 InsightFace 模型權重(~300MB)並裝 torch、onnxruntime
這些大型依賴。在它開始之前,你要決定:

- 你的開發機磁碟空間夠嗎?(至少需要 5GB 空間)
- 你要用 CPU 還是 GPU?(MacBook / 一般筆電 → CPU)
- 網路頻寬還好嗎?(模型權重要從 GitHub / HuggingFace 拉)

如果都 OK,**貼這段:**

```
即將執行 tasks/WEEK1-03-wire-insightface.md。
這會安裝 torch、onnxruntime、insightface(總共約 2GB),
並下載 InsightFace 的 buffalo_l 模型權重(約 300MB)。

在開始之前,請:
1. 確認 backend/.venv 已啟動
2. 確認 backend/requirements.txt 中的版本沒有衝突
3. 告訴我預估的安裝時間
4. 列出你預期可能會遇到的問題(以便我提前準備)

確認完才開始裝。如果安裝過程中有任何套件版本衝突,停下來告訴我。
```

**檢查點**:
- Claude Code 應該會提到 numpy 版本(必須 1.x,不是 2.x)
- 應該預估 5–15 分鐘
- 應該提到可能要 build wheel 的問題

✅ 確認它有想到才放行。

---

## ✅ Step 5 — 接 InsightFace (WEEK1-03)

**貼這段:**

```
開始實作 WEEK1-03。

幾個額外要求:
- 在 detect_faces() 加 logging,記錄偵測到幾張臉與每張的 confidence
- 測試用的人臉圖片請放在 backend/tests/fixtures/,不要塞在 root
- 如果找不到合適的公領域測試圖,告訴我,我來提供
- 完成後跑一次 pytest -m "not ml" 確認舊測試沒回歸
```

**檢查點**:
- `pipeline.py` 中 `# TODO(week-1)` 標記應該都不見了(InsightFace 相關部分)
- `tests/test_pipeline_insightface.py` 存在且通過
- 舊的 18 個測試還是綠的

**最關鍵**:`pipeline.estimate_age()` **應該還是會拋 NotImplementedError**。
Claude Code 如果「順便」把它也實作了,把它退回去 —— 那是下一個 task 的工作,
混在一起會搞不清楚誰壞了。

✅ 過了再 commit、貼 Step 6。

---

## ✅ Step 6 — 接 MiVOLO (WEEK1-04)

**貼這段:**

```
開始實作 WEEK1-04。

特別注意:
- MiVOLO 的 GitHub repo 可能跟 task 描述的 API 有出入,以實際 repo 為準
- 如果發現 MiVOLO 的安裝或使用比預期複雜很多(例如要付費權重、要學術授權),
  停下來告訴我,我們考慮改用 DeepFace
- 測試圖片用真實年齡標註的開源資料集片段,不要用我自己 / 親友的照片
  (公開 repo 不能含個資)
- sigma_years = 4 是預設值,請在註解中說明這個選擇

完成後跑 pytest -m ml 確認 ML 測試通過。
```

**檢查點**:
- `pipeline.estimate_age()` 不再拋 `NotImplementedError`
- 對測試圖片回傳的年齡區間「合理」(誤差 < 10 歲)
- `requirements.txt` 註解了 MiVOLO commit SHA

✅ 過了 commit。

---

## ✅ Step 7 — 端對端測試 (WEEK1-05)

**貼這段:**

```
執行 tasks/WEEK1-05-integration-test-pipeline.md。

額外要求:
- TestClient 觸發 lifespan 的測試會非常慢(載模型),
  確保這類測試標記 @pytest.mark.ml 且不會被 default 跑
- fake DB 模式不要污染真實環境變數,用 fixture 與 monkeypatch
- 完成後,跑一次完整 pytest(不分 marker)確認全綠
```

**檢查點**:
- 可以用 `pytest -m "not ml"` 在 1 秒內跑完
- 可以用 `pytest -m ml` 跑 ML 整合測試
- 端對端測試確實打到 `/verify` 並收到合理回應

✅ 過了 commit。

---

## ⚠️ Step 8 — Supabase 串接前的重要停頓

`WEEK1-06` 需要真實 Supabase 連線。在開始前你要:

1. 登入 Supabase dashboard
2. 把 `supabase/001_initial_schema.sql` 整份貼到 SQL Editor 並執行
3. 在 Authentication → Users 建一個測試帳號(用你自己的 email)
4. 在 SQL Editor 跑:
   ```sql
   -- 把 <YOUR_AUTH_USER_ID> 換成你剛剛建的帳號的 uid
   insert into stores (id, name, owner_id) values (
     '00000000-0000-0000-0000-000000000001',
     'Demo Store',
     '<YOUR_AUTH_USER_ID>'
   );
   insert into policies (store_id, threshold_age, buffer_years, min_face_confidence)
   values ('00000000-0000-0000-0000-000000000001', 18, 3, 0.7);
   ```
5. 把 `SUPABASE_URL`、`SUPABASE_SERVICE_KEY`、`SUPABASE_JWT_SECRET` 寫進 `backend/.env`
6. **確認 `.env` 在 `.gitignore` 中(已經設好,但再確認一次)**

做完上面 6 件事再貼 prompt。

---

## ✅ Step 9 — Supabase 串接 (WEEK1-06)

**貼這段:**

```
我已經完成 Supabase 設置:
- schema 已套用
- 測試店家(id = 00000000-0000-0000-0000-000000000001)與 policy 已建立
- backend/.env 已填入連線資訊

開始執行 tasks/WEEK1-06-supabase-client-wire-up.md。

額外要求:
- 任何 DB 呼叫的錯誤訊息都不要包含 secrets(URL 可以,key 絕對不可以)
- repositories.py 的 fake mode 不要因為這個 task 被移除 —— 它對之後的測試還有用
- 跑完 test_repositories.py 後,請告訴我要去哪裡(Supabase dashboard 的哪個頁面)
  確認資料真的寫進去了
```

**檢查點**:
- `repositories.py` 所有 TODO 都實作了
- `test_repositories.py` 存在且通過
- 你親自登入 Supabase dashboard 看 audit_logs 表,應該有測試寫入的紀錄
- `cat backend/.env` 不能在任何 git diff 出現

✅ 過了 commit。

---

## 🎉 Week 1 完成檢查清單

**貼這段做最後驗收:**

```
WEEK1 應該全部完成了。請幫我整理:

1. 對照 tasks/INDEX.md,列出每個 WEEK1 task 的完成狀態
2. 跑一次完整測試:
   - pytest -m "not ml"(應該 1 秒內全綠)
   - pytest -m ml(應該全綠,但慢)
   - pytest -m db(需要 Supabase 連線)
3. 列出 WEEK1 過程中任何偏離原計畫的決策
4. 列出 WEEK1 過程中發現,但留到後面才做的事
5. 對 WEEK2 的建議:有沒有需要根據 WEEK1 的學習調整 task 設計

整理完不要動手改 WEEK2 的 task,等我評估。
```

**你親自做**:

```bash
# 看一下整體進度
git log --oneline

# 確認所有變更都 commit 了
git status

# 看 tasks/ 資料夾,所有 WEEK1 task 末尾都該有 Completion Log
ls tasks/
```

---

## 出狀況時的緊急指令

### Claude Code 鬼打牆(同個錯反覆嘗試)

```
停下來。把目前狀態整理給我:
1. 你想做什麼
2. 嘗試了哪幾種方法(列點)
3. 看到的錯誤訊息原文
4. 你目前的假設

不要再嘗試任何新的修改,等我回應。
```

### 它說要安裝新套件

```
等等。新增 dependency 需要我確認。請說明:
1. 套件名稱與版本
2. 為什麼必要(現有的不能用嗎?)
3. 是否會影響其他模組
4. 替代方案

確認前不要 pip/npm install。
```

### 它想改 schema 或 decision.py

```
這個檔案是核心檔案。先給我看你想改什麼、為什麼、影響範圍,
我看完才動手。
```

### 完全壞掉,想重來

```bash
# 你自己做,不是叫 Claude Code 做
git status                    # 看現在亂在哪
git stash                     # 暫存(以防有用的)
git checkout .                # 還原所有 tracked 檔案
git clean -fd                 # 刪掉新增的檔案(小心!)

# 然後重啟 Claude Code session,重新貼當前 step
```

---

## 後續(Week 2 以後)

Week 1 完成後,告訴我:
- 哪些 task 偏離計畫
- 你開發過程中的痛點
- 你想優先做的下一件事

我會根據實際情況產生 Week 2 的 task 檔案,而不是按死板的 roadmap 走。

這是有意的設計:**真實工程中,Week 2 該做什麼往往要等 Week 1 跑完才會清楚。**
