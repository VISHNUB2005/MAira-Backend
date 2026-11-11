from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr, Field
from typing import Literal

from m_user.m_user_sm_roles import (
    ADMIN,
    has_permission
)


router = APIRouter(
    prefix="/api/v1/admin/users",
    tags=["Admin User Access"]
)


# ==========================================
# 1. REQUEST MODELS
# ==========================================

# Admin creates an account using name and email.
# Admin cannot set the student's password.

class StudentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    email: EmailStr


class StudentStatus(BaseModel):
    status: Literal["ACTIVE", "INACTIVE"]


# ==========================================
# 2. TEMPORARY IN-MEMORY STORAGE
# ==========================================

# Temporary storage for testing.
# Later, replace this with PostgreSQL.

students = []

next_user_id = 1


# ==========================================
# 3. AUTHENTICATION PLACEHOLDER
# ==========================================

def get_current_role():
    """
    Temporary placeholder.

    Group 4 must provide the actual authentication
    dependency that returns the authenticated user's role.

    Until then, protected endpoints deny access.
    """

    raise HTTPException(
        status_code=401,
        detail="Authentication integration pending"
    )


# ==========================================
# 4. RBAC PERMISSION CHECK
# ==========================================

def check_permission(role: str, permission: str):

    if not has_permission(role, permission):
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )


# ==========================================
# 5. ADMIN ROLE CHECK
# ==========================================

def check_admin_permission(permission: str, role: str):

    if role != ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    check_permission(role, permission)


# ==========================================
# 6. CREATE STUDENT ACCOUNT
# ==========================================

@router.post("/")
def create_student(
    student: StudentCreate,
    role: str = Depends(get_current_role)
):

    global next_user_id

    check_admin_permission("student:create", role)

    # Check duplicate email

    for existing_student in students:

        if existing_student["email"] == str(student.email):

            raise HTTPException(
                status_code=409,
                detail="Student account already exists"
            )

    # Create student account

    new_student = {
        "user_id": next_user_id,
        "name": student.name,
        "email": str(student.email),
        "status": "ACTIVE",
        "password_set": False
    }

    students.append(new_student)

    next_user_id += 1

    return {
        "message": "Student account created successfully",
        "student": {
            "user_id": new_student["user_id"],
            "name": new_student["name"],
            "email": new_student["email"],
            "status": new_student["status"]
        },
        "password_setup_required": True
    }


# ==========================================
# 7. VIEW ALL STUDENTS
# ==========================================

@router.get("/")
def get_all_students(
    role: str = Depends(get_current_role)
):

    check_admin_permission("student:view_basic", role)

    return {
        "students": [
            {
                "user_id": student["user_id"],
                "name": student["name"],
                "email": student["email"],
                "status": student["status"]
            }
            for student in students
        ]
    }


# ==========================================
# 8. VIEW STUDENT ANALYTICS
# ==========================================

@router.get("/analytics/summary")
def get_student_analytics(
    role: str = Depends(get_current_role)
):

    check_admin_permission("student:analytics:view", role)

    total_students = len(students)

    active_students = sum(
        1 for student in students
        if student["status"] == "ACTIVE"
    )

    inactive_students = sum(
        1 for student in students
        if student["status"] == "INACTIVE"
    )

    return {
        "total_students": total_students,
        "active_students": active_students,
        "inactive_students": inactive_students
    }


# ==========================================
# 9. VIEW SINGLE STUDENT
# ==========================================

@router.get("/{user_id}")
def get_student(
    user_id: int,
    role: str = Depends(get_current_role)
):

    check_admin_permission("student:view_basic", role)

    for student in students:

        if student["user_id"] == user_id:

            return {
                "user_id": student["user_id"],
                "name": student["name"],
                "email": student["email"],
                "status": student["status"]
            }

    raise HTTPException(
        status_code=404,
        detail="Student not found"
    )


# ==========================================
# 10. ACTIVATE / DEACTIVATE STUDENT
# ==========================================

@router.patch("/{user_id}/status")
def update_student_status(
    user_id: int,
    data: StudentStatus,
    role: str = Depends(get_current_role)
):

    if data.status == "ACTIVE":

        check_admin_permission("student:activate", role)

    else:

        check_admin_permission("student:deactivate", role)

    for student in students:

        if student["user_id"] == user_id:

            student["status"] = data.status

            return {
                "message": "Student status updated successfully",
                "user_id": user_id,
                "status": data.status
            }

    raise HTTPException(
        status_code=404,
        detail="Student not found"
    )


# ==========================================
# 11. DELETE STUDENT
# ==========================================

@router.delete("/{user_id}")
def delete_student(
    user_id: int,
    role: str = Depends(get_current_role)
):

    check_admin_permission("student:delete", role)

    for index, student in enumerate(students):

        if student["user_id"] == user_id:

            deleted_student = students.pop(index)

            return {
                "message": "Student deleted successfully",
                "student": {
                    "user_id": deleted_student["user_id"],
                    "name": deleted_student["name"],
                    "email": deleted_student["email"]
                }
            }

    raise HTTPException(
        status_code=404,
        detail="Student not found"
    )