from decimal import Decimal

from app.services.analysis.statistics import (
    Distribution,
    median,
    modified_zscore,
    percentile,
)
from app.services.analysis.unit_price import compute_unit_price


def test_compute_unit_price_valid():
    result = compute_unit_price(Decimal("175000"), Decimal("5000"), "Unidade")
    assert result.is_valid
    assert result.unit_price == Decimal("35.000000")


def test_compute_unit_price_rejects_zero_quantity():
    result = compute_unit_price(Decimal("100"), Decimal("0"), "Unidade")
    assert not result.is_valid
    assert result.unit_price is None
    assert any("quantidade" in issue for issue in result.issues)


def test_compute_unit_price_flags_missing_unit():
    result = compute_unit_price(Decimal("100"), Decimal("10"), None)
    assert result.unit_price == Decimal("10.000000")
    assert any("unidade" in issue for issue in result.issues)


def test_median_and_percentile():
    values = [1, 2, 3, 4, 5]
    assert median(values) == 3
    assert percentile(values, 25) == 2
    assert percentile(values, 75) == 4


def test_iqr_distribution_and_outlier_zscore():
    values = [10, 11, 12, 13, 14, 15, 100]
    dist = Distribution.from_values(values)
    assert dist.count == 7
    assert dist.median == 13
    assert dist.iqr is not None and dist.iqr > 0
    z = modified_zscore(100, values)
    assert z is not None and z > 3
