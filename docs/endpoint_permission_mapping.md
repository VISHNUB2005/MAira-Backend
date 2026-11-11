Admin endpoints
No.	HTTP Method	Endpoint	Permission	Role
1	POST	/api/v1/admin/users/	student:create	ADMIN
2	GET	/api/v1/admin/users/	student:view_basic	ADMIN
3	GET	/api/v1/admin/users/analytics/summary	student:analytics:view	ADMIN
4	GET	/api/v1/admin/users/{user_id}	student:view_basic	ADMIN
5	PATCH	/api/v1/admin/users/{user_id}/status	student:activate or student:deactivate	ADMIN
6	DELETE	/api/v1/admin/users/{user_id}	student:delete	ADMIN