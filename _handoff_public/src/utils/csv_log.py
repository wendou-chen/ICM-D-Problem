# -*- coding: utf-8 -*-
"""
Robust CSV writers for experiment logging.

Goals:
- Append one dict-row to CSV with fixed column order.
- Create file with header if missing.
- Prevent column drift across runs.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd


def append_row_csv(path: str | Path, row: Dict, columns: Optional[Iterable[str]] = None) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    if columns is None:
        columns = list(row.keys())
    else:
        columns = list(columns)

    df = pd.DataFrame([{k: row.get(k, None) for k in columns}], columns=columns)
    write_header = not p.exists()
    df.to_csv(p, mode="a", index=False, header=write_header, encoding="utf-8-sig")
    return p


def write_table_csv(path: str | Path, rows: List[Dict], columns: Optional[Iterable[str]] = None) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    if columns is None:
        cols: List[str] = []
        seen = set()
        for r in rows:
            for k in r.keys():
                if k not in seen:
                    cols.append(k)
                    seen.add(k)
        columns = cols
    else:
        columns = list(columns)

    df = pd.DataFrame([{k: r.get(k, None) for k in columns} for r in rows], columns=columns)
    df.to_csv(p, index=False, encoding="utf-8-sig")
    return p
