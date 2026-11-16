"""Role-Based Access Control (RBAC) and Permissions Matrix."""

from typing import Dict, Set

# Role Constants
ADMIN = "ADMIN"
STUDENT = "STUDENT"
FACULTY = "FACULTY"

VALID_ROLES = {ADMIN, STUDENT, FACULTY}

# Permission Constants
STUDENT_CREATE = "student:create"
STUDENT_ACTIVATE = "student:activate"
STUDENT_DEACTIVATE = "student:deactivate"
STUDENT_DELETE = "student:delete"
STUDENT_VIEW_BASIC = "student:view_basic"
STUDENT_ANALYTICS_VIEW = "student:analytics:view"

PROFILE_VIEW_OWN = "profile:view_own"
AI_USE = "ai:use"
CHAT_CREATE = "chat:create"
CHAT_VIEW_OWN = "chat:view_own"
CHAT_DELETE_OWN = "chat:delete_own"

# Role -> Permissions Mapping
ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    ADMIN: {
        STUDENT_CREATE,
        STUDENT_ACTIVATE,
        STUDENT_DEACTIVATE,
        STUDENT_DELETE,
        STUDENT_VIEW_BASIC,
        STUDENT_ANALYTICS_VIEW,
    },
    STUDENT: {
        PROFILE_VIEW_OWN,
        AI_USE,
        CHAT_CREATE,
        CHAT_VIEW_OWN,
        CHAT_DELETE_OWN,
    },
    FACULTY: {
        PROFILE_VIEW_OWN,
        AI_USE,
        CHAT_CREATE,
        CHAT_VIEW_OWN,
        CHAT_DELETE_OWN,
    },
}


def validate_role(role: str) -> bool:
    """Check whether a role exists."""
    if not role or role.upper() not in ROLE_PERMISSIONS:
        raise ValueError(f"Invalid role: '{role}'")
    return True


def has_permission(role: str, permission: str) -> bool:
    """Check if a role possesses the specified permission."""
    if not role or not permission:
        return False
    perms = ROLE_PERMISSIONS.get(role.upper(), set())
    return permission in perms


def get_role_permissions(role: str) -> Set[str]:
    """Retrieve all permissions assigned to a role."""
    validate_role(role)
    return ROLE_PERMISSIONS[role.upper()].copy()
