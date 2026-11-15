"""Host reboot and per-container state sensors."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import FleetEntity
from .dynamic import DockerEntityReconciler


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        HostBinary(coordinator, 'reboot', 'Reboot required', BinarySensorDeviceClass.PROBLEM),
        HostBinary(coordinator, 'docker', 'Docker reachable', BinarySensorDeviceClass.CONNECTIVITY),
    ])
    reconciler = DockerEntityReconciler(
        hass, entry, coordinator, 'binary_sensor', ('container_',), async_add_entities
    )

    @callback
    def sync_containers():
        entities = [
            ContainerBinary(coordinator, container_key(c), c['name'])
            for c in coordinator.data['docker'].get('containers', [])
        ]
        reconciler.reconcile(entities)

    sync_containers()
    entry.async_on_unload(coordinator.async_add_listener(sync_containers))


def container_key(c: dict) -> str:
    """Stable across container recreation (name/Compose identity, not Docker id)."""
    if c.get('compose_project') and c.get('compose_service'):
        return f"compose:{c['compose_project']}/{c['compose_service']}"
    return f"container:{c['name']}"


class HostBinary(FleetEntity, BinarySensorEntity):
    def __init__(self, coordinator, key, name, device_class):
        super().__init__(coordinator, key, name)
        self.key = key
        self._attr_device_class = device_class

    @property
    def is_on(self):
        if self.key == 'reboot':
            return self.coordinator.data['host'].get('reboot_required')
        return self.coordinator.data['docker']['available']


class ContainerBinary(FleetEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator, key, name):
        super().__init__(coordinator, f'container_{key}_problem', name)
        self.key = key

    def _container(self):
        return next((c for c in self.coordinator.data['docker'].get('containers', [])
                     if container_key(c) == self.key), None)

    @property
    def available(self):
        return super().available and self._container() is not None

    @property
    def is_on(self):
        c = self._container()
        return bool(c and (c['state'] != 'running' or c['health'] == 'unhealthy'))

    @property
    def extra_state_attributes(self):
        c = self._container()
        if not c:
            return None
        return {'state': c['state'], 'health': c['health'], 'image': c['image'],
                'compose_project': c['compose_project'],
                'compose_service': c['compose_service']}
