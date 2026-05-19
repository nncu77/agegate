# Conservative Decision Policy — 設計說明

> 這份文件解釋 AgeGate 為何採用「保守決策」而非直接輸出年齡。
> 這是整個系統最重要的工程決策,也是面試時最值得展開的技術點。

## 問題:點估計的陷阱

年齡估測模型(MiVOLO、DeepFace、Rekognition AgeRange⋯)的輸出本質上是
**機率分布**,但工程上常被簡化為「我預測 X 歲」這個點估計。

直接用點估計做合規判斷會出兩種問題:

1. **False negative(放未成年通過)** — 模型把 17 歲估成 19 歲,
   系統說「通過」,店家被罰。
2. **False positive(攔下成年人)** — 模型把 25 歲估成 17 歲,
   系統說「拒絕」,顧客不爽走人。

這兩種錯誤的**代價非對稱**:第一類有法律責任,第二類只有客訴。
工程設計必須反映這個非對稱性。

## 解法:三態決策 + 安全緩衝

AgeGate 的核心輸入不是「年齡」,而是 `[age_low, age_high]` 區間,
搭配 `face_confidence`。輸出是三態:

| 結果 | 觸發條件 | 操作員行動 |
|---|---|---|
| 🟢 PASS | `age_low ≥ threshold + buffer` | 正常服務 |
| 🔴 REJECT | `age_high < threshold` | 拒絕交易 |
| 🟡 MANUAL_CHECK | 其他情況 | **強制查驗證件** |

### 為什麼 PASS 需要 buffer?

如果 `age_low ≥ threshold` 就放行,代表模型只要說「最低 18 歲」我就過。
但模型的 95% 信賴區間並不等於真值區間 — 真值落在區間外的機率不為零。

加上 `buffer_years = 3` 之後,放行條件變成「模型認為最低 21 歲」。
這把臨界區的 false negative 大幅降低。

代價是 false positive 上升 — 21 歲以下的人即使是成年,
仍會被要求查驗證件。這個代價我們接受。

### 為什麼 REJECT 用 `age_high < threshold`?

對稱於 PASS。只有當「最高估測」都低於門檻,我們才敢直接拒絕。
邊界年齡的拒絕同樣會誤傷成年人,但因為這時系統會把 MANUAL_CHECK
讓給人類處理,所以實務上會走 MANUAL 路徑,不會直接 REJECT。

## 與業界做法的比較

商用 API 如 AWS Rekognition 直接回傳 `AgeRange: { Low, High }`,
但**不告訴你怎麼做決策**。決策邏輯是應用層的責任。多數整合範例會
天真地用 `(Low + High) / 2 ≥ threshold` 來判斷 — 這正是 AgeGate
要避免的反模式。

## 操作員覆寫機制

MANUAL_CHECK 不是「系統不確定就丟給人」這麼簡單,它是一個
**設計上的功能**:讓人類查驗證件,然後把人類的決定也記錄下來。

```
audit_log row:
    decision: 'manual_check'
    reason: 'range_straddles_threshold'
    operator_override: 'pass'       ← 操作員看了證件,確認成年
    operator_note: '駕照 A1234**, 25 歲'
    operator_acted_at: 2026-05-18T14:23:11Z
```

這份記錄在被稽查時是「店家有盡到查驗義務」的證據。

## 參數敏感度

| 參數 | 預設 | 調高的效果 | 調低的效果 |
|---|---|---|---|
| `threshold_age` | 18 | 法定門檻直接搬,不該動 | 違法 |
| `buffer_years` | 3 | 更多 MANUAL,更少 false negative | 更多 PASS,風險上升 |
| `min_face_confidence` | 0.7 | 更多重拍要求,品質提升 | 模糊照也接受,品質下降 |

實務上建議:菸酒場景門檻 18 / buffer 3;電子煙與夜店 20 / buffer 3。
高客流場景可考慮 buffer = 2 以降低 MANUAL 比例,但要做好統計監控。

## 未來改進方向

- **模型不確定度校準**:目前用固定 sigma 推 `age_low / age_high`,
  更好的做法是讓模型直接輸出 well-calibrated 區間。
- **族裔偏差量化**:已知年齡估測模型對亞洲年輕女性常低估,
  buffer 可依 demographic 動態調整(但要注意這本身是 fairness 議題)。
- **多幀融合**:單張照片誤差大,連續擷取 3 幀取交集區間會更穩。
