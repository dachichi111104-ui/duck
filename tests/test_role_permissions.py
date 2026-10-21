import pytest
from PyQt6.QtWidgets import QApplication

from app.database.seed import seed_database
from app.services.auth_service import AuthService, CurrentUser
from app.services.user_management_service import UserManagementService
from app.config.constants import Roles, MenuKeys, ROLE_MENU_PERMISSIONS
from app.ui.veterinary.veterinary_record_dialog import VeterinaryRecordDialog
from app.ui.veterinary.vaccination_dialog import VaccinationDialog
from app.ui.flocks.flock_list_view import FlockListView
from app.ui.barns.barn_view import BarnView
from app.ui.inventory.inventory_view import InventoryView
from app.ui.users.users_view import UsersView


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture(autouse=True)
def seeded():
    seed_database()


def test_list_veterinarians():
    service = UserManagementService()
    vets = service.list_veterinarians()
    assert len(vets) > 0
    vet_usernames = [v.username for v in vets]
    assert "vet" in vet_usernames


def test_role_menu_permissions():
    admin = CurrentUser(id=1, username="admin", full_name="Admin", role_name=Roles.ADMIN)
    assert admin.can_access(MenuKeys.USERS)
    assert admin.can_access(MenuKeys.VETERINARY)
    assert admin.can_access(MenuKeys.INVENTORY)

    manager = CurrentUser(id=2, username="manager", full_name="Manager", role_name=Roles.FARM_MANAGER)
    assert not manager.can_access(MenuKeys.USERS)
    assert manager.can_access(MenuKeys.VETERINARY)
    assert manager.can_access(MenuKeys.FLOCKS)

    vet = CurrentUser(id=3, username="vet", full_name="Vet", role_name=Roles.VETERINARIAN)
    assert not vet.can_access(MenuKeys.USERS)
    assert not vet.can_access(MenuKeys.INVENTORY)
    assert vet.can_access(MenuKeys.VETERINARY)
    assert vet.can_access(MenuKeys.VACCINATION)

    staff = CurrentUser(id=4, username="staff", full_name="Staff", role_name=Roles.STAFF)
    assert not staff.can_access(MenuKeys.USERS)
    assert not staff.can_access(MenuKeys.VETERINARY)
    assert not staff.can_access(MenuKeys.VACCINATION)
    assert staff.can_access(MenuKeys.INVENTORY)


def test_veterinary_record_dialog_role_assignment(qapp):
    admin_user = CurrentUser(id=1, username="admin", full_name="Quản trị viên", role_name=Roles.ADMIN)
    dlg_admin = VeterinaryRecordDialog(admin_user)
    # Admin assigns vet, dropdown has options
    assert dlg_admin.veterinarian_combo.count() > 0
    assert dlg_admin.veterinarian_combo.currentText() != ""

    vet_user = CurrentUser(id=4, username="vet", full_name="Bác sĩ thú y", role_name=Roles.VETERINARIAN)
    dlg_vet = VeterinaryRecordDialog(vet_user)
    assert "Bác sĩ thú y" in dlg_vet.veterinarian_combo.currentText()

    # Test backward compatibility wrapper
    dlg_vet.veterinarian_input.setText("BS. Test Specialist")
    assert "BS. Test Specialist" in dlg_vet.veterinarian_combo.currentText()
    assert dlg_vet.veterinarian_input.text() == "BS. Test Specialist"


def test_vaccination_dialog_role_assignment(qapp):
    admin_user = CurrentUser(id=1, username="admin", full_name="Quản trị viên", role_name=Roles.ADMIN)
    dlg_admin = VaccinationDialog(admin_user)
    assert dlg_admin.veterinarian_combo.count() > 0

    vet_user = CurrentUser(id=4, username="vet", full_name="Bác sĩ thú y", role_name=Roles.VETERINARIAN)
    dlg_vet = VaccinationDialog(vet_user)
    assert "Bác sĩ thú y" in dlg_vet.veterinarian_combo.currentText()

    # Test backward compatibility wrapper
    dlg_vet.veterinarian_input.setText("BS. Vaccinator")
    assert "BS. Vaccinator" in dlg_vet.veterinarian_combo.currentText()
    assert dlg_vet.veterinarian_input.text() == "BS. Vaccinator"


def test_view_button_permissions_for_staff(qapp):
    staff_user = CurrentUser(id=3, username="staff", full_name="Nhân viên", role_name=Roles.STAFF)
    admin_user = CurrentUser(id=1, username="admin", full_name="Admin", role_name=Roles.ADMIN)

    # Flocks
    flock_view_staff = FlockListView(staff_user)
    assert flock_view_staff.empty_state.action_btn.isHidden()

    # Barns
    barn_view_staff = BarnView(staff_user)
    assert barn_view_staff.empty_state.action_btn.isHidden()

    # Users
    users_view_staff = UsersView(staff_user)
    assert users_view_staff.empty_state.action_btn.isHidden()
