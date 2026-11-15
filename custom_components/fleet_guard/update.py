"""Actionable APT and allowlisted Compose service updates."""
from __future__ import annotations

from homeassistant.components.update import UpdateEntity, UpdateEntityFeature
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
    if coordinator.data['host'].get('kind') == 'proxmox':
        async_add_entities([ProxmoxUpdate(coordinator)])
    elif (coordinator.data['host'].get('reboot_required') is not None
          or 'apt_upgrade' in coordinator.data.get('allowed_actions', [])):
        # Synology's Docker-agent is not the NAS package manager. Its APT
        # result is unknown and its host reboot status is explicitly None.
        async_add_entities([APTUpdate(coordinator)])
    reconciler = DockerEntityReconciler(
        hass, entry, coordinator, 'update', ('compose_update_', 'standalone_update_'),
        async_add_entities
    )

    @callback
    def sync_services():
        entities = []
        # Registry scans run less frequently than the live container inventory.
        # Never resurrect a deleted container from stale cached update metadata.
        containers = coordinator.data['docker'].get('containers', [])
        compose_present = {
            f"{c['compose_project']}/{c['compose_service']}"
            for c in containers if c.get('compose_project') and c.get('compose_service')
        }
        standalone_present = {
            c['name'] for c in containers if not c.get('compose_project')
        }
        if 'compose_update' in coordinator.data.get('allowed_actions', []):
            for key in coordinator.data['docker'].get('compose_updates', {}):
                if key in compose_present:
                    entities.append(ComposeUpdate(coordinator, key))
        for name in coordinator.data['docker'].get('standalone_updates', {}):
            if name in standalone_present:
                entities.append(StandaloneUpdate(coordinator, name))
        reconciler.reconcile(entities)

    sync_services()
    entry.async_on_unload(coordinator.async_add_listener(sync_services))


class FleetUpdate(FleetEntity, UpdateEntity):
    _attr_supported_features = UpdateEntityFeature.INSTALL

    async def _install_action(self, action, target=None):
        try:
            await self.coordinator.perform(action, target, wait=True)
        except FleetAPIError as exc:
            raise HomeAssistantError(str(exc)) from exc


class APTUpdate(FleetUpdate):
    @property
    def supported_features(self):
        return (UpdateEntityFeature.INSTALL if 'apt_upgrade' in
                self.coordinator.data.get('allowed_actions', []) else 0)

    def __init__(self, coordinator):
        super().__init__(coordinator, 'apt_update', 'APT packages')
        self._attr_icon = 'mdi:package-up'

    @property
    def available(self):
        return super().available and self.coordinator.data['apt'].get('count') is not None

    @property
    def installed_version(self):
        n = self.coordinator.data['apt'].get('count')
        return f'{n} pending' if n is not None else None

    @property
    def latest_version(self):
        return '0 pending'

    @property
    def has_update(self):
        return (self.coordinator.data['apt'].get('count') or 0) > 0

    @property
    def extra_state_attributes(self):
        return {'packages': self.coordinator.data['apt'].get('names', []),
                'note': 'APT upgrade without automatic package removals'}

    async def async_install(self, version=None, backup=False, **kwargs):
        if backup:
            raise HomeAssistantError('Automatic backup not supported')
        await self._install_action('apt_upgrade')


class ProxmoxUpdate(APTUpdate):
    """Proxmox APT full-upgrade with an explicit, agent-side allowlist."""

    def __init__(self, coordinator):
        FleetUpdate.__init__(self, coordinator, 'apt_update', 'Proxmox packages')
        self._attr_icon = 'mdi:server-network'

    @property
    def supported_features(self):
        return (UpdateEntityFeature.INSTALL if 'pve_upgrade' in
                self.coordinator.data.get('allowed_actions', []) else 0)

    @property
    def extra_state_attributes(self):
        info = super().extra_state_attributes
        return {**(info or {}), 'note': 'Proxmox apt full-upgrade; package removals blocked',
                'removals_planned': self.coordinator.data['apt'].get('removals_planned')}

    async def async_install(self, version=None, backup=False, **kwargs):
        if version is not None or backup:
            raise HomeAssistantError('Specific version selection and backups are not supported')
        if 'pve_upgrade' not in self.coordinator.data.get('allowed_actions', []):
            raise HomeAssistantError('Proxmox upgrades are not enabled on the agent')
        await self._install_action('pve_upgrade')


class ComposeUpdate(FleetUpdate):
    def __init__(self, coordinator, key):
        super().__init__(coordinator, f'compose_update_{key}', f'{key} image')
        self.key = key
        self._attr_icon = 'mdi:docker'

    def _update(self):
        return self.coordinator.data['docker'].get('compose_updates', {}).get(self.key)

    @property
    def available(self):
        d = self._update()
        exists = any(container_key(c) == 'compose:' + self.key for c in
                     self.coordinator.data['docker'].get('containers', []))
        return (super().available and exists and d is not None
                and d.get('local_digest') is not None and d.get('remote_digest') is not None)

    @property
    def installed_version(self):
        d = self._update() or {}
        digest = d.get('local_digest')
        return digest[:19] if digest else None

    @property
    def latest_version(self):
        d = self._update() or {}
        digest = d.get('remote_digest')
        return digest[:19] if digest else None

    @property
    def has_update(self):
        d = self._update() or {}
        return d.get('update_available') is True

    @property
    def extra_state_attributes(self):
        return self._update()

    async def async_install(self, version=None, backup=False, **kwargs):
        if backup:
            raise HomeAssistantError('Compose backups not supported')
        await self._install_action('compose_update', self.key)


class StandaloneUpdate(FleetUpdate):
    """Per-container image update; stable identity is container name, not ID."""

    def __init__(self, coordinator, name):
        super().__init__(coordinator, f'standalone_update_{name}', f'{name} image')
        self.container_name = name
        self._attr_icon = 'mdi:docker'

    def _update(self):
        return self.coordinator.data['docker'].get('standalone_updates', {}).get(self.container_name)

    def _current_id(self):
        for container in self.coordinator.data['docker'].get('containers', []):
            if container_key(container) == 'container:' + self.container_name:
                return container['id']
        return None

    @property
    def supported_features(self):
        u = self._update()
        return UpdateEntityFeature.INSTALL if u and u.get('allowed') else 0

    @property
    def available(self):
        u = self._update()
        return (super().available and u is not None and self._current_id() is not None
                and u.get('local_digest') is not None and u.get('remote_digest') is not None)

    @property
    def installed_version(self):
        digest = (self._update() or {}).get('local_digest')
        return digest[:19] if digest else None

    @property
    def latest_version(self):
        digest = (self._update() or {}).get('remote_digest')
        return digest[:19] if digest else None

    @property
    def has_update(self):
        return (self._update() or {}).get('update_available') is True

    @property
    def extra_state_attributes(self):
        return self._update()

    async def async_install(self, version=None, backup=False, **kwargs):
        if version is not None:
            raise HomeAssistantError('Specific image versions are not supported')
        if backup:
            raise HomeAssistantError('Data volume backup is not supported')
        update = self._update()
        if not update or not update.get('allowed'):
            raise HomeAssistantError('Container updates are disabled on this agent')
        container_id = self._current_id()
        if not container_id:
            raise HomeAssistantError('Container no longer available')
        await self._install_action('standalone_update', container_id)
