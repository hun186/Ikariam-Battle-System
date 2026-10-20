# Codex Memory Archive

此目錄只存放已從 active `.codex/*.md` 移出的、仍有追溯價值的舊條目。一般任務不得例行載入本目錄。

## Archive Index

| 檔案 | 內容範圍 | 歸檔日期 | 來源 active 文件 | 讀取時機 |
| --- | --- | --- | --- | --- |
| [land-BL008-research-history-2026-10.md](land-BL008-research-history-2026-10.md) | BL-008 長期追加式研究描述，已濃縮為 active 穩定任務，原條目僅供歷史審查 | 2026-10-19 | `.codex/backlog.md` | 需要還原舊數值推論時 |
| [land-research-handoff-2026-10.md](land-research-handoff-2026-10.md) | LAND R1/R80–89 and different 400-Slinger R76–80 research: 18 superseded Current Focus entries (archival wording only; use active facts instead) | 2026-10-19 | `.codex/memory.md` | 僅研究歷史、審查來源追溯 |


## 歸檔原則

- 優先移動條目，不反覆複製整份 active 文件快照。
- 檔名使用主題與時間範圍，例如 `memory-2026-07.md`、`decisions-2026.md`。
- 歸檔內容仍不得包含秘密、個資、完整敏感 payload 或不必要的命令輸出。
- 能由 Git 歷史可靠重建、而且對後續推理沒有持久價值的細節不需另行歸檔。
- 只有使用者要求追溯、active 文件明確連結、或需釐清已取代設計時才讀取特定檔案。

## 濃縮檢查

歸檔後確認 active 文件仍保留：

- 目前有效的專案目的、架構、契約與工作命令。
- 所有 open known issues。
- 所有 accepted／in-progress backlog。
- 所有 active decisions 及 supersede 關係。
- 未完成 stub 與必要 handoff。
