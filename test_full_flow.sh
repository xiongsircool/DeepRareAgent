#!/bin/bash

# 完整流程测试脚本
# 测试从预诊断 → 触发深度诊断 → prepare_mdt → mdt_diagnosis → summary

THREAD_ID="fcc8f972-c7f9-4cc8-9b3c-1eff44afa06b"
API_URL="http://127.0.0.1:2024"

echo "=========================================="
echo "🧪 完整诊断流程测试"
echo "=========================================="
echo ""

# 第一轮：发送初始症状
echo "📍 第一轮：发送初始症状..."
echo ""
curl -X POST "$API_URL/runs/stream" \
  -H "Content-Type: application/json" \
  -d "{
    \"assistant_id\": \"agent\",
    \"thread_id\": \"$THREAD_ID\",
    \"input\": {
      \"messages\": [
        {
          \"role\": \"human\",
          \"content\": \"我最近总是感到极度疲劳，四肢无力，皮肤也出现了异常色素沉着，特别是手掌和牙龈。\"
        }
      ]
    },
    \"stream_mode\": [\"updates\", \"values\"]
  }" 2>/dev/null | grep -E "(event: updates|event: values)" | head -20

echo ""
echo "⏳ 等待 5 秒后继续..."
sleep 5
echo ""

# 第二轮：补充信息
echo "📍 第二轮：补充患者基本信息..."
echo ""
curl -X POST "$API_URL/runs/stream" \
  -H "Content-Type: application/json" \
  -d "{
    \"assistant_id\": \"agent\",
    \"thread_id\": \"$THREAD_ID\",
    \"input\": {
      \"messages\": [
        {
          \"role\": \"human\",
          \"content\": \"我35岁，男性。症状大概持续了3个月，期间还出现了食欲下降、体重减轻约5公斤，偶尔有恶心的感觉。\"
        }
      ]
    },
    \"stream_mode\": [\"updates\"]
  }" 2>/dev/null | grep "event: updates" | head -10

echo ""
echo "⏳ 等待 5 秒后继续..."
sleep 5
echo ""

# 第三轮：确认开始深度诊断（关键步骤）
echo "📍 第三轮：确认开始深度诊断（触发 MDT 流程）..."
echo ""
curl -X POST "$API_URL/runs/stream" \
  -H "Content-Type: application/json" \
  -d "{
    \"assistant_id\": \"agent\",
    \"thread_id\": \"$THREAD_ID\",
    \"input\": {
      \"messages\": [
        {
          \"role\": \"human\",
          \"content\": \"是的，我确认开始深度诊断，请帮我分析可能的病因。\"
        }
      ]
    },
    \"stream_mode\": [\"updates\", \"debug\"]
  }" 2>/dev/null

echo ""
echo "=========================================="
echo "✅ 测试完成"
echo "=========================================="
