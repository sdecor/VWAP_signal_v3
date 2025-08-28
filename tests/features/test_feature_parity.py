# tests/features/test_feature_parity.py
import pandas as pd

from signals.features.feature_schema import (
    select_required_features,
    build_feature_frame,
    build_feature_vector_for_row,
    validate_feature_values,
    check_feature_parity,
)
from signals.features.feature_adapter import get_feature_vector_for_prediction


def test_select_required_features_prefers_schedule():
    cfg = {"model": {"features": ["a", "b", "c"]}}
    cfg_now = {"features": ["x", "y"]}
    feats = select_required_features(cfg, cfg_now)
    assert feats == ["x", "y"]


def test_select_required_features_fallback_model():
    cfg = {"model": {"features": ["a", "b", "c"]}}
    feats = select_required_features(cfg, None)
    assert feats == ["a", "b", "c"]


def test_build_feature_frame_order_and_fill_missing():
    df = pd.DataFrame({
        "normalized_dist_to_vwap": [2.1, 1.7],
        "hour": [10, 11],
    })
    wanted = ["normalized_dist_to_vwap", "minute", "hour"]
    X = build_feature_frame(df, wanted)
    assert list(X.columns) == wanted
    # "minute" manquant -> rempli
    assert "minute" in X.columns
    assert float(X.iloc[0]["minute"]) == 0.0


def test_build_feature_vector_for_row_single_row_and_order():
    df = pd.DataFrame({
        "a": [1.1, 2.2],
        "b": [3.3, 4.4],
        "c": [5.5, 6.6],
    })
    wanted = ["b", "a"]
    x0 = build_feature_vector_for_row(df, 0, wanted)
    assert list(x0.columns) == ["b", "a"]
    assert x0.shape == (1, 2)
    assert float(x0.iloc[0]["b"]) == 3.3
    assert float(x0.iloc[0]["a"]) == 1.1


def test_validate_feature_values_flags_nan_and_ranges():
    df = pd.DataFrame({
        "normalized_dist_to_vwap": [float("nan")],
        "hour": [25],
        "minute": [-1],
    })
    feats = ["normalized_dist_to_vwap", "hour", "minute"]
    errs = validate_feature_values(df.iloc[0], feats)
    assert any(e.startswith("nan_or_inf:normalized_dist_to_vwap") for e in errs)
    assert "range:hour" in errs
    assert "range:minute" in errs


def test_check_feature_parity_non_empty_ok():
    df = pd.DataFrame({
        "normalized_dist_to_vwap": [2.0],
        "hour": [10],
        "minute": [30],
    })
    feats = ["normalized_dist_to_vwap", "hour", "minute"]
    X, errs = check_feature_parity(df, feats)
    assert list(X.columns) == feats
    assert errs == []


def test_feature_adapter_returns_vector_and_errors():
    cfg = {"model": {"features": ["x", "y"]}}
    df = pd.DataFrame({"x": [1.0, 2.0]})  # "y" manquant -> sera 0.0
    X, feats, errs = get_feature_vector_for_prediction(enriched_df=df, cfg=cfg, cfg_now=None)
    assert feats == ["x", "y"]
    assert list(X.columns) == ["x", "y"]
    assert float(X.iloc[0]["y"]) == 0.0
    assert errs == []
