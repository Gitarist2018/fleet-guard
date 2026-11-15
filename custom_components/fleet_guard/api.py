"""Asynchronous HTTP API client for the Fleet Guard agent."""
from __future__ import annotations

import asyncio
from typing import Any

import aiohttp


class FleetAPIError(Exception):
    """An agent API request failed."""


class FleetAPI:
    def __init__(self, session: aiohttp.ClientSession, url: str, token: str,
                 verify_ssl: bool = True) -> None:
        self._session = session
        self._url = url.rstrip('/')
        self._token = token
        self._ssl = verify_ssl

    async def _call(self, method: str, path: str, payload: dict | None = None) -> dict:
        try:
            async with self._session.request(
                method,
                self._url + path,
                headers={'Authorization': f'Bearer {self._token}'},
                json=payload,
                ssl=self._ssl,
                timeout=aiohttp.ClientTimeout(total=35),
            ) as response:
                data: Any = await response.json(content_type=None)
                if response.status >= 400:
                    detail = data.get('error') if isinstance(data, dict) else 'Agent error'
                    raise FleetAPIError(f'Agent returned HTTP {response.status}: {detail}')
                if not isinstance(data, dict):
                    raise FleetAPIError('Invalid response: expected JSON object')
                return data
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
            raise FleetAPIError(f'Cannot contact agent: {exc}') from exc

    async def status(self) -> dict:
        return await self._call('GET', '/v1/status')

    async def enqueue(self, action: str, target: str | None = None) -> dict:
        body = {'action': action}
        if target is not None:
            body['target'] = target
        return await self._call('POST', '/v1/actions', body)

    async def job(self, job_id: str) -> dict:
        return await self._call('GET', f'/v1/jobs/{job_id}')

    async def wait_job(self, job_id: str, timeout: int = 3600) -> dict:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while loop.time() < deadline:
            await asyncio.sleep(4)
            data = await self.job(job_id)
            if data.get('state') == 'success':
                return data
            if data.get('state') == 'failed':
                raise FleetAPIError(data.get('error') or 'Maintenance operation failed')
        raise FleetAPIError('Maintenance job timed out; check the host before retrying')
