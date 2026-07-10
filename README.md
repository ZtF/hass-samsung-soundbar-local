# Samsung Soundbar **Local** – Home Assistant Integration

> **Local IP control for 2024-line Samsung Wi-Fi soundbars**  
> HW-Q990D · HW-Q800D · HW-QS730D · HW-S800D · HW-S801D · HW-S700D · HW-S60D · HW-S61D · HW-LS60D

---

## What is it?

`soundbar_local` is a custom Home Assistant component that talks **directly** to your 2024 Samsung soundbar over the LAN (TCP 1516, same JSON-RPC API used by the SmartThings app).  
No cloud, no SmartThings integration in Home Assistant – everything stays on your network.

### Key features

| Function | Details |
|----------|---------|
| Power control | `turn_on`, `turn_off` |
| Audio | volume **set / step / mute** |
| Subwoofer | woofer ± exposed as Home Assistant `button` entities |
| Inputs | HDMI1, HDMI2, E-ARC, ARC, Digital, Bluetooth, Wi-Fi |
| Sound modes | Standard, Surround, Game, Movie, Music, Clear Voice, DTS Virtual X, Adaptive |
| Attributes | current audio codec and device identifier exposed on the media player |
| Options | configurable polling interval (5–300 s) via the integration's **Configure** dialog |

The entity is exposed as `media_player.soundbar_<ipaddr>` and works with dashboards, automations and scripts just like any other media-player device.

---

## Supported models

* HW-Q990D  – HW-Q800D  – HW-QS730D  
* HW-S800D  – HW-S801D  – HW-S700D  – HW-S60D  – HW-S61D  – HW-LS60D

> Older (2023 and below) bars do **not** implement the same API and will **not** work.

---

## Requirements

* Home Assistant 2024.11 or newer
* Python 3.12 (bundled with HA OS / Container)
* Your soundbar **added to the Samsung SmartThings app, connected to Wi-Fi** and
  **“IP control” enabled** in the device settings.
  This setting allows the bar to produce an *Access Token* that the integration uses.

> The soundbar exposes its API over HTTPS using a self-signed certificate, so
> TLS verification is disabled by default. You can enable verification in the
> config flow if you have configured a trusted CA on your network.

---

## Installation

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=ZtF&repository=hass-samsung-soundbar-local&category=integration)


1. **Download the latest ZIP** from the [releases](https://github.com/ZtF/hass-samsung-soundbar-local/releases) page.  
2. Unzip to `<config>/custom_components/`
3. Restart Home Assistant.  
4. Go to **Settings → Devices & Services → + Add Integration**, search for  
**“Samsung Soundbar Local”**, enter the soundbar’s IP address and confirm.
