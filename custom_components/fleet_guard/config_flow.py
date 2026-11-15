"""Config flow: add a host by URL and long-lived per-host token."""
from __future__ import annotations

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import FleetAPI, FleetAPIError
from .const import CONF_TOKEN, CONF_URL, CONF_VERIFY_SSL, DOMAIN


class FleetGuardConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            url = user_input[CONF_URL].strip().rstrip('/')
            if not url.startswith(('https://', 'http://')):
                errors['base'] = 'invalid_url'
            else:
                try:
                    api = FleetAPI(async_get_clientsession(self.hass), url,
                                   user_input[CONF_TOKEN], user_input[CONF_VERIFY_SSL])
                    status = await api.status()
                    host = status['host']
                    machine = host['machine_id']
                    if not machine or not host.get('hostname'):
                        raise KeyError('machine_id or hostname')
                    await self.async_set_unique_id(f'fleet_guard_{machine}')
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=host['hostname'],
                        data={**user_input, CONF_URL: url},
                    )
                except FleetAPIError as exc:
                    if '401' in str(exc):
                        errors['base'] = 'invalid_auth'
                    else:
                        errors['base'] = 'cannot_connect'
                except (KeyError, ValueError, TypeError):
                    errors['base'] = 'invalid_response'
        return self.async_show_form(
            step_id='user',
            data_schema=vol.Schema({
                vol.Required(CONF_URL, default='https://192.168.148.10:8765'): str,
                vol.Required(CONF_TOKEN): str,
                vol.Required(CONF_VERIFY_SSL, default=True): bool,
            }),
            errors=errors,
        )
