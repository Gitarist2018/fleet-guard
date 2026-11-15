"""Linux metrics, maintenance jobs, and Docker overview."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import FleetEntity

METRICS = {
    'cpu_percent': ('CPU usage', '%', 'mdi:cpu-64-bit'),
    'memory_percent': ('Memory usage', '%', 'mdi:memory'),
    'disk_percent': ('Root disk usage', '%', 'mdi:harddisk'),
    'load_1': ('Load average 1 minute', None, 'mdi:speedometer'),
    'uptime_seconds': ('Uptime', 's', 'mdi:clock-outline'),
    'packages': ('Pending APT updates', None, 'mdi:package-up'),
    'docker_total': ('Docker containers', None, 'mdi:docker'),
    'docker_running': ('Running Docker containers', None, 'mdi:docker'),
    'docker_unhealthy': ('Unhealthy Docker containers', None, 'mdi:alert'),
    'docker_updates': ('Docker image updates', None, 'mdi:package-up'),
    'job': ('Last maintenance job', None, 'mdi:progress-wrench'),
    'pve_vm_total': ('Proxmox virtual machines', None, 'mdi:monitor-multiple'),
    'pve_vm_running': ('Running Proxmox VMs', None, 'mdi:monitor'),
    'pve_ct_total': ('Proxmox LXC containers', None, 'mdi:package-variant'),
    'pve_ct_running': ('Running Proxmox LXC', None, 'mdi:package-variant-closed'),
    'pve_guests': ('Proxmox guests', None, 'mdi:server-network'),
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    is_pve = coordinator.data['host'].get('kind') == 'proxmox'
    async_add_entities([FleetSensor(coordinator, key) for key in METRICS
                        if is_pve or not key.startswith('pve_')])


class FleetSensor(FleetEntity, SensorEntity):
    def __init__(self, coordinator, key):
        name, unit, icon = METRICS[key]
        super().__init__(coordinator, key, name)
        self.key = key
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = unit
        if key not in {'job'}:
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def available(self):
        if self.key.startswith('pve_'):
            return super().available and bool(self.coordinator.data.get('proxmox', {}).get('available'))
        return super().available

    @property
    def native_value(self):
        data = self.coordinator.data
        if self.key in data['host']:
            return data['host'][self.key]
        if self.key == 'packages':
            return data['apt'].get('count')
        containers = data['docker'].get('containers', [])
        if self.key == 'docker_total':
            return len(containers) if data['docker']['available'] else None
        if self.key == 'docker_running':
            return sum(c['state'] == 'running' for c in containers) if data['docker']['available'] else None
        if self.key == 'docker_unhealthy':
            return sum(c['health'] == 'unhealthy' for c in containers) if data['docker']['available'] else None
        if self.key == 'docker_updates':
            updates = (list(data['docker'].get('compose_updates', {}).values()) +
                       list(data['docker'].get('standalone_updates', {}).values()))
            return sum(u['update_available'] is True for u in updates) if data['docker']['available'] else None
        if self.key.startswith('pve_'):
            guests = data.get('proxmox', {}).get('guests', [])
            if self.key == 'pve_guests':
                return len(guests)
            by_type = 'qemu' if '_vm_' in self.key else 'lxc'
            group = [g for g in guests if g.get('type') == by_type]
            return (sum(g.get('state') == 'running' for g in group)
                    if self.key.endswith('_running') else len(group))
        if self.key == 'job':
            return (data.get('last_job') or {}).get('state', 'none')
        return None

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        if self.key == 'packages':
            return {'packages': data['apt'].get('names', []),
                    'checked': data['apt'].get('checked'),
                    'error': data['apt'].get('error')}
        if self.key == 'docker_updates':
            return {'checked': data['docker'].get('checked'),
                    'unknown': sum(u['update_available'] is None for u in
                                   list(data['docker'].get('compose_updates', {}).values()) +
                                   list(data['docker'].get('standalone_updates', {}).values())),
                    'error': data['docker'].get('error')}
        if self.key == 'pve_guests':
            return {'guests': data.get('proxmox', {}).get('guests', []),
                    'version': data.get('proxmox', {}).get('version'),
                    'error': data.get('proxmox', {}).get('error')}
        if self.key == 'job':
            return data.get('last_job') or {}
        return None
