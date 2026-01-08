# -*- coding: utf-8 -*-
import json
import re
import typing
import json5

def parse_json_from_markdown(text: str) -> typing.Dict[str, typing.Any]:
    """
    Robustly parse JSON from text that might contain Markdown code blocks
    or be raw JSON.
    """
    # 1. Try parsing directly first
    try:
        return json5.loads(text)
    except Exception:
        pass
    
    # 2. Try extracting from markdown code blocks (```json ... ``` or just ``` ... ```)
    # Match ```json {content} ``` or ``` {content} ```
    pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
    match = re.search(pattern, text, re.DOTALL)
    
    if match:
        json_str = match.group(1)
        try:
            return json5.loads(json_str)
        except Exception:
            pass
            
    # 3. Try finding the first '{' and last '}'
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            json_str = text[start : end + 1]
            return json5.loads(json_str)
    except Exception:
        pass
        
    # 4. Fallback: If minimal structure exists, return empty or raise error
    # For this system, we might want to return a safe default or let it fail 
    # so the caller knows something went wrong. 
    # Let's let the caller handle exceptions if completely failed.
    raise ValueError(f"Failed to parse JSON from response: {text[:200]}...")
