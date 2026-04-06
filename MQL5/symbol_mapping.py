"""
Webhook 銘柄 → MetaTrader 5 正式名の変換（config/mapping.json）。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_MAPPING_PATH = Path(__file__).resolve().parent.parent / "config" / "mapping.json"
_MAPPING_MTIME: float | None = None
_MAPPING_CACHE: dict[str, str] = {}


def strip_exchange_prefix(symbol: str) -> str:
    if ":" in symbol:
        return symbol.split(":")[-1]
    return symbol


def load_symbol_mapping(path: Path | None = None) -> dict[str, str]:
    """
    mapping.json を読み込む。ファイルが無い／不正なら空 dict。
    キーが "_" で始まる項目は無視（メモ用プレースホルダ可）。
    """
    global _MAPPING_MTIME, _MAPPING_CACHE
    p = path or _MAPPING_PATH
    try:
        mtime = p.stat().st_mtime
    except OSError:
        _MAPPING_MTIME, _MAPPING_CACHE = None, {}
        return {}

    if _MAPPING_MTIME == mtime and _MAPPING_CACHE is not None:
        return _MAPPING_CACHE

    out: dict[str, str] = {}
    try:
        with open(p, encoding="utf-8") as f:
            raw: Any = json.load(f)
        if isinstance(raw, dict):
            for k, v in raw.items():
                sk = str(k).strip()
                if not sk or sk.startswith("_"):
                    continue
                if isinstance(v, str) and v.strip():
                    out[sk] = v.strip()
    except (json.JSONDecodeError, OSError):
        out = {}

    _MAPPING_MTIME, _MAPPING_CACHE = mtime, out
    return out


def resolve_symbol_for_mt5(raw_symbol: str, mapping: dict[str, str]) -> str:
    """
    Webhook 側の symbol を MT5 用に解決する。
    1) 元文字列、"EXCHANGE:SYMBOL" の SYMBOL 部の順でマップを照会（大文字小文字無視の突き合わせあり）
    2) マップに無ければ従来どおりプレフィックス除去のみ
    """
    if not raw_symbol or not str(raw_symbol).strip():
        return raw_symbol
    s = str(raw_symbol).strip()
    if not mapping:
        return strip_exchange_prefix(s)

    stripped = strip_exchange_prefix(s)

    def lookup(needle: str) -> str | None:
        if needle in mapping:
            return mapping[needle]
        nu = needle.upper()
        for mk, mv in mapping.items():
            if mk.upper() == nu:
                return mv
        return None

    for cand in (s, stripped):
        hit = lookup(cand)
        if hit:
            return hit

    return stripped
