"""Risk-coverage analysis for skill reuse.

A gate either commits to a retrieved skill or falls back to the generic
baseline.  For a threshold on the gate score, ``coverage`` is the fraction of
tasks on which the gate commits, and ``risk`` is the fraction of committed
tasks whose selected skill is worse than the fallback by more than a small
margin.  This module turns the task-level records in ``results.json`` into
risk-coverage curves and summaries.
"""
from __future__ import annotations

from html import escape
import json
from pathlib import Path

from .tasks import SUCCESS_THRESHOLD

EPSILON = 0.02
TARGET_RISKS = (0.05, 0.10, 0.20)
METHOD_LABELS = {
    "random": "random",
    "semantic": "embedding",
    "frequency": "frequency",
    "logistic": "logistic",
    "temperature": "temperature",
    "isotonic": "isotonic",
    "fewshot": "target-calibrated",
    "isotonic_budget": "budgeted",
    "proposed": "proposed gate",
}
COLORS = {
    "random": "#9aa0a6",
    "semantic": "#e8a33d",
    "frequency": "#8e7cc3",
    "logistic": "#4a86c5",
    "temperature": "#5aa469",
    "isotonic": "#c0392b",
    "fewshot": "#7f3c8d",
    "isotonic_budget": "#2c3e50",
    "proposed": "#111111",
}


def _mean(values):
    return sum(values) / len(values) if values else 0.0


def _fallback_success(row):
    return 1.0 if row["baseline_score"] >= SUCCESS_THRESHOLD.get(row["family"], 1.0) else 0.0


def curve(rows, target_risks=TARGET_RISKS, epsilon: float = EPSILON) -> dict:
    """Compute a risk-coverage curve by sweeping the gate threshold."""
    if not rows:
        return {"curve": [], "metrics": {}}
    scores = sorted({float(row["score_model"]) for row in rows})
    # Keep the curve small and stable while covering the full score range.
    if len(scores) > 100:
        indexes = {round(i * (len(scores) - 1) / 99) for i in range(100)}
        scores = [scores[i] for i in sorted(indexes)]
    thresholds = [max(scores) + 1e-9] + scores
    points = []
    for threshold in thresholds:
        committed = [row for row in rows if float(row["score_model"]) >= threshold]
        coverage = len(committed) / len(rows)
        if committed:
            risk = _mean([1.0 if row["utility"] < -epsilon else 0.0 for row in committed])
            success = _mean([float(row["success"]) for row in committed])
            utility = _mean([float(row["utility"]) for row in committed])
            attempts = _mean([float(row["attempts"]) for row in committed])
        else:
            risk = 0.0
            success = _mean([_fallback_success(row) for row in rows])
            utility = 0.0
            attempts = 0.0
        points.append({
            "threshold": threshold,
            "coverage": coverage,
            "risk": risk,
            "success": success,
            "utility": utility,
            "attempts": attempts,
        })
    points.sort(key=lambda point: (point["coverage"], point["risk"]))
    # Remove duplicate coverage values, keeping the lowest risk at each coverage.
    dedup = {}
    for point in points:
        key = round(point["coverage"], 6)
        if key not in dedup or point["risk"] < dedup[key]["risk"]:
            dedup[key] = point
    points = [dedup[key] for key in sorted(dedup)]

    metrics = {}
    for target in target_risks:
        feasible = [point for point in points if point["risk"] <= target + 1e-12]
        best = max(feasible, key=lambda point: point["coverage"]) if feasible else None
        metrics[f"coverage@{int(target * 100)}%"] = best["coverage"] if best else 0.0
        metrics[f"success@{int(target * 100)}%"] = best["success"] if best else 0.0
        metrics[f"utility@{int(target * 100)}%"] = best["utility"] if best else 0.0
    # Area under the risk-coverage curve, normalized to [0, 1].
    area = 0.0
    previous = (0.0, 0.0)
    for point in points:
        area += (point["coverage"] - previous[0]) * (point["risk"] + previous[1]) / 2.0
        previous = (point["coverage"], point["risk"])
    metrics["risk_auc"] = area
    metrics["coverage"] = points[-1]["coverage"] if points else 0.0
    metrics["risk"] = points[-1]["risk"] if points else 0.0
    return {"curve": points, "metrics": metrics}


def evaluate(results: dict) -> dict:
    """Evaluate all methods and gate variants in a results payload."""
    outputs = {}
    for name in ("random", "semantic", "frequency", "logistic", "temperature",
                 "isotonic", "fewshot", "isotonic_budget"):
        rows = [row for seed in results["seeds"] for row in seed["methods"][name]["tasks"]]
        outputs[name] = curve(rows)
    for name in ("none", "semantic", "outcome", "proposed"):
        rows = [row for seed in results["seeds"] for row in seed["selection"][name]["tasks"]]
        outputs["proposed" if name == "proposed" else f"gate_{name}"] = curve(rows)
    return outputs


def _svg(width, height, body):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="Helvetica, Arial, sans-serif">'
        f'<rect width="{width}" height="{height}" fill="white"/>{body}</svg>'
    )


def _plot(outputs: dict, path: Path) -> None:
    width, height = 860, 420
    x0, y0, plot_w, plot_h = 90, 50, 500, 300
    body = [
        f'<text x="{x0}" y="26" font-size="15" font-weight="bold">Risk-coverage of skill reuse</text>',
        f'<line x1="{x0}" y1="{y0 + plot_h}" x2="{x0 + plot_w}" y2="{y0 + plot_h}" stroke="#555"/>',
        f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y0 + plot_h}" stroke="#555"/>',
    ]
    y_max = 0.35
    for tick in (0.0, 0.1, 0.2, 0.3):
        y = y0 + plot_h - tick / y_max * plot_h
        body.append(f'<line x1="{x0}" y1="{y}" x2="{x0 + plot_w}" y2="{y}" stroke="#eee"/>')
        body.append(f'<text x="{x0 - 8}" y="{y + 4}" font-size="10" text-anchor="end" fill="#555">{tick:.1f}</text>')
    for tick in (0.0, 0.25, 0.5, 0.75, 1.0):
        x = x0 + tick * plot_w
        body.append(f'<text x="{x}" y="{y0 + plot_h + 18}" font-size="10" text-anchor="middle" fill="#555">{tick:.2f}</text>')
    body.append(f'<text x="{x0 + plot_w / 2}" y="{y0 + plot_h + 42}" font-size="12" text-anchor="middle">coverage</text>')
    body.append(
        f'<text x="{x0 - 50}" y="{y0 + plot_h / 2}" font-size="12" text-anchor="middle" '
        f'transform="rotate(-90 {x0 - 50} {y0 + plot_h / 2})">negative-transfer risk</text>'
    )
    for target in TARGET_RISKS:
        y = y0 + plot_h - target / y_max * plot_h
        body.append(f'<line x1="{x0}" y1="{y}" x2="{x0 + plot_w}" y2="{y}" stroke="#999" stroke-dasharray="4,4"/>')
    names = ["semantic", "logistic", "temperature", "isotonic", "proposed"]
    for index, name in enumerate(names):
        if name not in outputs:
            continue
        points = outputs[name]["curve"]
        if not points:
            continue
        color = COLORS.get(name, "#333")
        data = " ".join(
            f"{x0 + point['coverage'] * plot_w:.1f},{y0 + plot_h - min(y_max, point['risk']) / y_max * plot_h:.1f}"
            for point in points
        )
        body.append(f'<polyline points="{data}" fill="none" stroke="{color}" stroke-width="2"/>')
        legend_y = y0 + 12 + index * 20
        body.append(f'<line x1="{x0 + plot_w + 30}" y1="{legend_y - 4}" x2="{x0 + plot_w + 56}" y2="{legend_y - 4}" stroke="{color}" stroke-width="3"/>')
        body.append(f'<text x="{x0 + plot_w + 64}" y="{legend_y}" font-size="11">{escape(METHOD_LABELS.get(name, name))}</text>')
    path.write_text(_svg(width, height, "".join(body)), encoding="utf-8")


def _bars(outputs: dict, path: Path) -> None:
    names = [name for name in ("semantic", "logistic", "isotonic", "proposed") if name in outputs]
    width, height = 760, 360
    x0, y0, plot_w, plot_h = 80, 55, 500, 230
    body = [
        f'<text x="{x0}" y="28" font-size="15" font-weight="bold">Coverage at a fixed negative-transfer risk</text>',
        f'<line x1="{x0}" y1="{y0 + plot_h}" x2="{x0 + plot_w}" y2="{y0 + plot_h}" stroke="#555"/>',
        f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y0 + plot_h}" stroke="#555"/>',
    ]
    for tick in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = y0 + plot_h - tick * plot_h
        body.append(f'<line x1="{x0}" y1="{y}" x2="{x0 + plot_w}" y2="{y}" stroke="#eee"/>')
        body.append(f'<text x="{x0 - 8}" y="{y + 4}" font-size="10" text-anchor="end" fill="#555">{tick:.2f}</text>')
    risks = (5, 10, 20)
    colors = {5: "#c0392b", 10: "#4a86c5", 20: "#7f8c8d"}
    slot = plot_w / len(names)
    bar_w = slot / (len(risks) + 2)
    for index, name in enumerate(names):
        for risk_index, risk in enumerate(risks):
            value = outputs[name]["metrics"][f"coverage@{risk}%"]
            x = x0 + index * slot + (risk_index + 0.2) * bar_w
            y = y0 + plot_h - value * plot_h
            body.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{value * plot_h:.1f}" fill="{colors[risk]}"/>')
        body.append(f'<text x="{x0 + index * slot + slot / 2:.1f}" y="{y0 + plot_h + 18}" font-size="10" text-anchor="middle">{METHOD_LABELS.get(name, name)}</text>')
    for legend_index, risk in enumerate(risks):
        lx, ly = x0 + plot_w + 25, y0 + 15 + legend_index * 20
        body.append(f'<rect x="{lx}" y="{ly - 8}" width="12" height="12" fill="{colors[risk]}"/>')
        body.append(f'<text x="{lx + 18}" y="{ly + 2}" font-size="10">risk ≤ {risk}%</text>')
    path.write_text(_svg(width, height, "".join(body)), encoding="utf-8")


def write_outputs(results: dict, output: str | Path) -> dict:
    output = Path(output)
    (output / "tables").mkdir(parents=True, exist_ok=True)
    (output / "figures").mkdir(parents=True, exist_ok=True)
    outputs = evaluate(results)
    payload = {name: {"metrics": value["metrics"], "curve": value["curve"]}
               for name, value in outputs.items()}
    (output / "risk_coverage.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = ["method,target_risk,coverage,success,utility,risk_auc"]
    for name, value in outputs.items():
        for target in TARGET_RISKS:
            key = int(target * 100)
            lines.append(
                f"{name},{target:.2f},{value['metrics'][f'coverage@{key}%']:.4f},"
                f"{value['metrics'][f'success@{key}%']:.4f},"
                f"{value['metrics'][f'utility@{key}%']:.4f},"
                f"{value['metrics']['risk_auc']:.4f}"
            )
    (output / "tables" / "risk_coverage.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    _plot(outputs, output / "figures" / "risk_coverage.svg")
    _bars(outputs, output / "figures" / "risk_bars.svg")
    return outputs


def main(argv=None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Compute risk-coverage curves")
    parser.add_argument("--results", default="experiments/results.json")
    parser.add_argument("--output", default="experiments")
    args = parser.parse_args(argv)
    results = json.loads(Path(args.results).read_text(encoding="utf-8"))
    outputs = write_outputs(results, args.output)
    for name in ("semantic", "isotonic", "proposed"):
        if name in outputs:
            print(name, outputs[name]["metrics"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
