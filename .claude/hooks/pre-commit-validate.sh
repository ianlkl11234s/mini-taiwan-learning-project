#!/bin/bash
# Pre-commit validation hook for transport data files
# 驗證 JSON/GeoJSON 檔案格式和完整性

set -e

# 從 stdin 讀取 JSON 輸入
INPUT=$(cat)

# 取得檔案路徑
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# 只處理 public/data 下的 JSON/GeoJSON 檔案
if [[ ! "$FILE_PATH" =~ ^.*public/data/.*\.(json|geojson)$ ]]; then
    exit 0
fi

# 驗證 JSON 語法
if ! python3 -m json.tool "$FILE_PATH" > /dev/null 2>&1; then
    echo "❌ Invalid JSON syntax in: $FILE_PATH" >&2
    exit 2
fi

# 驗證時刻表檔案
if [[ "$FILE_PATH" =~ schedules.*\.json$ ]]; then
    # 檢查必要欄位
    TRACK_ID=$(jq -r '.track_id // empty' "$FILE_PATH")
    if [[ -z "$TRACK_ID" ]]; then
        echo "❌ Missing track_id in: $FILE_PATH" >&2
        exit 2
    fi

    # 檢查 departures 是否存在
    DEPARTURES=$(jq -r '.departures // empty' "$FILE_PATH")
    if [[ -z "$DEPARTURES" ]]; then
        echo "❌ Missing departures in: $FILE_PATH" >&2
        exit 2
    fi

    # 檢查 train_id 重複
    DUPLICATES=$(jq -r '[.departures[].train_id] | group_by(.) | map(select(length > 1)) | .[0][0] // empty' "$FILE_PATH")
    if [[ -n "$DUPLICATES" ]]; then
        echo "❌ Duplicate train_id: $DUPLICATES in: $FILE_PATH" >&2
        exit 2
    fi
fi

# 驗證 station_progress 檔案
if [[ "$FILE_PATH" =~ station_progress\.json$ ]]; then
    # 檢查每個 track 的 progress 範圍
    INVALID=$(jq -r 'to_entries[] | select(.value | to_entries | map(.value) | (min != 0 or max != 1)) | .key' "$FILE_PATH" 2>/dev/null || echo "")
    if [[ -n "$INVALID" ]]; then
        echo "⚠️ Warning: $INVALID progress range not 0-1 in: $FILE_PATH"
        # 警告不阻止，繼續
    fi
fi

# 驗證 GeoJSON 軌道檔案
if [[ "$FILE_PATH" =~ tracks.*\.geojson$ ]]; then
    # 檢查座標範圍 (台灣)
    COORDS_OUT=$(jq -r '
        .geometry.coordinates // .features[0].geometry.coordinates |
        flatten(1) |
        map(select(.[0] < 119 or .[0] > 123 or .[1] < 21 or .[1] > 26)) |
        length
    ' "$FILE_PATH" 2>/dev/null || echo "0")

    if [[ "$COORDS_OUT" -gt 0 ]]; then
        echo "❌ Coordinates out of Taiwan range in: $FILE_PATH" >&2
        exit 2
    fi
fi

echo "✅ Validation passed: $FILE_PATH"
exit 0
