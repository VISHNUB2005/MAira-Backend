RBAC Security Assumptions
1. Purpose
The purpose of RBAC is to ensure that users can access only the features and resources permitted by their assigned roles.
2. Supported roles
Phase 1 supports two roles:
- ADMIN
- STUDENT
3. Role-based access rules
Rule	Description
Admin access	Admin can create, view basic details, activate, deactivate and delete student accounts.
Student access	Students can use AI, manage their own chats and view their own profiles.
Admin restrictions	Admin cannot access student conversations or AI features.
Student restrictions	Students cannot access Admin functionalities.


4. Authorization assumptions
1. Every protected API must perform an authorization check.
2. Unknown roles must be denied.
3. Unknown permissions must be denied.
4. Missing permissions must result in access denial.
5. Users cannot assign themselves Admin privileges.
6. Users cannot access another user's private resources.
7. Authorization decisions must use trusted authenticated identity information.
5. Security implementation
The current implementation uses:
- Hardcoded role-permission mapping.
- Reusable permission-checking functions.
- FastAPI dependencies for protected endpoints.
- HTTP 401 for authentication failures.
- HTTP 403 for authorization failures.
6. Current limitations
Area	Current status
Authentication	Group 4 integration pending
Database	Temporary in-memory storage
Permission storage	Hardcoded in Python
Audit logging	Group 8 integration pending
Object-level authorization	Pending integration with relevant APIs
Admin account deletion	Prototype uses physical deletion; final policy pending


7. Future integration
The RBAC implementation will be integrated with:
- Group 4 authentication and session management.
- Group 5 database implementation.
- Group 8 security and audit logging.
- Group 9 API inventory and integration testing.