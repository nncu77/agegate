# 本地開發設定

## 前置需求

- Python 3.11(InsightFace 對 3.12 還沒完全支援,建議用 3.11)
- Node.js 20 LTS
- Supabase CLI(`brew install supabase/tap/supabase` 或對應系統指令)
- 一個 Supabase 專案(免費方案足夠開發)

## 1. 後端

```bash
cd backend

# 建立 venv
python3.11 -m venv .venv
source .venv/bin/activate

# 安裝依賴
pip install -r requirements.txt

# 安裝 MiVOLO(從 source)
pip install git+https://github.com/WildChlamydia/MiVOLO.git

# 複製設定
cp .env.example .env
# 編輯 .env,填入 Supabase 連線資訊

# 下載 ML 模型權重(第一次跑會自動下載 InsightFace,但建議手動以避免
# 第一個 request 的冷啟動)
python -c "from insightface.app import FaceAnalysis; \
           FaceAnalysis(name='buffalo_l').prepare(ctx_id=-1)"

# 啟動
uvicorn app.main:app --reload
```

API 開在 `http://localhost:8000`,文件在 `http://localhost:8000/docs`。

## 2. Supabase

```bash
# 套用 schema
supabase db push  # 或在 dashboard 的 SQL Editor 貼上 supabase/001_initial_schema.sql
```

開發階段建一個假店家方便測試:

```sql
insert into stores (id, name, owner_id)
values (
  '00000000-0000-0000-0000-000000000001',
  'Demo Store',
  auth.uid()  -- 先用 dashboard 註冊一個帳號,複製 uid 進來
);

insert into policies (store_id, threshold_age, buffer_years, min_face_confidence)
values ('00000000-0000-0000-0000-000000000001', 18, 3, 0.7);
```

## 3. 前端

```bash
cd frontend
npm install
cp .env.example .env.local
# 編輯 .env.local 填入 NEXT_PUBLIC_API_URL 與 Supabase 公開 key

# 攝影機需要 HTTPS 或 localhost。localhost 直接 npm run dev 就好。
npm run dev
```

打開 `http://localhost:3000`。

## 常見問題

**Q: 攝影機在 IP 位址(192.168.x.x)開不起來?**
A: WebRTC `getUserMedia` 需要 secure context。在區網測試請用 mkcert 起 HTTPS:
```bash
brew install mkcert
mkcert -install
mkcert localhost 192.168.1.10
```

**Q: `pip install insightface` 失敗?**
A: 通常是 build dependencies。macOS:`brew install cmake`。
Ubuntu:`apt install build-essential cmake libopencv-dev`。

**Q: InsightFace 跑很慢?**
A: 你應該在 CPU 上跑,單張 ~200ms 是正常的。改用 GPU 需要 onnxruntime-gpu
而非 onnxruntime,並把 `INFERENCE_DEVICE=cuda`。

**Q: 測試決策邏輯時不想跑 ML 怎麼辦?**
A: `pytest tests/test_decision.py` 不依賴模型,可單獨跑。ML 整合測試請開
另一個 marker(目前還沒寫,Week 1 task)。
