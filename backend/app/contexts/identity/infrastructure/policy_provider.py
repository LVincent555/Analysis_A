"""Policy provider adapter for Operations policies."""

from ...operations.infrastructure.policy_engine import CachedPolicyProvider


class OperationsSessionPolicyProvider:
    def get_login_policy(self) -> dict:
        return CachedPolicyProvider.get_login_policy()

    def get_session_policy(self, user) -> dict:
        return CachedPolicyProvider.get_session_policy(user)


session_policy_provider = OperationsSessionPolicyProvider()
