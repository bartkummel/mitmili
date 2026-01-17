"""Light platform for Man in the Middle Light integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    ATTR_RGB_COLOR,
    ATTR_RGBW_COLOR,
    ATTR_RGBWW_COLOR,
    ATTR_TRANSITION,
    ATTR_WHITE,
    ATTR_XY_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device import async_entity_id_to_device
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity

from .const import CONF_SOURCE_ENTITY_ID, DOMAIN, SUFFIX_OVERRIDE, SUFFIX_OVERRIDDEN, SUFFIX_PROXY

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Man in the Middle Light entities."""
    source_entity_id = entry.options.get(CONF_SOURCE_ENTITY_ID) or entry.data.get(
        CONF_SOURCE_ENTITY_ID
    )

    # Create proxy and override light entities
    proxy_light = ProxyLight(hass, entry, source_entity_id, is_override=False)
    override_light = ProxyLight(hass, entry, source_entity_id, is_override=True)

    async_add_entities([proxy_light, override_light])


class ProxyLight(RestoreEntity, LightEntity):
    """Representation of a Proxy Light."""

    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        source_entity_id: str,
        is_override: bool,
    ) -> None:
        """Initialize the proxy light."""
        self.hass = hass
        self._entry = entry
        self._source_entity_id = source_entity_id
        self._is_override = is_override

        # Generate unique_id based on config entry and type
        suffix = SUFFIX_OVERRIDE if is_override else SUFFIX_PROXY
        self._attr_unique_id = f"{entry.entry_id}_{suffix}"
        self._attr_name = f"{entry.title} {suffix}"

        # Link this entity to the source entity's device
        self.device_entry = async_entity_id_to_device(hass, source_entity_id)

        # Initialize state attributes
        self._attr_is_on = False
        self._attr_brightness: int | None = None
        self._attr_color_mode: ColorMode | None = None
        # Set default color mode, will be updated from source light
        self._attr_supported_color_modes: set[ColorMode] = {ColorMode.ONOFF}
        self._attr_supported_features: LightEntityFeature = LightEntityFeature(0)
        self._attr_hs_color: tuple[float, float] | None = None
        self._attr_rgb_color: tuple[int, int, int] | None = None
        self._attr_rgbw_color: tuple[int, int, int, int] | None = None
        self._attr_rgbww_color: tuple[int, int, int, int, int] | None = None
        self._attr_xy_color: tuple[float, float] | None = None
        self._attr_color_temp_kelvin: int | None = None
        self._attr_min_color_temp_kelvin: int | None = None
        self._attr_max_color_temp_kelvin: int | None = None
        self._attr_effect_list: list[str] | None = None
        self._attr_effect: str | None = None
        self._attr_white: int | None = None

    def _get_overridden_switch_entity_id(self) -> str | None:
        """Get the entity ID of the overridden switch by looking up its unique_id."""
        ent_reg = er.async_get(self.hass)
        unique_id = f"{self._entry.entry_id}_{SUFFIX_OVERRIDDEN}"

        # Find the switch entity by unique_id
        for entity_id, entry in ent_reg.entities.items():
            if entry.unique_id == unique_id:
                _LOGGER.debug(
                    "Found overridden switch entity: %s for light %s",
                    entity_id,
                    self._attr_name,
                )
                return entity_id

        _LOGGER.warning(
            "Could not find overridden switch entity with unique_id %s for light %s",
            unique_id,
            self._attr_name,
        )
        return None

    def _sync_to_source(self) -> None:
        """Sync this proxy's state to the source light."""
        # Prepare service data
        service_data: dict[str, Any] = {"entity_id": self._source_entity_id}

        if self._attr_is_on:
            # Turn on with current attributes
            if self._attr_brightness is not None:
                service_data[ATTR_BRIGHTNESS] = self._attr_brightness
            if self._attr_hs_color is not None:
                service_data[ATTR_HS_COLOR] = self._attr_hs_color
            if self._attr_rgb_color is not None:
                service_data[ATTR_RGB_COLOR] = self._attr_rgb_color
            if self._attr_rgbw_color is not None:
                service_data[ATTR_RGBW_COLOR] = self._attr_rgbw_color
            if self._attr_rgbww_color is not None:
                service_data[ATTR_RGBWW_COLOR] = self._attr_rgbww_color
            if self._attr_xy_color is not None:
                service_data[ATTR_XY_COLOR] = self._attr_xy_color
            if self._attr_color_temp_kelvin is not None:
                service_data[ATTR_COLOR_TEMP_KELVIN] = self._attr_color_temp_kelvin
            if self._attr_effect is not None:
                service_data[ATTR_EFFECT] = self._attr_effect
            if self._attr_white is not None:
                service_data[ATTR_WHITE] = self._attr_white

            self.hass.async_create_task(
                self.hass.services.async_call("light", "turn_on", service_data)
            )
        else:
            # Turn off
            self.hass.async_create_task(
                self.hass.services.async_call("light", "turn_off", service_data)
            )

    def _copy_source_capabilities(self) -> None:
        """Copy capabilities from the source light."""
        source_state = self.hass.states.get(self._source_entity_id)
        if not source_state:
            _LOGGER.warning(
                "Could not get source light %s state to copy capabilities",
                self._source_entity_id,
            )
            return

        # Copy supported color modes
        supported_color_modes = source_state.attributes.get("supported_color_modes")
        if supported_color_modes:
            self._attr_supported_color_modes = set(
                ColorMode(mode) for mode in supported_color_modes
            )
            _LOGGER.debug(
                "Light %s copied color modes: %s",
                self._attr_name,
                self._attr_supported_color_modes,
            )

        # Copy current color mode
        color_mode = source_state.attributes.get("color_mode")
        if color_mode:
            self._attr_color_mode = ColorMode(color_mode)
        elif self._attr_supported_color_modes:
            # If no color mode set, use the first supported mode
            self._attr_color_mode = next(iter(self._attr_supported_color_modes))

        # Copy supported features
        supported_features = source_state.attributes.get("supported_features", 0)
        self._attr_supported_features = LightEntityFeature(supported_features)

        # Copy color temperature range if supported
        if ColorMode.COLOR_TEMP in (self._attr_supported_color_modes or set()):
            self._attr_min_color_temp_kelvin = source_state.attributes.get(
                "min_color_temp_kelvin"
            )
            self._attr_max_color_temp_kelvin = source_state.attributes.get(
                "max_color_temp_kelvin"
            )

        # Copy effect list if supported
        effect_list = source_state.attributes.get("effect_list")
        if effect_list:
            self._attr_effect_list = effect_list

    async def async_added_to_hass(self) -> None:
        """Handle entity added to hass."""
        await super().async_added_to_hass()

        # Try to restore capabilities from previous state first
        last_state = await self.async_get_last_state()
        capabilities_restored = False

        if last_state and last_state.attributes:
            _LOGGER.debug(
                "Light %s: attempting to restore capabilities from previous state",
                self._attr_name,
            )

            # Restore supported color modes
            supported_color_modes = last_state.attributes.get("supported_color_modes")
            if supported_color_modes and supported_color_modes != [ColorMode.ONOFF]:
                self._attr_supported_color_modes = set(
                    ColorMode(mode) for mode in supported_color_modes
                )
                capabilities_restored = True
                _LOGGER.info(
                    "Light %s: restored color modes from state: %s",
                    self._attr_name,
                    self._attr_supported_color_modes,
                )

            # Restore supported features
            supported_features = last_state.attributes.get("supported_features")
            if supported_features is not None and supported_features != 0:
                self._attr_supported_features = LightEntityFeature(supported_features)
                capabilities_restored = True
                _LOGGER.info(
                    "Light %s: restored features from state: %s",
                    self._attr_name,
                    self._attr_supported_features,
                )

            # Restore color temperature range
            min_kelvin = last_state.attributes.get("min_color_temp_kelvin")
            max_kelvin = last_state.attributes.get("max_color_temp_kelvin")
            if min_kelvin and max_kelvin:
                self._attr_min_color_temp_kelvin = min_kelvin
                self._attr_max_color_temp_kelvin = max_kelvin

            # Restore effect list
            effect_list = last_state.attributes.get("effect_list")
            if effect_list:
                self._attr_effect_list = effect_list

        # If no saved state or capabilities weren't restored, copy from source
        if not capabilities_restored:
            _LOGGER.debug(
                "Light %s: no saved capabilities, copying from source light %s",
                self._attr_name,
                self._source_entity_id,
            )
            self._copy_source_capabilities()

        # Track override switch for state changes
        switch_entity_id = self._get_overridden_switch_entity_id()
        if switch_entity_id:
            _LOGGER.debug(
                "Light %s tracking switch %s for state changes",
                self._attr_name,
                switch_entity_id,
            )
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, [switch_entity_id], self._handle_overridden_change
                )
            )
        else:
            _LOGGER.error(
                "Light %s could not find switch entity to track", self._attr_name
            )

    @callback
    def _handle_overridden_change(self, event: Event) -> None:
        """Handle changes to the overridden boolean."""
        # When the overridden state changes, sync the active proxy to the source
        new_state = event.data.get("new_state")
        if new_state is None:
            return

        is_overridden = new_state.state == "on"

        _LOGGER.debug(
            "Light %s received switch change event, is_overridden=%s, this is override=%s",
            self._attr_name,
            is_overridden,
            self._is_override,
        )

        # If this proxy just became active, sync to source
        if (self._is_override and is_overridden) or (
            not self._is_override and not is_overridden
        ):
            _LOGGER.info(
                "Light %s became active, syncing state to source light %s",
                self._attr_name,
                self._source_entity_id,
            )
            self._sync_to_source()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        # Update internal state
        self._attr_is_on = True

        if ATTR_BRIGHTNESS in kwargs:
            self._attr_brightness = kwargs[ATTR_BRIGHTNESS]

        # Color attributes are mutually exclusive - clear others when one is set
        # Also update color_mode to match the attribute being set
        if ATTR_HS_COLOR in kwargs:
            self._attr_hs_color = kwargs[ATTR_HS_COLOR]
            self._attr_rgb_color = None
            self._attr_rgbw_color = None
            self._attr_rgbww_color = None
            self._attr_xy_color = None
            self._attr_color_temp_kelvin = None
            self._attr_color_mode = ColorMode.HS
        elif ATTR_RGB_COLOR in kwargs:
            self._attr_rgb_color = kwargs[ATTR_RGB_COLOR]
            self._attr_hs_color = None
            self._attr_rgbw_color = None
            self._attr_rgbww_color = None
            self._attr_xy_color = None
            self._attr_color_temp_kelvin = None
            self._attr_color_mode = ColorMode.RGB
        elif ATTR_RGBW_COLOR in kwargs:
            self._attr_rgbw_color = kwargs[ATTR_RGBW_COLOR]
            self._attr_hs_color = None
            self._attr_rgb_color = None
            self._attr_rgbww_color = None
            self._attr_xy_color = None
            self._attr_color_temp_kelvin = None
            self._attr_color_mode = ColorMode.RGBW
        elif ATTR_RGBWW_COLOR in kwargs:
            self._attr_rgbww_color = kwargs[ATTR_RGBWW_COLOR]
            self._attr_hs_color = None
            self._attr_rgb_color = None
            self._attr_rgbw_color = None
            self._attr_xy_color = None
            self._attr_color_temp_kelvin = None
            self._attr_color_mode = ColorMode.RGBWW
        elif ATTR_XY_COLOR in kwargs:
            self._attr_xy_color = kwargs[ATTR_XY_COLOR]
            self._attr_hs_color = None
            self._attr_rgb_color = None
            self._attr_rgbw_color = None
            self._attr_rgbww_color = None
            self._attr_color_temp_kelvin = None
            self._attr_color_mode = ColorMode.XY
        elif ATTR_COLOR_TEMP_KELVIN in kwargs:
            self._attr_color_temp_kelvin = kwargs[ATTR_COLOR_TEMP_KELVIN]
            self._attr_hs_color = None
            self._attr_rgb_color = None
            self._attr_rgbw_color = None
            self._attr_rgbww_color = None
            self._attr_xy_color = None
            self._attr_color_mode = ColorMode.COLOR_TEMP
        elif ATTR_BRIGHTNESS in kwargs and self._attr_color_mode is None:
            # If only brightness is set and no color mode, use brightness mode
            self._attr_color_mode = ColorMode.BRIGHTNESS
        elif self._attr_color_mode is None:
            # If nothing specific is set, default to ONOFF
            self._attr_color_mode = ColorMode.ONOFF

        if ATTR_EFFECT in kwargs:
            self._attr_effect = kwargs[ATTR_EFFECT]
        if ATTR_WHITE in kwargs:
            self._attr_white = kwargs[ATTR_WHITE]

        self.async_write_ha_state()

        # Sync to source if this is the active proxy
        switch_entity_id = self._get_overridden_switch_entity_id()
        if switch_entity_id:
            overridden_state = self.hass.states.get(switch_entity_id)
            if overridden_state:
                is_overridden = overridden_state.state == "on"

                if (self._is_override and is_overridden) or (not self._is_override and not is_overridden):
                    # Prepare service data for source light
                    service_data: dict[str, Any] = {"entity_id": self._source_entity_id}

                    if ATTR_BRIGHTNESS in kwargs:
                        service_data[ATTR_BRIGHTNESS] = kwargs[ATTR_BRIGHTNESS]
                    if ATTR_HS_COLOR in kwargs:
                        service_data[ATTR_HS_COLOR] = kwargs[ATTR_HS_COLOR]
                    if ATTR_RGB_COLOR in kwargs:
                        service_data[ATTR_RGB_COLOR] = kwargs[ATTR_RGB_COLOR]
                    if ATTR_RGBW_COLOR in kwargs:
                        service_data[ATTR_RGBW_COLOR] = kwargs[ATTR_RGBW_COLOR]
                    if ATTR_RGBWW_COLOR in kwargs:
                        service_data[ATTR_RGBWW_COLOR] = kwargs[ATTR_RGBWW_COLOR]
                    if ATTR_XY_COLOR in kwargs:
                        service_data[ATTR_XY_COLOR] = kwargs[ATTR_XY_COLOR]
                    if ATTR_COLOR_TEMP_KELVIN in kwargs:
                        service_data[ATTR_COLOR_TEMP_KELVIN] = kwargs[ATTR_COLOR_TEMP_KELVIN]
                    if ATTR_EFFECT in kwargs:
                        service_data[ATTR_EFFECT] = kwargs[ATTR_EFFECT]
                    if ATTR_WHITE in kwargs:
                        service_data[ATTR_WHITE] = kwargs[ATTR_WHITE]
                    if ATTR_TRANSITION in kwargs:
                        service_data[ATTR_TRANSITION] = kwargs[ATTR_TRANSITION]

                    await self.hass.services.async_call("light", "turn_on", service_data)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        self._attr_is_on = False
        self.async_write_ha_state()

        # Sync to source if this is the active proxy
        switch_entity_id = self._get_overridden_switch_entity_id()
        if switch_entity_id:
            overridden_state = self.hass.states.get(switch_entity_id)
            if overridden_state:
                is_overridden = overridden_state.state == "on"

                if (self._is_override and is_overridden) or (not self._is_override and not is_overridden):
                    service_data: dict[str, Any] = {"entity_id": self._source_entity_id}

                    if ATTR_TRANSITION in kwargs:
                        service_data[ATTR_TRANSITION] = kwargs[ATTR_TRANSITION]

                    await self.hass.services.async_call("light", "turn_off", service_data)