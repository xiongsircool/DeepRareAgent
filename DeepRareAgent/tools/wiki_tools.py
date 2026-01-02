"""
维基百科搜索工具集

这个模块提供了用于搜索维基百科的工具，主要用于获取医学和科学信息的权威解释。

主要功能：
1. search_wikipedia: 搜索维基百科词条并返回摘要信息

数据来源：
- 维基百科 (Wikipedia) API: 支持多语言搜索

使用场景：
- 医学概念解释
- 疾病背景信息查询
- 医学术语定义
- 患者教育材料准备
- 医学研究背景了解

支持语言：
- 中文 (zh)
- 英文 (en)
- 以及其他维基百科支持的语言

作者: Rare Diagnosis Agent Team
版本: 1.0.0
"""

from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool

import wikipedia

class WikiSearchRequest(BaseModel):
    query: str = Field(..., description="要检索的百科词条名称")
    lang: Optional[str] = Field("zh", description="维基百科语言代码，如'zh', 'en'等")
    sentences: Optional[int] = Field(3, description="摘要返回几句话")

class WikiSearchResult(BaseModel):
    title: str
    summary: str
    error: bool = Field(False, description="是否因异常或缺少结果而降级")
    message: Optional[str] = Field(None, description="异常说明或歧义提示")

@tool("search_wikipedia", args_schema=WikiSearchRequest)
def search_wikipedia_tool(query: str, lang: Optional[str] = "zh", sentences: Optional[int] = 3) -> WikiSearchResult:
    """检索维基百科摘要，处理歧义与异常"""
    wikipedia.set_lang(lang)
    try:
        page = wikipedia.page(query, auto_suggest=False)
    except wikipedia.DisambiguationError as e:
        # 词条歧义，返回第一个候选
        page = wikipedia.page(e.options[0])
    except Exception as e:
        return WikiSearchResult(
            title=query,
            summary="",
            error=True,
            message=f"未找到词条或请求异常: {e}"
        )
    # 摘要只取前几句话
    sentences = sentences or 3
    summary = "。".join(page.summary.split("。")[:sentences])
    return WikiSearchResult(
        title=page.title,
        summary=summary,
        error=False,
        message=None
    )

# --- main 测试入口 ---
if __name__ == "__main__":
    res = search_wikipedia_tool.invoke({"query": "视网膜色素变性", "lang": "zh", "sentences": 3})
    print("标题:", res.title)
    print("摘要:", res.summary)
