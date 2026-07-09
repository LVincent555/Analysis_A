"""Identity value objects."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DeviceId:
    value: str = "default"

    def __post_init__(self) -> None:
        normalized = self.value or "default"
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class SessionPolicy:
    max_devices: int
    access_token_hours: int
    refresh_token_days: int

    def __post_init__(self) -> None:
        if self.max_devices < 1:
            raise ValueError("max_devices must be greater than or equal to 1")
        if self.access_token_hours < 1:
            raise ValueError("access_token_hours must be greater than or equal to 1")
        if self.refresh_token_days < 1:
            raise ValueError("refresh_token_days must be greater than or equal to 1")
