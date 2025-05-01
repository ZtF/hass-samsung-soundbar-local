# Samsung Soundbar **Local** – Home Assistant Integration

> **Local IP control for 2024-line Samsung Wi-Fi soundbars**  
> HW-Q990D · HW-Q930D · HW-Q800D · HW-QS730D · HW-S800D · HW-S801D · HW-S700D · HW-S60D · HW-S61D · HW-LS60D

---

## What is it?

`soundbar_local` is a custom Home Assistant component that talks **directly** to your 2024 Samsung soundbar over the LAN (TCP 1516, same JSON-RPC API used by the SmartThings app).  
No cloud, no SmartThings integration in Home Assistant – everything stays on your network.

### Key features

| Function | Details |
|----------|---------|
| Power control | `turn_on`, `turn_off` |
| Audio | volume **set / step / mute** |
| Subwoofer | woofer ± (not presented to Home Assistant yet) |
| Inputs | HDMI1, E-ARC, ARC, Digital, Bluetooth, Wi-Fi |
| Sound modes | Standard, Surround, Game, Movie, Music, Clear Voice, DTS Virtual X, Adaptive |

The entity is exposed as `media_player.soundbar_<ipaddr>` and works with dashboards, automations and scripts just like any other media-player device.

---

## Supported models

* HW-Q990D  – HW-Q930D  – HW-Q800D  – HW-QS730D  
* HW-S800D  – HW-S801D  – HW-S700D  – HW-S60D  – HW-S61D  – HW-LS60D

> Older (2023 and below) bars do **not** implement the same API and will **not** work.

---

## Requirements

* Home Assistant 2023.12 or newer  
* Python 3.11 (bundled with HA OS / Container)  
* Your soundbar **added to the Samsung SmartThings app, connected to Wi-Fi** and  
  **“IP control” enabled** in the device settings.  
  This setting allows the bar to produce an *Access Token* that the integration uses.

---

## Installation

Preferably using HACS custom repo. Or...
1. **Download the latest ZIP** from the [releases](https://github.com/ZtF/hass-samsung-soundbar-local/releases) page.  
2. Unzip to `<config>/custom_components/`
3. Restart Home Assistant.  
4. Go to **Settings → Devices & Services → + Add Integration**, search for  
**“Samsung Soundbar Local”**, enter the soundbar’s IP address and confirm.
