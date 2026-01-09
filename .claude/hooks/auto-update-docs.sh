#!/bin/bash
# Auto-update documentation hook
# 在特定檔案修改後提醒更新相關文件

set -e

# 從 stdin 讀取 JSON 輸入
INPUT=$(cat)

# 取得檔案路徑
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# 輸出 JSON 格式的系統訊息
output_message() {
    local message="$1"
    echo "{\"systemMessage\": \"$message\", \"continue\": true}"
}

# traInfo.ts 被修改 → 提醒更新 TRA_IMPLEMENTATION_ROADMAP.md
if [[ "$FILE_PATH" =~ traInfo\.ts$ ]]; then
    output_message "📝 traInfo.ts 已修改，請考慮更新 docs/TRA_IMPLEMENTATION_ROADMAP.md 的實作狀態"
    exit 0
fi

# 新增 TrainEngine → 提醒更新 README
if [[ "$FILE_PATH" =~ TrainEngine\.ts$ ]]; then
    output_message "📝 新增 TrainEngine，請考慮更新 README.md 的支援路線列表"
    exit 0
fi

# 新增 3DLayer → 提醒更新 README
if [[ "$FILE_PATH" =~ 3DLayer\.ts$ ]]; then
    output_message "📝 新增 3DLayer，請考慮更新 README.md 的核心模組表"
    exit 0
fi

# 時刻表修改 → 提醒更新班次統計
if [[ "$FILE_PATH" =~ schedules.*\.json$ ]]; then
    output_message "📝 時刻表已修改，班次統計可能需要更新"
    exit 0
fi

exit 0
