"""Thin CLI: `python -m earthquakes.cli {info,viz,predict}`."""

from __future__ import annotations

import argparse
import json
import re
import sys

import pandas as pd

from . import data_loader, viz, predict


def _parse_max_yyyymm(value: str) -> pd.Timestamp:
    if not re.fullmatch(r"\d{6}", value):
        raise argparse.ArgumentTypeError("--max must use yyyyMM format, e.g. 202412")

    year = int(value[:4])
    month = int(value[4:6])
    if month < 1 or month > 12:
        raise argparse.ArgumentTypeError("--max month must be between 01 and 12")
    return pd.Timestamp(year=year, month=month, day=1)


def _cmd_info(_: argparse.Namespace) -> int:
    info = data_loader.summary()
    print(json.dumps(info, indent=2, default=str))
    return 0


def _cmd_viz(args: argparse.Namespace) -> int:
    df = data_loader.load(refresh=args.refresh)
    out = viz.build_all(
        df,
        cluster=not args.no_cluster,
        sample=args.sample,
        min_magnitude=args.min_magnitude,
    )
    for name, path in out.items():
        print(f"{name}: {path}")
    return 0


def _cmd_predict(args: argparse.Namespace) -> int:
    df = data_loader.load(refresh=args.refresh)
    report = predict.train_and_evaluate(
        df, target=args.target, max_month=args.max_month
    )
    units = "events / month" if report.target == "count" else "magnitude"
    print(f"target           : {report.target}  ({units})")
    print(f"train rows       : {report.n_train}   (cell-month samples)")
    print(f"test rows        : {report.n_test}   (last 12 months held out)")
    print(f"MAE (holdout)    : {report.mae:.4f}   ({units})")
    print()
    print("Top 10 cells by predicted next-month value:")
    print("  region           = most common 'place' label seen in that cell")
    print("  lat_bin / lon_bin = south-west corner of a 5deg x 5deg cell")
    print("  last_observed    = most recent month with data (model input)")
    print("  forecast_for     = month being predicted")
    print(f"  forecast_next_month = predicted {report.target} ({units})")
    print()
    with pd.option_context("display.max_colwidth", 60, "display.width", 200):
        print(report.top_predictions.to_string(index=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="earthquakes", allow_abbrev=False)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_info = sub.add_parser("info", help="Print dataset schema + summary stats")
    p_info.set_defaults(func=_cmd_info)

    p_viz = sub.add_parser("viz", help="Build interactive HTML map + timeline")
    p_viz.add_argument("--refresh", action="store_true", help="Re-download dataset")
    p_viz.add_argument(
        "--no-cluster",
        action="store_true",
        help="Draw one marker per earthquake (no clustering). Use with --sample / --min-magnitude.",
    )
    p_viz.add_argument(
        "--sample",
        type=int,
        nargs="?",
        const=30_000,
        default=20_000,
        help="Max markers on the map (bare --sample uses 30000)",
    )
    p_viz.add_argument(
        "--min-magnitude", type=float, default=4.5, help="Filter: minimum magnitude on the map"
    )
    p_viz.set_defaults(func=_cmd_viz)

    p_pred = sub.add_parser("predict", help="Train baseline forecaster + report MAE")
    p_pred.add_argument("--target", choices=["count", "max_mag"], default="count")
    p_pred.add_argument("--refresh", action="store_true", help="Re-download dataset")
    p_pred.add_argument(
        "--max",
        dest="max_month",
        type=_parse_max_yyyymm,
        default=None,
        help="Use data only through yyyyMM, then forecast the next month (e.g. 202412 -> 2025-01).",
    )
    p_pred.set_defaults(func=_cmd_predict)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
