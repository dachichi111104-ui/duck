import sys, traceback

def test():
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication(sys.argv)
        from app.database.connection import init_database
        init_database()
        from app.ui.production.production_view import ProductionView
        from app.services.auth_service import CurrentUser
        user = CurrentUser(1, 'admin', 'Quản trị viên', 'ADMIN')
        pv = ProductionView(user)
        print("SUCCESS: ProductionView refreshed cleanly without DetachedInstanceError!")
    except Exception as e:
        traceback.print_exc()

if __name__ == "__main__":
    test()
