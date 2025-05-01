"""
Asynchronous client for Samsung soundbar.

Should work on HW-Q990D, HW-Q930D, HW-Q800D, HW-QS730D, HW-S800D, HW-S801D, HW-S700D, HW-S60D, HW-S61D, HW-LS60D
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Optional

import aiohttp
import async_timeout


class SoundbarApiError(Exception):
    """Raised when the soundbar API returns an error."""


class AsyncSoundbar:
    """Async client class."""

    def __init__(
        self,
        host: str,
        session: aiohttp.ClientSession,
        *,
        port: int = 1516,
        verify_ssl: bool = False,
        timeout: int = 8,
    ) -> None:
        self._url = f"https://{host}:{port}/"
        self._session = session
        self._verify_ssl = verify_ssl
        self._timeout = timeout
        self._token: Optional[str] = None

    # ------------------ internal helpers ------------------
    async def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raw = json.dumps(payload, separators=(",", ":"))
        try:
            async with async_timeout.timeout(self._timeout):
                resp = await self._session.post(
                    self._url,
                    data=raw,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    ssl=self._verify_ssl,
                )
            resp.raise_for_status()
            data = await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise SoundbarApiError(str(err)) from err

        if "error" in data:
            raise SoundbarApiError(data["error"])
        return data["result"]

    async def _call(self, method: str, **params: Any):
        if method != "createAccessToken":
            if not self._token:
                await self.create_token()
            params.setdefault("AccessToken", self._token)

        payload = {"jsonrpc": "2.0", "method": method, "id": 1}
        if params:
            payload["params"] = params
        return await self._post(payload)

    # ------------------ public API ------------------
    async def create_token(self) -> str:
        self._token = (await self._call("createAccessToken"))["AccessToken"]
        return self._token

    # Power ----------------------------------
    async def power_on(self):  await self._call("powerControl", power="powerOn")
    async def power_off(self): await self._call("powerControl", power="powerOff")

    # Volume & mute --------------------------
    async def volume_up(self):      await self._call("remoteKeyControl", remoteKey="VOL_UP")
    async def volume_down(self):    await self._call("remoteKeyControl", remoteKey="VOL_DOWN")
    async def sub_plus(self):       await self._call("remoteKeyControl", remoteKey="WOOFER_PLUS")
    async def sub_minus(self):      await self._call("remoteKeyControl", remoteKey="WOOFER_MINUS")
    async def mute_toggle(self):    await self._call("remoteKeyControl", remoteKey="MUTE")

    async def set_volume(self, level: int):
        if not 0 <= level <= 100:
            raise ValueError("Volume has to be in range 0–100")
        current = await self.volume()
        while current != level:
            if current < level:
                await self.volume_up()
                current += 1
            else:
                await self.volume_down()
                current -= 1

    # Input & sound mode ---------------------
    async def select_input(self, src: str):
        await self._call("inputSelectControl", inputSource=src)

    async def set_sound_mode(self, mode: str):
        await self._call("soundModeControl", soundMode=mode)

    # Helpers --------------------------------
    async def volume(self) -> int:      return int((await self._call("getVolume"))["volume"])
    async def is_muted(self) -> bool:   return bool((await self._call("getMute"))["mute"])
    async def input(self) -> str:       return (await self._call("inputSelectControl"))["inputSource"]
    async def sound_mode(self) -> str:  return (await self._call("soundModeControl"))["soundMode"]
    async def power_state(self) -> str: return (await self._call("powerControl"))["power"]
    async def codec(self) -> Optional[str]:       return (await self._call("getCodec")).get("codec")
    async def identifier(self) -> Optional[str]:  return (await self._call("getIdentifier")).get("identifier")

    async def status(self) -> Dict[str, Any]:
        """Return a consolidated status dict."""
        return {
            "power": await self.power_state(),
            "volume": await self.volume(),
            "mute": await self.is_muted(),
            "input": await self.input(),
            "sound_mode": await self.sound_mode(),
            "codec": await self.codec(),
            "identifier": await self.identifier(),
        }
