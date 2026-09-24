"""
Application-wide constants: roles, statuses, enums, and the color/design
system used throughout the UI.
"""

# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------
class Roles:
    ADMIN = "ADMIN"
    FARM_MANAGER = "FARM_MANAGER"
    VETERINARIAN = "VETERINARIAN"
    STAFF = "STAFF"

    ALL = [ADMIN, FARM_MANAGER, VETERINARIAN, STAFF]

    LABELS_VI = {
        ADMIN: "Quản trị viên",
        FARM_MANAGER: "Quản lý trang trại",
        VETERINARIAN: "Bác sĩ thú y",
        STAFF: "Nhân viên",
    }


# Menu keys used for permission checks. Each maps to a sidebar entry.
class MenuKeys:
    DASHBOARD = "dashboard"
    MONITORING = "monitoring"
    CAMERAS = "cameras"
    AI_DETECTION = "ai_monitoring"
    FLOCKS = "flocks"
    BARNS = "barns"
    PRODUCTION = "production"
    INVENTORY = "inventory"
    VETERINARY = "veterinary"
    VACCINATION = "vaccination"
    ALERTS = "alerts"
    HISTORY = "history"
    REPORTS = "reports"
    USERS = "users"
    SETTINGS = "settings"


# role -> set of menu keys that role can see
ROLE_MENU_PERMISSIONS = {
    Roles.ADMIN: {
        MenuKeys.DASHBOARD, MenuKeys.MONITORING, MenuKeys.CAMERAS, MenuKeys.AI_DETECTION,
        MenuKeys.FLOCKS, MenuKeys.BARNS, MenuKeys.PRODUCTION, MenuKeys.INVENTORY,
        MenuKeys.VETERINARY, MenuKeys.VACCINATION, MenuKeys.ALERTS, MenuKeys.HISTORY,
        MenuKeys.REPORTS, MenuKeys.USERS, MenuKeys.SETTINGS,
    },
    Roles.FARM_MANAGER: {
        MenuKeys.DASHBOARD, MenuKeys.MONITORING, MenuKeys.CAMERAS, MenuKeys.AI_DETECTION,
        MenuKeys.FLOCKS, MenuKeys.BARNS, MenuKeys.PRODUCTION, MenuKeys.INVENTORY,
        MenuKeys.ALERTS, MenuKeys.HISTORY, MenuKeys.REPORTS, MenuKeys.SETTINGS,
    },
    Roles.VETERINARIAN: {
        MenuKeys.DASHBOARD, MenuKeys.MONITORING, MenuKeys.AI_DETECTION, MenuKeys.FLOCKS,
        MenuKeys.VETERINARY, MenuKeys.VACCINATION, MenuKeys.ALERTS, MenuKeys.HISTORY, MenuKeys.REPORTS,
    },
    Roles.STAFF: {
        MenuKeys.DASHBOARD, MenuKeys.MONITORING, MenuKeys.FLOCKS, MenuKeys.BARNS,
        MenuKeys.INVENTORY, MenuKeys.ALERTS,
    },
}


# ---------------------------------------------------------------------------
# Statuses / enums (plain strings so SQLite stores them simply)
# ---------------------------------------------------------------------------
class UserStatus:
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class BarnStatus:
    ACTIVE = "ACTIVE"
    MAINTENANCE = "MAINTENANCE"
    INACTIVE = "INACTIVE"


class FlockStatus:
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class FlockEventType:
    IMPORT = "IMPORT"          # nhập đàn
    DEATH = "DEATH"            # chết
    CULL = "CULL"              # loại thải
    TRANSFER = "TRANSFER"      # chuyển chuồng
    ADDITION = "ADDITION"      # bổ sung

    LABELS_VI = {
        IMPORT: "Nhập đàn",
        DEATH: "Chết",
        CULL: "Loại thải",
        TRANSFER: "Chuyển chuồng",
        ADDITION: "Bổ sung",
    }


class InventoryTransactionType:
    IMPORT = "IMPORT"
    EXPORT = "EXPORT"
    ADJUSTMENT = "ADJUSTMENT"


class ItemStatus:
    ACTIVE = "ACTIVE"
    DISCONTINUED = "DISCONTINUED"


class VetRecordStatus:
    THEO_DOI = "THEO_DOI"
    DANG_DIEU_TRI = "DANG_DIEU_TRI"
    DA_KHOI = "DA_KHOI"
    CAN_TAI_KHAM = "CAN_TAI_KHAM"

    LABELS_VI = {
        THEO_DOI: "Theo dõi",
        DANG_DIEU_TRI: "Đang điều trị",
        DA_KHOI: "Đã khỏi",
        CAN_TAI_KHAM: "Cần tái khám",
    }


class VaccinationStatus:
    SCHEDULED = "SCHEDULED"
    COMPLETED = "COMPLETED"
    OVERDUE = "OVERDUE"

    LABELS_VI = {
        SCHEDULED: "Đã lên lịch",
        COMPLETED: "Hoàn thành",
        OVERDUE: "Quá hạn",
    }


class HealthStatus:
    NORMAL = "NORMAL"
    SUSPECTED = "SUSPECTED"


class AISessionStatus:
    PENDING = "PENDING"
    PLACEHOLDER_DONE = "PLACEHOLDER_DONE"
    FAILED = "FAILED"


class AlertSeverity:
    RED = "RED"
    ORANGE = "ORANGE"
    GREEN = "GREEN"

    LABELS_VI = {
        RED: "Đỏ",
        ORANGE: "Cam",
        GREEN: "Xanh",
    }


class AlertType:
    DISEASE_SUSPECTED = "DISEASE_SUSPECTED"
    STOCK_CRITICAL = "STOCK_CRITICAL"
    STOCK_LOW = "STOCK_LOW"
    ITEM_EXPIRING = "ITEM_EXPIRING"
    VACCINATION_OVERDUE = "VACCINATION_OVERDUE"
    VACCINATION_DUE_SOON = "VACCINATION_DUE_SOON"
    FLOCK_WATCH = "FLOCK_WATCH"
    IMPORT_SUCCESS = "IMPORT_SUCCESS"
    VIDEO_ANALYSIS_DONE = "VIDEO_ANALYSIS_DONE"
    VACCINATION_DONE = "VACCINATION_DONE"


class AlertStatus:
    UNREAD = "UNREAD"
    READ = "READ"
    DISMISSED = "DISMISSED"


DEFAULT_SPECIES = "Vịt trời"

DISEASE_SEED = [
    {
        "name": "Lật ngửa",
        "cause": "Virus",
        "behavior_signs": "Té ngã, khó hoặc không tự đứng dậy, nằm ngửa",
    },
    {
        "name": "Tụ huyết trùng",
        "cause": "Vi khuẩn",
        "behavior_signs": "Liệt chân, uống nước bất thường, tách đàn, đứng riêng lẻ",
    },
]

# ---------------------------------------------------------------------------
# Design system (colors) — Light theme spec
# ---------------------------------------------------------------------------
class Colors:
    """Design tokens — Duck AI Light Theme."""
    PRIMARY = "#2E7D32"               # Primary green
    PRIMARY_DARK = "#1B5E20"          # Dark green
    PRIMARY_LIGHT = "#E8F3E9"         # Light green
    ACCENT_YELLOW = "#F4A62D"         # Secondary yellow accent
    LIGHT_YELLOW = "#FFF4DD"          # Light yellow background
    DANGER = "#D32F2F"                # Danger red
    LIGHT_RED = "#FDECEC"             # Light red background
    BACKGROUND = "#F5F7F3"            # Main application background
    CARD_BG = "#FFFFFF"               # Card background
    BORDER = "#D8E2DA"                # Border color
    TEXT_PRIMARY = "#26332A"          # Main text
    TEXT_SECONDARY = "#68736B"        # Secondary text
    TEXT_DISABLED = "#9AA39D"         # Disabled text
    VIDEO_BG = "#101512"              # Video / camera preview area dark background

    # Aliases
    SURFACE = CARD_BG
    WARNING = ACCENT_YELLOW
    SUCCESS = PRIMARY
    INPUT_BORDER = "#D8DED9"
    TABLE_HEADER_BG = "#F1F4F1"
    TABLE_ROW_HOVER = "#F7FAF7"
    SIDEBAR_BG = "#FFFFFF"
    SIDEBAR_TEXT = "#26332A"
    SIDEBAR_ACTIVE_BG = "#E8F3E9"
    SIDEBAR_ACTIVE_TEXT = "#2E7D32"
    SIDEBAR_GROUP_LABEL = "#68736B"
    VIDEO_SURFACE = VIDEO_BG
