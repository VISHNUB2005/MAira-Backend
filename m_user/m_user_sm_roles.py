# Role definitions

ADMIN = "ADMIN"
STUDENT = "STUDENT"


# Permission definitions

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


# Role-Permission mapping

ROLE_PERMISSIONS = {

    ADMIN: {
        STUDENT_CREATE,
        STUDENT_ACTIVATE,
        STUDENT_DEACTIVATE,
        STUDENT_DELETE,
        STUDENT_VIEW_BASIC,
        STUDENT_ANALYTICS_VIEW
    },

    STUDENT: {
        PROFILE_VIEW_OWN,
        AI_USE,
        CHAT_CREATE,
        CHAT_VIEW_OWN,
        CHAT_DELETE_OWN
    }
}


# Check whether a role exists

def validate_role(role):

    if role not in ROLE_PERMISSIONS:
        raise ValueError("Invalid role")

    return True


# Check whether a permission exists

def validate_permission(permission):

    all_permissions = set()

    for permissions in ROLE_PERMISSIONS.values():
        all_permissions.update(permissions)

    if permission not in all_permissions:
        raise ValueError("Invalid permission")

    return True


# Check whether a role has a permission

def has_permission(role, permission):

    if role not in ROLE_PERMISSIONS:
        return False

    return permission in ROLE_PERMISSIONS[role]


# Authorize an action

def authorize_action(role, permission):

    validate_role(role)
    validate_permission(permission)

    if not has_permission(role, permission):
        raise PermissionError("Access denied")

    return True


# Get all permissions assigned to a role

def get_permissions(role):

    validate_role(role)

    return ROLE_PERMISSIONS[role].copy()

#test cases 2
try:
    authorize_action(ADMIN, "student:create")
    print("Admin access granted")

    authorize_action(STUDENT, "student:create")
    print("Student access granted")

except PermissionError as error:
    print(error)
#test cases 1
if __name__ == "__main__":

    print(has_permission(ADMIN, "student:create"))

    print(has_permission(STUDENT, "student:create"))

    print(has_permission(STUDENT, "ai:use"))

    print(has_permission("UNKNOWN", "student:create"))
#test cases 3
try:
    print(validate_role(ADMIN))
    print(validate_role(STUDENT))
    print(validate_role("UNKNOWN"))

except ValueError as error:
    print(error) 

#test cases 4
try:
    print(validate_permission("student:create"))
    print(validate_permission("student:promote"))

except ValueError as error:
    print(error)

#test cases 5 
print("Admin permissions:", get_permissions(ADMIN))
print("Student permissions:", get_permissions(STUDENT))