#!/usr/bin/env python3
"""
Graph visualization module for displaying NetworkX graphs.
Supports saving as interactive HTML (pyvis) or static PNG (matplotlib).

"""

import json
import re
import math
import rdflib
import networkx as nx
from html import escape
from typing import Mapping, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

DEFAULT_LABEL_PALETTE = [
    "#C9A0A0", "#D4A5A5", "#E8C5B0", "#F2D4CC", "#B8A089",
    "#D9BFB0", "#A68E8E", "#C2A391", "#EBC7AF", "#D1B399",
]
DEFAULT_SEMANTIC_LABEL_COLORS = {
    "Class": "#7DA2FF",
    "Backbone": "#5EC8A7",
    "Property": "#F2B36D",
    "__default__": "#C9A0A0",
}

try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    from pyvis.network import Network
    PYVIS_AVAILABLE = True
except ImportError:
    PYVIS_AVAILABLE = False


def save_graph_html(
    G: nx.Graph,
    filename: str = "graph.html",
    title: str = "Graph",
    height: str = "750px",
    label_color_map: Optional[Mapping[str, str]] = None,
    layout_preset: str = "spacious",
    show_legend: bool = True,
    show_graph_stats: bool = True,
) -> None:
    """
    Save an interactive graph visualization as an HTML file (via pyvis).
    Open the file in a browser to explore: drag nodes, zoom, hover for info.

    Args:
        G: NetworkX graph object
        filename: Output HTML file path
        title: Page title shown above the graph
        height: Canvas height (e.g. "750px")
        label_color_map: Optional mapping from node label to node color
        layout_preset: 布局预设（compact/spacious）
        show_legend: Whether to render a color legend (auto-hidden when only one label type exists)
        show_graph_stats: Whether to render node/edge statistics below title
    """
    if not PYVIS_AVAILABLE:
        raise ImportError("pyvis is required. Install with: pip install pyvis")

    directed = G.is_directed()
    safe_title = escape(title, quote=True)
    net = Network(
        height=height,
        width="100%",
        directed=directed,
        notebook=False,
        heading="",
    )
    resolved_label_colors = dict(DEFAULT_SEMANTIC_LABEL_COLORS)
    if label_color_map:
        resolved_label_colors.update(label_color_map)

    preset_name = str(layout_preset).strip().lower()
    layout_presets = {
        "compact": {
            "cell_size": 560.0,
            "radius_min": 70.0,
            "radius_max": 160.0,
            "radius_factor": 30.0,
            "node_size": 23,
            "gravity": -45,
            "central_gravity": 0.009,
            "spring_length": 135,
            "avoid_overlap": 0.6,
            "stabilization": 180,
        },
        "spacious": {
            "cell_size": 760.0,
            "radius_min": 90.0,
            "radius_max": 220.0,
            "radius_factor": 38.0,
            "node_size": 21,
            "gravity": -55,
            "central_gravity": 0.006,
            "spring_length": 165,
            "avoid_overlap": 0.85,
            "stabilization": 220,
        },
    }
    if preset_name not in layout_presets:
        logger.warning("Unknown layout_preset=%s, fallback to compact", layout_preset)
        preset_name = "compact"
    layout_cfg = layout_presets[preset_name]

    node_id_map = {node: str(index) for index, node in enumerate(G.nodes())}
    node_display_id_map = {node: f"n{index}" for index, node in enumerate(G.nodes(), start=1)}

    def _component_sets(graph: nx.Graph) -> list[set]:
        if graph.number_of_nodes() == 0:
            return []
        if graph.is_directed():
            components = [set(c) for c in nx.weakly_connected_components(graph)]
        else:
            components = [set(c) for c in nx.connected_components(graph)]
        components.sort(key=lambda comp: (-len(comp), min(str(node) for node in comp)))
        return components

    def _initial_positions(graph: nx.Graph) -> dict:
        components = _component_sets(graph)
        if not components:
            return {}

        positions: dict = {}
        cols = max(1, int(math.ceil(math.sqrt(len(components)))))
        cell_size = layout_cfg["cell_size"]

        for idx, comp_nodes in enumerate(components):
            row = idx // cols
            col = idx % cols
            offset_x = col * cell_size
            offset_y = row * cell_size
            ordered_nodes = sorted(comp_nodes, key=lambda n: str(n))
            node_count = len(ordered_nodes)
            if node_count == 1:
                positions[ordered_nodes[0]] = (offset_x, offset_y)
                continue

            radius = max(
                layout_cfg["radius_min"],
                min(layout_cfg["radius_max"], layout_cfg["radius_factor"] * math.sqrt(node_count)),
            )
            for local_idx, node in enumerate(ordered_nodes):
                angle = (2.0 * math.pi * local_idx) / node_count
                positions[node] = (
                    offset_x + radius * math.cos(angle),
                    offset_y + radius * math.sin(angle),
                )

        if positions:
            mean_x = sum(x for x, _ in positions.values()) / len(positions)
            mean_y = sum(y for _, y in positions.values()) / len(positions)
            positions = {n: (x - mean_x, y - mean_y) for n, (x, y) in positions.items()}

        return positions

    node_positions = _initial_positions(G)
    used_type_keys: set[str] = set()

    def _node_labels(data: dict) -> list[str]:
        raw = data.get("label", [])
        if isinstance(raw, list):
            return [str(x) for x in raw if x is not None and str(x) != ""]
        if raw is None or str(raw) == "":
            return []
        return [str(raw)]

    def _format_json_block(value: object) -> str:
        try:
            return json.dumps(value, ensure_ascii=False, indent=2, default=str)
        except Exception:
            return str(value)

    def _first_non_empty(*values: object) -> Optional[str]:
        for value in values:
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return None

    for node, data in G.nodes(data=True):
        props = data.get("properties", {})
        node_labels = _node_labels(data)
        short_node_id = node_display_id_map[node]
        label = _first_non_empty(
            data.get("name"),
            props.get("name"),
            short_node_id,
        ) or short_node_id
        label_text = ", ".join(node_labels) if node_labels else ""
        if props:
            node_title = (
                f"id: {node}\n"
                f"display_id: {short_node_id}\n"
                f"label: {label_text}\n"
                f"properties:\n{_format_json_block(props)}"
            )
        else:
            node_title = f"id: {node}\ndisplay_id: {short_node_id}\nlabel: {label_text}"

        # Assign color by first label type
        type_key = str(node_labels[0]) if node_labels else "__default__"
        if type_key not in resolved_label_colors:
            resolved_label_colors[type_key] = DEFAULT_LABEL_PALETTE[len(resolved_label_colors) % len(DEFAULT_LABEL_PALETTE)]
        color = resolved_label_colors[type_key]
        used_type_keys.add(type_key)

        net.add_node(
            node_id_map[node],
            label=str(label),
            title=node_title,
            x=node_positions.get(node, (0.0, 0.0))[0],
            y=node_positions.get(node, (0.0, 0.0))[1],
            shape="dot",
            size=layout_cfg["node_size"],
            color={
                "background": color,
                "border": "#A08080",
                "highlight": {"background": color, "border": "#8E6E6E"},
                "hover": {"background": color, "border": "#8E6E6E"},
            },
            font={"size": 14, "face": "Tahoma", "color": "#333333"},
            shadow={"enabled": True, "color": "rgba(0,0,0,0.15)"},
        )

    for u, v, data in G.edges(data=True):
        rel_id = data.get("id", "")
        rel_label = data.get("label", "")
        rel_props = data.get("properties", {})
        extra_attrs = {k: v for k, v in data.items() if k not in {"id", "label", "properties"} }
        
        edge_title_lines = []
        # 边的信息：id、label、properties/attributes
        if rel_id is not None and rel_id != "":
            edge_title_lines.append(f"id: {rel_id}")
        
        edge_title_lines.append(f"label: {rel_label}")
        
        if rel_props:
            edge_title_lines.append("properties:")
            edge_title_lines.append(_format_json_block(rel_props))
        if extra_attrs:
            edge_title_lines.append("attributes:")
            edge_title_lines.append(_format_json_block(extra_attrs))
        
        edge_title = "\n".join(edge_title_lines)
        
        net.add_edge(
            node_id_map[u], node_id_map[v],
            title=edge_title,
            label=str(rel_label),
            color={"color": "#D3D3D3", "highlight": "#A9A9A9"},
            font={"size": 10, "color": "#666666", "strokeWidth": 3, "strokeColor": "#ffffff"},
            width=1,
            shadow=False,
        )

    options = {
        "nodes": {
            "borderWidth": 2,
            "borderWidthSelected": 4,
            "font": {
                "size": 13,
                "face": "Tahoma",
                "color": "#333333",
            },
        },
        "layout": {
            "improvedLayout": True,
        },
        "edges": {
            "smooth": {"type": "continuous", "roundness": 0.4},
            "color": {"color": "#D3D3D3", "inherit": False},
            "width": 1,
        },
        "interaction": {
            "hover": True,
            "navigationButtons": True,
            "tooltipDelay": 200,
        },
        "physics": {
            "solver": "forceAtlas2Based",
            "forceAtlas2Based": {
                "gravitationalConstant": layout_cfg["gravity"],
                "centralGravity": layout_cfg["central_gravity"],
                "springLength": layout_cfg["spring_length"],
                "springConstant": 0.08,
                "avoidOverlap": layout_cfg["avoid_overlap"],
            },
            "maxVelocity": 50,
            "stabilization": {"iterations": layout_cfg["stabilization"]},
        },
    }
    if directed:
        options["edges"]["arrows"] = {"to": {"enabled": True, "scaleFactor": 0.8}}

    net.set_options(json.dumps(options))

    net.save_graph(filename)
    legend_items = _build_legend_items(used_type_keys, resolved_label_colors)
    _postprocess_saved_html(
        filename,
        safe_title,
        legend_items=legend_items,
        show_legend=show_legend,
        node_count=G.number_of_nodes(),
        edge_count=G.number_of_edges(),
        show_graph_stats=show_graph_stats,
    )

    logger.info("Interactive graph saved to %s", filename)


def _build_legend_items(
    used_type_keys: set[str],
    resolved_label_colors: Mapping[str, str],
) -> list[tuple[str, str]]:
    type_keys = sorted([k for k in used_type_keys if k != "__default__"], key=lambda x: x.lower())
    if "__default__" in used_type_keys:
        type_keys.append("__default__")

    legend_items: list[tuple[str, str]] = []
    for type_key in type_keys:
        display_name = "Default" if type_key == "__default__" else str(type_key)
        color = resolved_label_colors.get(type_key, DEFAULT_SEMANTIC_LABEL_COLORS["__default__"])
        legend_items.append((display_name, str(color)))
    return legend_items


def _render_html_legend(legend_items: list[tuple[str, str]]) -> str:
    if not legend_items:
        return ""

    items_html = "\n".join(
        (
            '<div class="legend-item">'
            f'<span class="legend-swatch" style="background:{escape(color, quote=True)};"></span>'
            f'<span class="legend-label">{escape(label, quote=False)}</span>'
            "</div>"
        )
        for label, color in legend_items
    )

    return f"""
<style>
#legend-box {{
  position: fixed;
  top: 88px;
  right: 16px;
  z-index: 999;
  background: rgba(255,255,255,0.95);
  border: 1px solid rgba(0,0,0,0.12);
  border-radius: 10px;
  padding: 10px 12px;
  font-family: Tahoma, Arial, sans-serif;
  font-size: 13px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
  max-width: 240px;
  max-height: 60vh;
  overflow: auto;
}}
#legend-box .legend-header {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
  font-weight: 600;
  color: #333;
}}
#legend-box .legend-toggle {{
  border: 1px solid rgba(0,0,0,0.18);
  border-radius: 8px;
  background: #f7f7f7;
  cursor: pointer;
  padding: 2px 8px;
  font-size: 12px;
  color: #333;
}}
#legend-items.hidden {{
  display: none;
}}
.legend-item {{
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 6px 0;
}}
.legend-swatch {{
  width: 12px;
  height: 12px;
  border-radius: 3px;
  border: 1px solid rgba(0,0,0,0.18);
}}
.legend-label {{
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}}
</style>
<div id="legend-box">
  <div class="legend-header">
    <div>Legend</div>
    <button class="legend-toggle" onclick="toggleLegend()">Hide</button>
  </div>
  <div id="legend-items">
    {items_html}
  </div>
</div>
<script>
function toggleLegend() {{
  var items = document.getElementById('legend-items');
  var btn = document.querySelector('#legend-box .legend-toggle');
  if (!items || !btn) return;
  var hidden = items.classList.toggle('hidden');
  btn.textContent = hidden ? 'Show' : 'Hide';
}}
</script>
"""


def _postprocess_saved_html(
    filename: str,
    safe_title: str,
    *,
    legend_items: Optional[list[tuple[str, str]]] = None,
    show_legend: bool = True,
    node_count: int = 0,
    edge_count: int = 0,
    show_graph_stats: bool = True,
) -> None:
    """清理 pyvis 生成页面中的重复标题，并可选插入图例。"""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            html = f.read()
        html = re.sub(r"<center>\s*<h1>.*?</h1>\s*</center>\s*", "", html, flags=re.DOTALL)

        legend_block = ""
        if show_legend and legend_items and len(legend_items) > 1:
            legend_block = _render_html_legend(legend_items)

        insertion = "<body>\n"
        if safe_title:
            insertion += f"<center>\n<h1>{safe_title}</h1>\n</center>\n"
        if show_graph_stats:
            if node_count == 0 and edge_count == 0:
                stats_html = (
                    '<center><div style="font-family:Tahoma,Arial,sans-serif;font-size:13px;'
                    'color:#B00020;margin-top:5px;margin-bottom:3px;">'
                    f'⚠ Empty Graph · Nodes: {node_count} · Edges: {edge_count}'
                    "</div></center>\n"
                )
            else:
                stats_html = (
                    '<center><div style="font-family:Tahoma,Arial,sans-serif;font-size:13px;'
                    'color:#555;margin-top:5px;margin-bottom:3px;">'
                    f'Nodes: {node_count} · Edges: {edge_count}'
                    "</div></center>\n"
                )
            insertion += stats_html
        if legend_block:
            insertion += legend_block
        html = html.replace("<body>", insertion, 1)

        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)
    except Exception:
        logger.exception("Failed to postprocess graph html: %s", filename)



def rdflib_to_networkx(
    rdf_graph: rdflib.Graph,
    exclude_literals: bool = True,  # 是否排除字面量节点（避免图过于冗余）
    node_label_key: str = "label",
    edge_predicate_key: str = "label"
) -> nx.DiGraph:
    """
    将 rdflib.Graph 转换为 networkx.DiGraph（RDF 是有向图）
    :param rdf_graph: rdflib 图对象
    :param exclude_literals: 排除 Literal 类型的节点（Literal 通常是属性值，非核心节点）
    :param node_label_key: 节点标签存储的 key（对应现有可视化函数的 label 字段）
    :param edge_predicate_key: 边的谓词存储的 key（对应现有可视化函数的 label 字段）
    :return: 转换后的 NetworkX 有向图
    """
    nx_graph = nx.DiGraph()
    
    # 遍历 RDF 三元组 (s, p, o)
    for subj, pred, obj in rdf_graph:
        # 处理节点：统一转为字符串，避免 URIRef/BNode 类型问题
        def _node_id(node):
            if isinstance(node, rdflib.BNode):
                return f"bnode_{node}"  # BNode 转为可读字符串
            return str(node)
        
        subj_id = _node_id(subj)
        obj_id = _node_id(obj)
        
        # 过滤字面量节点（可选）
        if exclude_literals and isinstance(obj, rdflib.Literal):
            continue
        
        # 添加主体节点（带基础属性）
        if subj_id not in nx_graph.nodes:
            nx_graph.add_node(
                subj_id,
                {
                    node_label_key: [str(subj.split("#")[-1] if "#" in str(subj) else subj)],
                    "type": "URI" if isinstance(subj, rdflib.URIRef) else "BNode",
                    "original": subj  # 保留原始 rdflib 对象（可选）
                }
            )
        
        # 添加客体节点（带基础属性）
        if obj_id not in nx_graph.nodes:
            nx_graph.add_node(
                obj_id,
                {
                    node_label_key: [str(obj.split("#")[-1] if "#" in str(obj) else obj)],
                    "type": "URI" if isinstance(obj, rdflib.URIRef) else "BNode",
                    "original": obj  # 保留原始 rdflib 对象（可选）
                }
            )
        
        # 添加边（谓词作为边的 label）
        pred_label = str(pred.split("#")[-1] if "#" in str(pred) else pred)
        nx_graph.add_edge(
            subj_id,
            obj_id,
            {
                edge_predicate_key: pred_label,
                "predicate_uri": str(pred),
                "original_predicate": pred  # 保留原始谓词对象（可选）
            }
        )
    
    return nx_graph

# 新增兼容版可视化函数（对用户透明）
def save_graph_html_compatible(
    graph,  # 支持 networkx.Graph 或 rdflib.Graph
    *args, **kwargs
):
    """兼容 rdflib.Graph 的 HTML 可视化函数"""
    if isinstance(graph, rdflib.Graph):
        nx_graph = rdflib_to_networkx(graph)
    elif isinstance(graph, nx.Graph):
        nx_graph = graph
    else:
        raise TypeError(f"不支持的图类型：{type(graph)}，仅支持 networkx.Graph 或 rdflib.Graph")
    
    # 调用原有函数
    return save_graph_html(nx_graph, *args, **kwargs)