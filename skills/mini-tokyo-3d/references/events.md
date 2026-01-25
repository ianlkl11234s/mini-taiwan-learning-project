# Mini Tokyo 3D - Events Reference

## Event Handling

### on(type, listener)
Register an event listener.

```javascript
map.on('load', () => {
  console.log('Map fully loaded');
});

map.on('click', (e) => {
  console.log('Clicked at:', e.lngLat);
});
```

### once(type, listener)
One-time event listener.

```javascript
map.once('selection', (e) => {
  console.log('First selection:', e.selection);
});
```

### off(type, listener)
Remove event listener.

```javascript
const handler = (e) => console.log(e);
map.on('click', handler);
map.off('click', handler);
```

## Event Types

### Map Interaction Events

| Event | Description | Properties |
|-------|-------------|------------|
| `click` | Map click | lngLat, point |
| `dblclick` | Double click | lngLat, point |
| `contextmenu` | Right click | lngLat, point |
| `mousedown` | Mouse button down | lngLat, point |
| `mousemove` | Mouse movement | lngLat, point |
| `mouseover` | Mouse enters map | lngLat, point |
| `mouseup` | Mouse button up | lngLat, point |
| `wheel` | Scroll wheel | delta |
| `resize` | Map resized | - |

### Drag Events

| Event | Description |
|-------|-------------|
| `dragstart` | Drag begins |
| `drag` | Dragging |
| `dragend` | Drag ends |
| `boxzoomstart` | Shift+drag zoom starts |
| `boxzoomcancel` | Box zoom cancelled |
| `boxzoomend` | Box zoom ends |
| `rotatestart` | Rotation begins |
| `rotate` | Rotating |
| `rotateend` | Rotation ends |

### View Change Events

| Event | Description |
|-------|-------------|
| `movestart` | View movement begins |
| `move` | View moving |
| `moveend` | View movement ends |
| `zoomstart` | Zoom begins |
| `zoom` | Zooming |
| `zoomend` | Zoom ends |
| `pitchstart` | Tilt begins |
| `pitch` | Tilting |
| `pitchend` | Tilt ends |

### Touch Events

| Event | Description |
|-------|-------------|
| `touchstart` | Touch begins |
| `touchmove` | Touch moving |
| `touchend` | Touch ends |
| `touchcancel` | Touch cancelled |

### Mode Change Events

```javascript
map.on('clockmode', (e) => {
  console.log('Clock mode:', e.mode);  // 'realtime' or 'playback'
});

map.on('ecomode', (e) => {
  console.log('Eco mode:', e.mode);  // 'normal' or 'eco'
});

map.on('trackingmode', (e) => {
  console.log('Tracking mode:', e.mode);
});

map.on('viewmode', (e) => {
  console.log('View mode:', e.mode);  // 'ground' or 'underground'
});
```

### Selection Events

```javascript
// Fired when train/flight/station is tracked/selected
map.on('selection', (e) => {
  console.log('Selected trains:', e.selection.trains);
  console.log('Selected flights:', e.selection.flights);
  console.log('Selected stations:', e.selection.stations);
});

// Fired when tracking/selection is cancelled
map.on('deselection', () => {
  console.log('Selection cleared');
});
```

### System Events

```javascript
// Map fully rendered and ready
map.on('load', () => {
  console.log('Map ready');
});

// Error occurred
map.on('error', (e) => {
  console.error('Map error:', e.message);
});
```

## Common Patterns

### Wait for Load

```javascript
map.on('load', () => {
  // Safe to call API methods here
  map.setSelection('Tokyo');
});
```

### Track User Interactions

```javascript
map.on('selection', (e) => {
  // Analytics tracking
  analytics.track('train_selected', {
    trainId: e.selection.trains[0]?.id,
    stationId: e.selection.stations[0]?.id
  });
});
```

### Sync UI State

```javascript
map.on('viewmode', (e) => {
  document.querySelector('#underground-toggle').checked = (e.mode === 'underground');
});

map.on('ecomode', (e) => {
  document.querySelector('#eco-toggle').checked = (e.mode === 'eco');
});
```
