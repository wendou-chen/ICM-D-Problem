---
name: data_visualization_expert
version: 0.1.0
description: 专注于使用 Python (Matplotlib/Seaborn) 生成出版级可复现可比较的数据可视化，并支持复杂网络可视化（NetworkX）
autodetect: true

dependencies:
  python: ">=3.10"
  packages:
    - pandas: ">=2.0"
    - numpy: ">=1.24"
    - matplotlib: ">=3.7"
    - seaborn: ">=0.12"
    - networkx: ">=3.1"

defaults:
  output_dir: "./figs"
  export_formats: ["png", "pdf", "svg"]
  dpi: 300
  bbox_inches: "tight"
  pad_inches: 0.05
  figsize:
    single_column: [3.4, 2.6]
    double_column: [7.0, 3.0]
  random_seed: 42
  palette: "colorblind"

api:
  required_args:
    - data
  optional_args:
    - intent: ["auto", "distribution", "compare", "relationship", "timeseries", "network"]
    - schema: "dict{col: continuous|categorical|time}"   # 可选：显式指定字段类型
    - title: "str"
    - save_name: "str"                                  # 不含后缀；若缺省则自动生成
    - export: "bool"                                    # 默认 true

inputs:
  - type: dataframe
    desc: pandas.DataFrame，优先；列名可包含中文
  - type: dict/array
    desc: dict/list/numpy array；需能转换成 DataFrame
  - type: graph
    desc: networkx.Graph / DiGraph，用于网络可视化
  - type: file_path
    desc: csv/xlsx/json 路径（若提供则加载）

outputs:
  - type: figure
    desc: 返回 (fig, ax) 或 axes 数组
  - type: files
    desc: 默认保存 png + pdf + svg 到 output_dir，并返回路径列表

robustness:
  missing:
    default: "dropna_report"        # 删除缺失并报告比例
  outliers:
    default: "show_raw_and_clipped" # 同时给原始图+截尾图（对比）
    clip_quantile: [0.01, 0.99]
  long_tail:
    default: "prefer_ecdf_or_log"   # 长尾优先 ECDF 或 log 轴

constraints:
  - 不使用 seaborn 主题覆盖过强的默认风格；必须可复现
  - 图中必须包含标题/轴标签/图例（除非用户要求去掉）
  - 默认颜色盲友好；默认 dpi>=300
---
