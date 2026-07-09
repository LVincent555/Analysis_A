"""Compatibility entrypoint for the Operations cached policy provider."""

from ..contexts.operations.infrastructure.policy_engine import CachedPolicyProvider as PolicyEngine

__all__ = ["PolicyEngine"]
