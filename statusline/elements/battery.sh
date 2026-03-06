#!/bin/bash
if [[ "$OSTYPE" == "darwin"* ]]; then
    percent=$(pmset -g batt 2>/dev/null | grep -o '[0-9]*%' | head -1)
    charging=$(pmset -g batt 2>/dev/null | grep -q 'AC Power' && echo "+" || echo "")
    [ -n "$percent" ] && echo "🔋 ${percent}${charging}"
else
    bat_path=$(ls /sys/class/power_supply/BAT*/capacity 2>/dev/null | head -1)
    if [ -n "$bat_path" ]; then
        percent=$(cat "$bat_path")
        echo "🔋 ${percent}%"
    fi
fi
