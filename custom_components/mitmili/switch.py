"""Switch platform for Man in the Middle Light integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device import async_entity_id_to_device
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_SOURCE_ENTITY_ID, SUFFIX_OVERRIDDEN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Man in the Middle Light switch."""
    source_entity_id = entry.options.get(CONF_SOURCE_ENTITY_ID) or entry.data.get(
        CONF_SOURCE_ENTITY_ID
    )
    overridden_switch = ProxyOverriddenSwitch(hass, entry, source_entity_id)
    async_add_entities([overridden_switch])


class ProxyOverriddenSwitch(SwitchEntity):
    """Representation of the overridden switch for Man in the Middle Light."""

    _attr_should_poll = False

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, source_entity_id: str
    ) -> None:
        """Initialize the switch."""
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{SUFFIX_OVERRIDDEN}"
        self._attr_name = f"{entry.title} {SUFFIX_OVERRIDDEN}"
        self._attr_is_on = False

        # Link this entity to the source entity's device
        self.device_entry = async_entity_id_to_device(hass, source_entity_id)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch."""
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        self._attr_is_on = False
        self.async_write_ha_state()