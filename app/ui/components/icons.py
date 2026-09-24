"""
Centralized vector icon utility powered by QtAwesome (FontAwesome 5).
Replaces all emojis with crisp, professional vector icons.
"""
from __future__ import annotations

import qtawesome as qta
from PyQt6.QtGui import QIcon
from app.config.constants import Colors, MenuKeys


def get_menu_icon(menu_key: str, color: str = Colors.PRIMARY) -> QIcon:
    icon_map = {
        MenuKeys.DASHBOARD: "fa5s.chart-line",
        MenuKeys.MONITORING: "fa5s.video",
        MenuKeys.CAMERAS: "fa5s.camera",
        MenuKeys.AI_DETECTION: "fa5s.brain",
        MenuKeys.FLOCKS: "fa5s.feather-alt",
        MenuKeys.BARNS: "fa5s.warehouse",
        MenuKeys.PRODUCTION: "fa5s.egg",
        MenuKeys.INVENTORY: "fa5s.boxes",
        MenuKeys.VETERINARY: "fa5s.user-md",
        MenuKeys.VACCINATION: "fa5s.syringe",
        MenuKeys.ALERTS: "fa5s.bell",
        MenuKeys.HISTORY: "fa5s.history",
        MenuKeys.REPORTS: "fa5s.file-alt",
        MenuKeys.USERS: "fa5s.users",
        MenuKeys.SETTINGS: "fa5s.cog",
    }
    name = icon_map.get(menu_key, "fa5s.circle")
    return qta.icon(name, color=color)


def get_icon(name: str, color: str = Colors.PRIMARY) -> QIcon:
    """Helper to fetch any FontAwesome icon with custom color."""
    return qta.icon(name, color=color)
