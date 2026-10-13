# AGENTS.md

本檔是此 repository 的 Codex 長期工作規則與上下文路由器。保持短小、可驗證、與目前專案一致；詳細知識放在 `.codex/` 專門文件。

## 指令優先順序與事實來源

- 目前使用者要求高於本檔中的一般工作慣例；安全、權限與明確禁止事項仍須遵守。
- 實際程式碼、設定、測試、schema 與可重現行為是專案事實來源。
- 文件與程式碼衝突時，先查證，不要直接假定任一方正確；確認後同步修正過時文件。
- 歷史紀錄只能解釋過去，不能取代目前程式碼與 current-state 文件。
- 不得把 API key、token、密碼、cookie、private key、連線字串、個資或其他機密寫入程式碼、測試輸出或 `.codex/` 文件。

## 專案快速摘要

以下區塊由首次初始化或後續明確的專案級變更維護；一般任務不要重寫其他規則。

<!-- BEGIN CODEX PROJECT QUICKSTART -->
- 初始化狀態：`INITIALIZED`
- 專案目的：以可解釋、可重現的 evidence-aware engine 提供 browser Ikariam Phase A 戰鬥模擬
- 主要技術：Python 3.11+ domain package、無 framework ASGI／Vercel adapter、vanilla HTML/CSS/JS
- 主要入口：`ikariam_battle.simulate()`、`POST /api/simulate`、`asgi:application`
- Battle domain 由 battlefield id 決定；UI 可先選 Land/Naval 來篩 battlefield，但不得另造第二個 executable domain truth。每一方另有 `army_kind=player|barbarian`：兩套兵種不可在同一側混用。Barbarian Village units 為 Land；Barbarian Fleet units 為 Naval，可在五種 `naval-mini/small/medium/large/max` 戰場執行；海軍 Help 五級距 Level 0+/8+/15+/22+/29+ 只證實 slot 數與容量，傷害位置排序仍採獨立 empirical reference，Level 來源與自動對應不得猜測。Barbarian Forge=0、Workshop=0、單一立即 entry batch、同 unit 不分 wave、軍分/資源計分基礎=0；目前兵量手動輸入，不依村落／艦隊階數自動生成。
- Land 戰場 UI 以遊戲實戰畫面排列為基準：前排為 `Flank | First/Main | Flank`，後排為 `Air bomber | Third/Artillery | Air defense`；也就是氣球在左、直昇機在右。這只是 presentation，不得藉此改動 engine slot identity、capacity 或 targeting。
- Slot 填入／同 wave 回合重建要依 PDF damage priority 的中央優先實體順序；回合開始不得把倖存兵留在可由已支援 formation 規則消除的內側空洞。Same-wave rebuild 本身仍不得跨 wave、跨 line 或新增 slot。其後有三條窄化的 cross-wave compaction：(1) 同一 entry batch 的 Heavy Infantry 可在既有 First-line slots 內跨兵種中央優先重排；(2) 相同 unit_id 的不同 waves／entry batches 可在相同既有 runtime line slots 內依 arrival/batch 順序接替，ammo、damage、upgrade 與 wave identity 必須各自保留；此 generic same-unit compaction 與 cross-wave rebuild safety guard 對所有 finite-ammo native line 都必須 ammo-aware：若 runtime line 就是該兵種 native line，可部署數不得超過剩餘 primary `ammo_pool_shots`，0 彈藥的較早 wave 不得因 formation precedence 把 slot 從仍有彈藥的後續 wave 搶回，也不得被 safety guard 誤判為仍需回填 native-line slot。此限制適用 Land／Naval 的 Second、Third 與 Air 等 finite-ammo native lines；耗彈 Long-Range 轉 First 使用 secondary weapon 屬 non-native fallback，另依 fallback／weapon-selection 規則處理，不受 primary-ammo native-line cap 誤擋；(3) Land Third/Artillery 另有 mixed-unit same-batch replacement：先讓規則 (2) 的 same-unit ammo-aware 接替完成，若仍有既有空 Third slot，才由該 slot 當前 owner 所在 entry batch 的其他 Third-line combat wave 依既有 strongest/weakest concrete-group policy 接替。第三條不得取代仍有兵的 slot、不得新增 physical slot、不得把不同 unit type 跨 entry batch 或跨 line；不同兵種跨 entry batch 仍 unsupported。
- 後續批次抵達時，非 First 的原生戰線若完全沒有任何實體 slot owner，且只有一個符合資格的新抵達 wave，可按該戰線 geometry.damage_priority 建立首次部署格子；仍需遵守 ammo cap，不能取代既有格子（即使該格 units=0）、跨線或替多個競爭 wave 猜測選擇順序。First 等仍保留原本安全邊界。
- 延遲增援即使已從舊 wave 接手部分 native-line 既有 slots，只要仍有可部署（扣除目前已部署 units 所需彈藥）Reserve，且幾何上還有從未建立過的 physical slot，必須保留 `UNKNOWN-CROSS-WAVE-FORMATION-REBUILD` 安全邊界，不可因該 wave `slots` 非空就忽略、讓模擬錯誤繼續；但已存在的 units=0 slot 仍屬既有 owner，可由既有 handoff 規則處理。
- Land initial formation 的同線兵種選擇不得再用 `unit_id` 字母序代理強弱。Long-range (`second`) 與 Artillery (`third`) 依官方 strongest-first 加上使用者 partial-group 實戰，逐 slot 比較可實際填入數量 × primary weapon Damage；因此 full group 會優先 Sulphur Carabineer/Mortar，但 partial group 可由較多的較弱單位勝出（例如 1 Mortar < 6 Battering Rams、5 Mortars > 6 Battering Rams）。
- Barbarian Clubman 的 tactical semantic class 是 `heavy_infantry`、native line 是 `first`；與 Spearman 的 equivalence 只可用於有證據的數值推導，不得反推為 Light Infantry。
- 同一 runtime formation 可由多種 unit type 組成；Attacking Matrix 必須以整個 formation 共用 row-major source columns。Target address book 以「相同 penetrable target-wave set」為共享邊界，而且必須在該 formation firing phase 的第一發之前 freeze runtime-line membership、eligibility set 與 slot addresses；中途傷亡不得讓 promoted Light wave 因 `_runtime_line()` 回退 native line 而縮小 address book。穿甲資格相同的 source waves 共用 frozen address book；若 weapon-specific `ATK>DEF` 導致合法 target set 不同，則各自 freeze 對應 address book。每個 source wave 的 weapon、Workshop、ammo 仍獨立。
- Target eligibility 必須先於 shot/ammo 消耗判斷：selected weapon 的 effective ATK 必須嚴格大於 candidate effective DEF；`ATK <= DEF` 的目標不可建立攻擊、不可耗彈，應繼續找下一個合法 priority target。Active Town Wall 存在時，Land Artillery 的已知 priority 為 Wall 優先於普通 First。Strict 仍以 `UNKNOWN-TOWN-WALL-COMBAT` 保護完整牆戰；Experimental 已接入 section-state core：可穿甲 Artillery 先集中牆段，但牆段原本佔有守方 First 位置，破口當回合不可立即補入守方方陣，必須從下一回合開始依前一回合破洞位置填入 First；攻守雙方 Flank 在有牆時均不部署，全牆破盡的下一回合才可上場（野戰壓制牆除外）；城牆破洞進入下一回合時，先由 native First（如 Hoplite）依中央優先填已破牆格，再讓耗盡主彈藥的 Long-Range／Light 等 non-native First fallback 競爭剩餘且確實已破牆的位置（有牆時被鎖在 Reserve、尚無側翼格 owner 的 Light Infantry 也能在這個限定 wall-gap fallback 階段進場；不可放寬一般無牆 fallback 的 live-native-line 前提），絕不能先讓火槍轉 First 佔掉原生方陣的位置，更不能填未破的牆格；多個 native Waves 爭奪新空牆格而 precedence 未證實時必須 UNKNOWN，不可猜測。可整除的 surviving-section round-start damage redistribution 可執行。同 geometry 的 initial open-field → wall re-entry 可直接切換；跨 geometry 仍由 `UNKNOWN-GARRISON-BATTLEFIELD-TRANSITION` 保護。牆段先後位置與每發皆視為 successful wall hit、牆本身攻擊停用，均以具名 Experimental assumptions 暴露；非整除 redistribution 仍停在 `UNKNOWN-TOWN-WALL-REDISTRIBUTION-ROUNDING`。
- Accuracy 的官方演算法仍未知；Strict 必須保留 `UNKNOWN-ACCURACY`。Experimental 不得把 Accuracy 當成每發獨立 Bernoulli miss：目前 `EXP-ACCURACY-CONCENTRATION-001` 只在已選定 slot 內做 deterministic individual-target concentration；one-shot-capable hit 不製造 miss，非 one-shot 以最殘血目標 remaining-HP% 與 weapon Accuracy 的門檻決定 spread/focus。新實戰證據可替換此假說，但不得悄悄改動 AM addressing、target priority、Damage、Ammo 或 firing chronology。
- 最快驗證：`pytest -q`
<!-- END CODEX PROJECT QUICKSTART -->

若狀態仍為 `UNINITIALIZED`：

- 使用者明確要求初始化時，依 `CODEX_BOOTSTRAP.md` 執行。
- 使用者要求實作變更時，先做足以安全完成任務的最小盤點，並一併初始化相關文件。
- 使用者只要求分析、說明或診斷時，不因本檔自行取得寫入授權；可盤點並在結果中指出尚未初始化。

## 新專案初始化與 README 閘門

只有在使用者明確要求「初始化新專案」、「執行 bootstrap」或授權建立專案基礎文件時，才執行本節；單純分析、診斷或回答問題不構成修改 `README.md` 的授權。

初始化時先檢查 repository root 的 `README.md`，並判定為下列其中一種狀態：

| 狀態 | 判定 | 動作 |
| --- | --- | --- |
| `ADEQUATE` | 有實質內容，且與目前程式、設定和專案目的大致一致 | 保留；只修正已證實的錯誤，不為統一格式而重寫 |
| `NEEDS_UPDATE` | 有可保留內容，但缺少關鍵使用資訊或已有明確過時內容 | 沿用原本語氣與結構，做最小必要補強 |
| `MISSING_OR_PLACEHOLDER` | 不存在、近乎空白、只含產生器預設文字，或內容明顯屬於另一專案 | 依 `.codex/templates/project-README.template.md` 建立適合本專案的 `README.md` |

一份適合新專案的 README 至少應做到：

- 用專案名稱和一段簡短文字說清楚用途、目前階段與主要使用者。
- 只列已由 manifest、設定、CI、程式入口、測試或使用者要求證實的安裝、執行及驗證方式。
- 若命令尚無法證實，明確標示「待確認」，不得依語言生態慣例猜一條看似合理的命令。
- 說明必要設定與環境變數名稱，但不得包含真實憑證、秘密或個資。
- 視專案需要交代主要目錄、資料／模型／產物邊界、已知限制及延伸文件連結；不適用的段落應刪除。
- 不捏造授權條款、版本、相容平台、完成度、效能數字、徽章、部署狀態或外部連結。

建立或更新 README 時：

1. 先保留原作者仍正確的說明、語言與有用連結，不整份覆寫已有實質內容的文件。
2. 若 repository 幾乎是空的，只能根據使用者已說明的專案目的建立最小 README，並把尚未存在的功能和命令標為規劃中或待確認。
3. 若連專案目的都無法從 repository 或本次要求證實，先詢問使用者，不自行編造定位。
4. 完成後同步 `.codex/project.md`；若 README 記載了可執行命令，也要與 `.codex/workflows.md` 交叉核對。
5. 最終回報 README 的判定狀態、採取的動作，以及仍待使用者確認的內容。

## 上下文載入路由

開始任務時：

1. 固定閱讀 `.codex/project.md`。
2. 固定閱讀 `.codex/memory.md` 的 Current Focus 與 Recent Outcomes。
3. 依下表只讀取與任務直接相關的文件。
4. 修改特定子目錄前，檢查該路徑是否有更接近的 `AGENTS.md` 或 `AGENTS.override.md`。
5. 一般任務不得主動讀 `.codex/archive/`；只有追溯歷史、current 文件明確引用，或釐清已被取代的決策時才讀。

| 任務類型 | 額外閱讀 |
| --- | --- |
| 安裝、執行、測試、lint、build、部署 | `.codex/workflows.md` |
| 模組邊界、資料流、跨層重構、依賴方向 | `.codex/architecture.md` |
| API、CLI、schema、檔案格式、事件、外部整合 | `.codex/contracts.md` |
| 技術選型、相容性取捨、重大設計變更 | `.codex/decisions.md` |
| 除錯、環境限制、已知失敗 | `.codex/known_issues.md` |
| 排程、優先度、延後工作、技術債 | `.codex/backlog.md` |

若文件不存在，只有在使用者要求的變更需要它，或使用者明確要求初始化記憶機制時才建立；不要為湊齊格式新增無內容文件。

## 探索與實作原則

- 先定位最小相關範圍，再擴大搜尋；優先使用 `rg` 與 `rg --files`。
- 預設略過 generated、vendor、dependency、build、cache、model、dataset、large output 與 archive 目錄，除非任務明確涉及。
- 先找既有入口、測試與相似實作；避免建立重複功能或新的通用雜物模組。
- 保留使用者既有變更，不修改無關檔案，不做未經要求的大規模重構。
- 修改應沿用目前模組邊界與風格；若必須跨越邊界，先說明理由並更新架構或決策文件。
- 不以 mock data、hard-coded output、fake success、silent fallback 或純 UI 假象宣稱真實功能完成。
- 暫時性 stub 必須在程式碼中明確標記，並只在使用者接受延後工作後加入 `.codex/backlog.md`。
- 未經查證不要猜測命令、路徑、環境變數、介面或部署方式。

## 計畫與變更範圍

符合任一情況時先建立簡短計畫：跨多模組、契約或資料遷移、不可逆操作、風險較高、需求仍有關鍵歧義，或預估需多個驗證階段。

計畫至少說明：

- 要改變的可觀察結果。
- 主要受影響檔案或模組。
- 需要維持的相容性或不變量。
- 驗證方式。

小型、明確、低風險修改可直接執行，不為流程製造多餘文件。

## 驗證與完成定義

完成實作前：

1. 從 `.codex/workflows.md` 選擇最小但足以證明變更的檢查。
2. 先跑最接近修改範圍的測試，再視風險擴大。
3. 檢查 diff 是否包含無關改動、秘密、產物或意外格式化。
4. 確認行為、測試與相關 current-state 文件一致。
5. 回報實際執行的驗證及結果；未執行的驗證不可暗示為已通過。

若受 sandbox、網路、權限、外部服務、缺少 runtime 或資料限制而無法驗證：

- 明確說明被阻擋的檢查與影響。
- 盡可能執行安全的替代檢查。
- 只有該限制可重現且可能影響後續任務時，才記入 `.codex/known_issues.md`。

## 專案記憶更新規則

每次完成任務時先做「記憶分流」，不要求每個檔案都更新：

| 資訊變化 | 更新位置 |
| --- | --- |
| 專案目的、範圍、技術、入口、目錄地圖 | `.codex/project.md`，必要時同步 Quickstart |
| 安裝、執行或驗證命令 | `.codex/workflows.md` |
| 目前模組、依賴方向、資料流、不變量 | `.codex/architecture.md` |
| 目前對外或跨模組介面 | `.codex/contracts.md` |
| 具有長期影響且存在取捨的設計選擇 | `.codex/decisions.md` |
| 已證實、尚未解決且可能再遇到的問題 | `.codex/known_issues.md` |
| 已接受的延後工作或完成正確性所需後續 | `.codex/backlog.md` |
| 本次有持久參考價值的結果與驗證 | `.codex/memory.md` |

不要記錄：完整命令輸出、聊天逐字稿、可由 diff 直接看出的瑣碎改動、一次性失敗嘗試、未採用的臨時猜測、重複摘要或敏感資訊。

使用者糾正了可能再次發生的錯誤假設時，把最短且可操作的規則寫到最接近作用範圍的 `AGENTS.md`；只影響當前事實的修正應寫入相應 `.codex/` 文件，不要讓根規則無限增長。

## Current-state 與歷史分離

- `project.md`、`workflows.md`、`architecture.md`、`contracts.md` 描述目前有效狀態，應原地修正，不追加日期流水帳。
- `decisions.md` 使用穩定 ID 記錄仍有價值的設計理由；被取代時標記 `Superseded` 並連到新決策。
- `known_issues.md` 與 `backlog.md` 使用穩定 ID 與狀態；解決或完成後標記，不悄悄刪除近期重要項目。
- `memory.md` 只保留最多 10 筆近期高價值成果與精簡 Current Focus。

任一 active 文件超過約 200 行、24 KB，或已明顯出現重複／失效內容時執行濃縮：

1. 保留目前有效結論於 active 文件。
2. 將需要追溯但不需例行載入的舊條目移到 `.codex/archive/`；不要反覆保存整份檔案快照。
3. 更新 `.codex/archive/README.md` 索引。
4. 可由 Git 歷史可靠追溯且沒有持久上下文價值的內容直接移除。
5. 濃縮後驗證未遺失 open issue、accepted backlog、active contract、重要決策或未完成 stub。

## 巢狀指引

- 只有子模組具有不同命令、邊界、風險或維護規則時才新增巢狀 `AGENTS.md`。
- 以 `.codex/templates/module-AGENTS.template.md` 為起點，刪除不適用段落。
- 不要為每個目錄建立一份，也不要複製根規則。
- 同一目錄若同時存在 `AGENTS.override.md` 與 `AGENTS.md`，Codex 只會選擇前者；使用 override 前必須確認這是刻意行為。
