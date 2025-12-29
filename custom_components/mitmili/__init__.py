"""The Man in the Middle Light integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry, ConfigEntryError
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_SOURCE_ENTITY_ID

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SWITCH, Platform.LIGHT]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Man in the Middle Light from a config entry."""
    # Validate that the source entity exists
    source_entity_id = entry.options.get(CONF_SOURCE_ENTITY_ID) or entry.data.get(
        CONF_SOURCE_ENTITY_ID
    )

    if not source_entity_id:
        raise ConfigEntryError("Source entity ID not found in configuration")

    # Log a warning if source entity doesn't exist yet, but allow setup to continue
    # Entities will show as unavailable until the source entity becomes available
    if not hass.states.get(source_entity_id):
        _LOGGER.warning(
            "Source light entity '%s' not found yet. "
            "Proxy entities will be unavailable until the source entity is loaded",
            source_entity_id,
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(config_entry_update_listener))

    return True


async def config_entry_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener, called when the config entry options are changed."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
