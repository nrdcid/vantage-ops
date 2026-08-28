"""Dependency-light baseline delay model for the Phase 2 starting point."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


NUMERIC_FEATURES = ["scheduled_hour", "day_of_week", "distance", "weather_tmpf", "weather_dwpf", "weather_relh", "weather_drct", "weather_sknt", "weather_vsby", "weather_gust"]
CATEGORICAL_FEATURES = ["origin", "destination", "OP_UNIQUE_CARRIER"]


@dataclass
class BaselineModel:
    feature_names: list[str]
    means: np.ndarray
    scales: np.ndarray
    weights: np.ndarray

    def predict_proba(self, features: pd.DataFrame) -> np.ndarray:
        matrix = features.reindex(columns=self.feature_names, fill_value=0).astype(float).to_numpy()
        standardized = (matrix - self.means) / self.scales
        logits = np.clip(np.c_[np.ones(len(matrix)), standardized] @ self.weights, -35, 35)
        return 1 / (1 + np.exp(-logits))


def make_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Create operational and weather features without using delay outcomes."""
    required = {"scheduled_departure", "origin", "destination", "OP_UNIQUE_CARRIER", "DISTANCE", "delayed"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Processed dataset is missing required model columns: {', '.join(missing)}")
    result = frame.copy()
    departure = pd.to_datetime(result["scheduled_departure"], errors="coerce")
    result["scheduled_hour"] = departure.dt.hour + departure.dt.minute / 60
    result["day_of_week"] = departure.dt.dayofweek
    result["distance"] = result["DISTANCE"]
    for column in NUMERIC_FEATURES:
        if column not in result:
            result[column] = np.nan
        result[column] = pd.to_numeric(result[column], errors="coerce")
    result["weather_missing"] = result["weather_time"].isna().astype(float) if "weather_time" in result else 1.0
    numeric = result[NUMERIC_FEATURES + ["weather_missing"]].copy()
    numeric = numeric.fillna(numeric.median(numeric_only=True)).fillna(0)
    categorical = pd.get_dummies(result[CATEGORICAL_FEATURES].fillna("UNKNOWN").astype(str), dtype=float)
    return pd.concat([numeric, categorical], axis=1)


def _fit(features: pd.DataFrame, labels: pd.Series) -> BaselineModel:
    matrix = features.astype(float).to_numpy()
    means, scales = matrix.mean(axis=0), matrix.std(axis=0)
    scales[scales < 1e-9] = 1
    design = np.c_[np.ones(len(matrix)), (matrix - means) / scales]
    weights = np.zeros(design.shape[1])
    y = labels.astype(float).to_numpy()
    for _ in range(1500):
        probability = 1 / (1 + np.exp(-np.clip(design @ weights, -35, 35)))
        weights -= 0.08 * (design.T @ (probability - y)) / len(y)
    return BaselineModel(list(features.columns), means, scales, weights)


def _metrics(labels: pd.Series, probabilities: np.ndarray) -> dict[str, float]:
    actual = labels.astype(int).to_numpy()
    predicted = (probabilities >= 0.5).astype(int)
    tp = int(((predicted == 1) & (actual == 1)).sum())
    fp = int(((predicted == 1) & (actual == 0)).sum())
    fn = int(((predicted == 0) & (actual == 1)).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / int(actual.sum()) if actual.sum() else 0.0
    return {"rows": float(len(actual)), "positive_rate": float(actual.mean()), "accuracy": float((predicted == actual).mean()), "precision": precision, "recall": recall, "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0}


def train_baseline(path: Path) -> dict[str, object]:
    frame = pd.read_csv(path, low_memory=False)
    frame["flight_date"] = pd.to_datetime(frame["flight_date"], errors="coerce")
    dates = sorted(frame["flight_date"].dt.date.dropna().unique())
    if len(dates) < 3:
        raise ValueError("At least three distinct flight dates are required for a temporal split")
    train_end = dates[max(0, int(len(dates) * 0.7) - 1)]
    validation_end = dates[max(1, int(len(dates) * 0.85) - 1)]
    train = frame[frame["flight_date"].dt.date <= train_end]
    validation = frame[(frame["flight_date"].dt.date > train_end) & (frame["flight_date"].dt.date <= validation_end)]
    test = frame[frame["flight_date"].dt.date > validation_end]
    model = _fit(make_features(train), train["delayed"])
    metrics = {}
    for name, split in (("train", train), ("validation", validation), ("test", test)):
        metrics[name] = _metrics(split["delayed"], model.predict_proba(make_features(split)))
    return {"split": {"train_end": str(train_end), "validation_end": str(validation_end), "test_end": str(dates[-1])}, "features": model.feature_names, "metrics": metrics}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train the temporal baseline")
    parser.add_argument("--input", type=Path, default=Path("data/processed/flights_weather.csv"))
    parser.add_argument("--metrics", type=Path, default=Path("data/processed/baseline_metrics.json"))
    args = parser.parse_args(argv)
    result = train_baseline(args.input)
    args.metrics.parent.mkdir(parents=True, exist_ok=True)
    args.metrics.write_text(json.dumps(result, indent=2) + "\n")
    for split, values in result["metrics"].items():
        print(f"{split}: precision={values['precision']:.3f} recall={values['recall']:.3f} f1={values['f1']:.3f}")
    print(f"Wrote metrics to {args.metrics}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
