"""品类档案（CategoryProfile）+ 注册表 + active profile 解析。

一个共享引擎、多品类配置：引擎代码（geo/*）品类无关，运行时靠环境变量
`GEO_CATEGORY` 选定 active profile，profile 携带该品类的 queries / 货架 /
watchlist key / 段定义 / 路径根。

⚠️ 不要在本模块 import geo.config（config.get_settings 反过来 import 本模块）——
   避免 import 循环。本模块只依赖 stdlib + 运行时按需 import 各品类包。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # geo-intelligence/


@dataclass(frozen=True)
class CategoryProfile:
    key: str
    pkg: str
    segments: tuple
    real_segments: tuple
    mock_segments: tuple
    use_search: bool
    watchlist_keys: dict
    shelf: dict
    default_segment: str | None

    @property
    def root(self) -> Path:
        return ROOT / "categories" / self.pkg

    @property
    def queries(self):
        return import_module(f"categories.{self.pkg}.queries").QUERIES

    def build_payload(self, segment=None):
        mod = import_module(f"categories.{self.pkg}.dashboard_data")
        return mod.build_payload(segment if segment is not None else self.default_segment)


_PROFILES = {
    "gift-box": CategoryProfile(
        key="gift-box",
        pkg="gift_box",
        segments=("A", "B"),
        real_segments=("A",),
        mock_segments=("B",),
        use_search=True,
        watchlist_keys={"A": "segment_A_zh", "B": "segment_B_en"},
        shelf={"A": "抖音商城", "B": "Shopify/独立站"},
        default_segment=None,
    ),
    "tourism": CategoryProfile(
        key="tourism",
        pkg="tourism",
        segments=("A", "C", "B"),
        real_segments=("A", "C"),
        mock_segments=("B",),
        use_search=False,
        watchlist_keys={"A": "segment_A_domestic", "B": "segment_B_inbound", "C": "segment_C_local"},
        shelf={"A": "小红书/携程/抖音", "B": "TripAdvisor/Google", "C": "小红书/大众点评"},
        default_segment="A",
    ),
}


def active_profile() -> CategoryProfile:
    key = os.environ.get("GEO_CATEGORY", "gift-box")
    if key not in _PROFILES:
        raise ValueError(f"未知 GEO_CATEGORY={key!r}，可选 {list(_PROFILES)}")
    return _PROFILES[key]


def get_profile(key: str) -> CategoryProfile:
    return _PROFILES[key]


def all_profiles():
    return list(_PROFILES.values())
