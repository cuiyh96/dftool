# dftool - Data Function Tool

`dftool` 是一个日常数据处理的工具函数集合，提供了一系列便捷的数据处理、文件操作、JSON解析等功能。

## ✨ 功能特性

- **DataFrame 列处理**：列筛选、重命名、填充缺失值、字典列展开等
- **JSON 工具**：安全解析、从文本提取 JSON
- **通用工具**：文件读写（JSON/JSONL/YAML/TXT）、序列截断填充
- **路径工具**：路径转换、目录信息获取
- **时间工具**：时间格式转换、文件时间获取
- **图可视化**：NetworkX/Pyvis 交互式图渲染
- **命名空间工具**：字典与 Namespace 递归转换、路径访问、深度合并、JSON 序列化

## 项目结构
```
dftool/
├── dftool/             # 包源代码目录
│ ├── __init__.py       # 包入口，统一导出所有公共接口
│ ├── version.py        # 版本信息
│ ├── column_processor.py       # DataFrame 列处理工具（筛选、重命名、填充、展开等）
│ ├── common_utils.py           # 通用工具（文件读写、序列处理、哈希生成等）
│ ├── graph_tool.py             # 图可视化工具（NetworkX/Pyvis 交互式渲染）
│ ├── json_utils.py             # JSON 解析工具（安全解析、从文本提取 JSON）
│ ├── namespace_tools.py        # 命名空间工具（字典与 Namespace 递归转换）
│ ├── path_utils.py             # 路径操作工具（路径转换、目录信息、隐藏文件检测）
│ └── time_utils.py             # 时间处理工具（时间格式化、时间戳转换）
│
├── tests/               # 单元测试目录
│ ├── __init__.py          # 测试包初始化
│ ├── test_basic.py        # 核心功能单元测试
│ └── test_namespace.py    # 命名空间工具专项测试
│
├── pyproject.toml         # 项目配置文件（包元数据、依赖、构建配置）
├── README.md              # 项目说明文档
├── LICENSE                # MIT 许可证
└── .gitignore             # Git 版本控制忽略文件
```

### 模块功能说明

| 模块文件 | 主要功能 | 核心类/函数 |
|---------|---------|------------|
| `column_processor.py` | DataFrame 列处理 | `ColumnProcessor` 类 |
| `common_utils.py` | 通用工具 | `CommonUtils` 类 |
| `graph_tool.py` | 图可视化 | `save_graph_html()`, `save_graph_html_compatible()`, `rdflib_to_networkx()` |
| `json_utils.py` | JSON 解析 | `JsonUtils` 类 |
| `namespace_tools.py` | 命名空间转换 | `dict_to_namespace()`, `namespace_to_dict()`, `deep_update()`, `get_nested_attr()`, `set_nested_attr()`, `filter_namespace_keys()`, `to_json()`, `from_json()` |
| `path_utils.py` | 路径操作 | `PathUtils` 类 |
| `time_utils.py` | 时间处理 | `TimeUtils` 类 |

## 📦 安装

### 本地开发安装

```bash
cd /path/to/dftool
pip install -e .
```
