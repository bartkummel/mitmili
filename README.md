# Man in the Middle Light

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

![Man in the Middle Light](icons/icon.png)

A Home Assistant custom integration that creates proxy entities for controlling lights through an override system. 
This integration allows you to maintain both a default light state and an override state, switching between them with 
a simple toggle.

## Table of Contents

- [Overview](#overview)
- [Use Cases](#use-cases)
- [Installation](#installation)
  - [HACS (Recommended)](#hacs-recommended)
  - [Manual Installation](#manual-installation)
- [Configuration](#configuration)
- [How It Works](#how-it-works)
- [Entities Created](#entities-created)
- [Usage Examples](#usage-examples)
- [Troubleshooting](#troubleshooting)

## Overview

Man in the Middle Light creates a proxy layer between your automations and physical lights, giving you the ability to 
temporarily override the default behavior without disrupting your existing automations.

When you set up this integration for a light, it creates:
- A **Proxy Light** - represents the default/normal state
- An **Override Light** - represents the temporary override state
- An **Overridden Switch** - controls which light is active

Point your automations at the Proxy Light for normal operation, and use the Override Light when you want manual control.
Toggle the Overridden Switch to switch between them.

## Use Cases

The use case this integration was built for, is the following: I have an automation to turn off some lights as soon as
my media player starts playing. This is so the room is a bit darker when watching a movie. However, I also use scenes,
and that can be problematic. E.g. when a scene is activated during playback: the light turns on again. This Man in the
Middle Light solves that. The automation can now just turn the switch to overridden, while the scenes apply to the 
proxy. As long as the overridden switch is on, the light will stay off. As soon as the switch is turned off again, the
light will go back to the state of the currently active scene, even if the scene changed during the movie playback.

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click on "Integrations"
3. Click the three dots in the top right corner and select "Custom repositories"
4. Add this repository URL: `https://github.com/bartkummel/mitmili`
5. Select "Integration" as the category
6. Click "Add"
7. Search for "Man in the Middle Light" in HACS
8. Click "Download"
9. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/mitmili` directory to your Home Assistant's `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "Man in the Middle Light"
4. Select the source light entity you want to proxy
5Click **Submit**

You can modify the source light entity later through the integration's options.

## How It Works

The integration creates a proxy layer with three entities:

```
┌─────────────────────────────────────────────────┐
│                 Your Automations                │
│                       ↓                         │
│         ┌─────────────────────────┐             │
│         │   Overridden Switch     │             │
│         │   (OFF/ON)              │             │
│         └─────────────────────────┘             │
│           ↓                     ↓               │
│   ┌──────────────┐      ┌──────────────┐        │
│   │ Proxy Light  │      │Override Light│        │
│   │ (Default)    │      │  (Manual)    │        │
│   └──────────────┘      └──────────────┘        │
│           ↓                     ↓               │
│           └───────────┬─────────┘               │
│                       ↓                         │
│              ┌─────────────────┐                │
│              │  Physical Light │                │
│              └─────────────────┘                │
└─────────────────────────────────────────────────┘
```

- When **Overridden Switch is OFF**: Changes to the Proxy Light control the physical light
- When **Overridden Switch is ON**: Changes to the Override Light control the physical light
- Both lights maintain their individual states, so switching back and forth applies whichever light's state is active

## Entities Created

For each configured integration, three entities are created:

### 1. Proxy Light (`light.<name>_proxy`)

The default light entity. Point your automations and scenes at this entity. When the overridden switch is off, changes
to this entity control the physical light.

**Supported Features**: Inherits all capabilities from the source light (brightness, color, color temperature, 
effects, etc.)

### 2. Override Light (`light.<name>_override`)

The manual override entity. Use this in your dashboards or manual controls. When the overridden switch is on, changes 
to this entity control the physical light. If you just want the light to be off when overridden, you can leave this
as is and not add it to any dashboard.

**Supported Features**: Same as the proxy light

### 3. Overridden Switch (`switch.<name>_overridden`)

Controls which light is active:
- **OFF**: Proxy Light is active (default/automated mode)
- **ON**: Override Light is active (manual/override mode)

## Usage Examples

### Example: Media Player Override

This example shows the main use case: preventing scenes from changing lights during movie playback.

**Scene** (controls the Proxy Light):
```yaml
scene:
  - name: "Evening"
    entities:
      light.living_room_proxy:
        state: on
        brightness: 200
        color_temp: 370

  - name: "Night"
    entities:
      light.living_room_proxy:
        state: on
        brightness: 50
        color_temp: 454
```

**Automation** (enables override during playback):
```yaml
automation:
  - alias: "Lights Off When Playing"
    trigger:
      - platform: state
        entity_id: media_player.living_room_tv
        to: "playing"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.living_room_overridden

  - alias: "Lights Resume After Playing"
    trigger:
      - platform: state
        entity_id: media_player.living_room_tv
        from: "playing"
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.living_room_overridden
```

**How it works:**
1. Your scenes control the `light.living_room_proxy` entity
2. When the media player starts playing, the automation turns on the `switch.living_room_overridden` and turns off 
   the `light.living_room_override`
3. While the switch is on, any scene changes only affect the proxy light - the physical light stays off
4. When playback stops, the automation turns off the switch, and the physical light immediately returns to whatever 
   state the proxy light is in (which reflects the currently active scene)

## Troubleshooting

### Source Light Not Found Warning

If you see a warning like "Source light entity 'light.xxx' not found yet" in your logs:

- This is normal if the source light loads after this integration
- The proxy entities will appear as unavailable until the source light is ready
- No action needed - they'll become available automatically

## Contributing

Issues and pull requests are welcome on the [GitHub repository](https://github.com/bartkummel/mitmili).

## License

This integration is provided as-is under the [BSD Zero Clause License](LICENSE.txt).

## Credits

Developed by [@bartkummel](https://github.com/bartkummel)

## Support

If you find this integration useful, consider starring the repository or contributing to its development.
