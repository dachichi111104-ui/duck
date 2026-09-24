"""
Import every model module so they register themselves on Base.metadata.
This module is imported once by app.database.connection.init_database().
"""
from app.database.models.users import User, Role
from app.database.models.barns import Barn
from app.database.models.flocks import Flock, FlockEvent, ProductionRecord
from app.database.models.inventory import InventoryCategory, InventoryItem, InventoryTransaction
from app.database.models.veterinary import Disease, VeterinaryRecord, Vaccination
from app.database.models.ai import AIAnalysisSession, AIDetectionResult, AIAlert
from app.database.models.alerts import Notification

__all__ = [
    "User", "Role",
    "Barn",
    "Flock", "FlockEvent", "ProductionRecord",
    "InventoryCategory", "InventoryItem", "InventoryTransaction",
    "Disease", "VeterinaryRecord", "Vaccination",
    "AIAnalysisSession", "AIDetectionResult", "AIAlert",
    "Notification",
]
