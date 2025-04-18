from flask import session

class PermissionTypes:
    TAB_USERS = 1
    TAB_USERS_RIGHTS = 2
    USERS_EDIT = 3
    USERS_CREATE = 4
    TAB_RECOGNITIONS = 6
    RECOGNITIONS_EXPORT = 7
    TAB_PROFILE = 8

    MAP = {
        TAB_USERS: "TAB_USERS",
        TAB_USERS_RIGHTS: "TAB_USERS_RIGHTS",
        USERS_EDIT: "USERS_EDIT",
        USERS_CREATE: "USERS_CREATE",
        TAB_RECOGNITIONS: "TAB_RECOGNITIONS",
        RECOGNITIONS_EXPORT: "RECOGNITIONS_EXPORT",
        TAB_PROFILE: "TAB_PROFILE",
    }

    MAP_LABELS = {
        TAB_USERS: "Користувачі",
        TAB_USERS_RIGHTS: "Права доступу",
        USERS_EDIT: "Редагування користувачів",
        USERS_CREATE: "Створення користувачів",
        TAB_RECOGNITIONS: "Розпізнавання",
        RECOGNITIONS_EXPORT: "Експорт розпізнавань",
        TAB_PROFILE: "Профіль",
    }

    @classmethod
    def name(cls, permission_id):
        return cls.MAP.get(permission_id)

    @classmethod
    def all_ids(cls):
        return list(cls.MAP.keys())

    @classmethod
    def has_permission(cls, permission_id):
        from flask import g
        user = session.get("user")
        if not user:
            return False

        permissions = user.get("rights", {}).get("permissions", [])
        return permission_id in permissions

