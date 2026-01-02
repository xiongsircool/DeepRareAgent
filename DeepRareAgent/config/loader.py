# -*- coding: utf-8 -*-
import yaml
import os
from pathlib import Path
from typing import Any, Dict

class ConfigObject:
    def __init__(self, data: Dict[str, Any], root_path: Path):
        for key, value in data.items():
            if isinstance(value, dict):
                setattr(self, key, ConfigObject(value, root_path))
            elif isinstance(value, str) and ("path" in key or "dir" in key):
                # --- 核心改进：自动转换路径 ---
                # 如果是相对路径，自动拼上项目根目录
                p = Path(value)
                if not p.is_absolute():
                    setattr(self, key, str(root_path / value))
                else:
                    setattr(self, key, value)
            else:
                setattr(self, key, value)

    def to_dict(self) -> Dict[str, Any]:
        """递归转回字典，方便传给 ChatOpenAI 的 model_kwargs"""
        out = {}
        for k, v in self.__dict__.items():
            if isinstance(v, ConfigObject):
                out[k] = v.to_dict()
            else:
                out[k] = v
        return out

class Loader:
    def __init__(self):
        # 自动定位项目根目录（multi_agent 目录）
        self.project_root = Path(__file__).resolve().parents[2]
        self._config = self._load_from_yaml()

    def _load_from_yaml(self) -> ConfigObject:
        config_path = self.project_root / "config.yml"

        if not config_path.exists():
            # 这里的报错信息更友好一点
            raise FileNotFoundError(f"致命错误：找不到配置文件 {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        return ConfigObject(data, self.project_root)

    @property
    def settings(self):
        return self._config

# 实例化单例
cfg_loader = Loader()

# --- 增加测试块 ---
if __name__ == "__main__":
    # 直接运行此文件进行本地调试
    s = cfg_loader.settings
    print(f"项目根目录: {cfg_loader.project_root}")
    print(f"预诊断模型: {s.pre_diagnosis_agent.model_name}")
    print(f"预诊断Prompt路径: {s.pre_diagnosis_agent.system_prompt_path}")
    # 测试 model_kwargs 转换
    print(f"Model Kwargs 字典: {s.pre_diagnosis_agent.model_kwargs.to_dict()}")
    