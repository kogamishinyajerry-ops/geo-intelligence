"""旅游 GEO 仪表盘 CLI —— 装配 payload → 渲染单文件 HTML 控制台。

    python -m geo.reporting.dashboard [--out PATH] [--segment A|C|B]

接缝：build_payload(assembler) → render_html(renderer)。本 CLI 只做 I/O 编排，零指标逻辑。
输出自包含单文件 HTML（零外链 / 零网络），可 file:// 直开评审。
"""
from __future__ import annotations

import argparse
from pathlib import Path

from geo.reporting.dashboard_data import build_payload
from geo.reporting.dashboard_render import render_html

DEFAULT_OUT = (
    "/Users/Zhuanz/Desktop/geo-intelligence/shanghai-tourism-geo/dashboard.html"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="geo.reporting.dashboard",
        description="装配旅游 GEO 仪表盘 payload 并渲染单文件 HTML 控制台",
    )
    parser.add_argument("--out", default=DEFAULT_OUT, help="HTML 输出路径")
    parser.add_argument(
        "--segment",
        default="A",
        choices=["A", "C", "B"],
        help="游客客群（A 外地客主战场 / C 本地客 / B 入境客待 key）",
    )
    args = parser.parse_args(argv)

    payload = build_payload(args.segment)
    html = render_html(payload)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    n_captures = payload["meta"]["n_captures"]
    size_kb = out_path.stat().st_size / 1024
    print(f"dashboard → {out_path}")
    print(f"  segment={args.segment}  n_captures={n_captures}  size={size_kb:.1f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
