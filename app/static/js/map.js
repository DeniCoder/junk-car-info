/* ═══════════════════════════════════════════
   БРОШЕННАЯ ТЕХНИКА — Map Controller
   ═══════════════════════════════════════════ */

(function () {
    'use strict';

    var map = L.map('map', {
        center: [55.75, 37.62],
        zoom: 5,
        zoomControl: false,
        attributionControl: false
    });

    L.control.zoom({ position: 'topright' }).addTo(map);
    L.control.attribution({ position: 'bottomright', prefix: false }).addTo(map);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap',
        maxZoom: 19
    }).addTo(map);

    var markers = L.markerClusterGroup({
        maxClusterRadius: 50,
        iconCreateFunction: function (cluster) {
            var count = cluster.getChildCount();
            var cls = 'marker-cluster';
            if (count >= 20) cls += ' marker-cluster-large';
            else if (count >= 5) cls += ' marker-cluster-medium';
            else cls += ' marker-cluster-small';
            return L.divIcon({ className: cls, html: '<span>' + count + '</span>', iconSize: [36, 36] });
        }
    });
    map.addLayer(markers);

    var currentCategory = 'all';
    var loadedMarkers = {};

    function createMarkerIcon(finding) {
        var cls = 'marker-icon';
        if (finding.status === 'hidden') cls += ' status-hidden';
        return L.divIcon({
            className: cls,
            iconSize: [28, 28],
            iconAnchor: [14, 28],
            popupAnchor: [0, -28],
            html: '',
            data: { category: finding.category_id }
        });
    }

    function loadFindings() {
        var bounds = map.getBounds();
        var bbox = bounds.getSouth() + ',' + bounds.getWest() + ',' + bounds.getNorth() + ',' + bounds.getEast();
        var url = '/api/findings?bbox=' + bbox + '&status=published';
        if (currentCategory !== 'all') {
            url += '&category_id=' + currentCategory;
        }

        fetch(url)
            .then(function (r) { return r.json(); })
            .then(function (data) {
                markers.clearLayers();
                loadedMarkers = {};
                var count = data.count || 0;
                var counterEl = document.getElementById('totalFindings');
                if (counterEl) counterEl.textContent = count;

                var emptyState = document.getElementById('emptyState');
                if (emptyState) {
                    emptyState.style.display = count === 0 ? 'block' : 'none';
                }

                (data.findings || []).forEach(function (f) {
                    var icon = createMarkerIcon(f);
                    var marker = L.marker([f.lat, f.lon], { icon: icon });

                    var statusText = f.status === 'published' ? 'НА МЕСТЕ' : 'УВЕЗЛИ';
                    var statusColor = f.status === 'published' ? '#6F7A52' : '#E3B53E';
                    var thumbHtml = f.thumb_url ? '<img src="' + f.thumb_url + '" style="width:100%;height:120px;object-fit:cover;margin-bottom:8px;border:1px solid #38302A;">' : '';

                    var popupHtml =
                        '<div class="popup-title">' + escapeHtml(f.location_name || f.sub_type || 'Находка') + '</div>' +
                        '<div class="popup-location">' + f.lat.toFixed(6) + ', ' + f.lon.toFixed(6) + '</div>' +
                        '<div class="popup-status" style="color:' + statusColor + '">' + statusText + '</div>' +
                        thumbHtml +
                        '<a class="popup-link" href="/finding/' + f.id + '">ПОДРОБНЕЕ →</a>';

                    marker.bindPopup(popupHtml, { maxWidth: 280, className: '' });
                    marker.on('click', function () {
                        map.setView([f.lat, f.lon], Math.max(map.getZoom(), 12));
                    });
                    markers.addLayer(marker);
                    loadedMarkers[f.id] = marker;
                });
            })
            .catch(function (err) {
                console.error('Failed to load findings:', err);
            });
    }

    function escapeHtml(text) {
        var div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    map.on('moveend', loadFindings);
    map.on('zoomend', loadFindings);

    // Initial load
    loadFindings();

    // Category filter
    var legendItems = document.querySelectorAll('.legend-item');
    legendItems.forEach(function (item) {
        item.addEventListener('click', function () {
            legendItems.forEach(function (el) { el.classList.remove('active'); });
            item.classList.add('active');
            currentCategory = item.dataset.category;
            loadFindings();
        });
    });

    // Legend toggle
    var legendToggle = document.getElementById('legendToggle');
    var legendPanel = document.getElementById('legendPanel');
    if (legendToggle && legendPanel) {
        legendToggle.addEventListener('click', function () {
            legendPanel.classList.toggle('open');
        });
    }

    // Search
    var searchInput = document.getElementById('searchInput');
    if (searchInput) {
        var searchTimeout;
        searchInput.addEventListener('input', function () {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(function () {
                var q = searchInput.value.trim().toLowerCase();
                if (q.length < 2) {
                    loadFindings();
                    return;
                }
                // Simple client-side filter for visible markers
                markers.eachLayer(function (layer) {
                    if (layer.getPopup) {
                        var popup = layer.getPopup();
                        if (popup && popup.getContent) {
                            var content = popup.getContent();
                            if (typeof content === 'string' && content.toLowerCase().indexOf(q) === -1) {
                                markers.removeLayer(layer);
                            }
                        }
                    }
                });
            }, 300);
        });
    }

    // Expose map for other modules
    window.__map = map;
    window.__loadFindings = loadFindings;

    // Store for picking location
    window.__mapClickMode = false;
    window.__mapClickCallback = null;

    map.on('click', function (e) {
        if (window.__mapClickMode && window.__mapClickCallback) {
            window.__mapClickCallback(e.latlng.lat, e.latlng.lng);
        }
    });

})();
