import enum

class RoleEnum(str, enum.Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    USER = "USER"

class TrackerStatusEnum(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    MAINTENANCE = "MAINTENANCE"

class ShipmentStatusEnum(str, enum.Enum):
    CREATED = "CREATED"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"

class AlertTypeEnum(str, enum.Enum):
    TEMPERATURE_BREACH = "TEMPERATURE_BREACH"
    DOOR_OPEN = "DOOR_OPEN"
    LOW_BATTERY = "LOW_BATTERY"
