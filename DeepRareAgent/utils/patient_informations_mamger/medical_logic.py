import re
import json
import time
from uuid import uuid4
from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple, Optional

# =============================================================================
# 1. 逻辑核心：Stateless Manager
#    (提取了原 SectionStore 的核心算法，但去掉了状态存储功能)
# =============================================================================

class PatientManager:
    """
    无状态病历管理器。
    职责：接收 State 中的纯字典 -> 执行复杂的增删改查逻辑 -> 返回结果。
    """
    def __init__(self, data: Dict[str, List[Dict]]):
        # 直接引用 State 中的字典
        self.data = data if data is not None else {}

    # --- 内部工具 (保留原代码的精华：时间戳与寻址) ---
    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def _ensure_section(self, section: str) -> List[Dict]:
        return self.data.setdefault(section, [])

    def _parse_path(self, path: str) -> Tuple[str, Dict]:
        """
        保留原代码强大的寻址逻辑 (简化版)。
        支持: 'exams:BP' 或 'exams?k=BP'
        """
        if "?" in path:
            sec, query = path.split("?", 1)
            # 简单的解析: k=BP&value=120
            params = dict(item.split("=") for item in query.split("&") if "=" in item)
            return sec, params
        if ":" in path:
            sec, key = path.split(":", 1)
            return sec, {"k": key}
        return path, {}

    # --- 核心业务功能 ---

    def add(self, section: str, payload: Dict) -> str:
        """追加模式：保留历史记录"""
        items = self._ensure_section(section)
        
        # 注入元数据 (保留原代码的规范)
        record = payload.copy()
        record.setdefault("_id", uuid4().hex[:8])
        record.setdefault("_t", self._now_iso())
        record.setdefault("_src", "agent")
        
        items.append(record)
        return f"[PASS] 已追加记录到 [{section}] (当前共 {len(items)} 条)"

    def update(self, path: str, payload: Dict) -> str:
        """
        智能更新模式：
        1. 尝试根据 path 找到最近一条记录进行更新。
        2. 如果找不到，自动降级为 add 操作。
        """
        section, selector = self._parse_path(path)
        items = self._ensure_section(section)
        
        # 查找逻辑：寻找匹配 key 的最后一条
        target_idx = -1
        if "k" in selector:
            for i in range(len(items) - 1, -1, -1):
                if items[i].get("k") == selector["k"]:
                    target_idx = i
                    break
        elif items: 
            # 如果没指定 key，默认更新该板块最后一条
            target_idx = len(items) - 1

        if target_idx >= 0:
            # 更新现有记录
            items[target_idx].update(payload)
            items[target_idx]["_t"] = self._now_iso() # 更新修改时间
            return f"[PASS] 已更新 [{section}] 中匹配的记录。"
        else:
            # 没找到匹配项 -> 自动转为新增
            # 确保 key 存在
            if "k" in selector and "k" not in payload:
                payload["k"] = selector["k"]
            return self.add(section, payload)

    def get_flat_summary(self, section: str = None) -> str:
        """
        保留原代码的 print_flat 逻辑，生成 Token 友好的摘要。
        """
        lines = []
        targets = [section] if section else self.data.keys()
        
        for sec in targets:
            items = self.data.get(sec, [])
            if not items: continue
            
            lines.append(f"=== {sec} ===")
            for item in items:
                # 过滤掉下划线开头的元数据，只展示业务数据
                content_parts = []
                # 优先展示 k
                if "k" in item: content_parts.append(f"{item['k']}")
                
                for k, v in item.items():
                    if not k.startswith("_") and k != "k":
                        content_parts.append(f"{k}:{v}")
                
                # 加上时间供 AI 参考
                t_str = item.get("_t", "")[:16].replace("T", " ")
                lines.append(f"  [{t_str}] {' '.join(content_parts)}")
        
        return "\n".join(lines) or "暂无数据。"

    def export(self) -> Dict:
        """导出数据回写到 State"""
        return self.data

if __name__ == "__main__":
    print("🚀 开始 PatientManager 深度逻辑测试...\n")
    
    # 模拟 State 中的空字典
    mock_state_data = {}
    pm = PatientManager(mock_state_data)

    # --- 测试 1: 基础写入 (基本信息) ---
    print("--- 1. 写入基本信息 ---")
    print(pm.add("basic", {"k": "name", "value": "张三"}))
    print(pm.add("basic", {"k": "age", "value": 45}))
    print(pm.add("basic", {"k": "gender", "value": "男"}))
    
    # --- 测试 2: 时序追加 (模拟病情变化) ---
    print("\n--- 2. 模拟发烧病情演变 (列表追加测试) ---")
    # 上午 10:00
    print(pm.add("phenotypes", {"k": "fever", "value": "37.5", "unit": "C", "note": "低烧"}))
    time.sleep(0.1) # 稍微停顿模拟时间差
    # 下午 14:00 (病情加重) - 注意这里是 Add，意味着保留历史
    print(pm.add("phenotypes", {"k": "fever", "value": "39.0", "unit": "C", "note": "高烧，服药"}))
    
    # --- 测试 3: 精准更新 (修改最后一条记录) ---
    print("\n--- 3. 补充信息 (Update 测试) ---")
    # 医生发现刚才的高烧记录忘了写“伴有寒战”，需要更新最后那条 39.0 的记录
    # update 会自动找到 phenotypes 列表中 k=fever 的最后一条
    print(pm.update("phenotypes:fever", {"symptom_detail": "伴有严重寒战"}))
    
    # --- 测试 4: 自动新增 (Upsert 测试) ---
    print("\n--- 4. 记录新检查项 (不存在的Key) ---")
    # 原来没有 BP 记录，update 应该自动降级为 add
    print(pm.update("exams:BP", {"value": "120/80", "unit": "mmHg"}))
    
    # --- 测试 5: 修改历史错误 (模拟 basic 信息修正) ---
    print("\n--- 5. 修正基本信息 ---")
    # 发现年龄记错了，应该是 46
    print(pm.update("basic:age", {"value": 46, "note": "修正录入错误"}))

    # =================================================
    # 结果验证
    # =================================================
    print("\n" + "="*40)
    print("[INFO] [视图 1] AI 看到的摘要 (get_flat_summary)")
    print("="*40)
    print(pm.get_flat_summary())

    print("\n" + "="*40)
    print("💾 [视图 2] 数据库实际存储结构 (JSON Dump)")
    print("="*40)
    # 验证数据结构是否符合三层嵌套，以及是否有 _id 和 _t
    print(json.dumps(pm.export(), indent=2, ensure_ascii=False))

    # --- 自动化断言分析 ---
    data = pm.export()
    
    print("\n[SEARCH] 自动逻辑分析:")
    
    # 1. 验证基本信息是否更新成功
    age_record = [x for x in data["basic"] if x["k"] == "age"][0]
    if age_record["value"] == 46:
        print("[PASS] [Pass] 年龄更新成功 (45 -> 46)")
    else:
        print("[FAIL] [Fail] 年龄更新失败")

    # 2. 验证发烧记录是否保留了历史 (应该是 2 条)
    fever_records = [x for x in data["phenotypes"] if x["k"] == "fever"]
    if len(fever_records) == 2:
        print(f"[PASS] [Pass] 发烧历史保留成功 (共 {len(fever_records)} 条)")
    else:
        print(f"[FAIL] [Fail] 发烧历史丢失")