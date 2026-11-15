"""Keep Docker entities in sync with the agent's current inventory.

A stopped Docker container remains in the inventory; only absent containers
are deleted from Home Assistant. Two *successful* agent snapshots plus a short
grace period protect Compose recreations and registry settings.
"""
from __future__ import annotations

import logging
import time
from collections.abc import Iterable

from homeassistant.helpers import entity_registry as er

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# ~3 successful polls at the default 45-second interval. Allows typical
# Compose recreations to finish without deleting customized HA entity IDs.
REMOVE_GRACE_SECONDS = 90
MIN_ABSENT_SNAPSHOTS = 2


class DockerEntityReconciler:
    """Dynamically add Docker entities and retire only confirmed stale ones."""

    def __init__(self, hass, entry, coordinator, platform_domain, key_prefixes, add_entities):
        self._hass = hass
        self._entry = entry
        self._coordinator = coordinator
        self._platform_domain = platform_domain
        machine_id = coordinator.data['host']['machine_id']
        self._prefixes = tuple(f'{machine_id}_{prefix}' for prefix in key_prefixes)
        self._add_entities = add_entities
        self._seen: set[str] = set()
        # Map unique_id -> (first missing monotonic timestamp, valid snapshot count)
        self._missing: dict[str, tuple[float, int]] = {}
        self._skipping = False

    def reconcile(self, desired_entities: Iterable) -> None:
        """Compare a successful Docker snapshot with the HA entity registry."""
        data = self._coordinator.data
        docker = (data or {}).get('docker') or {}
        active = (data or {}).get('last_job') or {}
        if not docker.get('available', False) or active.get('state') in ('queued', 'running'):
            # A failed scan or a running update must never be treated as proof
            # that previously seen containers have been deleted.
            if not self._skipping:
                _LOGGER.debug(
                    'Skipping Docker entity cleanup: docker_available=%s, job=%s',
                    docker.get('available', False), active.get('state'),
                )
            self._skipping = True
            self._missing.clear()
            return
        self._skipping = False

        desired = {entity.unique_id: entity for entity in desired_entities}
        current = set(desired)
        pending = [entity for uid, entity in desired.items() if uid not in self._seen]
        if pending:
            self._seen.update(entity.unique_id for entity in pending)
            self._add_entities(pending)

        registry = er.async_get(self._hass)
        registered = {
            entity.unique_id: entity.entity_id
            for entity in er.async_entries_for_config_entry(registry, self._entry.entry_id)
            if entity.domain == self._platform_domain
            and entity.platform == DOMAIN
            and entity.unique_id.startswith(self._prefixes)
        }
        absent = (set(registered) | self._seen) - current
        now = time.monotonic()

        for uid in absent:
            first, count = self._missing.get(uid, (now, 0))
            count += 1
            self._missing[uid] = (first, count)
            age = now - first
            if age < REMOVE_GRACE_SECONDS or count < MIN_ABSENT_SNAPSHOTS:
                if count == 1:
                    _LOGGER.debug('Docker entity %s is absent; awaiting confirmation', uid)
                continue
            entity_id = registered.get(uid)
            if entity_id:
                # HA's entity registry handles unloading/removing live states.
                registry.async_remove(entity_id)
                _LOGGER.info('Fleet Guard removed deleted Docker entity: %s', entity_id)
            self._seen.discard(uid)
            self._missing.pop(uid, None)

        for uid in set(self._missing) - absent:
            self._missing.pop(uid, None)
