# Claude 協作筆記 — Mini Taipei v3

台灣交通運輸即時模擬系統（捷運、高鐵、台鐵的時刻表模擬）。

## 結構

```
.claude/
├── README.md              # 本檔案
├── principles.md          # 開發原則
├── agents/                # Claude Code agents（已存在）
├── hooks/                 # Claude Code hooks（已存在）
├── rules/                 # Claude Code rules（已存在）
├── skills/                # Claude Code skills（已存在）
├── settings.json          # Claude Code settings
└── pitfalls/              # 過往踩坑紀錄
```

## 文件清單

- [principles.md](principles.md) — 鐵道資料處理、時刻表模擬慣例
- 專案根 [`CLAUDE.md`](../CLAUDE.md) — 技術棧、專案概述、常用指令

## 角色
這個專案是 **鐵道時刻表資料的單一來源**。資料會被：
- `mini-taiwan-pulse` 透過 Supabase `reference.daily_schedules` 讀取
- 其他視覺化專案重用軌道 GeoJSON
