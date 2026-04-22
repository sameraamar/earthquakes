"""Thin CLI: `python -m earthquakes.cli {info,viz,predict}`."""

from __future__ import annotations

import argparse
import json
import sys

from . import data_loader, viz, predict


def _cmd_info(_: argparse.Namespace) -> int:
    info = data_loader.summary()
    print(json.dumps(info, indent=2, default=str))
    return 0


def _cmd_viz(args: argparse.Namespace) -> int:
    df = data_loader.load(refresh=args.refresh)
    out = viz.build_all(df)
    for name, path in out.items():
        print(f"{name}: {path}")
    return 0


def _cmd_predict(args: argparse.Namespace) -> int:
    df = data_loader.load(refresh=args.refresh)
    report = predict.train_and_evaluate(df, target=args.target)
    print(f"target           : {report.target}")
    print(f"train rows       : {report.n_train}")
    print(f"test rows        : {report.n_test}")
    print(f"MAE (holdout)    : {report.mae:.4f}")
    print("top next-month forecasts:")
    print(report.top_predictions.to_string(index=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="earthquakes")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_info = sub.add_parser("info", help="Print dataset schema + summary stats")
    p_info.set_defaults(func=_cmd_info)

    p_viz = sub.add_parser("viz", help="Build interactive HTML map + timeline")
    p_viz.add_argument("--refresh", action="store_true", help="Re-download dataset")
    p_viz.set_defaults(func=_cmd_viz)

    p_pred = sub.add_parser("predict", help="Train baseline forecaster + report MAE")
    p_pred.add_argument("--target", choices=["count", "max_mag"], default="count")
    p_pred.add_argument("--refresh", action="store_true", help="Re-download dataset")
    p_pred.set_defaults(func=_cmd_predict)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
