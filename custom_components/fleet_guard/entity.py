"""Base entity for Fleet Guard."""
from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FleetCoordinator


class FleetEntity(CoordinatorEntity[FleetCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: FleetCoordinator, key: str, name: str):
        super().__init__(coordinator)
        host = coordinator.data['host']
        self._attr_unique_id = f"{host['machine_id']}_{key}"
        self._attr_name = name
        self._attr_device_info = {
            'identifiers': {(DOMAIN, host['machine_id'])},
            'name': host['hostname'],
            'manufacturer': 'Fleet Guard',
            'model': host.get('os', 'Linux'),
            'sw_version': coordinator.data.get('version', ''),
        }
