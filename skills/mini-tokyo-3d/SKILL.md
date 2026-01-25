---
name: mini-tokyo-3d
description: Guide for integrating and customizing Mini Tokyo 3D - a real-time 3D digital map visualization of Tokyo's public transportation system. Use when building transit visualizations, embedding Tokyo train maps, or working with GTFS real-time data and Mapbox GL integration.
---

# Mini Tokyo 3D - Integration Guide

Real-time 3D visualization of Tokyo's public transportation system including trains, subways, and aircraft.

## When to Use This Skill

- Building real-time transportation visualizations
- Integrating Tokyo transit data into web applications
- Creating interactive 3D map experiences
- Working with GTFS data and live train positions
- Developing travel or tourism applications for Tokyo

## Prerequisites

### Required API Tokens

1. **Mapbox Access Token** - [mapbox.com](https://www.mapbox.com/) (Free tier: 50K/month)
2. **ODPT Token** - [developer-tokyochallenge.odpt.org](https://developer-tokyochallenge.odpt.org/)
3. **Challenge 2025 Token** - Also from ODPT portal

## Quick Start

### CDN Integration

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/mini-tokyo-3d@latest/dist/mini-tokyo-3d.min.css" />
  <script src="https://cdn.jsdelivr.net/npm/mini-tokyo-3d@latest/dist/mini-tokyo-3d.min.js"></script>
  <style>body { margin: 0; } #map { width: 100vw; height: 100vh; }</style>
</head>
<body>
  <div id="map"></div>
  <script>
    const map = new mt3d.Map({
      container: 'map',
      accessToken: '<MAPBOX_TOKEN>',
      secrets: {
        odpt: '<ODPT_TOKEN>',
        challenge2025: '<CHALLENGE_2025_TOKEN>'
      }
    });
  </script>
</body>
</html>
```

### NPM Integration

```bash
npm install mini-tokyo-3d
```

```javascript
import { Map } from 'mini-tokyo-3d';
import 'mini-tokyo-3d/dist/mini-tokyo-3d.min.css';

const map = new Map({
  container: 'map',
  accessToken: process.env.MAPBOX_TOKEN,
  secrets: {
    odpt: process.env.ODPT_TOKEN,
    challenge2025: process.env.CHALLENGE_2025_TOKEN
  }
});
```

## Constructor Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `container` | string | **required** | HTML element ID |
| `accessToken` | string | **required** | Mapbox token |
| `secrets` | Object | - | `{odpt, challenge2025}` tokens |
| `center` | [lng, lat] | [139.7670, 35.6814] | Initial center |
| `zoom` | number | 14 | Zoom level (0-22) |
| `pitch` | number | 60 | Tilt angle (0-85) |
| `bearing` | number | 0 | Rotation degrees |
| `lang` | string | browser | Language code |
| `ecoMode` | string | 'normal' | 'normal' or 'eco' |
| `plugins` | Array | [] | Plugin instances |

**Languages**: `ja`, `en`, `ko`, `zh-Hans`, `zh-Hant`, `th`, `ne`, `pt-BR`, `fr`, `es`, `de`

## Core API Reference

For detailed API documentation, see:
- [API Methods](references/api-methods.md) - Camera, selection, mode control
- [Events](references/events.md) - Event types and handlers
- [Examples](references/examples.md) - Common use cases

### Quick Method Reference

```javascript
// Camera
map.flyTo({ center: [139.7454, 35.6586], zoom: 16 });
map.setCenter([lng, lat]);
map.setPitch(45);
map.setBearing(90);

// Selection & Tracking
map.setSelection('JR-East.Yamanote.Outbound.1234');  // Track train
map.setSelection('Shibuya');  // Select station
map.setTrackingMode('helicopter');  // 'position'|'back'|'front'|'helicopter'|'drone'|'bird'

// Modes
map.setViewMode('underground');  // 'ground' or 'underground'
map.setClockMode('playback');    // 'realtime' or 'playback'
map.setEcoMode('eco');           // 'normal' or 'eco'

// Events
map.on('load', () => console.log('Ready'));
map.on('selection', (e) => console.log(e.selection));
```

## Plugins

```html
<script src="https://cdn.jsdelivr.net/npm/mini-tokyo-3d-plugin-precipitation@latest/dist/mini-tokyo-3d-plugin-precipitation.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/mini-tokyo-3d-plugin-fireworks@latest/dist/mini-tokyo-3d-plugin-fireworks.min.js"></script>
```

```javascript
const map = new mt3d.Map({
  plugins: [mt3dPrecipitation(), mt3dFireworks()]
});
```

## Resources

- **GitHub**: [github.com/nagix/mini-tokyo-3d](https://github.com/nagix/mini-tokyo-3d)
- **Demo**: [minitokyo3d.com](https://minitokyo3d.com)
- **License**: MIT
