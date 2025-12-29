"""Config flow for the Man in the Middle Light integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

import voluptuous as vol

from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.helpers import selector
from homeassistant.helpers.schema_config_entry_flow import (
    SchemaConfigFlowHandler,
    SchemaFlowFormStep,
    SchemaFlowMenuStep,
)

from .const import CONF_SOURCE_ENTITY_ID, DOMAIN

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SOURCE_ENTITY_ID): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=LIGHT_DOMAIN)
        ),
    }
)

OPTIONS_SCHEMA = CONFIG_SCHEMA

CONFIG_FLOW: dict[str, SchemaFlowFormStep | SchemaFlowMenuStep] = {
    "user": SchemaFlowFormStep(CONFIG_SCHEMA)
}

OPTIONS_FLOW: dict[str, SchemaFlowFormStep | SchemaFlowMenuStep] = {
    "init": SchemaFlowFormStep(OPTIONS_SCHEMA)
}


class ConfigFlowHandler(SchemaConfigFlowHandler, domain=DOMAIN):
    """Handle a config or options flow for Man in the Middle Light."""

    config_flow = CONFIG_FLOW
    options_flow = OPTIONS_FLOW

    def async_config_entry_title(self, options: Mapping[str, Any]) -> str:
        """Return config entry title."""
        # Get the source entity name from the entity registry
        entity_id = options.get(CONF_SOURCE_ENTITY_ID)
        if entity_id:
            # Get entity name from state
            state = self.hass.states.get(entity_id)
            if state and state.name:
                return state.name
            # Fallback to entity_id friendly name
            return entity_id.split(".")[-1].replace("_", " ").title()
        return "Man in the Middle Light"

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Handle the user step."""
        errors = {}

        if user_input is not None:
            # Validate the source entity exists
            source_entity_id = user_input[CONF_SOURCE_ENTITY_ID]
            if not self.hass.states.get(source_entity_id):
                errors["base"] = "entity_not_found"
            else:
                # Check for duplicate config entries with same source entity
                self._async_abort_entries_match({CONF_SOURCE_ENTITY_ID: source_entity_id})

        # If no errors, continue with default schema flow
        if user_input is not None and not errors:
            return await super().async_step_user(user_input)

        # Show form with errors if any
        if errors:
            return self.async_show_form(
                step_id="user",
                data_schema=CONFIG_SCHEMA,
                errors=errors,
            )

        return await super().async_step_user(user_input)
