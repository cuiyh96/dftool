from typing import Optional, Union, Dict, List
import re
import json
import ast
import demjson3
import pandas as pd

import logging
logger = logging.getLogger(__name__)

class JsonUtils:
    @staticmethod
    def safe_json_loads(text):
        """
        JSON解析函数，按顺序尝试多种解析方法
        
        Args:
            - text: 要解析的文本，可以是任意类型
        
        Returns:
            - 解析成功返回解析后的对象，失败返回 None
        
        解析优先级：
        1. json.loads() - 最快，标准JSON
        2. ast.literal_eval() - 中等，支持Python字面量
        3. demjson3.decode() - 最慢，但兼容性最好
        """
        # 1. 处理空值
        if pd.isna(text):
            return None
        
        # 2. 转换为字符串并去除空白
        text_str = str(text).strip()
        if not text_str:
            return None
        
        # 3. 快速预检查（提高性能）
        # 检查长度
        if len(text_str) < 2:
            return None
        
        # 4. 解析
        try:
            
            # 优先尝试：json.loads（最快）
            try:
                return json.loads(text_str)
            except json.JSONDecodeError:
                pass  # 继续尝试下一个解析器
            
            # 第二尝试：ast.literal_eval（支持单引号、Python字面量）
            try:
                return ast.literal_eval(text_str)
            except (SyntaxError, ValueError):
                pass  # 继续尝试下一个解析器
            
            # 最后尝试：demjson3.decode（兼容性最好，但最慢）
            try:
                return demjson3.decode(text_str, strict=False)
            except demjson3.JSONDecodeError:
                return None
                
        except Exception:
            # 捕获其他意外异常
            return None
        
    @staticmethod
    def extract_json_from_text(text: str) -> Optional[Union[Dict, List]]:
        """
        从文本中提取JSON子串并解析为Python对象
        
        Args:
            text: 包含JSON的原始文本
            
        Returns:
            解析后的JSON对象，如果提取失败返回None
        """
        if not text or not isinstance(text, str):
            return None
        # 预编译正则表达式以提高性能
        JSON_CODE_BLOCK_PATTERN = re.compile(r'```json\n(.*?)\n```', re.DOTALL)
        JSON_STRUCTURE_PATTERN = re.compile(r'(\{.*?\}|\[.*?\])', re.DOTALL)
        try:
            # 方法1：提取代码块格式的JSON
            json_match = JSON_CODE_BLOCK_PATTERN.search(text)
            if json_match:
                json_str = json_match.group(1).strip()
                return JsonUtils.safe_json_loads(json_str)
            
            # 方法2：提取内联JSON结构
            structure_matches = JSON_STRUCTURE_PATTERN.findall(text)
            for match in structure_matches:
                result = JsonUtils.safe_json_loads(match)
                if result is not None:
                    return result
            
            return None
            
        except Exception as e:
            logger.warning(f"提取JSON时出错: {e}, 文本: {text[:100]}...")
            return None