# 用 Claude Code 開發這個專案

> 這份是給你(人類)看的。教你怎麼跟 Claude Code 互動,以及什麼時候該介入。

## 第一次啟動

```bash
cd agegate
claude
```

Claude Code 啟動後會自動讀 `CLAUDE.md`、`AGENTS.md`,知道規矩。

第一個 prompt 建議:

```
請讀完 CLAUDE.md、AGENTS.md、tasks/INDEX.md,然後告訴我你的理解,
以及第一個要做的 task 是哪一個。先不要動手。
```

確認它說對之後再讓它開始做。

## 常用 prompt 範本

### 開始下一個 task

```
請執行 tasks/WEEK1-01-bootstrap-environment.md。
完成後在檔案末尾加 Completion Log,並把 INDEX.md 標記為 [x]。
```

### 中途暫停確認

如果你想中途看一下進度:
```
目前進度到哪?有遇到任何決策需要我確認的嗎?
```

### 卡住時

如果 Claude Code 看起來鬼打牆(同個錯誤反覆嘗試):
```
停下來。先把目前狀態整理給我看:
1. 你想做什麼
2. 嘗試了什麼
3. 看到什麼錯誤
4. 你的假設
不要再嘗試任何新的修改,等我回應。
```

### 跑完一個 phase

```
WEEK1 全部完成了。請:
1. 列出實際完成的 task(對照 INDEX.md)
2. 列出任何偏離原計畫的決策
3. 建議 WEEK2 task 是否需要根據 WEEK1 的學習做調整
```

### 想加新功能但沒在 task 裡

```
我想加 <X>。請評估:
1. 是否該現在做(vs 留到後面 phase)
2. 該寫成新 task 還是塞進現有 task
3. 影響範圍
評估完不要動手,等我決定。
```

### Code review

```
請對 backend/app/<file>.py 做 self code review,
從 AGENTS.md 的標準來檢查。列出可以改進的點,
但不要直接改 —— 我先看你的判斷。
```

## 你必須親自做的事

- **Git 操作**:Claude Code 不 commit/push。你看完它的工作再 commit。
- **Secrets**:Supabase URL/key、AWS credentials 等,你自己貼到 `.env`,
  不要叫 Claude Code 幫你「生一個」。
- **第三方服務註冊**:Supabase、Vercel、Railway 帳號自己開。
- **架構級決策**:換 ML 模型、改 schema、加新 dependency 都要你拍板。

## Claude Code 該停下來問你的時機

CLAUDE.md 列出了清單,但實務上你應該主動檢查:

- 看到 `pip install` 不在 requirements.txt 的套件 → 問為什麼
- 看到改 `supabase/*.sql` → 確認是否需要新 migration 檔
- 看到 `decision.py` 被修改 → 確認 `test_decision.py` 也同步更新
- 看到任何 `--force`、`rm -rf` → 直接打斷,問清楚

## 進度檢查節奏建議

- **每完成一個 task**:看一下 Completion Log,git diff 看實際改了什麼
- **每完成一個 Phase**:跑一次完整測試,確認沒回歸
- **每天結束**:commit 當天的進度,即使還沒做完一個 task

## 救援模式

如果 Claude Code 把專案搞壞了(這會發生):

1. `git status` 看改了什麼
2. `git stash` 或 `git checkout .` 還原
3. 重啟 Claude Code session
4. 提供更明確的 task 指示,或拆得更細

不要試圖讓它「修好它自己的爛攤子」—— 通常重來比較快。

## 何時該 fork 出新 task 檔

Claude Code 在 task 過程中經常會發現「啊這個應該也要做」。
正確流程:

1. 它在 Completion Log 中提出建議
2. 你看完評估
3. **你**(不是它)決定要不要,並建立新 task 檔
4. 加進 INDEX.md

這個流程的價值是避免 scope creep —— 不然一個 task 會無限長大。
