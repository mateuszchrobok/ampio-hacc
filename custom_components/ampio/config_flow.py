"""Config flow for Ampio integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .const import CONF_BROKER, DEFAULT_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Default scan interval in seconds
DEFAULT_SCAN_INTERVAL = 30


def _try_connection(host: str, port: int, username: str | None, password: str | None) -> bool:
    """Test if we can connect to the MQTT broker."""
    import paho.mqtt.client as mqtt

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        protocol=mqtt.MQTTv311,
    )

    if username:
        client.username_pw_set(username, password)

    try:
        result = client.connect(host, port, keepalive=10)
        if result == mqtt.MQTT_ERR_SUCCESS:
            client.disconnect()
            return True
    except OSError as err:
        _LOGGER.debug("Connection test failed: %s", err)
    return False


class AmpioConfigFlow(ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle an Ampio config flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._broker: str | None = None
        self._port: int = DEFAULT_PORT
        self._username: str | None = None
        self._password: str | None = None
        self._reauth_entry: ConfigEntry | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> AmpioOptionsFlow:
        """Get the options flow for this handler."""
        return AmpioOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        return await self.async_step_broker()

    async def async_step_broker(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle broker configuration step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            can_connect = await self.hass.async_add_executor_job(
                _try_connection,
                user_input[CONF_BROKER],
                user_input[CONF_PORT],
                user_input.get(CONF_USERNAME),
                user_input.get(CONF_PASSWORD),
            )

            if can_connect:
                # Use broker host as unique ID
                unique_id = f"ampio_{user_input[CONF_BROKER]}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Ampio ({user_input[CONF_BROKER]})",
                    data=user_input,
                )

            errors["base"] = "cannot_connect"

        schema = vol.Schema(
            {
                vol.Required(CONF_BROKER, default=self._broker or vol.UNDEFINED): str,
                vol.Required(CONF_PORT, default=self._port): vol.Coerce(int),
                vol.Optional(CONF_USERNAME, default=self._username or vol.UNDEFINED): str,
                vol.Optional(CONF_PASSWORD, default=self._password or vol.UNDEFINED): str,
            }
        )

        return self.async_show_form(
            step_id="broker",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_zeroconf(self, discovery_info: ZeroconfServiceInfo) -> ConfigFlowResult:
        """Handle zeroconf discovery."""
        self._broker = str(discovery_info.host)
        self._port = discovery_info.port or DEFAULT_PORT

        # Set unique ID based on broker host
        unique_id = f"ampio_{self._broker}"
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        self.context["title_placeholders"] = {"name": self._broker}

        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm zeroconf discovery."""
        if user_input is not None:
            return await self.async_step_broker(
                {
                    CONF_BROKER: self._broker,
                    CONF_PORT: self._port,
                    **user_input,
                }
            )

        schema = vol.Schema(
            {
                vol.Optional(CONF_USERNAME): str,
                vol.Optional(CONF_PASSWORD): str,
            }
        )

        return self.async_show_form(
            step_id="zeroconf_confirm",
            data_schema=schema,
            description_placeholders={"name": self._broker},
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Handle re-authentication."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if self._reauth_entry:
            self._broker = self._reauth_entry.data.get(CONF_BROKER)
            self._port = self._reauth_entry.data.get(CONF_PORT, DEFAULT_PORT)
            self._username = self._reauth_entry.data.get(CONF_USERNAME)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle re-authentication confirmation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            can_connect = await self.hass.async_add_executor_job(
                _try_connection,
                self._broker,
                self._port,
                user_input.get(CONF_USERNAME),
                user_input.get(CONF_PASSWORD),
            )

            if can_connect and self._reauth_entry:
                self.hass.config_entries.async_update_entry(
                    self._reauth_entry,
                    data={
                        **self._reauth_entry.data,
                        CONF_USERNAME: user_input.get(CONF_USERNAME),
                        CONF_PASSWORD: user_input.get(CONF_PASSWORD),
                    },
                )
                await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")

            errors["base"] = "cannot_connect"

        schema = vol.Schema(
            {
                vol.Optional(CONF_USERNAME, default=self._username or vol.UNDEFINED): str,
                vol.Optional(CONF_PASSWORD): str,
            }
        )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=schema,
            errors=errors,
            description_placeholders={"broker": self._broker},
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if entry:
            self._broker = entry.data.get(CONF_BROKER)
            self._port = entry.data.get(CONF_PORT, DEFAULT_PORT)
            self._username = entry.data.get(CONF_USERNAME)
            self._password = entry.data.get(CONF_PASSWORD)

        return await self.async_step_reconfigure_confirm()

    async def async_step_reconfigure_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration confirmation."""
        errors: dict[str, str] = {}
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])

        if user_input is not None:
            can_connect = await self.hass.async_add_executor_job(
                _try_connection,
                user_input[CONF_BROKER],
                user_input[CONF_PORT],
                user_input.get(CONF_USERNAME),
                user_input.get(CONF_PASSWORD),
            )

            if can_connect and entry:
                self.hass.config_entries.async_update_entry(
                    entry,
                    data=user_input,
                    title=f"Ampio ({user_input[CONF_BROKER]})",
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reconfigure_successful")

            errors["base"] = "cannot_connect"

        schema = vol.Schema(
            {
                vol.Required(CONF_BROKER, default=self._broker): str,
                vol.Required(CONF_PORT, default=self._port): vol.Coerce(int),
                vol.Optional(CONF_USERNAME, default=self._username or vol.UNDEFINED): str,
                vol.Optional(CONF_PASSWORD, default=self._password or vol.UNDEFINED): str,
            }
        )

        return self.async_show_form(
            step_id="reconfigure_confirm",
            data_schema=schema,
            errors=errors,
        )


class AmpioOptionsFlow(OptionsFlow):
    """Handle Ampio options."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get current options or defaults
        options = self.config_entry.options

        schema = vol.Schema(
            {
                vol.Optional(
                    "scan_interval",
                    default=options.get("scan_interval", DEFAULT_SCAN_INTERVAL),
                ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
                vol.Optional(
                    "discovery_enabled",
                    default=options.get("discovery_enabled", True),
                ): bool,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
        )
