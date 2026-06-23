"""
dftool - Data Function Tool
A collection of utility functions for daily data processing tasks.

This package provides various tools for:
- DataFrame column processing
- JSON parsing and extraction
- File I/O operations
- Path manipulation
- Time utilities
- Graph visualization
- Namespace operations
"""

from .version import __version__

# 核心工具类
from .column_processor import ColumnProcessor
from .common_utils import CommonUtils
from .json_utils import JsonUtils
from .path_utils import PathUtils
from .time_utils import TimeUtils

# 图可视化工具
from .graph_tool import (
    save_graph_html,
    save_graph_html_compatible,
    rdflib_to_networkx,
)

# 命名空间工具
from .namespace_tools import (
    dict_to_namespace,
    namespace_to_dict,
    deep_update,
    get_nested_attr,
    set_nested_attr,
    filter_namespace_keys,
    NamespaceEncoder,
    to_json,
    from_json,
    is_namespace,
    get_all_keys,
)

__all__ = [
    # 版本
    "__version__",
    # 核心工具类
    "ColumnProcessor",
    "CommonUtils",
    "JsonUtils",
    "PathUtils",
    "TimeUtils",
    # 图可视化
    "save_graph_html",
    "save_graph_html_compatible",
    "rdflib_to_networkx",
    # 命名空间工具
    "dict_to_namespace",
    "namespace_to_dict",
    "deep_update",
    "get_nested_attr",
    "set_nested_attr",
    "filter_namespace_keys",
    "NamespaceEncoder",
    "to_json",
    "from_json",
    "is_namespace",
    "get_all_keys",
]