"""仪表盘 CLI：build_payload → render_html → 写自包含单文件 HTML。

    python -m geo.reporting.dashboard [--out PATH] [--segment A]

默认 segment=None（全部，现仅 segment A 有真数据），默认 out=<repo>/dashboard.html。
零网络 / 零编造：数字全来自真实 captures 经纯函数计算（dashboard_data.build_payload）。
"""
from __future__ import annotations

import argparse
from pathlib import Path

from geo.category import ROOT, active_profile
from geo.reporting.dashboard_render import render_html


def main(argv: list[str] | None = None) -> int:
    prof = active_profile()
    default_out = ROOT / f"{prof.key}-dashboard.html"

    parser = argparse.ArgumentParser(description="GEO Intelligence 遥测控制台生成器")
    parser.add_argument("--out", type=Path, default=default_out, help="输出 HTML 路径")
    parser.add_argument("--segment", default=None, help="买家分段（如 A）；默认按品类")
    args = parser.parse_args(argv)

    payload = prof.build_payload(args.segment)
    html = render_html(payload)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    size_kb = out_path.stat().st_size / 1024
    n_captures = payload["meta"]["n_captures"]
    print(f"已生成仪表盘 → {out_path}")
    print(f"  大小 {size_kb:.1f} KB · n_captures={n_captures} · "
          f"segment={args.segment or '全部'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
