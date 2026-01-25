# Mini Tokyo 3D - API Methods Reference

## Camera Control

### jumpTo(options)
Instant view transition without animation.

```javascript
map.jumpTo({
  center: [139.7454, 35.6586],  // Shibuya
  zoom: 16,
  bearing: 45,
  pitch: 70
});
```

### easeTo(options)
Smooth animated transition.

```javascript
map.easeTo({
  center: [139.7016, 35.6895],  // Shinjuku
  zoom: 15,
  duration: 2000  // milliseconds
});
```

### flyTo(options)
Flight-path animation with zooming effect.

```javascript
map.flyTo({
  center: [139.7671, 35.6812],  // Tokyo Station
  zoom: 17,
  speed: 0.8
});
```

### Getters & Setters

| Method | Returns | Description |
|--------|---------|-------------|
| `getCenter()` | LngLat | Current center coordinates |
| `setCenter([lng, lat])` | Map | Set center position |
| `getZoom()` | number | Current zoom level |
| `setZoom(zoom)` | Map | Set zoom (0-22) |
| `getBearing()` | number | Current rotation |
| `setBearing(degrees)` | Map | Set rotation |
| `getPitch()` | number | Current tilt |
| `setPitch(degrees)` | Map | Set tilt (0-85) |

## Selection & Tracking

### setSelection(id)
Track a train/flight or select a station.

```javascript
// Track train by ID
map.setSelection('JR-East.Yamanote.Outbound.1234');

// Select station
map.setSelection('Shibuya');
map.setSelection('Tokyo');
map.setSelection('Shinjuku');
```

### getSelection()
Returns current tracked/selected items.

```javascript
const selection = map.getSelection();
// Returns: { trains: [...], flights: [...], stations: [...] }
```

### setTrackingMode(mode)
Set camera perspective when following a train.

**Available Modes**:
- `position` - Fixed overhead view
- `back` - Behind the train
- `topback` - Elevated behind view
- `front` - Ahead of the train
- `topfront` - Elevated front view
- `helicopter` - Circling helicopter view
- `drone` - Low-altitude following
- `bird` - High-altitude bird's eye

```javascript
map.setTrackingMode('helicopter');
```

## Mode Control

### Clock Mode
```javascript
map.setClockMode('realtime');  // Live data
map.setClockMode('playback');  // Historical playback
map.getClockMode();
```

### Eco Mode
```javascript
map.setEcoMode('normal');  // Full framerate
map.setEcoMode('eco');     // Battery saver
map.getEcoMode();
```

### View Mode
```javascript
map.setViewMode('ground');      // Surface view
map.setViewMode('underground'); // Subway view
map.getViewMode();
```

### hasDarkBackground()
Check if current map style has dark background (for UI theming).

```javascript
if (map.hasDarkBackground()) {
  document.body.classList.add('dark-theme');
}
```

## Layer Management

### addLayer(layer)
Add a custom map layer.

```javascript
map.addLayer({
  id: 'custom-layer',
  type: 'fill',
  source: 'custom-source',
  paint: { 'fill-color': '#ff0000' }
});
```

### removeLayer(id)
```javascript
map.removeLayer('custom-layer');
```

### setLayerVisibility(id, visibility)
```javascript
map.setLayerVisibility('custom-layer', 'visible');  // or 'none'
```

## Coordinate Conversion

### getModelPosition(lnglat, altitude)
Convert geographic coordinates to model coordinates (origin: Tokyo Station).

```javascript
const modelPos = map.getModelPosition([139.7671, 35.6812], 100);
```

### getModelScale()
Get mercator scale factor for accurate positioning.

```javascript
const scale = map.getModelScale();
```

### getMapboxMap()
Access underlying Mapbox GL JS instance.

```javascript
const mapboxMap = map.getMapboxMap();
mapboxMap.addSource('custom', { type: 'geojson', data: geojson });
```
