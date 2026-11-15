"""One polling coordinator per monitored host."""
from __future__ import annotations

import asyncio
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import FleetAPI, FleetAPIError
from .const import SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class FleetCoordinator(DataUpdateCoordinator[dict]):
    def __init__(self, hass: HomeAssistant, api: FleetAPI) -> None:
        super().__init__(hass, _LOGGER, name='Fleet Guard', update_interval=SCAN_INTERVAL)
        self.api = api
        # Agent queues accept only one mutating maintenance job at a time.
        # Serialize callers for this host while allowing other hosts to run in parallel.
        self._maintenance_lock = asyncio.Lock()

    async def _async_update_data(self) -> dict:
        try:
            data = await self.api.status()
            if 'host' not in data or 'docker' not in data:
                raise UpdateFailed('Incomplete agent response')
            return data
        except FleetAPIError as exc:
            raise UpdateFailed(str(exc)) from exc

    async def perform(self, action: str, target: str | None = None,
                      wait: bool = False) -> dict:
        """Dispatch maintenance jobs sequentially per host, not per HA entity.

        Multi-entity update.install calls can invoke multiple async_install
        methods concurrently. The Linux agent rejects overlapping mutating
        jobs. Holding this lock until job completion prevents lost updates.
        Independent Fleet Guard host coordinators have independent locks.
        """
        if action == 'check_updates':
            job = await self.api.enqueue(action, target)
            await self.async_request_refresh()
            return job

        async with self._maintenance_lock:
            job = await self.api.enqueue(action, target)
            if wait:
                job = await self.api.wait_job(job['id'])
            if action != 'reboot':
                await self.async_request_refresh()
            return job
