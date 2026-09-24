import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import QApplication
from app.services.auth_service import CurrentUser
from app.ui.main_window import MainWindow, MenuKeys

def main():
    app = QApplication(sys.argv)
    user = CurrentUser(
        id=1,
        username="admin",
        full_name="Quản trị viên Duck AI",
        role_name="ADMIN"
    )
    
    print("Creating MainWindow...")
    window = MainWindow(current_user=user, on_logout=lambda: None)
    
    all_keys = [
        MenuKeys.DASHBOARD,
        MenuKeys.MONITORING,
        MenuKeys.CAMERAS,
        MenuKeys.AI_DETECTION,
        MenuKeys.FLOCKS,
        MenuKeys.BARNS,
        MenuKeys.PRODUCTION,
        MenuKeys.INVENTORY,
        MenuKeys.VETERINARY,
        MenuKeys.VACCINATION,
        MenuKeys.ALERTS,
        MenuKeys.HISTORY,
        MenuKeys.REPORTS,
        MenuKeys.USERS,
        MenuKeys.SETTINGS,
    ]
    
    for key in all_keys:
        print(f"Testing view navigation: {key}...")
        window._select_menu(key)
        print(f"Successfully loaded {key}")

    print("\nSUCCESS: All views created and refreshed without errors!")

if __name__ == "__main__":
    main()
