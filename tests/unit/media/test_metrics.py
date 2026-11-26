from __future__ import annotations

import pytest

from fps_platform.observability.metrics import (
    UNKNOWN_PROVIDER_CODE,
    MetricLabels,
    MetricName,
    MetricOperation,
    MetricsRegistry,
    MetricStatus,
    normalize_provider_code,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("fake", "FAKE"),
        (" S3 ", "S3"),
        ("s3", "S3"),
        (None, UNKNOWN_PROVIDER_CODE),
        ("https://storage.test/bucket?sig=deadbeef", UNKNOWN_PROVIDER_CODE),
        ("s3:" + "x" * 100, UNKNOWN_PROVIDER_CODE),
    ],
)
def test_provider_code_is_normalized(raw: object, expected: str) -> None:
    assert normalize_provider_code(raw) == expected


def test_metrics_record_counter_and_duration_with_bounded_labels() -> None:
    registry = MetricsRegistry()
    labels = MetricLabels(
        status=MetricStatus.SUCCESS,
        operation=MetricOperation.RESOLVE_PUBLIC_URL,
        provider_code="FAKE",
    )

    registry.record(name=MetricName.MEDIA_OPERATIONS_TOTAL, labels=labels)
    registry.record(
        name=MetricName.MEDIA_OPERATION_DURATION_MS,
        labels=labels,
        value=12.5,
    )
    registry.record(
        name=MetricName.MEDIA_OPERATION_DURATION_MS,
        labels=labels,
        value=7.5,
    )

    samples = registry.snapshot()
    assert len(samples) == 2
    by_name = {sample.name: sample for sample in samples}
    total = by_name[MetricName.MEDIA_OPERATIONS_TOTAL]
    duration = by_name[MetricName.MEDIA_OPERATION_DURATION_MS]
    assert total.name is MetricName.MEDIA_OPERATIONS_TOTAL
    assert total.count == 1
    assert duration.name is MetricName.MEDIA_OPERATION_DURATION_MS
    assert duration.count == 2
    assert duration.total == 20.0
    assert duration.minimum == 7.5
    assert duration.maximum == 12.5


def test_metrics_snapshot_contains_no_free_form_material() -> None:
    registry = MetricsRegistry()
    labels = MetricLabels(
        status=MetricStatus.UNAVAILABLE,
        operation=MetricOperation.RECONCILE,
        provider_code=normalize_provider_code("https://bucket.test?X-Amz-Signature=deadbeef"),
    )
    registry.record(name=MetricName.MEDIA_OPERATIONS_TOTAL, labels=labels)

    serialized = str(registry.snapshot()).lower()
    for token in ("https", "bucket", "deadbeef", "signature", "storage_key", "credential"):
        assert token not in serialized


@pytest.mark.parametrize("status", list(MetricStatus))
@pytest.mark.parametrize("operation", list(MetricOperation))
def test_all_declared_labels_are_valid(status: MetricStatus, operation: MetricOperation) -> None:
    labels = MetricLabels(status=status, operation=operation)

    assert labels.provider_code == UNKNOWN_PROVIDER_CODE


def test_invalid_labels_are_refused() -> None:
    with pytest.raises(ValueError):
        MetricLabels(status="SUCCESS", operation=MetricOperation.RECONCILE)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        MetricLabels(
            status=MetricStatus.SUCCESS,
            operation=MetricOperation.RECONCILE,
            provider_code="https://bucket.test",
        )


def test_invalid_metric_value_is_refused() -> None:
    registry = MetricsRegistry()
    labels = MetricLabels(status=MetricStatus.SUCCESS, operation=MetricOperation.AUDIT_RECORD)

    with pytest.raises(ValueError):
        registry.record(name=MetricName.MEDIA_OPERATIONS_TOTAL, labels=labels, value=float("nan"))
    with pytest.raises(ValueError):
        registry.record(name=MetricName.MEDIA_OPERATIONS_TOTAL, labels=labels, value=-1)
