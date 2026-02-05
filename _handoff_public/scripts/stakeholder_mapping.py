import argparse
import logging
import os
import sys
import time
import json
import glob
import math
import pandas as pd
import numpy as np
import scipy.spatial
from shapely.geometry import Point, shape, MultiPolygon, Polygon
from shapely.prepared import prep

# =============================================================================
# CONSTANTS & CONFIG
# =============================================================================
LOG_SCHEMA = [
    "ts_utc", "level", "event", "repo", "script", "seed", "inputs", "outputs", "stats", "notes"
]

REQUIRED_COLUMNS_OD_LABELS = [
    "od_id", "origin", "dest", "stakeholder", "weight", 
    "origin_lon", "origin_lat", "dest_lon", "dest_lat",
    "dist_bus_o_m", "dist_bus_d_m", "ridership_o", "ridership_d",
    "in_city_o", "in_city_d"
]

STAKEHOLDER_ORDER = [
    "Residents", "Transit-dependent", "Business/Port", 
    "Suburban commuters", "Passthrough", "Tourists"
]

# Proxies (will be overridden by CLI or used as default)
# Default bbox strings
PORT_BBOX_DEFAULT = "-76.60,39.20,-76.52,39.27"
TOURIST_BBOX_DEFAULT = "-76.62,39.27,-76.59,39.30"

# =============================================================================
# LOGGING UTILS
# =============================================================================
def get_utc_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def write_log(log_path, record):
    """Append a JSON record to the log file."""
    for k in LOG_SCHEMA:
        if k not in record:
            record[k] = None
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record) + "\n")

# =============================================================================
# GEOMETRY HELPERS
# =============================================================================
def parse_bbox(bbox_str):
    try:
        parts = [float(x) for x in bbox_str.split(',')]
        if len(parts) != 4:
            raise ValueError
        return parts # min_lon, min_lat, max_lon, max_lat
    except:
        return None

def is_in_bbox(lon, lat, bbox):
    if bbox is None: return False
    return (lon >= bbox[0]) & (lon <= bbox[2]) & (lat >= bbox[1]) & (lat <= bbox[3])

def get_meter_proj_factors(lat0):
    # approximate meters per degree
    lat_rad = lat0 * math.pi / 180.0
    x_factor = math.cos(lat_rad) * 111320.0
    y_factor = 110540.0
    return x_factor, y_factor

def simple_to_markdown(df):
    """Simple markdown table generator to avoid tabulate dependency."""
    cols = list(df.columns)
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    lines = [header, sep]
    for _, row in df.iterrows():
        vals = []
        for c in cols:
            v = row[c]
            if isinstance(v, float):
                vals.append(f"{v:.6f}")
            else:
                vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)

# =============================================================================
# MAIN
# =============================================================================
def main():
    parser = argparse.ArgumentParser(description="Stakeholder Mapping for OD pairs")
    parser.add_argument("--repo", default=".", help="Repository root")
    parser.add_argument("--outdir", default="outputs/stakeholders", help="Output directory")
    parser.add_argument("--seed", type=int, default=20250101, help="Random seed")
    
    parser.add_argument("--od_pairs", default=None, help="Path to OD pairs JSON. If None, auto-select latest.")
    parser.add_argument("--r_bus_m", type=float, default=300, help="Max distance to bus stop for transit-dependent (meters)")
    parser.add_argument("--ridership_top_q", type=float, default=0.30, help="Top quantile for ridership (e.g. 0.30 means top 30%)")
    parser.add_argument("--eta", type=float, default=1.0, help="Weight multiplier factor for ridership")
    
    parser.add_argument("--port_bbox", default=PORT_BBOX_DEFAULT, help="lon_min,lat_min,lon_max,lat_max")
    parser.add_argument("--tourist_bbox", default=TOURIST_BBOX_DEFAULT, help="lon_min,lat_min,lon_max,lat_max")
    
    args = parser.parse_args()
    
    # Setup
    repo_root = os.path.abspath(args.repo)
    out_dir = os.path.join(repo_root, args.outdir)
    os.makedirs(out_dir, exist_ok=True)
    doc_dir = os.path.join(repo_root, "docs")
    os.makedirs(doc_dir, exist_ok=True)
    
    log_path = os.path.join(out_dir, "run_log.jsonl")
    
    import random
    random.seed(args.seed)
    np.random.seed(args.seed)
    
    # Init Log
    base_log = {
        "ts_utc": get_utc_iso(),
        "level": "INFO",
        "repo": repo_root,
        "script": os.path.basename(__file__),
        "seed": args.seed,
        "inputs": {},
        "outputs": {},
        "stats": {}
    }
    write_log(log_path, {**base_log, "event": "start"})
    
    try:
        # 1. Resolve Inputs
        # OD Pairs
        od_path = args.od_pairs
        if not od_path:
            # Auto-discover: outputs/task2/od_pairs_*.json
            pattern = os.path.join(repo_root, "outputs/task2/od_pairs_*.json")
            files = glob.glob(pattern)
            if not files:
                raise FileNotFoundError("No OD pairs files found in outputs/task2/")
            # Deterministic tie-break: sort by filename and take last
            files.sort()
            od_path = files[-1]
            print(f"Auto-selected OD pairs: {od_path}")
        
        graph_nodes_path = os.path.join(repo_root, "data/processed/graph_nodes.csv")
        bus_stops_path = os.path.join(repo_root, "data/processed/bus_stops_clean.csv")
        boundary_path = os.path.join(repo_root, "data/processed/boundary.geojson")
        
        base_log["inputs"] = {
            "od_pairs": od_path,
            "graph_nodes": graph_nodes_path,
            "bus_stops": bus_stops_path,
            "boundary": boundary_path
        }
        
        # 2. Load Data
        print("Loading data...")
        with open(od_path, 'r', encoding='utf-8') as f:
            od_json = json.load(f)
        
        # Handle dict format (from od_sampling.py) or plain list
        if isinstance(od_json, dict) and "pairs" in od_json:
            od_data = od_json["pairs"]
        elif isinstance(od_json, list):
            od_data = od_json
        else:
            raise ValueError(f"Unknown OD pairs format in {od_path}")
             # od_data structure: list of [origin_id, dest_id]
        
        # Convert to DF
        # We need a stable ID. unique? No, od pairs might repeat? 
        # Usually od_data is list of pairs.
        # Let's assign an ID: o_id + "_" + d_id + "_" + index
        # To be safe and compatible with expected schema, we need od_id.
        # Let's format it as "idx_u_v" ? Or just "u:v"? u:v might not be unique if sampled multiple times.
        # The prompt says: "Prefer od_id stable string 'o|d|idx' or similar"
        od_list = []
        for idx, pair in enumerate(od_data):
            u, v = str(pair[0]), str(pair[1])
            od_id = f"{u}|{v}|{idx}"
            od_list.append({'od_id': od_id, 'origin': u, 'dest': v})
        
        df_od = pd.DataFrame(od_list)
        
        # Nodes
        df_nodes = pd.read_csv(graph_nodes_path)
        df_nodes['node_id'] = df_nodes['node_id'].astype(str)
        nodes_map = df_nodes.set_index('node_id')[['lon', 'lat']].to_dict('index')
        
        # Bus Stops
        df_stops = pd.read_csv(bus_stops_path)
        if 'Stop_Rider' not in df_stops.columns:
            df_stops['Stop_Rider'] = 0
        df_stops['Stop_Rider'] = df_stops['Stop_Rider'].fillna(0)
        
        # 3. Augment OD with Coordinates
        print("Augmenting coordinates...")
        # map u -> lon, lat
        def get_coords(nid):
            if nid in nodes_map:
                return nodes_map[nid]['lon'], nodes_map[nid]['lat']
            return np.nan, np.nan
            
        # Vectorized map is faster, but simple apply is ok for N<100k
        # Actually join is better
        # Join O
        df_od = df_od.merge(df_nodes[['node_id', 'lon', 'lat']], left_on='origin', right_on='node_id', how='left').rename(columns={'lon': 'origin_lon', 'lat': 'origin_lat'}).drop(columns=['node_id'])
        # Join D
        df_od = df_od.merge(df_nodes[['node_id', 'lon', 'lat']], left_on='dest', right_on='node_id', how='left').rename(columns={'lon': 'dest_lon', 'lat': 'dest_lat'}).drop(columns=['node_id'])
        
        # Check completeness
        if df_od[['origin_lon', 'origin_lat', 'dest_lon', 'dest_lat']].isnull().any().any():
            write_log(log_path, {**base_log, "level": "WARN", "event": "missing_coords", "notes": "Some nodes not found in graph_nodes"})
            # Drop or fill? Requirements say "fail fast" or "run"? Code says "Inputs: graph_nodes". Presume clean.
            # We will keep them but values will be NaN, potentially crashing later steps if not careful.
            # Fill with 0 to safely run? Or drop. Drop is safer for analysis.
            # But OD file dictates the workload.
            pass
        
        # 4. Bus Stop Analysis (KDTree)
        print("Analyzing bus stops...")
        
        lat0 = df_nodes['lat'].mean()
        xf, yf = get_meter_proj_factors(lat0)
        
        # Project stops
        stop_x = df_stops['stop_lon'] * xf
        stop_y = df_stops['stop_lat'] * yf
        stop_points = np.column_stack((stop_x, stop_y))
        
        tree = scipy.spatial.cKDTree(stop_points)
        
        # Project OD points
        # Handle NaNs if any
        valid_mask = ~df_od['origin_lon'].isnull() & ~df_od['dest_lon'].isnull()
        
        # Origins
        o_x = df_od.loc[valid_mask, 'origin_lon'] * xf
        o_y = df_od.loc[valid_mask, 'origin_lat'] * yf
        o_points = np.column_stack((o_x, o_y))
        
        # Dests
        d_x = df_od.loc[valid_mask, 'dest_lon'] * xf
        d_y = df_od.loc[valid_mask, 'dest_lat'] * yf
        d_points = np.column_stack((d_x, d_y))
        
        # Query
        dist_o, idx_o = tree.query(o_points)
        dist_d, idx_d = tree.query(d_points)
        
        # Assign back
        df_od['dist_bus_o_m'] = np.nan
        df_od['dist_bus_d_m'] = np.nan
        df_od['ridership_o'] = 0.0
        df_od['ridership_d'] = 0.0
        
        df_od.loc[valid_mask, 'dist_bus_o_m'] = dist_o
        df_od.loc[valid_mask, 'dist_bus_d_m'] = dist_d
        
        # Ridership lookups
        ridership_vals = df_stops['Stop_Rider'].values
        df_od.loc[valid_mask, 'ridership_o'] = ridership_vals[idx_o]
        df_od.loc[valid_mask, 'ridership_d'] = ridership_vals[idx_d]
        
        # 5. City Boundary (Point in Polygon)
        print("Checking city boundary...")
        import geopandas as gpd
        gdf_bound = gpd.read_file(boundary_path)
        # Assume first polygon is the city
        city_poly = gdf_bound.geometry.iloc[0]
        prep_poly = prep(city_poly)
        
        def check_in_city(lon, lat):
            if pd.isnull(lon) or pd.isnull(lat): return 0
            return 1 if prep_poly.contains(Point(lon, lat)) else 0
        
        # Vectorize apply? Shapely is slow in apply.
        # But this is rigorous.
        df_od['in_city_o'] = df_od.apply(lambda r: check_in_city(r['origin_lon'], r['origin_lat']), axis=1)
        df_od['in_city_d'] = df_od.apply(lambda r: check_in_city(r['dest_lon'], r['dest_lat']), axis=1)
        
        # 6. Stakeholder Classification
        print("Classifying stakeholders...")
        
        port_bbox = parse_bbox(args.port_bbox)
        tourist_bbox = parse_bbox(args.tourist_bbox)
        
        # Ridership threshold
        # quantile excludes NaNs usually, list is clean
        ridership_threshold = np.quantile(df_stops['Stop_Rider'].dropna(), 1.0 - args.ridership_top_q)
        
        def classify_row(row):
            # 1) Business/Port
            if is_in_bbox(row['origin_lon'], row['origin_lat'], port_bbox) or \
               is_in_bbox(row['dest_lon'], row['dest_lat'], port_bbox):
                return "Business/Port"
            
            # 2) Tourists
            if is_in_bbox(row['origin_lon'], row['origin_lat'], tourist_bbox) or \
               is_in_bbox(row['dest_lon'], row['dest_lat'], tourist_bbox):
                return "Tourists"
            
            # 3) Transit-dependent
            # min dist <= r_bus_m AND max ridership >= threshold
            d_min = min(row['dist_bus_o_m'], row['dist_bus_d_m'])
            r_max = max(row['ridership_o'], row['ridership_d'])
            
            if (not pd.isnull(d_min)) and (d_min <= args.r_bus_m) and (r_max >= ridership_threshold):
                return "Transit-dependent"
            
            # 4) Suburban
            if row['in_city_o'] != row['in_city_d']:
                return "Suburban commuters"
            
            # 5) Residents
            if row['in_city_o'] == 1 and row['in_city_d'] == 1:
                return "Residents"
            
            # 6) Passthrough
            return "Passthrough"
        
        df_od['stakeholder'] = df_od.apply(classify_row, axis=1)
        
        # 7. Weight Calculation
        # B.6
        # Transit-dependent: weight = 1.0 + eta * norm_ridership
        # norm_ridership based on global min/max of endpoints average?
        # Prompt: "avg_endpoint_ridership".
        # Prompt: "norm_ridership = (avg_endpoint_ridership - min) / (max - min + 1e-9), clamped [0,1]"
        # "min" and "max" refer to the range of avg_ridership across ALL OD pairs? Or all stops?
        # Context suggests "among the OD pairs relevant"? Or global scale.
        # "norm_ridership = (avg_endpoint_ridership - min) / (max - min...)"
        # Let's compute avg_ridership for each row first.
        
        df_od['avg_ridership'] = (df_od['ridership_o'] + df_od['ridership_d']) / 2.0
        r_min = df_od['avg_ridership'].min()
        r_max = df_od['avg_ridership'].max()
        
        df_od['norm_ridership'] = (df_od['avg_ridership'] - r_min) / (r_max - r_min + 1e-9)
        df_od['norm_ridership'] = df_od['norm_ridership'].clip(0, 1)
        
        def calc_weight(row):
            w = 1.0
            if row['stakeholder'] == 'Transit-dependent':
                w = 1.0 + args.eta * row['norm_ridership']
            elif row['stakeholder'] == 'Business/Port':
                w = w * 1.2
            return w
            
        df_od['weight'] = df_od.apply(calc_weight, axis=1)
        df_od['weight'] = df_od['weight'].round(6)
        
        # 8. Outputs
        # Dist rounding
        df_od['dist_bus_o_m'] = df_od['dist_bus_o_m'].round(2)
        df_od['dist_bus_d_m'] = df_od['dist_bus_d_m'].round(2)
        
        # Sort
        df_od.sort_values('od_id', inplace=True)
        
        # File 1: Labels
        out_labels = os.path.join(out_dir, "od_stakeholder_labels.csv")
        df_od[REQUIRED_COLUMNS_OD_LABELS].to_csv(out_labels, index=False, float_format='%.6f', encoding='utf-8', lineterminator='\n')
        
        # File 2: Summary
        summary = df_od.groupby('stakeholder').agg(
            count=('stakeholder', 'count'),
            weight_mean=('weight', 'mean'),
            weight_sum=('weight', 'sum')
        ).reset_index()
        summary.sort_values('stakeholder', inplace=True)
        
        out_summary = os.path.join(out_dir, "stakeholder_summary.csv")
        summary.to_csv(out_summary, index=False, float_format='%.6f', encoding='utf-8', lineterminator='\n')
        
        # 9. Docs
        doc_path = os.path.join(doc_dir, "stakeholder_mapping.md")
        doc_content = f"""# Stakeholder Mapping Documentation

**Run Info**
- Date: {get_utc_iso()}
- OD Source: {os.path.basename(od_path)}
- Script: {os.path.basename(__file__)}

**Parameters**
- r_bus_m: {args.r_bus_m}
- ridership_top_q: {args.ridership_top_q}
- eta: {args.eta}
- Ridership Threshold used: {ridership_threshold:.2f}

**Rule Cascade**
1. **Business/Port**: Origin OR Dest in Port BBox ({args.port_bbox}).
2. **Tourists**: Origin OR Dest in Tourist BBox ({args.tourist_bbox}).
3. **Transit-dependent**: min(dist_bus) <= {args.r_bus_m}m AND max(ridership) >= {ridership_threshold:.2f}.
4. **Suburban commuters**: One inside city, one outside.
5. **Residents**: Both inside city.
6. **Passthrough**: Both outside city (and not captured above).

**Summary**
{simple_to_markdown(summary)}

**Limitations**
- Bounding boxes are rectangular proxies.
- "In City" check uses official boundary polygon.
- Ridership is based on nearest stop (direct distance), ignoring walk network.
"""
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write(doc_content)
            
        write_log(log_path, {**base_log, "event": "outputs_written", "outputs": {
            "labels": out_labels,
            "summary": out_summary,
            "docs": doc_path
        }})
        
        print(f"Done. Outputs in {out_dir}")
        write_log(log_path, {**base_log, "event": "done"})
        
    except Exception as e:
        write_log(log_path, {**base_log, "level": "ERROR", "event": "exception", "notes": str(e)})
        raise

if __name__ == "__main__":
    main()
