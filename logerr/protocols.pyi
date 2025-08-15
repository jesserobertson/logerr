"""Type stubs for logerr.protocols module."""

from typing import Protocol, runtime_checkable

@runtime_checkable
class SupportsDunderLT(Protocol):
    """Protocol for types that support less-than comparison."""

    def __lt__(self, other: object) -> bool: ...

@runtime_checkable
class SupportsDunderLE(Protocol):
    """Protocol for types that support less-than-or-equal comparison."""

    def __le__(self, other: object) -> bool: ...

@runtime_checkable
class SupportsDunderGT(Protocol):
    """Protocol for types that support greater-than comparison."""

    def __gt__(self, other: object) -> bool: ...

@runtime_checkable
class SupportsDunderGE(Protocol):
    """Protocol for types that support greater-than-or-equal comparison."""

    def __ge__(self, other: object) -> bool: ...

@runtime_checkable
class SupportsDunderEQ(Protocol):
    """Protocol for types that support equality comparison."""

    def __eq__(self, other: object) -> bool: ...

@runtime_checkable
class SupportsDunderNE(Protocol):
    """Protocol for types that support not-equal comparison."""

    def __ne__(self, other: object) -> bool: ...

@runtime_checkable
class SupportsComparison(
    SupportsDunderLT, SupportsDunderLE, SupportsDunderGT, SupportsDunderGE, Protocol
):
    """Protocol for types that support all comparison operations."""

    pass

@runtime_checkable
class SupportsEquality(SupportsDunderEQ, SupportsDunderNE, Protocol):
    """Protocol for types that support equality operations."""

    pass
