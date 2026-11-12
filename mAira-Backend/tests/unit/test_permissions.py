"""Unit tests for RBAC permissions matrix."""

import pytest
from app.security.permissions import (
    ADMIN,
    AI_USE,
    CHAT_CREATE,
    CHAT_DELETE_OWN,
    CHAT_VIEW_OWN,
    FACULTY,
    PROFILE_VIEW_OWN,
    STUDENT,
    STUDENT_ACTIVATE,
    STUDENT_ANALYTICS_VIEW,
    STUDENT_CREATE,
    STUDENT_DEACTIVATE,
    STUDENT_DELETE,
    STUDENT_VIEW_BASIC,
    get_role_permissions,
    has_permission,
    validate_role,
)


def test_admin_permissions():
    assert has_permission(ADMIN, STUDENT_CREATE) is True
    assert has_permission(ADMIN, STUDENT_VIEW_BASIC) is True
    assert has_permission(ADMIN, STUDENT_ANALYTICS_VIEW) is True
    assert has_permission(ADMIN, STUDENT_ACTIVATE) is True
    assert has_permission(ADMIN, STUDENT_DEACTIVATE) is True
    assert has_permission(ADMIN, STUDENT_DELETE) is True

    # Admin cannot use AI or access chats directly per Group 6 specs
    assert has_permission(ADMIN, AI_USE) is False
    assert has_permission(ADMIN, CHAT_CREATE) is False


def test_student_permissions():
    assert has_permission(STUDENT, AI_USE) is True
    assert has_permission(STUDENT, CHAT_CREATE) is True
    assert has_permission(STUDENT, CHAT_VIEW_OWN) is True
    assert has_permission(STUDENT, CHAT_DELETE_OWN) is True
    assert has_permission(STUDENT, PROFILE_VIEW_OWN) is True

    # Student cannot perform admin operations
    assert has_permission(STUDENT, STUDENT_CREATE) is False
    assert has_permission(STUDENT, STUDENT_DELETE) is False
    assert has_permission(STUDENT, STUDENT_ANALYTICS_VIEW) is False


def test_validate_role():
    assert validate_role(ADMIN) is True
    assert validate_role(STUDENT) is True
    assert validate_role(FACULTY) is True

    with pytest.raises(ValueError, match="Invalid role"):
        validate_role("SUPERUSER")

    with pytest.raises(ValueError, match="Invalid role"):
        validate_role("ANONYMOUS")


def test_get_role_permissions_immutability():
    perms = get_role_permissions(ADMIN)
    perms.add("fake:perm")
    assert has_permission(ADMIN, "fake:perm") is False
