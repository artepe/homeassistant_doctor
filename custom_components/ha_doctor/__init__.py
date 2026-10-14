"""HA Doctor Home Assistant sidebar panel."""
from __future__ import annotations
from pathlib import Path
from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN, PANEL_PATH, PANEL_URL, VERSION

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {"assets_registered": False})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    data = hass.data.setdefault(DOMAIN, {"assets_registered": False})
    if not data["assets_registered"]:
        path = Path(__file__).parent / "frontend"
        await hass.http.async_register_static_paths([
            StaticPathConfig(PANEL_URL, str(path), cache_headers=False)
        ])
        data["assets_registered"] = True
    if not frontend.async_panel_exists(hass, PANEL_PATH):
        await panel_custom.async_register_panel(
            hass,
            webcomponent_name="ha-doctor-panel",
            frontend_url_path=PANEL_PATH,
            sidebar_title="HA Doctor",
            sidebar_icon="mdi:stethoscope",
            module_url=f"{PANEL_URL}/panel.js?v={VERSION}",
            require_admin=True,
            embed_iframe=False,
            config={"version": VERSION},
        )
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if frontend.async_panel_exists(hass, PANEL_PATH):
        frontend.async_remove_panel(hass, PANEL_PATH, warn_if_unknown=False)
    return True
