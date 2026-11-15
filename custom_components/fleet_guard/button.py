"""Explicit user-triggered refreshes and restarts."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import FleetAPIError
from .const import DOMAIN
from .entity import FleetEntity
from .dynamic import DockerEntityReconciler
from .binary_sensor import container_key


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [FleetButton(coordinator, 'check_updates', 'Check updates', 'check_updates')]
    if 'reboot' in coordinator.data.get('allowed_actions', []):
        entities.append(FleetButton(coordinator, 'reboot', 'Reboot host', 'reboot'))
    async_add_entities(entities)
    reconciler = DockerEntityReconciler(
        hass, entry, coordinator, 'button', ('restart_', 'update_'), async_add_entities
    )

    @callback
    def sync_containers():
        entities = []
        allowed_actions = coordinator.data.get('allowed_actions', [])
        update_info = coordinator.data['docker'].get('standalone_updates', {})
        for c in coordinator.data['docker'].get('containers', []):
            key = container_key(c)
            if 'docker_restart' in allowed_actions:
                entities.append(ContainerRestartButton(coordinator, key, c['name']))
            if (not c.get('compose_project') and
                    'standalone_update' in allowed_actions and
                    update_info.get(c['name'], {}).get('allowed')):
                entities.append(ContainerUpdateButton(coordinator, key, c['name']))
        reconciler.reconcile(entities)

    sync_containers()
    entry.async_on_unload(coordinator.async_add_listener(sync_containers))


class FleetButton(FleetEntity, ButtonEntity):
    def __init__(self, coordinator, key, name, action, target=None):
        super().__init__(coordinator, key, name)
        self.action = action
        self.target = target
        self._attr_icon = 'mdi:restart' if action != 'check_updates' else 'mdi:refresh'

    async def async_press(self):
        try:
            await self.coordinator.perform(self.action, self.target)
        except FleetAPIError as exc:
            raise HomeAssistantError(str(exc)) from exc


class ContainerRestartButton(FleetButton):
    def __init__(self, coordinator, key, name):
        super().__init__(coordinator, f'restart_{key}', f'Restart {name}', 'docker_restart')
        self.container_key = key

    @property
    def available(self):
        return super().available and self._current_id() is not None

    def _current_id(self):
        for c in self.coordinator.data['docker'].get('containers', []):
            if container_key(c) == self.container_key:
                return c['id']
        return None

    async def async_press(self):
        container_id = self._current_id()
        if not container_id:
            raise HomeAssistantError('Container no longer available')
        try:
            await self.coordinator.perform('docker_restart', container_id)
        except FleetAPIError as exc:
            raise HomeAssistantError(str(exc)) from exc


class ContainerUpdateButton(ContainerRestartButton):
    """Manual update even if registry digest discovery is inconclusive."""

    def __init__(self, coordinator, key, name):
        super().__init__(coordinator, key, name)
        self._attr_unique_id = f"{coordinator.data['host']['machine_id']}_update_{key}"
        self._attr_name = f'Update {name}'
        self._attr_icon = 'mdi:package-up'
        self.action = 'standalone_update'

    async def async_press(self):
        container_id = self._current_id()
        if not container_id:
            raise HomeAssistantError('Container no longer available')
        try:
            await self.coordinator.perform('standalone_update', container_id, wait=True)
        except FleetAPIError as exc:
            raise HomeAssistantError(str(exc)) from exc
