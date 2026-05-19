# WEEK1-02: Verify Decision Logic Tests Pass

## 目標
確認 `backend/app/core/decision.py` 與其 18 個單元測試 100% 綠燈。
這是系統最核心的純邏輯,必須穩固。

## 步驟

1. 跑:
   ```bash
   cd backend
   PYTHONPATH=. python -m pytest tests/test_decision.py -v
   ```
2. 預期看到 **18 passed**。
3. 跑覆蓋率檢查:
   ```bash
   pip install coverage --quiet
   PYTHONPATH=. coverage run -m pytest tests/test_decision.py
   coverage report --include='app/core/decision.py'
   ```
4. 預期 `decision.py` 覆蓋率 ≥ 95%。

## 驗收條件

- [ ] 所有 18 個測試通過
- [ ] `decision.py` 覆蓋率 ≥ 95%
- [ ] 若覆蓋率不足,在 `tests/test_decision.py` 補測試覆蓋遺漏的分支

## 重要

如果你看到測試失敗,**不要修改測試**。先讀 `app/core/decision.py` 的 docstring
與 `docs/decision-policy.md`,確認測試對應的是文件描述的政策。
測試是規格,程式碼配合規格。

## Completion Log

**完成時間**:2026-05-18

**結果**:全綠 + 100% 覆蓋率(超過 95% 門檻)。

**驗證**:
- `pytest tests/test_decision.py -v` → 19 passed(原 18 + 新增 1)
- `coverage report --include='app/core/decision.py'` → `56 / 56 stmts, 100%`

**過程**:
- 初次覆蓋率 98%,缺 line 93 — `DecisionResult.to_dict()` 整個方法沒被測。
- `to_dict()` 是 audit log JSON 序列化的契約,雖然 98% 已過門檻,但這是
  下游(API 回應、audit 寫入、稽查匯出)會依賴的 shape,值得 pin 住。
- 新增 `TestSerialization::test_to_dict_shape_and_confidence_rounding`,
  同時驗證 dict 結構與 `face_confidence` 的 `round(_, 3)` 行為。

**未修改**:
- 沒動任何既有測試斷言(規格不動,只加新測試)
- 沒動 `decision.py` 本身
- 沒動 `docs/decision-policy.md`

**對後續的建議**:
- 之後 `repositories.py` / API 層真的開始寫 audit log 時,可以重用這個
  dict shape 當 fixture,避免重複定義。

