"""Admin user query-side use cases for the Identity context."""

from ....shared.errors import AppError, ErrorCode
from ....shared.time import utc_now_naive
from .ports import IdentityUserQueryRepository
from .queries import GetAdminUserDetailQuery, ListAdminUsersQuery


def _not_found(message: str) -> AppError:
    return AppError(ErrorCode.NOT_FOUND, message)


class ListAdminUsersUseCase:
    def __init__(self, *, users: IdentityUserQueryRepository) -> None:
        self.users = users

    def execute(self, query: ListAdminUsersQuery) -> dict:
        total, rows, session_counts = self.users.list_users(
            page=query.page,
            page_size=query.page_size,
            search=query.search,
            role=query.role,
            status=query.status,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
            include_deleted=query.include_deleted,
            now=utc_now_naive(),
        )
        items = []
        for user in rows:
            item = user.to_dict_simple()
            item["active_sessions"] = session_counts.get(user.id, 0)
            items.append(item)

        return {
            "total": total,
            "page": query.page,
            "page_size": query.page_size,
            "items": items,
        }


class GetAdminUserDetailUseCase:
    def __init__(self, *, users: IdentityUserQueryRepository) -> None:
        self.users = users

    def execute(self, query: GetAdminUserDetailQuery) -> dict:
        user = self.users.get_user_by_id(query.user_id)
        if not user:
            raise _not_found("用户不存在")

        result = user.to_dict(include_sessions=True)
        sessions = self.users.list_unrevoked_sessions_for_user(query.user_id)
        result["sessions"] = [session.to_dict() for session in sessions]
        return result
