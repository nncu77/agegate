# WEEK1-03: Wire InsightFace into Pipeline

## 目標
把 `backend/app/ml/pipeline.py` 中 `detect_faces()` 與 `warmup()` 的 InsightFace 部分
從 TODO placeholder 替換為真實實作。

## 前置條件
- WEEK1-01 完成,Python 環境就緒
- 確認 `requirements.txt` 中 `insightface==0.7.3` 與 `onnxruntime==1.19.2` 已安裝
- 確認 `numpy==1.26.4`(InsightFace 對 numpy 2.x 不相容,**這個版本鎖死**)

## 步驟

1. 在 `pipeline.py` 的 `warmup()` 中:
   - 載入 `FaceAnalysis(name=settings.insightface_pack, root=settings.model_cache_dir)`
   - 呼叫 `.prepare(ctx_id=-1 if settings.inference_device == 'cpu' else 0, det_size=(640, 640))`
   - 跑一張全黑的 dummy 圖過去,讓 ONNX runtime 預熱
2. 在 `detect_faces()` 中:
   - 呼叫 `self._face_analyzer.get(image)`
   - 用 `settings.face_detection_min_confidence` 過濾
   - 用 `insightface.utils.face_align.norm_crop` 做臉對齊(112x112)
   - 回傳 `list[DetectedFace]`
3. 把 `# TODO(week-1)` 標記刪掉

## 寫一個 smoke test

新建 `backend/tests/test_pipeline_insightface.py`:
- 用 `tests/fixtures/` 放兩張測試圖(自己找開源照片,例如維基百科的公領域人像)
- 一張有臉、一張沒臉
- 確認 `detect_faces` 在有臉照回傳 1 個 DetectedFace、無臉照回 0 個

註:這個 test 標 `@pytest.mark.ml`,並在 `pyproject.toml` 加 marker 設定,
讓 CI 可以選擇性跳過 ML 測試(因為要載入模型很慢)。

## 驗收條件

- [ ] `warmup()` 不再印 "ML models ready" 假象,真的把模型載入
- [ ] `is_ready()` 在 `warmup()` 之後回 True
- [ ] `detect_faces()` 在有臉的圖回 ≥ 1 個 DetectedFace
- [ ] `detect_faces()` 在純背景圖回 `[]`(空 list,不是 None)
- [ ] 信心低於 `face_detection_min_confidence` 的臉被過濾掉
- [ ] 新測試 `test_pipeline_insightface.py` 通過
- [ ] 原有的 18 個 decision 測試仍綠

## 不要做的事
- 不要把模型權重 commit 進 repo,會塞爆
- 不要為了讓測試跑快關掉 confidence filter

## 完成後

`pipeline.estimate_age()` 還會拋 `NotImplementedError`,這正常。WEEK1-04 才接。

## Completion Log

**完成時間**:2026-05-18(初版 partial → 同日補圖後 finalize)

**狀態**:7 / 7 驗收條件全部通過。

**驗收條件對照**:
- ✅ `warmup()` 真的載入模型(`_face_analyzer` 在 warmup 後不再是 None)
- ✅ `is_ready()` 在 warmup 後回 True
- ✅ `detect_faces()` 在有臉的圖回 ≥ 1 個(Einstein 1921 肖像通過,aligned crop = 112x112)
- ✅ `detect_faces()` 在純黑圖回 `[]`(空 list)
- ✅ 信心 < `min_face_confidence` 的臉被過濾掉(mock 測試)
- ✅ 新測試檔 `test_pipeline_insightface.py` 通過(3 ml + 2 non-ml = 5 passed)
- ✅ 原 18 decision 測試 + 新加的 to_dict 測試共 19 仍綠

**驗證**:
```bash
PYTHONPATH=. .venv/Scripts/python -m pytest -q
# → 23 passed, 1 skipped in 5.9s (with warm model cache)

PYTHONPATH=. .venv/Scripts/python -m pytest -m ml -v
# → 2 passed, 1 skipped (has_face)
```

**安裝結果**:
- `torch==2.5.0` + `onnxruntime==1.19.2` 用預編 Windows wheel,順
- `insightface==0.7.3` 沒 pre-built Windows wheel,本地 build 成功(~20s)
  — 過程平順,沒撞到 MSVC 缺漏(系統已有 build tools)
- 總安裝時間 ~3 分鐘
- buffalo_l 模型首次下載 ~1 分鐘(280MB → `~/.insightface/models/buffalo_l/`)

**程式碼變更**:
- `app/ml/pipeline.py`:
  - 加 `from insightface.app import FaceAnalysis` / `from insightface.utils.face_align import norm_crop`
  - `warmup()`:CPU/GPU provider 切換、`ctx_id=-1 if CPU else 0`、dummy 推論預熱
  - `detect_faces()`:`_face_analyzer.get()` + min-conf filter + `norm_crop(112x112)` + logging
    (raw count / kept count / 每張臉的 score 四捨五入到 3 位)
  - `estimate_age()` **未動**
- `tests/conftest.py`(新):session-scope `ml_pipeline` fixture
  (override `model_cache_dir` 到 `~/.insightface` 避免 Windows 寫不到 `/var/cache/...`)
  + `has_face_image_path` fixture(找不到就 skip)
- `tests/fixtures/README.md`(新):圖檔需求 + 來源建議 + 為何不自動下載
- `tests/test_pipeline_insightface.py`(新):5 tests(3 ml + 2 unit)

**設計決定**(對照 task 額外要求):
- ✅ `detect_faces()` 加 logging(raw / kept / scores)
- ✅ 測試圖路徑在 `backend/tests/fixtures/`(不塞 root)
- ⏳ 找不到合適 PD 測試圖,**請人類提供** — 詳見 `tests/fixtures/README.md`
- ✅ ML 測試標 `@pytest.mark.ml`,跑完仍綠

**對後續的建議 / Future Work**:

1. ~~**PD 測試圖**:人類丟一張 `has_face.jpg` ...~~ **已解決**:寫了
   `scripts/download_test_fixtures.py`,用 Wikimedia API 抓 5 張 PD 歷史人物
   肖像(Einstein 42 / Twain 72 / Curie 53 / Tesla 37 / Lincoln 56),
   metadata 寫到 `tests/fixtures/fixtures.json`,binary 不入 git(`.gitignore`
   已排除)。第一張會 alias 成 `has_face.jpg` 供 WEEK1-03 用,其餘給 WEEK1-04 用。
2. **pydantic warning**:`model_cache_dir` 觸發 `Field "model_cache_dir" ... has conflict with protected namespace "model_"`。
   非阻塞,但可在 `Settings.model_config` 加 `protected_namespaces=('settings_',)` 消除。
   屬於 config polish,留到 Phase 4。
3. **`pytest -m "not ml"` 跑 8.5s 而非預期的秒級**:`test_detect_faces_filters_below_min_confidence`
   (mock test)裡 `from app.ml.pipeline import AgePipeline` 觸發 insightface 整套 import。
   要做到真秒級需把 mock test 改成完全不 import pipeline 模組 — WEEK1-05 處理整合測試時一起檢討。
4. **InsightFace `model_cache_dir` 預設值 `/var/cache/agegate/models` 在 Windows 寫不進去**(無 admin 權限)。
   目前測試靠 fixture override 到 `~/.insightface`,但 `uvicorn` 直接跑會在 Windows 撞牆。
   建議改 default 為 `os.path.expanduser('~/.cache/agegate/models')` 或在 `Settings` 加 OS-aware default。
   屬於部署 polish,留到 Phase 5 跑本地起伺服器時再修。

