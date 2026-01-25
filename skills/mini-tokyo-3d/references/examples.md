# Mini Tokyo 3D - Examples

## Tourist Information App

```javascript
const map = new mt3d.Map({
  container: 'map',
  accessToken: '<token>',
  secrets: { odpt: '<token>', challenge2025: '<token>' },
  lang: 'en',
  center: [139.7671, 35.6812],  // Tokyo Station
  zoom: 15,
  pitch: 60,
  bearing: -20,
  searchControl: true,
  fullscreenControl: true
});

// Auto-tour of popular stations
const tourSpots = [
  { id: 'Tokyo', name: 'Tokyo Station' },
  { id: 'Shibuya', name: 'Shibuya Crossing' },
  { id: 'Shinjuku', name: 'Shinjuku Hub' },
  { id: 'Akihabara', name: 'Electric Town' }
];

tourSpots.forEach((spot, i) => {
  setTimeout(() => {
    map.setSelection(spot.id);
    map.flyTo({ zoom: 16, duration: 3000 });
  }, i * 5000);
});
```

## Real-time Monitoring Dashboard

```javascript
const map = new mt3d.Map({
  container: 'map',
  accessToken: '<token>',
  secrets: { odpt: '<token>', challenge2025: '<token>' },
  clockControl: true,
  configControl: false,  // Hide for kiosk mode
  modeControl: true,
  ecoMode: 'normal',
  trackingMode: 'helicopter'
});

// Monitor selected train
map.on('load', () => {
  setInterval(() => {
    const selection = map.getSelection();
    if (selection.trains.length > 0) {
      updateDashboard(selection.trains);
    }
  }, 5000);
});

// Subway monitoring button
document.getElementById('subway-btn').addEventListener('click', () => {
  map.setViewMode('underground');
});
```

## Embedded Widget (Minimal UI)

```javascript
const map = new mt3d.Map({
  container: 'mini-map',
  accessToken: '<token>',
  secrets: { odpt: '<token>', challenge2025: '<token>' },
  // Disable all controls
  clockControl: false,
  configControl: false,
  fullscreenControl: false,
  modeControl: false,
  navigationControl: false,
  searchControl: false,
  // Fixed view
  center: [139.7671, 35.6812],
  zoom: 16,
  pitch: 45,
  bearing: 0
});
```

## Custom GTFS Integration

```javascript
const map = new mt3d.Map({
  container: 'map',
  accessToken: '<token>',
  // Custom transit data sources
  dataSources: [{
    url: 'https://your-gtfs-server.com/data',
    type: 'gtfs'
  }]
});
```

## Dynamic Theme Switching

```javascript
map.on('load', () => {
  updateTheme();
});

function updateTheme() {
  const isDark = map.hasDarkBackground();
  document.body.classList.toggle('dark-theme', isDark);

  // Update UI elements
  document.querySelectorAll('.panel').forEach(el => {
    el.style.backgroundColor = isDark ? '#1a1a2e' : '#ffffff';
    el.style.color = isDark ? '#ffffff' : '#333333';
  });
}
```

## Mobile Optimization

```javascript
// Detect mobile and enable eco mode
if (/Mobi|Android/i.test(navigator.userAgent)) {
  map.setEcoMode('eco');
}

// Lazy load map when visible
const observer = new IntersectionObserver((entries) => {
  if (entries[0].isIntersecting) {
    initMap();
    observer.disconnect();
  }
});
observer.observe(document.getElementById('map'));
```

## Weather Plugin Integration

```html
<script src="https://cdn.jsdelivr.net/npm/mini-tokyo-3d-plugin-precipitation@latest/dist/mini-tokyo-3d-plugin-precipitation.min.js"></script>
```

```javascript
const map = new mt3d.Map({
  container: 'map',
  accessToken: '<token>',
  secrets: { odpt: '<token>', challenge2025: '<token>' },
  plugins: [mt3dPrecipitation()]
});
```

## Festive Effects

```html
<script src="https://cdn.jsdelivr.net/npm/mini-tokyo-3d-plugin-fireworks@latest/dist/mini-tokyo-3d-plugin-fireworks.min.js"></script>
```

```javascript
const map = new mt3d.Map({
  container: 'map',
  plugins: [mt3dFireworks()]
});
```

## Container Styling

```css
#map {
  width: 100%;
  height: 100vh;
  position: relative;
}

/* Dark mode overlay */
#map.dark-mode::after {
  content: '';
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  pointer-events: none;
}

/* Custom control positioning */
.mapboxgl-ctrl-top-right {
  top: 60px;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .mapboxgl-ctrl-group {
    transform: scale(0.85);
  }
}
```

## Troubleshooting

### Map Not Loading
- Verify Mapbox token is valid
- Check CORS settings if self-hosting data
- Ensure container element exists before initialization

### No Train Data
- Verify ODPT and Challenge 2025 tokens
- Check browser console for API errors
- Tokens may need yearly renewal

### Performance Issues
- Enable eco mode: `map.setEcoMode('eco')`
- Reduce visible layers
- Use lower zoom levels for overview

### Underground View Issues
- Call `setViewMode('underground')` after load event
- Some stations may not have underground data
