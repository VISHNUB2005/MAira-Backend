import pytest

from m_user.m_user_sm_roles import (
    ADMIN,
    STUDENT,
    has_permission,
    authorize_action,
    validate_role,
    validate_permission,
    get_permissions
)


# Test 1: Admin can create students
def test_admin_can_create_student():
    assert has_permission(ADMIN, "student:create") is True


# Test 2: Student cannot create students
def test_student_cannot_create_student():
    assert has_permission(STUDENT, "student:create") is False


# Test 3: Student can use AI
def test_student_can_use_ai():
    assert has_permission(STUDENT, "ai:use") is True


# Test 4: Admin cannot use student AI permissions
def test_admin_cannot_use_student_ai():
    assert has_permission(ADMIN, "ai:use") is False


# Test 5: Unknown role is denied
def test_unknown_role_is_denied():
    assert has_permission("UNKNOWN", "student:create") is False


# Test 6: Unauthorized action raises an error
def test_unauthorized_action():
    with pytest.raises(PermissionError):
        authorize_action(STUDENT, "student:create")


# Test 7: Invalid role is rejected
def test_invalid_role():
    with pytest.raises(ValueError):
        validate_role("UNKNOWN")


# Test 8: Invalid permission is rejected
def test_invalid_permission():
    with pytest.raises(ValueError):
        validate_permission("unknown:permission")


# Test 9: Get Admin permissions
def test_get_admin_permissions():
    permissions = get_permissions(ADMIN)

    assert "student:create" in permissions
    assert "student:view_basic" in permissions
    assert "student:activate" in permissions
    assert "student:deactivate" in permissions
    assert "student:delete" in permissions
    assert "student:analytics:view" in permissions


# Test 10: Get Student permissions
def test_get_student_permissions():
    permissions = get_permissions(STUDENT)

    assert "ai:use" in permissions
    assert "chat:create" in permissions
    