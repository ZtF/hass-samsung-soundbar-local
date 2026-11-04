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
| Subwoofer | woofer ± (not presented to Home Assistant yet) |
| Inputs | HDMI1, E-ARC, ARC, Digital, Bluetooth, Wi-Fi |
| Sound modes | Standard, Surround, Game, Movie, Music, Clear Voice, DTS Virtual X, Adaptive |

The entity is exposed as `media_player.soundbar_<ipaddr>` and works with dashboards, automations and scripts just like any other media-player device.

---

## Supported models

* HW-Q990D  – HW-Q800D  – HW-QS730D  
* HW-S800D  – HW-S801D  – HW-S700D  – HW-S60D  – HW-S61D  – HW-LS60D

> Older (2023 and below) bars do **not** implement the same API and will **not** work.

---

## Requirements

* Home Assistant 2023.12 or newer  
* Python 3.11 (bundled with HA OS / Container)  
* Your soundbar added to SmartThings and connected to Wi-Fi. The integration needs
  access to its local API on port 1516. Enable **IP control** in SmartThings when
  that option is available for your model; some models do not expose it.

---

## Installation

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=ZtF&repository=hass-samsung-soundbar-local&category=integration)


1. **Download the latest ZIP** from the [releases](https://github.com/ZtF/hass-samsung-soundbar-local/releases) page.  
2. Unzip to `<config>/custom_components/`
3. Restart Home Assistant.  
4. Go to **Settings → Devices & Services → + Add Integration**, search for  
**“Samsung Soundbar Local”**, enter the soundbar’s IP address and confirm.

## Connection troubleshooting

Enter the **soundbar's** IP address, not the IP address of Home Assistant or your
router. Find it in your router's connected devices list or in Home Assistant's
**Settings → System → Network → DHCP Browser**. If setup cannot connect, check
that the soundbar and Home Assistant can reach each other on the local network,
then check for the **IP control** option in the soundbar's SmartThings settings.
The absence of that option can mean the model or firmware does not expose the
local API this integration needs. A successful connection does not guarantee
that every command is supported by that model.
