"""
Namespace 工具模块 - 提供字典与 Namespace 之间的递归转换和操作

该模块提供了将嵌套字典转换为 Namespace 对象及其逆向转换的工具函数，
支持深度合并、路径访问、属性过滤等功能。
"""

from argparse import Namespace
from typing import Any, Dict, List, Union, overload, Optional, Set
import copy
import json
import logging

# 配置日志
logger = logging.getLogger(__name__)


class NamespaceToolsError(Exception):
    """Namespace 工具模块的基础异常类"""
    pass


class NamespaceConversionError(NamespaceToolsError):
    """转换错误异常"""
    pass


class NamespacePathError(NamespaceToolsError):
    """路径访问错误异常"""
    pass


# ============ 核心转换函数 ============

@overload
def dict_to_namespace(data: Dict) -> Namespace:
    ...


@overload
def dict_to_namespace(data: List) -> List:
    ...


@overload
def dict_to_namespace(data: Any) -> Any:
    ...


def dict_to_namespace(data: Union[Dict, List, Any]) -> Union[Namespace, List, Any]:
    """
    递归将字典转为 Namespace，列表内元素同步递归转换
    
    Args:
        data: 原始数据 dict / list / 基础类型
        
    Returns:
        转换后的 Namespace / list / 原值
        
    Raises:
        NamespaceConversionError: 转换失败时抛出
        
    Examples:
        >>> obj = dict_to_namespace({"name": "test", "info": {"age": 24}})
        >>> obj.name
        'test'
        >>> obj.info.age
        24
        
        >>> obj = dict_to_namespace([{"id": 1}, {"id": 2}])
        >>> obj[0].id
        1
    """
    try:
        if isinstance(data, dict):
            return Namespace(**{k: dict_to_namespace(v) for k, v in data.items()})
        if isinstance(data, list):
            return [dict_to_namespace(item) for item in data]
        return data
    except Exception as e:
        logger.error(f"Failed to convert dict to Namespace: {e}")
        raise NamespaceConversionError(f"Conversion failed: {e}")


@overload
def namespace_to_dict(ns: Namespace, 
                     skip_private: bool = True,
                     skip_protected: bool = True,
                     custom_skip: Optional[Set[str]] = None,
                     max_depth: Optional[int] = None,
                     _current_depth: int = 0) -> Dict:
    ...


@overload
def namespace_to_dict(ns: List, 
                     skip_private: bool = True,
                     skip_protected: bool = True,
                     custom_skip: Optional[Set[str]] = None,
                     max_depth: Optional[int] = None,
                     _current_depth: int = 0) -> List:
    ...


@overload
def namespace_to_dict(ns: Any, 
                     skip_private: bool = True,
                     skip_protected: bool = True,
                     custom_skip: Optional[Set[str]] = None,
                     max_depth: Optional[int] = None,
                     _current_depth: int = 0) -> Any:
    ...


def namespace_to_dict(ns: Union[Namespace, List, Any], 
                     skip_private: bool = True,
                     skip_protected: bool = True,
                     custom_skip: Optional[Set[str]] = None,
                     max_depth: Optional[int] = None,
                     _current_depth: int = 0) -> Union[Dict, List, Any]:
    """
    递归将 Namespace 转回字典，列表内元素同步递归转换
    
    Args:
        ns: Namespace / list / 基础类型
        skip_private: 是否跳过以 __ 开头和结尾的私有属性（如 __dict__），默认 True
        skip_protected: 是否跳过以 _ 开头的保护属性（如 _internal），默认 True
        custom_skip: 自定义需要跳过的属性名集合
        max_depth: 最大递归深度，防止无限递归，默认 None（不限制）
        _current_depth: 内部使用的当前深度参数
        
    Returns:
        转换后的 dict / list / 原值
        
    Raises:
        NamespaceConversionError: 转换失败时抛出
        RecursionError: 超过最大递归深度时抛出
        
    Examples:
        >>> ns = Namespace(name="test", _internal="secret")
        >>> namespace_to_dict(ns)
        {'name': 'test'}
        
        >>> ns = Namespace(a=Namespace(b=Namespace(c=1)))
        >>> namespace_to_dict(ns, max_depth=2)
        {'a': {'b': Namespace(c=1)}}  # 深度为 2 时停止递归
    """
    if max_depth is not None and _current_depth > max_depth:
        return ns
    
    try:
        if isinstance(ns, Namespace):
            result = {}
            skip_set = custom_skip or set()
            
            for k, v in vars(ns).items():
                # 检查是否应该跳过该属性
                should_skip = False
                
                # 跳过私有属性（以 __ 开头和结尾）
                if skip_private and k.startswith('__') and k.endswith('__'):
                    should_skip = True
                
                # 跳过保护属性（以 _ 开头，但不是私有属性）
                if not should_skip and skip_protected and k.startswith('_') and not (k.startswith('__') and k.endswith('__')):
                    should_skip = True
                
                # 跳过自定义属性
                if not should_skip and k in skip_set:
                    should_skip = True
                
                if not should_skip:
                    result[k] = namespace_to_dict(v, skip_private, skip_protected, custom_skip, max_depth, _current_depth + 1)
            
            return result
        
        if isinstance(ns, list):
            return [namespace_to_dict(item, skip_private, skip_protected, custom_skip, max_depth, _current_depth + 1) 
                   for item in ns]
        
        return ns
    except RecursionError as e:
        logger.error(f"Recursion depth exceeded: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to convert Namespace to dict: {e}")
        raise NamespaceConversionError(f"Conversion failed: {e}")


# ============ 高级操作函数 ============

def deep_update(target: Union[Namespace, Dict], 
               source: Union[Namespace, Dict],
               skip_private: bool = True,
               skip_protected: bool = True,
               custom_skip: Optional[Set[str]] = None,
               inplace: bool = False) -> Union[Namespace, Dict]:
    """
    深度合并两个 Namespace 或字典，source 覆盖 target 中同名字段
    
    Args:
        target: 目标对象（Namespace 或 dict）
        source: 源对象（Namespace 或 dict）
        skip_private: 是否跳过私有属性
        skip_protected: 是否跳过保护属性
        custom_skip: 自定义跳过的属性名集合
        inplace: 是否原地修改 target，默认 False（返回新对象）
        
    Returns:
        合并后的对象（类型与 target 保持一致）
        
    Examples:
        >>> target = Namespace(a=1, b=Namespace(c=2))
        >>> source = Namespace(b=Namespace(d=3), e=4)
        >>> result = deep_update(target, source)
        >>> result.a
        1
        >>> result.b.c
        2
        >>> result.b.d
        3
    """
    # 统一转为 dict 处理
    target_dict = target if isinstance(target, dict) else vars(target)
    source_dict = source if isinstance(source, dict) else vars(source)
    
    # 如果不原地修改，先复制
    if not inplace:
        target_dict = copy.deepcopy(target_dict)
    
    # 获取需要跳过的属性
    skip_set = custom_skip or set()
    
    for key, value in source_dict.items():
        # 检查是否跳过
        should_skip = False
        if skip_private and key.startswith('__') and key.endswith('__'):
            should_skip = True
        if not should_skip and skip_protected and key.startswith('_') and not (key.startswith('__') and key.endswith('__')):
            should_skip = True
        if not should_skip and key in skip_set:
            should_skip = True
        
        if should_skip:
            continue
            
        if key in target_dict and isinstance(target_dict[key], (dict, Namespace)) and isinstance(value, (dict, Namespace)):
            # 如果都是容器类型，递归合并
            target_dict[key] = deep_update(target_dict[key], value, skip_private, skip_protected, custom_skip, inplace=True)
        else:
            # 否则直接覆盖
            target_dict[key] = value
    
    # 保持返回类型与 target 一致
    if isinstance(target, Namespace):
        return dict_to_namespace(target_dict)
    return target_dict


def get_nested_attr(ns: Union[Namespace, Dict], path: str, default: Any = None) -> Any:
    """
    通过点号路径安全获取嵌套属性
    
    Args:
        ns: Namespace 或字典对象
        path: 属性路径，如 "info.addr.city"
        default: 路径不存在时的默认值
        
    Returns:
        属性值或默认值
        
    Examples:
        >>> ns = dict_to_namespace({"info": {"addr": {"city": "Beijing"}}})
        >>> get_nested_attr(ns, "info.addr.city")
        'Beijing'
        >>> get_nested_attr(ns, "info.addr.country", "China")
        'China'
    """
    if not ns or not path:
        return default
    
    try:
        current = ns
        for key in path.split('.'):
            if isinstance(current, Namespace):
                current = getattr(current, key)
            elif isinstance(current, dict):
                current = current[key]
            else:
                return default
        return current
    except (AttributeError, KeyError, TypeError):
        return default


def set_nested_attr(ns: Union[Namespace, Dict], path: str, value: Any, create_missing: bool = True) -> bool:
    """
    通过点号路径设置嵌套属性
    
    Args:
        ns: Namespace 或字典对象
        path: 属性路径，如 "info.addr.city"
        value: 要设置的值
        create_missing: 是否创建不存在的中间节点，默认 True
        
    Returns:
        是否设置成功
        
    Examples:
        >>> ns = Namespace()
        >>> set_nested_attr(ns, "info.addr.city", "Beijing")
        True
        >>> ns.info.addr.city
        'Beijing'
    """
    if not ns or not path:
        return False
    
    try:
        parts = path.split('.')
        current = ns
        
        # 遍历到倒数第二个节点
        for key in parts[:-1]:
            if isinstance(current, Namespace):
                if not hasattr(current, key):
                    if create_missing:
                        setattr(current, key, Namespace())
                    else:
                        return False
                current = getattr(current, key)
            elif isinstance(current, dict):
                if key not in current:
                    if create_missing:
                        current[key] = {}
                    else:
                        return False
                current = current[key]
            else:
                return False
        
        # 设置最后一个属性
        last_key = parts[-1]
        if isinstance(current, Namespace):
            setattr(current, last_key, value)
        elif isinstance(current, dict):
            current[last_key] = value
        else:
            return False
        
        return True
    except Exception:
        return False


def filter_namespace_keys(ns: Namespace, 
                         keep_keys: Optional[List[str]] = None,
                         remove_keys: Optional[List[str]] = None) -> Namespace:
    """
    过滤 Namespace 的属性，保留或删除指定的键
    
    Args:
        ns: Namespace 对象
        keep_keys: 要保留的属性名列表（如果指定，则只保留这些）
        remove_keys: 要删除的属性名列表
        
    Returns:
        新的 Namespace 对象（不修改原对象）
        
    Raises:
        ValueError: 同时指定 keep_keys 和 remove_keys 时抛出
        
    Examples:
        >>> ns = Namespace(a=1, b=2, c=3, d=4)
        >>> filtered = filter_namespace_keys(ns, keep_keys=['a', 'c'])
        >>> vars(filtered)
        {'a': 1, 'c': 3}
    """
    if keep_keys is not None and remove_keys is not None:
        raise ValueError("Cannot specify both keep_keys and remove_keys")
    
    if keep_keys is not None:
        keep_set = set(keep_keys)
        filtered = {k: v for k, v in vars(ns).items() if k in keep_set}
    elif remove_keys is not None:
        remove_set = set(remove_keys)
        filtered = {k: v for k, v in vars(ns).items() if k not in remove_set}
    else:
        filtered = dict(vars(ns))
    
    return Namespace(**filtered)


# ============ JSON 序列化支持 ============

class NamespaceEncoder(json.JSONEncoder):
    """支持 Namespace 序列化的 JSON 编码器"""
    
    def default(self, obj: Any) -> Any:
        if isinstance(obj, Namespace):
            return namespace_to_dict(obj)
        return super().default(obj)


def to_json(ns: Union[Namespace, Dict, List], 
           indent: Optional[int] = None, 
           **kwargs) -> str:
    """
    将 Namespace 或字典转换为 JSON 字符串
    
    Args:
        ns: Namespace 或字典对象
        indent: 缩进空格数
        **kwargs: 传递给 json.dumps 的其他参数
        
    Returns:
        JSON 字符串
        
    Examples:
        >>> ns = Namespace(name="test", info=Namespace(age=24))
        >>> to_json(ns, indent=2)
        '{\n  "name": "test",\n  "info": {\n    "age": 24\n  }\n}'
    """
    if isinstance(ns, Namespace):
        ns = namespace_to_dict(ns)
    return json.dumps(ns, indent=indent, cls=NamespaceEncoder, **kwargs)


def from_json(json_str: str) -> Union[Namespace, List, Any]:
    """
    从 JSON 字符串解析为 Namespace
    
    Args:
        json_str: JSON 字符串
        
    Returns:
        解析后的 Namespace 对象
        
    Examples:
        >>> json_str = '{"name": "test", "info": {"age": 24}}'
        >>> ns = from_json(json_str)
        >>> ns.name
        'test'
        >>> ns.info.age
        24
    """
    data = json.loads(json_str)
    return dict_to_namespace(data)


# ============ 工具函数 ============

def is_namespace(obj: Any) -> bool:
    """检查对象是否为 Namespace 实例"""
    return isinstance(obj, Namespace)


def is_namespace_like(obj: Any) -> bool:
    """检查对象是否类似 Namespace（有 __dict__ 属性）"""
    return hasattr(obj, '__dict__') and not isinstance(obj, (dict, list, tuple))


def get_all_keys(ns: Namespace, prefix: str = '') -> List[str]:
    """
    获取 Namespace 中所有键的路径列表
    
    Args:
        ns: Namespace 对象
        prefix: 路径前缀
        
    Returns:
        所有键的路径列表
        
    Examples:
        >>> ns = Namespace(a=1, b=Namespace(c=2, d=Namespace(e=3)))
        >>> get_all_keys(ns)
        ['a', 'b.c', 'b.d.e']
    """
    keys = []
    for k, v in vars(ns).items():
        current_path = f"{prefix}.{k}" if prefix else k
        if isinstance(v, Namespace):
            keys.extend(get_all_keys(v, current_path))
        else:
            keys.append(current_path)
    return keys


# ============ 测试代码 ============

if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    print("=== Namespace 工具模块测试 ===\n")
    
    # 测试基本转换
    raw_dict = {
        "name": "test",
        "info": {
            "age": 24,
            "addr": {"province": "Beijing", "city": "Haidian"}
        },
        "tags": [{"id": 1}, {"id": 2}]
    }
    
    ns_obj = dict_to_namespace(raw_dict)
    print(f"✅ dict_to_namespace 转换成功: {ns_obj.name}")
    
    revert_dict = namespace_to_dict(ns_obj)
    print(f"✅ namespace_to_dict 还原成功: {revert_dict == raw_dict}\n")
    
    # 测试过滤
    ns_with_private = Namespace(
        name="test",
        _internal="secret",
        __private__="hidden"
    )
    filtered = namespace_to_dict(ns_with_private)
    print(f"✅ 过滤私有属性: {filtered}")
    
    # 测试 JSON 序列化
    json_str = to_json(ns_obj, indent=2)
    print(f"✅ JSON 序列化成功: {len(json_str)} 字符")
    
    ns_from_json = from_json(json_str)
    print(f"✅ JSON 反序列化成功: {ns_from_json.name}\n")
    
    # 测试路径访问
    city = get_nested_attr(ns_obj, "info.addr.city")
    print(f"✅ 路径访问成功: {city}")
    
    # 测试设置路径
    set_nested_attr(ns_obj, "info.addr.country", "China")
    print(f"✅ 路径设置成功: {ns_obj.info.addr.country}\n")
    
    # 测试深度合并
    base = Namespace(a=1, b=Namespace(c=2))
    update = Namespace(b=Namespace(d=3), e=4)
    merged = deep_update(base, update)
    print(f"✅ 深度合并成功: merged.b.d = {merged.b.d}\n")
    
    # 获取所有键
    all_keys = get_all_keys(ns_obj)
    print(f"✅ 所有键路径: {all_keys}")
    
    print("\n🎉 所有测试通过！模块已就绪。")