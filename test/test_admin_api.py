import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

import m_admin.m_admin_sm_user_access as user_access

from m_user.m_user_sm_roles import ADMIN, STUDENT


# Create FastAPI application
app = FastAPI()

app.include_router(user_access.router)

client = TestClient(app)


# ==========================================
# AUTHENTICATION OVERRIDE FOR TESTING
# ==========================================

def authenticate_as_admin():
    return ADMIN


def authenticate_as_student():
    return STUDENT


# ==========================================
# RESET TEST DATA BEFORE EACH TEST
# ==========================================

@pytest.fixture(autouse=True)
def reset_test_data():

    user_access.students.clear()
    user_access.next_user_id = 1

    app.dependency_overrides.clear()

    yield

    app.dependency_overrides.clear()


# ==========================================
# 1. TEST ADMIN OPERATIONS
# ==========================================

def test_admin_apis():

    app.dependency_overrides[
        user_access.get_current_role
    ] = authenticate_as_admin

    # Create student

    response = client.post(
        "/api/v1/admin/users/",
        json={
            "name": "Student One",
            "email": "student1@example.com"
        }
    )

    print("CREATE:", response.status_code, response.json())

    assert response.status_code == 200
    assert response.json()["student"]["name"] == "Student One"

    # View all students

    response = client.get(
        "/api/v1/admin/users/"
    )

    print("VIEW ALL:", response.status_code, response.json())

    assert response.status_code == 200
    assert len(response.json()["students"]) == 1

    # View one student

    response = client.get(
        "/api/v1/admin/users/1"
    )

    print("VIEW ONE:", response.status_code, response.json())

    assert response.status_code == 200
    assert response.json()["email"] == "student1@example.com"

    # Deactivate student

    response = client.patch(
        "/api/v1/admin/users/1/status",
        json={"status": "INACTIVE"}
    )

    print("DEACTIVATE:", response.status_code, response.json())

    assert response.status_code == 200
    assert response.json()["status"] == "INACTIVE"

    # Activate student

    response = client.patch(
        "/api/v1/admin/users/1/status",
        json={"status": "ACTIVE"}
    )

    print("ACTIVATE:", response.status_code, response.json())

    assert response.status_code == 200
    assert response.json()["status"] == "ACTIVE"

    # Delete student

    response = client.delete(
        "/api/v1/admin/users/1"
    )

    print("DELETE:", response.status_code, response.json())

    assert response.status_code == 200

    # Confirm student is deleted

    response = client.get(
        "/api/v1/admin/users/1"
    )

    assert response.status_code == 404


# ==========================================
# 2. TEST DUPLICATE STUDENT
# ==========================================

def test_duplicate_student():

    app.dependency_overrides[
        user_access.get_current_role
    ] = authenticate_as_admin

    student_data = {
        "name": "Student One",
        "email": "student1@example.com"
    }

    # Create first student

    response = client.post(
        "/api/v1/admin/users/",
        json=student_data
    )

    assert response.status_code == 200

    # Try creating the same student again

    response = client.post(
        "/api/v1/admin/users/",
        json=student_data
    )

    print("DUPLICATE:", response.status_code, response.json())

    assert response.status_code == 409


# ==========================================
# 3. TEST STUDENT CANNOT ACCESS ADMIN API
# ==========================================

def test_student_cannot_create_student():

    app.dependency_overrides[
        user_access.get_current_role
    ] = authenticate_as_student

    response = client.post(
        "/api/v1/admin/users/",
        json={
            "name": "Another Student",
            "email": "student2@example.com"
        }
    )

    print("STUDENT ACCESS:", response.status_code, response.json())

    assert response.status_code == 403


# ==========================================
# 4. TEST UNAUTHENTICATED ACCESS
# ==========================================

def test_unauthenticated_user_denied():

    # No authentication override

    response = client.get(
        "/api/v1/admin/users/"
    )

    print("UNAUTHENTICATED:", response.status_code, response.json())

    assert response.status_code == 401

def test_admin_can_view_analytics():

    app.dependency_overrides[user_access.get_current_role] = authenticate_as_admin

    response = client.get(
        "/api/v1/admin/users/analytics/summary"
    )

    assert response.status_code == 200

    data = response.json()

    assert "total_students" in data
    assert "active_students" in data
    assert "inactive_students" in data


def test_student_cannot_view_admin_analytics():

    app.dependency_overrides[user_access.get_current_role] = authenticate_as_student

    response = client.get(
        "/api/v1/admin/users/analytics/summary"
    )

    assert response.status_code == 403

def test_student_cannot_view_all_students():

    app.dependency_overrides[user_access.get_current_role] = authenticate_as_student

    response = client.get(
        "/api/v1/admin/users/"
    )

    assert response.status_code == 403


def test_student_cannot_update_student_status():

    app.dependency_overrides[user_access.get_current_role] = authenticate_as_student

    response = client.patch(
        "/api/v1/admin/users/1/status",
        json={"status": "INACTIVE"}
    )

    assert response.status_code == 403


def test_student_cannot_delete_student():

    app.dependency_overrides[user_access.get_current_role] = authenticate_as_student

    response = client.delete(
        "/api/v1/admin/users/1"
    )

    assert response.status_code == 403

def test_unknown_role_cannot_access_admin_api():
    app.dependency_overrides[user_access.get_current_role]=(
        lambda:"UNKNOWN"
    )
    response = client.get(
        "/api/v1/admin/users/"
    )
    assert response.status_code == 403

def test_missing_role_cannot_access_admin_api():
    app.dependency_overrides[user_access.get_current_role]=(
        lambda:""
    )
    response = client.get(
        "/api/v1/admin/users/"
    )
    assert response.status_code == 403