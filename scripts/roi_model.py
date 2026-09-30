#!/usr/bin/env python3
"""Illustrative, undiscounted project cash-flow sensitivity; Python standard library only.

No default is a vendor quote, observed saving, or industry average.
Material and utility bases must be disjoint to avoid double counting.
Run: python3 scripts/roi_model.py [--config path/to/assumptions.json]
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def number(data: dict[str, Any], key: str, *, rate: bool = False,
           positive: bool = False) -> float:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key}: expected a finite number")
    value = float(value)
    if not math.isfinite(value) or value < 0 or (positive and value == 0):
        raise ValueError(f"{key}: invalid nonnegative/positive value")
    if rate and value > 1:
        raise ValueError(f"{key}: use a fraction between 0 and 1, not a percent")
    return value


def calculate(config: dict[str, Any]) -> dict[str, Any]:
    capex = number(config, "installed_capex", positive=True)
    opex = number(config, "annual_opex")
    material = number(config, "addressable_material_cost_per_year", positive=True)
    utilities = number(config, "metered_utilities_cost_per_year")
    target = number(config, "target_payback_years", positive=True)
    currency = config.get("currency")
    if not isinstance(currency, str) or not currency.strip():
        raise ValueError("currency: expected a nonempty string")
    scenarios = config.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("scenarios: expected a nonempty list")
    rows = []
    for scenario in scenarios:
        if not isinstance(scenario, dict) or not isinstance(scenario.get("name"), str):
            raise ValueError("each scenario needs a string name")
        r = number(scenario, "material_savings_rate", rate=True)
        u = number(scenario, "utilities_savings_rate", rate=True)
        material_saved = material * r
        utilities_saved = utilities * u
        gross = material_saved + utilities_saved
        net = gross - opex
        # Threshold is conditional on this scenario's assumed utility saving.
        needed = max(0.0, (capex / target + opex - utilities_saved) / material)
        rows.append({
            "scenario": scenario["name"],
            "material_savings_per_year": round(material_saved, 2),
            "utilities_savings_per_year": round(utilities_saved, 2),
            "gross_savings_per_year": round(gross, 2),
            "net_cash_benefit_per_year": round(net, 2),
            "simple_payback_years": round(capex / net, 6) if net > 0 else None,
            "payback_status": "finite_under_assumptions" if net > 0 else "no_positive_annual_net_benefit",
            "required_material_savings_rate_for_target_payback": round(needed, 8),
            "threshold_exceeds_material_base": needed > 1,
        })
    return {
        "warning": "Illustrative assumptions only; no verified return or quoted installed cost.",
        "currency": currency,
        "target_payback_years": target,
        "excludes": ["tax", "discounting", "ramp-up", "financing", "replacement capex", "residual value"],
        "results": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path,
                        default=Path(__file__).resolve().parents[1] / "data" / "roi-assumptions.example.json")
    args = parser.parse_args()
    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        if not isinstance(config, dict):
            raise ValueError("top-level JSON must be an object")
        print(json.dumps(calculate(config), ensure_ascii=False, indent=2, allow_nan=False))
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(2, f"Invalid configuration: {exc}\n")


if __name__ == "__main__":
    main()
