from __future__ import annotations

from enum import StrEnum


class ContactWorkflowStatus(StrEnum):
    RECEIVED = "RECEIVED"
    CONTACTED = "CONTACTED"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"


class ContactDeliveryStatus(StrEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class ContactSource(StrEnum):
    WEBSITE = "WEBSITE"


class ContactLocale(StrEnum):
    FR = "fr"
    EN = "en"


class ContactSubject(StrEnum):
    ETUDE_CLINIQUE = "Etude clinique"
    REPRESENTATION_LEGALE_UE = "Representation Legale UE"
    FORMATION = "Formation"
    PARTENARIAT = "Partenariat"
    AUTRE = "Autre"


class ContactDeliveryChannel(StrEnum):
    EMAIL = "EMAIL"


class ContactEmailProviderMode(StrEnum):
    MOCK = "mock"
    DISABLED = "disabled"
