from enum import Enum

class RoleEnum(str, Enum):
    ADMIN = "admin"
    DOCENTE = "docente"
    ESTUDIANTE = "estudiante"

class StatusEnum(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"

class GradeStatusEnum(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    FINAL = "final"
    LOCKED = "locked"