from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from re import Pattern, compile

KNOWN_PROVIDER_CODES = frozenset({"FAKE", "S3"})
UNKNOWN_PROVIDER_CODE = "UNKNOWN"
PROVIDER_CODE_PATTERN: Pattern[str] = compile(r"^[A-Z0-9_-]{1,32}$")


class MetricName(StrEnum):
    MEDIA_OPERATIONS_TOTAL = "media_operations_total"
    MEDIA_OPERATION_DURATION_MS = "media_operation_duration_ms"


class MetricStatus(StrEnum):
    SUCCESS = "SUCCESS"
    NOT_FOUND = "NOT_FOUND"
    INVALID = "INVALID"
    UNAVAILABLE = "UNAVAILABLE"


class MetricOperation(StrEnum):
    RESOLVE_PUBLIC_URL = "RESOLVE_PUBLIC_URL"
    RECONCILE = "RECONCILE"
    AUDIT_RECORD = "AUDIT_RECORD"


def normalize_provider_code(value: object) -> str:
    if isinstance(value, str):
        normalized = value.strip().upper()
        if normalized in KNOWN_PROVIDER_CODES and PROVIDER_CODE_PATTERN.fullmatch(normalized):
            return normalized
    return UNKNOWN_PROVIDER_CODE


@dataclass(frozen=True, slots=True)
class MetricLabels:
    status: MetricStatus
    operation: MetricOperation
    provider_code: str = UNKNOWN_PROVIDER_CODE

    def __post_init__(self) -> None:
        if not isinstance(self.status, MetricStatus):
            raise ValueError("metric status is not allowed")
        if not isinstance(self.operation, MetricOperation):
            raise ValueError("metric operation is not allowed")
        normalized = normalize_provider_code(self.provider_code)
        if normalized != self.provider_code:
            raise ValueError("metric provider code is not normalized")
        if len(self.provider_code) > 32 or any(
            character in self.provider_code for character in "\r\n\t ?/\\"
        ):
            raise ValueError("metric provider code is invalid")


@dataclass(frozen=True, slots=True)
class MetricSample:
    name: MetricName
    labels: MetricLabels
    count: int
    total: float
    minimum: float
    maximum: float


class MetricsRegistry:
    def __init__(self) -> None:
        self._samples: dict[
            tuple[MetricName, MetricStatus, MetricOperation, str], dict[str, float | int]
        ] = {}

    def record(
        self,
        *,
        name: MetricName,
        labels: MetricLabels,
        value: float = 1.0,
    ) -> None:
        if not isinstance(name, MetricName):
            raise ValueError("metric name is not allowed")
        if value < 0 or value != value or value == float("inf"):
            raise ValueError("metric value is invalid")
        key = (name, labels.status, labels.operation, labels.provider_code)
        sample = self._samples.setdefault(
            key,
            {"count": 0, "total": 0.0, "minimum": value, "maximum": value},
        )
        sample["count"] = int(sample["count"]) + 1
        sample["total"] = float(sample["total"]) + value
        sample["minimum"] = min(float(sample["minimum"]), value)
        sample["maximum"] = max(float(sample["maximum"]), value)

    def snapshot(self) -> tuple[MetricSample, ...]:
        samples = [
            MetricSample(
                name=key[0],
                labels=MetricLabels(status=key[1], operation=key[2], provider_code=key[3]),
                count=int(item["count"]),
                total=float(item["total"]),
                minimum=float(item["minimum"]),
                maximum=float(item["maximum"]),
            )
            for key, item in sorted(
                self._samples.items(),
                key=lambda entry: (
                    entry[0][0].value,
                    entry[0][1].value,
                    entry[0][2].value,
                    entry[0][3],
                ),
            )
        ]
        return tuple(samples)
