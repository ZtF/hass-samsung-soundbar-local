"""Focused tests that run without a Home Assistant installation."""

import asyncio
import importlib.util
import json
import sys
import types
import unittest
from contextlib import asynccontextmanager
from enum import IntFlag
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

ORIGINAL_SLEEP = asyncio.sleep


COMPONENT = Path(__file__).resolve().parents[1] / "custom_components/samsung_soundbar_local"


def module(name):
    result = types.ModuleType(name)
    sys.modules[name] = result
    return result


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, COMPONENT / filename)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


aiohttp = module("aiohttp")
aiohttp.ClientError = type("ClientError", (Exception,), {})
aiohttp.ClientSession = type("ClientSession", (), {})
async_timeout = module("async_timeout")
@asynccontextmanager
async def timeout(seconds):
    yield


async_timeout.timeout = timeout
vol = module("voluptuous")
vol.Schema = lambda schema: schema
vol.Required = lambda key: key
vol.Optional = lambda key, default=None: key

package = module("test_soundbar_component")
package.__path__ = [str(COMPONENT)]
const = module("test_soundbar_component.const")
const.DOMAIN = "soundbar_local"
const.CONF_VERIFY_SSL = "verify_ssl"
soundbar_module = load("test_soundbar_component.soundbar", "soundbar.py")

homeassistant = module("homeassistant")
homeassistant.__path__ = []
components = module("homeassistant.components")
components.__path__ = []
media = module("homeassistant.components.media_player")


class Features(IntFlag):
    TURN_ON = 1
    TURN_OFF = 2
    VOLUME_STEP = 4
    VOLUME_SET = 8
    VOLUME_MUTE = 16
    SELECT_SOURCE = 32
    SELECT_SOUND_MODE = 64


media.MediaPlayerEntityFeature = Features
media.MediaPlayerDeviceClass = types.SimpleNamespace(SPEAKER="speaker")
media.MediaPlayerEntity = type("MediaPlayerEntity", (), {})
config_entries = module("homeassistant.config_entries")


class ConfigFlow:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()

    async def async_set_unique_id(self, unique_id):
        self.unique_id = unique_id

    def _abort_if_unique_id_configured(self):
        pass

    def async_create_entry(self, **kwargs):
        return kwargs

    def async_show_form(self, **kwargs):
        return kwargs


config_entries.ConfigFlow = ConfigFlow
config_entries.ConfigEntry = type("ConfigEntry", (), {})
ha_const = module("homeassistant.const")
ha_const.CONF_HOST = "host"
ha_const.STATE_OFF = "off"
ha_const.STATE_ON = "on"
ha_core = module("homeassistant.core")
ha_core.callback = lambda fn: fn
data_entry_flow = module("homeassistant.data_entry_flow")
data_entry_flow.FlowResult = dict
helpers = module("homeassistant.helpers")
helpers.__path__ = []
helpers.aiohttp_client = types.SimpleNamespace(async_get_clientsession=lambda *a, **kw: object())
entity = module("homeassistant.helpers.entity")
entity.DeviceInfo = dict
coordinator_module = module("homeassistant.helpers.update_coordinator")
coordinator_module.CoordinatorEntity = type("CoordinatorEntity", (), {})

media_player_module = load("test_soundbar_component.media_player", "media_player.py")
config_flow_module = load("test_soundbar_component.config_flow", "config_flow.py")


class SoundbarStatusTests(unittest.IsolatedAsyncioTestCase):
    async def test_unsupported_optional_method_keeps_power_and_other_values(self):
        client = soundbar_module.AsyncSoundbar("192.0.2.1", object())
        client._token = "token"
        client.power_state = AsyncMock(return_value="powerOn")
        client.volume = AsyncMock(return_value=34)
        client.is_muted = AsyncMock(return_value=False)
        client.input = AsyncMock(side_effect=soundbar_module.SoundbarApiError("unsupported"))
        client.sound_mode = AsyncMock(return_value="STANDARD")
        client.codec = AsyncMock(return_value=None)
        client.identifier = AsyncMock(return_value="test")

        status = await client.status()

        self.assertEqual(status["power"], "powerOn")
        self.assertEqual(status["volume"], 34)
        self.assertIsNone(status["input"])
        self.assertEqual(status["sound_mode"], "STANDARD")

    async def test_power_failure_remains_fatal(self):
        client = soundbar_module.AsyncSoundbar("192.0.2.1", object())
        client._token = "token"
        client.power_state = AsyncMock(side_effect=soundbar_module.SoundbarApiError("offline"))
        with self.assertRaises(soundbar_module.SoundbarApiError):
            await client.status()


class MediaPlayerFeedbackTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.player = object.__new__(media_player_module.SoundbarLocalEntity)
        self.player._soundbar = Mock()
        self.player.coordinator = Mock(data={"power": "powerOn", "volume": 20, "mute": False})
        self.player.coordinator.async_request_refresh = AsyncMock()

    async def test_volume_readback_updates_only_changed_field(self):
        self.player._soundbar.volume_up = AsyncMock()
        self.player._soundbar.volume = AsyncMock(return_value=21)

        await self.player.async_volume_up()

        self.player.coordinator.async_set_updated_data.assert_called_once_with(
            {"power": "powerOn", "volume": 21, "mute": False}
        )
        self.player.coordinator.async_request_refresh.assert_not_called()

    async def test_mute_readback_updates_only_changed_field(self):
        self.player._soundbar.set_mute = AsyncMock()
        self.player._soundbar.is_muted = AsyncMock(return_value=True)

        await self.player.async_mute_volume(True)

        self.player.coordinator.async_set_updated_data.assert_called_once_with(
            {"power": "powerOn", "volume": 20, "mute": True}
        )

    async def test_failed_readback_falls_back_to_full_refresh(self):
        self.player._soundbar.volume_up = AsyncMock()
        self.player._soundbar.volume = AsyncMock(
            side_effect=soundbar_module.SoundbarApiError("unavailable")
        )

        await self.player.async_volume_up()

        self.player.coordinator.async_request_refresh.assert_awaited_once()
        self.player.coordinator.async_set_updated_data.assert_not_called()


class ConfigFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_reachable_host_creates_entry(self):
        flow = config_flow_module.SoundbarLocalConfigFlow()
        flow.hass = object()
        with patch.object(config_flow_module, "AsyncSoundbar") as client_class:
            client_class.return_value.create_token = AsyncMock(return_value="token")
            client_class.return_value.power_state = AsyncMock(return_value="powerOn")
            result = await flow.async_step_user({"host": "192.0.2.1"})

        self.assertEqual(result["data"], {"host": "192.0.2.1"})
        self.assertEqual(flow.unique_id, "192.0.2.1")
        client_class.return_value.power_state.assert_awaited_once()

    async def test_unreachable_host_shows_form_error(self):
        flow = config_flow_module.SoundbarLocalConfigFlow()
        flow.hass = object()
        with patch.object(config_flow_module, "AsyncSoundbar") as client_class:
            client_class.return_value.create_token = AsyncMock(
                side_effect=soundbar_module.SoundbarApiError("connection refused")
            )
            result = await flow.async_step_user({"host": "192.0.2.1"})

        self.assertEqual(result["errors"], {"base": "cannot_connect"})



class FakeResponse:
    def __init__(self, session, body):
        self.session = session
        self.body = body

    def raise_for_status(self):
        if isinstance(self.body, Exception):
            self.session.in_flight -= 1
            raise self.body

    async def text(self):
        await ORIGINAL_SLEEP(0)
        self.session.in_flight -= 1
        return self.body if isinstance(self.body, str) else json.dumps(self.body)


class FakeSession:
    def __init__(self, *bodies):
        self.bodies = list(bodies)
        self.payloads = []
        self.in_flight = 0
        self.max_in_flight = 0

    async def post(self, url, *, data, headers, ssl):
        self.payloads.append(json.loads(data))
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        return FakeResponse(self, self.bodies.pop(0))


def result(value):
    return {"jsonrpc": "2.0", "id": "1", "result": value}


def error(code, message="Method not found"):
    return {"jsonrpc": "2.0", "id": "1", "error": {"code": code, "message": message}}


class SoundbarProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_post_standard_error_code(self):
        client = soundbar_module.AsyncSoundbar("192.0.2.1", FakeSession(error(-32601)))
        with self.assertRaises(soundbar_module.SoundbarApiError) as caught:
            await client._post({})
        self.assertEqual(caught.exception.code, -32601)

    async def test_post_top_level_error_code(self):
        client = soundbar_module.AsyncSoundbar("192.0.2.1", FakeSession({"code": -32700, "message": "Parse error"}))
        with self.assertRaises(soundbar_module.SoundbarApiError) as caught:
            await client._post({})
        self.assertEqual(caught.exception.code, -32700)

    async def test_post_missing_result(self):
        client = soundbar_module.AsyncSoundbar("192.0.2.1", FakeSession({"jsonrpc": "2.0", "id": "1"}))
        with self.assertRaises(soundbar_module.SoundbarApiError) as caught:
            await client._post({})
        self.assertIsNone(caught.exception.code)

    async def test_post_invalid_json(self):
        client = soundbar_module.AsyncSoundbar("192.0.2.1", FakeSession("not JSON"))
        with self.assertRaises(soundbar_module.SoundbarApiError):
            await client._post({})

    async def test_post_client_error(self):
        client = soundbar_module.AsyncSoundbar("192.0.2.1", FakeSession(aiohttp.ClientError("offline")))
        with self.assertRaises(soundbar_module.SoundbarApiError):
            await client._post({})

    async def test_call_creates_token_and_injects_it(self):
        session = FakeSession(result({"AccessToken": "first"}), result({"volume": 29}))
        client = soundbar_module.AsyncSoundbar("192.0.2.1", session)
        self.assertEqual(await client._call("getVolume"), {"volume": 29})
        self.assertEqual([p["method"] for p in session.payloads], ["createAccessToken", "getVolume"])
        self.assertEqual(session.payloads[1]["params"]["AccessToken"], "first")

    async def test_call_reauthenticates_and_retries_once(self):
        session = FakeSession(result({"AccessToken": "first"}), {"code": -32700, "message": "Parse error"}, result({"AccessToken": "second"}), result({"volume": 29}))
        client = soundbar_module.AsyncSoundbar("192.0.2.1", session)
        with patch.object(soundbar_module.asyncio, "sleep", new=AsyncMock()):
            self.assertEqual(await client._call("getVolume"), {"volume": 29})
        self.assertEqual([p["method"] for p in session.payloads], ["createAccessToken", "getVolume", "createAccessToken", "getVolume"])
        self.assertEqual(session.payloads[-1]["params"]["AccessToken"], "second")

    async def test_call_second_failure_raises(self):
        session = FakeSession(result({"AccessToken": "first"}), {"code": -32700}, result({"AccessToken": "second"}), {"code": -32700})
        client = soundbar_module.AsyncSoundbar("192.0.2.1", session)
        with patch.object(soundbar_module.asyncio, "sleep", new=AsyncMock()):
            with self.assertRaises(soundbar_module.SoundbarApiError):
                await client._call("getVolume")
        self.assertEqual(len(session.payloads), 4)

    async def test_call_missing_method_does_not_retry(self):
        session = FakeSession(result({"AccessToken": "first"}), error(-32601))
        client = soundbar_module.AsyncSoundbar("192.0.2.1", session)
        with patch.object(soundbar_module.asyncio, "sleep", new=AsyncMock()) as sleep:
            with self.assertRaises(soundbar_module.SoundbarApiError):
                await client._call("getVolume")
        self.assertEqual([p["method"] for p in session.payloads], ["createAccessToken", "getVolume"])
        self.assertEqual(client._token, "first")
        sleep.assert_not_awaited()

    async def test_set_volume_absolute(self):
        session = FakeSession(result({"success": True}))
        client = soundbar_module.AsyncSoundbar("192.0.2.1", session)
        client._token = "token"
        await client.set_volume(29)
        self.assertEqual([p["method"] for p in session.payloads], ["volumeControl"])
        self.assertEqual(session.payloads[0]["params"]["volume"], 29)

    async def test_set_volume_falls_back_and_remembers(self):
        session = FakeSession(error(-32601), result({"volume": 2}), result({"success": True}), result({"volume": 3}), result({"success": True}))
        client = soundbar_module.AsyncSoundbar("192.0.2.1", session)
        client._token = "token"
        await client.set_volume(3)
        await client.set_volume(2)
        self.assertEqual([p["method"] for p in session.payloads], ["volumeControl", "getVolume", "remoteKeyControl", "getVolume", "remoteKeyControl"])
        self.assertEqual([session.payloads[i]["params"]["remoteKey"] for i in (2, 4)], ["VOL_UP", "VOL_DOWN"])

    async def test_set_volume_rejects_failure(self):
        client = soundbar_module.AsyncSoundbar("192.0.2.1", FakeSession(result({"success": False})))
        client._token = "token"
        with self.assertRaises(soundbar_module.SoundbarApiError):
            await client.set_volume(29)

    async def test_set_volume_rejects_out_of_range_without_request(self):
        session = FakeSession()
        client = soundbar_module.AsyncSoundbar("192.0.2.1", session)
        for level in (101, -1):
            with self.assertRaises(ValueError):
                await client.set_volume(level)
        self.assertEqual(session.payloads, [])

    async def test_set_mute_absolute(self):
        session = FakeSession(result({"success": True}))
        client = soundbar_module.AsyncSoundbar("192.0.2.1", session)
        client._token = "token"
        await client.set_mute(True)
        self.assertEqual([p["method"] for p in session.payloads], ["muteControl"])
        self.assertIs(session.payloads[0]["params"]["mute"], True)

    async def test_set_mute_fallback_toggles_only_when_needed(self):
        session = FakeSession(error(-32601), result({"mute": False}), result({"success": True}), result({"mute": True}))
        client = soundbar_module.AsyncSoundbar("192.0.2.1", session)
        client._token = "token"
        await client.set_mute(True)
        await client.set_mute(True)
        self.assertEqual([p["method"] for p in session.payloads], ["muteControl", "getMute", "remoteKeyControl", "getMute"])
        self.assertFalse(client._mute_control_supported)

    async def test_set_mute_rejects_failure(self):
        client = soundbar_module.AsyncSoundbar("192.0.2.1", FakeSession(result({"success": False})))
        client._token = "token"
        with self.assertRaises(soundbar_module.SoundbarApiError):
            await client.set_mute(True)

    async def test_status_and_volume_up_serialize_requests(self):
        session = FakeSession(result({"power": "powerOn"}), result({"volume": 30}), result({"mute": False}), result({"inputSource": "BT"}), result({"soundMode": "STANDARD"}), result({"codec": "AAC"}), result({"identifier": "device"}), result({"success": True}))
        client = soundbar_module.AsyncSoundbar("192.0.2.1", session)
        client._token = "token"
        await asyncio.gather(client.status(), client.volume_up())
        self.assertEqual(session.max_in_flight, 1)

    async def test_status_reads_sequentially_and_keeps_other_values(self):
        session = FakeSession(result({"power": "powerOn"}), result({"volume": 30}), result({"mute": False}), error(-32601), result({"soundMode": "STANDARD"}), result({"codec": "AAC"}), result({"identifier": "device"}))
        client = soundbar_module.AsyncSoundbar("192.0.2.1", session)
        client._token = "token"
        status = await client.status()
        self.assertEqual(status["power"], "powerOn")
        self.assertEqual(status["volume"], 30)
        self.assertIsNone(status["input"])
        self.assertEqual(status["sound_mode"], "STANDARD")
        self.assertEqual([p["method"] for p in session.payloads], ["powerControl", "getVolume", "getMute", "inputSelectControl", "soundModeControl", "getCodec", "getIdentifier"])

    async def test_status_power_failure_raises(self):
        session = FakeSession(error(-32601))
        client = soundbar_module.AsyncSoundbar("192.0.2.1", session)
        client._token = "token"
        with self.assertRaises(soundbar_module.SoundbarApiError):
            await client.status()
        self.assertEqual(len(session.payloads), 1)


class MediaPlayerAbsoluteControlTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.player = object.__new__(media_player_module.SoundbarLocalEntity)
        self.player._soundbar = Mock()
        self.player.coordinator = Mock(data={"power": "powerOn", "volume": 20, "mute": None})
        self.player.coordinator.async_request_refresh = AsyncMock()

    async def test_set_volume_level_rounds_to_29(self):
        self.player._soundbar.set_volume = AsyncMock()
        self.player._soundbar.volume = AsyncMock(return_value=29)
        await self.player.async_set_volume_level(0.29)
        self.player._soundbar.set_volume.assert_awaited_once_with(29)

    async def test_mute_sets_even_when_state_unknown_and_reads_back(self):
        self.player._soundbar.set_mute = AsyncMock()
        self.player._soundbar.is_muted = AsyncMock(return_value=True)
        await self.player.async_mute_volume(True)
        self.player._soundbar.set_mute.assert_awaited_once_with(True)
        self.player.coordinator.async_set_updated_data.assert_called_once_with({"power": "powerOn", "volume": 20, "mute": True})

    async def test_failed_mute_readback_requests_full_refresh(self):
        self.player._soundbar.set_mute = AsyncMock()
        self.player._soundbar.is_muted = AsyncMock(side_effect=soundbar_module.SoundbarApiError("unavailable"))
        await self.player.async_mute_volume(True)
        self.player.coordinator.async_request_refresh.assert_awaited_once()
        self.player.coordinator.async_set_updated_data.assert_not_called()

if __name__ == "__main__":
    unittest.main()
