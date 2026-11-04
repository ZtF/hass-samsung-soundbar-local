"""
Asynchronous client for Samsung soundbar.

Should work on HW-Q990D, HW-Q930D, HW-Q800D, HW-QS730D, HW-S800D, HW-S801D, HW-S700D, HW-S60D, HW-S61D, HW-LS60D

The soundbar issues a single access token; each createAccessToken call invalidates the
previous one, so any other client (the SmartThings app, another tool) can invalidate the
token this client is holding. Responses that carry neither "result" nor "error" - e.g.
{"code": -32700, "message": "Parse error"} - are therefore expected, and used to crash
the coordinator with a KeyError, leaving the media_player entity permanently unavailable
because the token was never refreshed. They are now surfaced as SoundbarApiError, and a
failed call re-authenticates once and retries, except for an unsupported method.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Optional

import aiohttp
import async_timeout

_LOGGER = logging.getLogger(__name__)


class SoundbarApiError(Exception):
    """Raised when the soundbar API returns an error."""

    def __init__(self, message: str, code: int | None = None) -> None:
        super().__init__(message)
        self.code = code


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
        self._volume_control_supported = True
        self._mute_control_supported = True
        # The soundbar's JSON-RPC server can't handle concurrent requests
        self._lock = asyncio.Lock()

    # ------------------ internal helpers ------------------
    async def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raw = json.dumps(payload, separators=(",", ":"))
        try:
            async with self._lock:
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
                    text = await resp.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise SoundbarApiError(str(err)) from err

        try:
            data = json.loads(text)
        except ValueError as err:
            raise SoundbarApiError(f"invalid JSON response: {text[:200]!r}") from err

        if "error" in data:
            error = data["error"]
            raise SoundbarApiError(error, code=error.get("code") if isinstance(error, dict) else None)
        if "result" not in data:
            # Some models or stale tokens return top-level {"code": ..., "message": ...}.
            raise SoundbarApiError(f"unexpected response: {data}", code=data.get("code"))
        return data["result"]

    async def _call(self, method: str, **params: Any):
        if method == "createAccessToken":
            payload = {"jsonrpc": "2.0", "method": method, "id": 1}
            return await self._post(payload)

        attempts = 0
        while True:
            if not self._token:
                await self.create_token()
            params["AccessToken"] = self._token
            payload = {"jsonrpc": "2.0", "method": method, "id": 1, "params": params}
            try:
                return await self._post(payload)
            except SoundbarApiError as err:
                if err.code == -32601 or attempts >= 1:
                    raise
                attempts += 1
                # Drop the cached token and re-authenticate once.
                _LOGGER.debug(
                    "soundbar call %s failed; re-authenticating and retrying", method
                )
                self._token = None
                await asyncio.sleep(0.5)

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
        if self._volume_control_supported:
            try:
                result = await self._call("volumeControl", volume=level)
            except SoundbarApiError as err:
                # Models without volumeControl ("Method not found") fall back to
                # stepping with VOL_UP/VOL_DOWN
                if err.code != -32601:
                    raise
                self._volume_control_supported = False
            else:
                if not result.get("success", True):
                    raise SoundbarApiError(f"Failed to set volume to {level}")
                return
        current = await self.volume()
        while current != level:
            if current < level:
                await self.volume_up()
                current += 1
            else:
                await self.volume_down()
                current -= 1

    async def set_mute(self, mute: bool) -> None:
        """Set mute, using the remote key when muteControl is unavailable."""
        if self._mute_control_supported:
            try:
                result = await self._call("muteControl", mute=mute)
            except SoundbarApiError as err:
                if err.code != -32601:
                    raise
                self._mute_control_supported = False
            else:
                if not result.get("success", True):
                    raise SoundbarApiError(f"Failed to set mute {mute}")
                return
        if await self.is_muted() != mute:
            await self.mute_toggle()

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
        power = await self.power_state()
        optional_values = []
        for getter in (
            self.volume,
            self.is_muted,
            self.input,
            self.sound_mode,
            self.codec,
            self.identifier,
        ):
            try:
                optional_values.append(await getter())
            except (SoundbarApiError, KeyError, TypeError, ValueError):
                optional_values.append(None)
        return {
            "power": power,
            "volume": optional_values[0],
            "mute": optional_values[1],
            "input": optional_values[2],
            "sound_mode": optional_values[3],
            "codec": optional_values[4],
            "identifier": optional_values[5],
        }
