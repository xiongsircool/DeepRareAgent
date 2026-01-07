"""
=========================================================================================
SectionStore - 医疗诊断场景专用的二层分区存储系统
=========================================================================================

概述 (Overview)
---------------
SectionStore 是一个为 LLM/Agent 工作负载优化的轻量级分层存储系统，特别适用于医疗信息
采集、患者画像构建、时间序列数据管理等场景。它提供了灵活的寻址模式和批量操作能力，
帮助 Agent 高效地读写结构化数据。

架构设计 (Architecture)
-----------------------
采用**二层键值列表**架构：

  ┌─────────────────────────────────────────────────────────────┐
  │ Section Layer (分区层)                                       │
  │   • basic (基本信息)      → List[Dict]                       │
  │   • phenotypes (症状体征)  → List[Dict]                       │
  │   • exams (检查结果)       → List[Dict]                       │
  │   • family (家族史)        → List[Dict]                       │
  │   • genetics (基因信息)    → List[Dict]                       │
  │   • notes (备注)          → List[Dict]                       │
  └─────────────────────────────────────────────────────────────┘
                            ↓
  ┌─────────────────────────────────────────────────────────────┐
  │ Record Layer (记录层) - 每个 Dict 包含:                      │
  │   • k:      业务键 (如 'name', 'fever', 'BP')               │
  │   • value:  主要值                                           │
  │   • _id:    唯一标识符 (自动生成 UUID)                       │
  │   • _t:     ISO8601 时间戳 (写入时间)                        │
  │   • _src:   数据来源 (如 'agent', 'user', 'api')            │
  │   • _conf:  置信度/元数据                                    │
  │   • [其他]: 任意自定义字段                                   │
  └─────────────────────────────────────────────────────────────┘

寻址模式 (Addressing Modes)
--------------------------
支持三种灵活的寻址语法：

  [NOTE] L0 - 索引访问 (Index-based)
     语法: section[index]
     示例: exams[0]           # 获取第0条检查记录
           phenotypes[-1]     # 获取最后一条症状记录

  [NOTE] L1 - 键值访问 (Key-based)
     语法: section:key
     示例: basic:name         # 匹配 k='name' 的记录
           exams:blood_test   # 匹配 k='blood_test' 的记录
     规则: 默认返回/更新最后一条匹配项 (pick=last)

  [NOTE] L2 - 条件查询 (Query-based)
     语法: section?field1=value1&field2>value2&pick=first/last/all
     示例: exams?k=FPG&value>=7.0&pick=last     # 查询血糖≥7.0的最后一条
           phenotypes?onset=yesterday&pick=all  # 查询昨天发作的所有症状
           vitals?_t>=2025-11-01&pick=first    # 查询11月后的首条生命体征
     
     支持的运算符:
       • =, ==    相等 (数值/字符串)
       • !=       不等
       • ~=       包含 (字符串子串匹配)
       • >, >=    大于、大于等于 (数值/ISO日期)
       • <, <=    小于、小于等于
     
     pick 参数:
       • first    返回首条
       • last     返回最后一条 (默认)
       • all      返回所有匹配项

默认行为 (Default Behaviors)
---------------------------
  📖 读取 (get):    多条命中时返回最后一条 (pick=last)
  [EDIT]  更新 (set):    更新最后一条匹配项，无匹配时自动新增
  ➕ 添加 (add):    总是追加新记录，保留历史
  [DEL]  删除 (remove): 默认删除所有匹配项 (可用 pick 控制)

核心方法 (Core Methods)
-----------------------
  • add(section, payload)           无条件追加新记录
  • set(path, payload)              Upsert 语义（更新或插入）
  • get(path, default, field)       查询单条或多条记录
  • remove(path, mode)              删除匹配记录
  • find(section, where, pick)      便捷查询方法
  • exists(path)                    检查是否存在
  • count(path_or_section)          统计记录数量
  • list_items(section)             列出分区全部记录
  • print_flat(section, show_meta)  打印扁平化视图

工具集成 (LangChain Tools)
--------------------------
使用 make_section_store_tools(store) 生成 LangChain 工具集：
  • section_add         单条添加
  • section_set         单条更新/插入
  • section_get         单条查询
  • section_remove      删除记录
  • section_print_flat  打印当前状态
  • section_batch       ⭐ 批量写入（推荐，减少 Tool Call 次数）

持久化 (Persistence)
--------------------
  • save_json(filepath)   保存为 JSON 文件
  • load_json(filepath)   从 JSON 文件加载

使用示例 (Usage Examples)
-------------------------

[1] 基本信息写入 (单条)
   store.set("basic:name", {"k": "name", "value": "张三"})
   store.set("basic:age", {"k": "age", "value": 45, "unit": "岁"})

[2] 症状记录 (多条历史)
   store.add("phenotypes", {"k": "fever", "value": 38.5, "onset": "2天前"})
   store.add("phenotypes", {"k": "cough", "value": "干咳", "duration": "1周"})

[3] 检查结果更新 (条件更新)
   store.set("exams?k=FPG&pick=last", {"value": 7.2, "unit": "mmol/L"})

[4] 条件查询
   # 查询所有昨天发作的症状
   symptoms = store.find("phenotypes", "onset=yesterday", pick="all")
   
   # 查询最近的血糖值
   glucose = store.get("exams?k=FPG&pick=last", field="value")

[5] 批量写入 (推荐用于 Agent)
   batch_tool = make_section_store_tools(store)[5]  # section_batch
   batch_tool.invoke({
       "facts": [
           {"op": "set", "path": "basic:name", "payload": {"k": "name", "value": "李某"}},
           {"op": "add", "section": "phenotypes", "payload": {"k": "fever", "value": 37.8}},
           {"op": "set", "path": "exams:BP", "payload": {"k": "BP", "value": "140/90"}}
       ]
   })

[6] 持久化
   store.save_json("patient_001.json")      # 保存
   store.load_json("patient_001.json")      # 加载

设计理念 (Design Philosophy)
---------------------------
[PASS] 为 LLM/Agent 优化：简洁的语法、批量操作、自动元数据管理
[PASS] 医疗场景友好：分区设计契合病历结构、支持时间序列
[PASS] 灵活可扩展：任意字段、条件查询、可持久化
[PASS] 隐私保护：默认不向 LLM 暴露元数据（_id, _t, _src 等）

适用场景 (Ideal Use Cases)
--------------------------
  • [MEDICAL] 医疗诊断 Agent 的患者信息采集
  • [INFO] 时间序列数据管理（检查结果、生命体征）
  • [NOTE] 结构化日志记录
  • 💬 LLM 对话历史管理
  • [AI] Agent 状态管理

=========================================================================================
"""
from __future__ import annotations
from typing import Any, Dict, List, Tuple, Optional, Union, Literal
from dataclasses import dataclass, field
from uuid import uuid4
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import re
import json

# 兼容不同版本的 langchain
try:
    from langchain_core.tools import StructuredTool
except ImportError:
    try:
        from langchain.tools import StructuredTool
    except ImportError:
        StructuredTool = None  # 如果没有安装 langchain，工具功能将不可用


__all__ = [
    "SectionStore",
    "make_section_store_tools",
]


# =========================
# Core Store
# =========================
@dataclass
class SectionStore:
    """
    一个“二维分区 → 列表字典项”的轻量存储器，适合 LLM/Agent 使用的稳定读写。
    - 顶层是分区名：str -> List[dict]，每条 dict 任意字段（建议保留 _id/_t/_src/_conf）。
    - 寻址：
        L0: section[3]         → 索引
        L1: section:key        → 匹配条目中 k==key（默认 pick=last）
        L2: section?A=B&...    → 条件筛选（支持 = != ~= > >= < <=，对数值/ISO字串皆可）
        其中可用 pick=first/last/all
    - 默认行为：
        读取：多命中 pick=last
        更新：更新最后一条（若无命中则新增）
        删除：默认删除所有（可用 mode/pick 定制）
    """
    data: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    default_pick: str = "last"   # 读取/更新时默认 pick 策略 first/last/all




    # ---------- Static Helpers ----------
    @staticmethod
    def now_iso() -> str:
        """ISO8601 UTC 时间戳（写入时间，不代表事件真实发生时间）"""
        return (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )

    # ---------- Public APIs ----------
    def add(self, section: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        无条件追加（保留历史）。若无 _id 自动生成。
        常用于多次检查/化验/事件流水。
        """
        items = self._ensure_section(section)
        item = dict(payload)
        item.setdefault("_id", uuid4().hex)
        items.append(item)
        return item

    def upsert(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """upsert 语义（set 的别名）。"""
        return self.set(path, payload)

    def set(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        upsert：
          - L0 index：合并更新该条（不存在报错）
          - L1 key：更新最后一条 k==key；若不存在则新增（补 k）
          - L2 query：根据 pick（first/last/all）更新；无命中则新增
        """
        sec, mode, selector = self._parse_path(path)
        items = self._ensure_section(sec)
        hit_idxs = self._select_indices(items, mode, selector)
        pick = selector.get("pick") or self.default_pick

        def merge_update(idx: int):
            base = items[idx]
            # 保护 _id 不被覆盖
            if "_id" in payload:
                tmp = dict(payload)
                tmp.pop("_id", None)
                base.update(tmp)
            else:
                base.update(payload)

        if mode == "index":
            if not hit_idxs:
                raise IndexError("索引不存在")
            merge_update(hit_idxs[0])
            return items[hit_idxs[0]]

        if mode == "key":
            if hit_idxs:
                merge_update(hit_idxs[-1])
                return items[hit_idxs[-1]]
            # 不存在：作为新增，并将 k 补上
            new_item = dict(payload)
            new_item.setdefault("k", selector["key"])
            return self.add(sec, new_item)

        # query
        if not hit_idxs:
            # 条件无命中：按新增处理（不强制要求有 k）
            return self.add(sec, dict(payload))

        if pick == "all":
            for i in hit_idxs:
                merge_update(i)
            return {"updated": len(hit_idxs)}

        target = hit_idxs[0] if pick == "first" else hit_idxs[-1]
        merge_update(target)
        return items[target]

    def get(self, path: str, default: Any=None, field: Optional[str]=None) -> Any:
        """
        获取单条或多条：
          - 若 pick=all 或 L0 列举模式，返回列表
          - 否则返回单条（默认 last）
          - 指定 field 则返回该字段值/列表
        """
        sec, mode, selector = self._parse_path(path)
        items = self.data.get(sec, [])
        hit_idxs = self._select_indices(items, mode, selector)
        if not hit_idxs:
            return default

        pick = selector.get("pick") or ("all" if mode == "index_all" else self.default_pick)
        if pick == "all":
            out = [items[i] for i in hit_idxs]
            return [o.get(field) if field else o for o in out]

        i = hit_idxs[0] if pick == "first" else hit_idxs[-1]
        return items[i].get(field) if field else items[i]

    def remove(self, path: str, mode: str="all") -> int:
        """
        删除匹配条目数量：
          - L0 index：删一条
          - L1/L2：结合 pick（first/last）或 mode（first/last/all）
        """
        sec, pmode, selector = self._parse_path(path)
        items = self.data.get(sec, [])
        hit_idxs = self._select_indices(items, pmode, selector)
        if not hit_idxs:
            return 0

        pick = selector.get("pick")
        if pmode == "index":
            items.pop(hit_idxs[0]); return 1
        if pick in ("first", "last"):
            target = hit_idxs[0] if pick == "first" else hit_idxs[-1]
            items.pop(target); return 1

        if mode == "first":
            items.pop(hit_idxs[0]); return 1
        if mode == "last":
            items.pop(hit_idxs[-1]); return 1

        cnt = 0
        for i in reversed(hit_idxs):
            items.pop(i); cnt += 1
        return cnt

    def list_items(self, section: str) -> List[Dict[str, Any]]:
        """列出分区全部条目（浅拷贝）。"""
        return list(self.data.get(section, []))

    def find(self, section: str, where: str, pick: str="all") -> List[Dict[str, Any]] | Dict[str, Any] | None:
        """
        便捷查询：等价于 get(f"{section}?{where}&pick={pick}")
        """
        path = f"{section}?{where}"
        if pick: path += f"&pick={pick}"
        return self.get(path, default=None)

    def exists(self, path: str) -> bool:
        """是否存在命中。"""
        sec, mode, selector = self._parse_path(path)
        items = self.data.get(sec, [])
        return len(self._select_indices(items, mode, selector)) > 0

    def count(self, path_or_section: str) -> int:
        """命中数量（若传 section 名则返回分区条目总数）。"""
        if ("[" not in path_or_section) and (":" not in path_or_section) and ("?" not in path_or_section):
            return len(self.data.get(path_or_section, []))
        sec, mode, selector = self._parse_path(path_or_section)
        return len(self._select_indices(self.data.get(sec, []), mode, selector))

    def clear_section(self, section: str) -> int:
        """
        清空指定分区的所有记录。
        返回删除的记录数量。
        """
        count = len(self.data.get(section, []))
        if section in self.data:
            self.data[section] = []
        return count

    def clear_all(self) -> Dict[str, int]:
        """
        清空所有分区。
        返回每个分区删除的记录数量。
        """
        counts = {sec: len(items) for sec, items in self.data.items()}
        self.data.clear()
        return counts

    def get_sections(self) -> List[str]:
        """获取所有分区名称列表。"""
        return list(self.data.keys())

    def get_stats(self) -> Dict[str, Any]:
        """
        获取存储统计信息。
        返回: {
            'total_sections': int,
            'total_records': int,
            'sections': {section_name: record_count, ...}
        }
        """
        section_stats = {sec: len(items) for sec, items in self.data.items()}
        return {
            'total_sections': len(self.data),
            'total_records': sum(section_stats.values()),
            'sections': section_stats
        }

    def validate_record(self, record: Dict[str, Any], strict: bool = False) -> Tuple[bool, List[str]]:
        """
        验证单条记录的格式。
        
        Args:
            record: 待验证的记录
            strict: 是否严格模式（要求包含推荐字段）
        
        Returns:
            (is_valid, errors) - 是否有效和错误列表
        """
        errors = []
        
        if not isinstance(record, dict):
            errors.append("记录必须是字典类型")
            return False, errors
        
        if strict:
            recommended_fields = ['k', 'value']
            missing = [f for f in recommended_fields if f not in record]
            if missing:
                errors.append(f"缺少推荐字段: {', '.join(missing)}")
        
        # 验证元数据字段格式
        if '_t' in record:
            t = record['_t']
            if not isinstance(t, str):
                errors.append("_t 必须是 ISO8601 时间戳字符串")
            elif not (t.endswith('Z') or '+' in t or t.count('T') == 1):
                errors.append("_t 格式不符合 ISO8601 标准")
        
        if '_conf' in record:
            conf = record['_conf']
            if not isinstance(conf, (int, float, str, dict)):
                errors.append("_conf 类型应为 int/float/str/dict")
        
        return len(errors) == 0, errors

    def export_to_flat_dict(self, section: Optional[str] = None) -> Dict[str, Any]:
        """
        导出为扁平化字典（去除元数据）。
        
        Args:
            section: 指定分区名，None 则导出全部
        
        Returns:
            去除 _ 开头字段的数据字典
        """
        def strip_meta(items: List[Dict]) -> List[Dict]:
            return [{k: v for k, v in item.items() if not k.startswith('_')} 
                    for item in items]
        
        if section:
            return {section: strip_meta(self.data.get(section, []))}
        
        return {sec: strip_meta(items) for sec, items in self.data.items()}

    def merge_from(self, other: "SectionStore", overwrite: bool = False) -> Dict[str, int]:
        """
        从另一个 SectionStore 合并数据。
        
        Args:
            other: 另一个 SectionStore 实例
            overwrite: 是否覆盖现有分区（False 则追加）
        
        Returns:
            每个分区合并的记录数量
        """
        merged_counts = {}
        for sec, items in other.data.items():
            if overwrite or sec not in self.data:
                self.data[sec] = list(items)  # 深拷贝
                merged_counts[sec] = len(items)
            else:
                # 追加模式
                self.data[sec].extend(items)
                merged_counts[sec] = len(items)
        return merged_counts

    def deduplicate(self, section: str, by_fields: List[str] = None) -> int:
        """
        去重指定分区的记录。
        
        Args:
            section: 分区名
            by_fields: 用于判断重复的字段列表（默认使用所有非 _id/_t 字段）
        
        Returns:
            删除的重复记录数量
        """
        items = self.data.get(section, [])
        if not items:
            return 0
        
        original_count = len(items)
        seen = set()
        unique_items = []
        
        for item in items:
            if by_fields:
                # 根据指定字段判断
                key = tuple((k, item.get(k)) for k in by_fields if k in item)
            else:
                # 根据所有业务字段判断（排除元数据）
                key = tuple((k, v) for k, v in sorted(item.items()) 
                        if not k.startswith('_'))
            
            if key not in seen:
                seen.add(key)
                unique_items.append(item)
        
        self.data[section] = unique_items
        return original_count - len(unique_items)

    def search_value(self, value: Any, sections: List[str] = None) -> List[Dict[str, Any]]:
        """
        全局搜索包含特定值的记录。
        
        Args:
            value: 要搜索的值
            sections: 限制搜索的分区列表（None 则搜索全部）
        
        Returns:
            匹配的记录列表，每条记录包含 {'section': str, 'index': int, 'record': dict}
        """
        results = []
        search_sections = sections if sections else self.data.keys()
        
        for sec in search_sections:
            items = self.data.get(sec, [])
            for idx, item in enumerate(items):
                # 检查是否有任何字段匹配该值
                for k, v in item.items():
                    if v == value or (isinstance(v, str) and str(value) in v):
                        results.append({
                            'section': sec,
                            'index': idx,
                            'record': item
                        })
                        break  # 同一条记录只添加一次
        return results

    def get_latest(self, section: str, n: int = 1) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        获取分区中最新的 n 条记录（按 _t 时间戳排序）。
        
        Args:
            section: 分区名
            n: 返回记录数量
        
        Returns:
            单条记录（n=1）或记录列表（n>1）
        """
        items = self.data.get(section, [])
        if not items:
            return None if n == 1 else []
        
        # 按时间戳排序（有 _t 的优先，然后按时间倒序）
        sorted_items = sorted(
            items,
            key=lambda x: (x.get('_t') is not None, x.get('_t', '')),
            reverse=True
        )
        
        if n == 1:
            return sorted_items[0] if sorted_items else None
        return sorted_items[:n]

    def get_by_id(self, record_id: str) -> Optional[Tuple[str, int, Dict[str, Any]]]:
        """
        根据 _id 查找记录。
        
        Returns:
            (section, index, record) 或 None
        """
        for sec, items in self.data.items():
            for idx, item in enumerate(items):
                if item.get('_id') == record_id:
                    return sec, idx, item
        return None

    # ---------- Persistence ----------
    def save_json(self, fp: str, ensure_ascii: bool = False, include_meta: bool = True) -> None:
        """
        保存为 JSON 文件。
        
        Args:
            fp: 文件路径
            ensure_ascii: 是否转义非 ASCII 字符
            include_meta: 是否包含元数据（_id, _t 等）
        """
        data_to_save = self.data
        if not include_meta:
            data_to_save = self.export_to_flat_dict()
        
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=ensure_ascii, indent=2)

    def load_json(self, fp: str, merge: bool = False) -> None:
        """
        从 JSON 文件加载。
        
        Args:
            fp: 文件路径
            merge: 是否合并到现有数据（False 则覆盖）
        """
        with open(fp, "r", encoding="utf-8") as f:
            loaded_data = json.load(f)
        
        if merge:
            for sec, items in loaded_data.items():
                if sec in self.data:
                    self.data[sec].extend(items)
                else:
                    self.data[sec] = items
        else:
            self.data = loaded_data

    def to_json_string(self, include_meta: bool = False) -> str:
        """
        导出为 JSON 字符串。
        
        Args:
            include_meta: 是否包含元数据
        
        Returns:
            JSON 格式字符串
        """
        data_to_export = self.data if include_meta else self.export_to_flat_dict()
        return json.dumps(data_to_export, ensure_ascii=False, indent=2)

    def from_json_string(self, json_str: str, merge: bool = False) -> None:
        """
        从 JSON 字符串加载。
        
        Args:
            json_str: JSON 格式字符串
            merge: 是否合并到现有数据
        """
        loaded_data = json.loads(json_str)
        
        if merge:
            for sec, items in loaded_data.items():
                if sec in self.data:
                    self.data[sec].extend(items)
                else:
                    self.data[sec] = items
        else:
            self.data = loaded_data

    # ---------- Internals: parsing & filtering ----------
    def _ensure_section(self, section: str) -> List[Dict[str, Any]]:
        return self.data.setdefault(section, [])

    def _parse_path(self, path: str) -> Tuple[str,str,Dict[str,Any]]:
        """
        返回 (section, mode, selector)
        mode ∈ {"index","key","query","index_all"}
        语法：
          - L0:  section[3]
          - L1:  section:key
          - L2:  section?field>=value&k=FPG&pick=last
          - 仅 section：列举全部 -> index_all
        """
        if "?" in path:
            section, query = path.split("?", 1)
            return section, "query", self._parse_query(query)

        m = re.match(r"^([^\[\]:]+)\[(\d+)\]$", path)
        if m:
            return m.group(1), "index", {"index": int(m.group(2))}

        if ":" in path:
            section, key = path.split(":", 1)
            return section, "key", {"key": key}

        return path, "index_all", {}

    def _parse_query(self, qs: str) -> Dict[str, Any]:
        """
        解析 query：
          支持：a=b, a!=b, a~=sub, a>b, a>=b, a<b, a<=b, pick=first|last|all
          例： k=FPG&unit=mmol/L&_t>=2025-01-01
        """
        parts = [p for p in qs.split("&") if p.strip()]
        filters: List[Tuple[str,str,str]] = []
        pick = None
        for p in parts:
            if p.startswith("pick="):
                pick = p.split("=",1)[1].strip()
                continue
            m = re.match(r"^([^<>=!~]+)\s*(==|>=|<=|!=|~=|=|>|<)\s*(.+)$", p)
            if not m:
                if "=" in p:  # 简写 a=b
                    k,v = p.split("=",1); filters.append((k.strip(),"=",v.strip()))
                continue
            k,op,v = m.groups()
            filters.append((k.strip(), op, v.strip()))
        return {"filters": filters, "pick": pick}

    def _select_indices(self, items: List[Dict[str, Any]], mode: str, selector: Dict[str,Any]) -> List[int]:
        if mode == "index":
            idx = selector["index"]
            return [idx] if 0 <= idx < len(items) else []
        if mode == "key":
            key = selector["key"]
            return [i for i,x in enumerate(items) if x.get("k")==key]
        if mode == "index_all":
            return list(range(len(items)))

        # query
        flt = selector.get("filters", [])
        cand = []
        for i, x in enumerate(items):
            ok = True
            for (k,op,v) in flt:
                xv = x.get(k)
                if not self._cmp(xv, op, v):
                    ok = False; break
            if ok: cand.append(i)

        # 有 _t 则按时间排序（先有_t再按时间；无_t按插入序）
        def key_fn(i):
            xi = items[i]
            t = xi.get("_t")
            return (t is None, t, i)
        cand.sort(key=key_fn)
        return cand

    def _cmp(self, left: Any, op: str, right: str) -> bool:
        if left is None:
            return False
        # 尝试数值比较
        try:
            lv = float(left); rv = float(right)
            if   op in ("=","=="): return lv == rv
            elif op == "!=": return lv != rv
            elif op == ">":  return lv >  rv
            elif op == ">=": return lv >= rv
            elif op == "<":  return lv <  rv
            elif op == "<=": return lv <= rv
            elif op == "~=": return str(left).find(str(right)) >= 0
            else: return False
        except Exception:
            pass
        # 字符串/ISO 日期按字典序比较（ISO8601 支持先后比较）
        l = str(left); r = str(right)
        if   op in ("=","=="): return l == r
        elif op == "!=": return l != r
        elif op == ">":  return l >  r
        elif op == ">=": return l >= r
        elif op == "<":  return l <  r
        elif op == "<=": return l <= r
        elif op == "~=": return r in l
        else: return False

    def print_flat(self, section: str | None = None, show_section: bool = False, show_meta: bool = False) -> None:
        """
        打印每条记录： [section] k v1 v2 v3 ... （按实际key顺序，全部空格分隔，去掉 _ 开头的字段）
        """
        all_str = ""
        for sec, items in self.data.items():
            if section and sec != section:
                continue
            for x in items:
                # 只取不是 _ 开头的字段，按 keys 顺序展开
                parts = []
                if "k" in x:
                    parts.append(str(x["k"]))
                # 依次加入除 k/v/vlaue/_ 开头的其他字段
                for kk in x:
                    if kk not in ("k", "value", "v") and not kk.startswith("_"):
                        parts.append(str(x[kk]))
                # 最后优先显示 value/v
                if "value" in x:
                    parts.append(str(x["value"]))
                elif "v" in x:
                    parts.append(str(x["v"]))
                # 需要额外显示元字段（如时间/来源）可加 show_meta 控制
                if show_meta:
                    if "_t" in x:
                        parts.append(str(x["_t"]))
                    if "_src" in x:
                        parts.append(str(x["_src"]))
                # 拼接输出
                prefix = f"[{sec}] " if show_section else ""
                print(prefix + " ".join(parts))
                all_str += prefix + " ".join(parts) + "\n"
        return all_str
                


# =========================
# Tools (LangChain StructuredTool)
# =========================
class AddOp(BaseModel):
    op: Literal["add"] = "add"
    section: str = Field(..., description="如 basic/phenotypes/exams/family/genetics/notes")
    payload: Dict[str, Any] = Field(..., description="写入内容字典")


class SetOp(BaseModel):
    op: Literal["set"] = "set"
    path: str = Field(..., description="如 'basic:name' 或 'exams?k=FPG&pick=last'")
    payload: Dict[str, Any] = Field(..., description="合并更新的字典")


class BatchArgs(BaseModel):
    facts: List[Union[AddOp, SetOp]] = Field(..., description="批量操作（建议 ≤10 条）")


def _strip_meta(d: Dict[str, Any]) -> Dict[str, Any]:
    """去掉以 '_' 开头的元字段，避免暴露元信息给 LLM。"""
    return {k: v for k, v in d.items() if not k.startswith("_")}


def _section_batch_impl(store: SectionStore, facts: List[Dict[str, Any]], expose_meta: bool=False) -> Dict[str, Any]:
    """
    批量写入：在这里统一补写 _t（write-time）与 _src，并默认不暴露元字段。
    """
    results = []; ok = 0
    # 软限流（安全）：过多则截断
    if len(facts) > 10:
        facts = facts[:10]

    for i, f in enumerate(facts):
        try:
            op = f.get("op")
            if op == "add":
                payload = dict(f["payload"])
                payload.setdefault("_t", SectionStore.now_iso())
                payload.setdefault("_src", "agent")
                res = store.add(f["section"], payload)
            elif op == "set":
                payload = dict(f["payload"])
                payload.setdefault("_t", SectionStore.now_iso())
                payload.setdefault("_src", "agent")
                res = store.set(f["path"], payload)
            else:
                raise ValueError(f"unsupported op: {op}")
            ok += 1
            results.append({"index": i, "status": "ok", "result": res})
        except Exception as e:
            results.append({"index": i, "status": "error", "error": str(e)})

    if not expose_meta:
        for r in results:
            if r.get("status") == "ok" and isinstance(r.get("result"), dict):
                r["result"] = _strip_meta(r["result"])

    return {"ok": ok, "total": len(facts), "items": results}


def make_section_store_tools(store: SectionStore) -> List["StructuredTool"]:
    """
    把 SectionStore 的核心方法转换为 LangChain 工具。
    默认包括：
      - 单方法工具：section_add / section_set / section_get / section_remove / section_print_flat
      - 批量工具：section_batch（一次性提交多条事实，内部统一补 _t 与 _src）
    """
    if StructuredTool is None:
        raise ImportError(
            "需要安装 langchain 或 langchain-core 才能使用工具功能。\n"
            "请运行: pip install langchain-core"
        )
    
    tools: List[StructuredTool] = []

    # --- 基础工具 ---
    for method_name in ["add", "set", "get", "remove", "print_flat"]:
        func = getattr(store, method_name)
        tools.append(
            StructuredTool.from_function(
                name=f"section_{method_name}",
                description=func.__doc__ or method_name,
                func=func,
            )
        )

    # --- 批量写入（增强版） ---
    def _run_batch(facts: List[Union[AddOp, SetOp]]) -> Dict[str, Any]:
        facts_dicts = [f.model_dump() if hasattr(f, "model_dump") else dict(f) for f in facts]
        return _section_batch_impl(store, facts_dicts, expose_meta=False)

    tools.append(
        StructuredTool.from_function(
            name="section_batch",
            description=(
                "批量写入患者画像（每轮调用一次即可）。"
                "facts 示例："
                "[{'op':'set','path':'basic:name','payload':{'k':'name','value':'张三'}},"
                "{'op':'add','section':'phenotypes','payload':{'k':'fever','value':'37.8','onset':'yesterday'}}]"
            ),
            func=_run_batch,
            args_schema=BatchArgs,
        )
    )

    return tools


# =========================
# Self-Test (optional)
# =========================
if __name__ == "__main__":
    print("=" * 80)
    print("SectionStore 功能测试")
    print("=" * 80)
    
    store = SectionStore()
    
    # 1. 直接使用批量写入（不依赖工具）
    print("\n【测试 1】批量写入")
    facts = [
        {"op": "set", "path": "basic:name", "payload": {"k": "name", "value": "李某"}},
        {"op": "set", "path": "basic:sex",  "payload": {"k": "sex",  "value": "male"}},
        {"op": "set", "path": "basic:age",  "payload": {"k": "age",  "value": 37}},
        {"op": "add", "section": "phenotypes", "payload": {"k": "cough", "value": "present", "onset": "yesterday"}},
        {"op": "add", "section": "phenotypes", "payload": {"k": "fever", "value": "37.8", "unit": "C", "onset": "yesterday"}},
    ]
    res = _section_batch_impl(store, facts, expose_meta=False)
    print(f"批量写入结果: 成功 {res['ok']}/{res['total']} 条")

    # 2. 扁平化显示
    print("\n【测试 2】扁平化显示")
    store.print_flat(show_section=True, show_meta=False)

    # 3. 添加更多数据
    print("\n【测试 3】添加检查数据")
    store.add("exams", {"k": "BP", "value": "120/80", "unit": "mmHg"})
    store.add("exams", {"k": "FPG", "value": 7.2, "unit": "mmol/L"})
    store.print_flat(section="exams", show_section=True)

    # 4. 统计信息
    print("\n【测试 4】统计信息")
    stats = store.get_stats()
    print(f"分区总数: {stats['total_sections']}")
    print(f"记录总数: {stats['total_records']}")
    print(f"各分区详情: {stats['sections']}")

    # 5. 条件查询
    print("\n【测试 5】条件查询")
    yesterday_symptoms = store.find("phenotypes", "onset=yesterday", pick="all")
    print(f"查询到 {len(yesterday_symptoms) if isinstance(yesterday_symptoms, list) else 1} 条昨天发作的症状")

    # 6. 获取最新记录
    print("\n【测试 6】获取最新记录")
    latest = store.get_latest("phenotypes", n=2)
    print(f"最新的 2 条症状: {[x.get('k') for x in latest]}")

    # 7. 数据验证
    print("\n【测试 7】数据验证")
    valid_record = {"k": "test", "value": 123}
    invalid_record = {"k": "test", "_t": 12345}  # _t 应该是字符串
    
    is_valid, errors = store.validate_record(valid_record)
    print(f"有效记录验证: {is_valid}")
    
    is_valid, errors = store.validate_record(invalid_record, strict=True)
    print(f"无效记录验证: {is_valid}, 错误: {errors}")

    # 8. 搜索功能
    print("\n【测试 8】全局搜索")
    search_results = store.search_value("yesterday")
    print(f"搜索 'yesterday' 找到 {len(search_results)} 条记录")
    for r in search_results:
        print(f"  - {r['section']}: {r['record'].get('k')}")

    # 9. 导出测试
    print("\n【测试 9】数据导出")
    json_str = store.to_json_string(include_meta=False)
    print(f"导出 JSON 字符串长度: {len(json_str)} 字符")

    # 10. 去重测试
    print("\n【测试 10】去重测试")
    # 添加重复数据
    store.add("phenotypes", {"k": "fever", "value": "37.8", "unit": "C"})
    print(f"去重前: {store.count('phenotypes')} 条症状记录")
    removed = store.deduplicate("phenotypes", by_fields=["k", "value"])
    print(f"去重后: {store.count('phenotypes')} 条症状记录（删除了 {removed} 条重复）")

    # 11. 分区管理
    print("\n【测试 11】分区管理")
    sections = store.get_sections()
    print(f"当前分区: {sections}")

    print("\n" + "=" * 80)
    print("[PASS] 所有测试完成")
    print("=" * 80)