"""
Asynchronous client for Samsung soundbar.

Should work on HW-Q990D, HW-Q930D, HW-Q800D, HW-QS730D, HW-S800D, HW-S801D,
HW-S700D, HW-S60D, HW-S61D, HW-LS60D.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any

import aiohttp


class SoundbarApiError(Exception):
    """Raised when the soundbar API returns an error."""


class SoundbarAuthError(SoundbarApiError):
    """Raised when the soundbar rejects the access token."""


class SoundbarConnectionError(SoundbarApiError):
    """Raised when the soundbar cannot be reached."""


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
        self._token: str | None = None
        self._token_lock = asyncio.Lock()
        # The soundbar's embedded HTTP server cannot handle concurrent
        # connections (it resets them), so every request is serialized.
        self._request_lock = asyncio.Lock()
        # None = unknown, True = supported, False = unsupported (use fallback)
        self._has_set_volume: bool | None = None

    # ------------------ internal helpers ------------------
    async def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        raw = json.dumps(payload, separators=(",", ":"))
        async with self._request_lock:
            data = await self._post_locked(raw)

        if "error" in data:
            err_payload = data["error"]
            message = (
                err_payload.get("message", str(err_payload))
                if isinstance(err_payload, dict)
                else str(err_payload)
            )
            if "token" in message.lower() or "auth" in message.lower():
                raise SoundbarAuthError(message)
            raise SoundbarApiError(message)
        if "result" not in data:
            raise SoundbarApiError(f"Unexpected response: {data}")
        return data["result"]

    async def _post_locked(self, raw: str) -> dict[str, Any]:
        # A reset or disconnect on the first attempt usually means the
        # device dropped the pooled keep-alive connection (or momentarily
        # refused the connect); retry once on a fresh connection before
        # giving up. The request was not processed in that case, so the
        # retry is safe.
        for attempt in range(2):
            try:
                async with asyncio.timeout(self._timeout):
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
                    return await resp.json()
            except (
                aiohttp.ServerDisconnectedError,
                aiohttp.ClientOSError,
            ) as err:
                if attempt:
                    raise SoundbarConnectionError(str(err)) from err
                await asyncio.sleep(0.5)
            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                raise SoundbarConnectionError(str(err)) from err
        raise SoundbarConnectionError("Request failed")  # unreachable

    async def _ensure_token(self) -> None:
        if self._token:
            return
        async with self._token_lock:
            if self._token:
                return
            await self._create_token_locked()

    async def _create_token_locked(self) -> None:
        payload = {"jsonrpc": "2.0", "method": "createAccessToken", "id": 1}
        result = await self._post(payload)
        self._token = result["AccessToken"]

    async def _call(self, method: str, **params: Any) -> dict[str, Any]:
        if method == "createAccessToken":
            return await self._post(
                {"jsonrpc": "2.0", "method": method, "id": 1}
            )

        await self._ensure_token()
        params.setdefault("AccessToken", self._token)
        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
            "id": 1,
            "params": params,
        }

        try:
            return await self._post(payload)
        except SoundbarAuthError:
            # Token may have been invalidated; refresh once and retry.
            async with self._token_lock:
                self._token = None
                await self._create_token_locked()
            params["AccessToken"] = self._token
            payload["params"] = params
            return await self._post(payload)

    # ------------------ public API ------------------
    async def create_token(self) -> str:
        """Force a new token to be created and return it."""
        async with self._token_lock:
            self._token = None
            await self._create_token_locked()
        return self._token  # type: ignore[return-value]

    # Power ----------------------------------
    async def power_on(self) -> None:
        await self._call("powerControl", power="powerOn")

    async def power_off(self) -> None:
        await self._call("powerControl", power="powerOff")

    # Volume & mute --------------------------
    async def volume_up(self) -> None:
        await self._call("remoteKeyControl", remoteKey="VOL_UP")

    async def volume_down(self) -> None:
        await self._call("remoteKeyControl", remoteKey="VOL_DOWN")

    async def sub_plus(self) -> None:
        await self._call("remoteKeyControl", remoteKey="WOOFER_PLUS")

    async def sub_minus(self) -> None:
        await self._call("remoteKeyControl", remoteKey="WOOFER_MINUS")

    async def mute_toggle(self) -> None:
        await self._call("remoteKeyControl", remoteKey="MUTE")

    async def set_volume(self, level: int) -> None:
        if not 0 <= level <= 100:
            raise ValueError("Volume has to be in range 0-100")

        # Try direct setter first; cache the result so we only probe once.
        if self._has_set_volume is not False:
            try:
                await self._call("setVolume", volume=level)
                self._has_set_volume = True
                return
            except (SoundbarAuthError, SoundbarConnectionError):
                # Transport or auth failure, not a missing method — don't
                # permanently disable the direct setter.
                raise
            except SoundbarApiError:
                self._has_set_volume = False

        # Fallback: step the volume one increment at a time.
        current = await self.volume()
        while current != level:
            if current < level:
                await self.volume_up()
                current += 1
            else:
                await self.volume_down()
                current -= 1

    # Input & sound mode ---------------------
    async def select_input(self, src: str) -> None:
        await self._call("inputSelectControl", inputSource=src)

    async def set_sound_mode(self, mode: str) -> None:
        await self._call("soundModeControl", soundMode=mode)

    # Helpers --------------------------------
    async def volume(self) -> int:
        return int((await self._call("getVolume"))["volume"])

    async def is_muted(self) -> bool:
        return bool((await self._call("getMute"))["mute"])

    # NOTE: the soundbar firmware reuses the `*Control` RPC names as getters
    # when called without a value parameter. Verified on HW-Q990D / HW-S800D.
    async def input(self) -> str:
        return (await self._call("inputSelectControl"))["inputSource"]

    async def sound_mode(self) -> str:
        return (await self._call("soundModeControl"))["soundMode"]

    async def power_state(self) -> str:
        return (await self._call("powerControl"))["power"]

    async def codec(self) -> str | None:
        return (await self._call("getCodec")).get("codec")

    async def identifier(self) -> str | None:
        return (await self._call("getIdentifier")).get("identifier")

    async def _optional(self, getter: Callable[[], Awaitable[Any]]) -> Any:
        """Run an informational getter, returning None if unsupported.

        Auth and transport errors still propagate so real outages are not
        masked.
        """
        try:
            return await getter()
        except (SoundbarAuthError, SoundbarConnectionError):
            raise
        except SoundbarApiError:
            return None

    async def status(self) -> dict[str, Any]:
        """Return a consolidated status dict.

        The individual queries are serialized by the request lock — the
        soundbar resets concurrent connections.
        """
        power, volume, mute, src, mode, codec, ident = await asyncio.gather(
            self.power_state(),
            self.volume(),
            self.is_muted(),
            self.input(),
            self.sound_mode(),
            self._optional(self.codec),
            self._optional(self.identifier),
        )
        return {
            "power": power,
            "volume": volume,
            "mute": mute,
            "input": src,
            "sound_mode": mode,
            "codec": codec,
            "identifier": ident,
        }
