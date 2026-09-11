/* ═══════════════════════════════════════════
   БРОШЕННАЯ ТЕХНИКА — Map Controller
   ═══════════════════════════════════════════ */

(function () {
    'use strict';

    var map = L.map('map', {
        center: [20, 0],
        zoom: 3,
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
    var searchInput = document.getElementById('searchInput');

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

    // Store popup timeout ref for hover behavior
    var popupTimeout = null;

    function addPopupEvents(marker, finding) {
        var statusText = 'НА МЕСТЕ';
        var statusColor = '#6F7A52';

        var thumbHtml = finding.thumb_url
            ? '<img src="' + finding.thumb_url + '" style="width:100%;height:120px;object-fit:cover;margin-bottom:8px;border:1px solid #38302A;">'
            : '';

        var popupHtml =
            '<div class="popup-title">' + escapeHtml(finding.location_name || finding.sub_type || 'Находка') + '</div>' +
            '<div class="popup-location">' + finding.lat.toFixed(6) + ', ' + finding.lon.toFixed(6) + '</div>' +
            '<div class="popup-status" style="color:' + statusColor + '">' + statusText + '</div>' +
            thumbHtml +
            '<a class="popup-link" href="/finding/' + finding.id + '">ПОДРОБНЕЕ \u2192</a>';

        marker.bindPopup(popupHtml, {
            maxWidth: 280,
            autoPanPadding: [50, 50],
            closeOnClick: false,
            autoPan: true
        });

        marker.on('mouseover', function () {
            clearTimeout(popupTimeout);
            marker.openPopup();
        });

        marker.on('mouseout', function () {
            // Long delay — cancelled if mouse enters popup
            popupTimeout = setTimeout(function () {
                marker.closePopup();
            }, 600);
        });

        marker.on('popupopen', function () {
            var el = marker.getPopup().getElement();
            if (el) {
                el.addEventListener('mouseenter', function () {
                    clearTimeout(popupTimeout);
                });
                el.addEventListener('mouseleave', function () {
                    popupTimeout = setTimeout(function () {
                        marker.closePopup();
                    }, 300);
                });
            }
        });

        marker.on('click', function () {
            map.setView([finding.lat, finding.lon], Math.max(map.getZoom(), 12));
        });
    }

    function loadFindings() {
        var bounds = map.getBounds();
        var bbox = bounds.getSouth() + ',' + bounds.getWest() + ',' + bounds.getNorth() + ',' + bounds.getEast();
        var url = '/api/findings?bbox=' + bbox;

        fetch(url)
            .then(function (r) { return r.json(); })
            .then(function (data) {
                markers.clearLayers();

                var allFindings = data.findings || [];

                // Client-side category filter
                var filtered = allFindings;
                if (currentCategory !== 'all') {
                    filtered = filtered.filter(function (f) {
                        return String(f.category_id) === String(currentCategory);
                    });
                }

                // Client-side search filter (location_name)
                var q = (searchInput && searchInput.value) ? searchInput.value.trim().toLowerCase() : '';
                if (q.length >= 2) {
                    filtered = filtered.filter(function (f) {
                        var haystack = ((f.location_name || '') + ' ' + (f.sub_type || '')).toLowerCase();
                        return haystack.indexOf(q) !== -1;
                    });
                }

                // Update counter with filtered count
                var counterEl = document.getElementById('totalFindings');
                if (counterEl) counterEl.textContent = filtered.length;

                var emptyState = document.getElementById('emptyState');
                if (emptyState) {
                    emptyState.style.display = filtered.length === 0 ? 'block' : 'none';
                }

                filtered.forEach(function (f) {
                    var icon = createMarkerIcon(f);
                    var marker = L.marker([f.lat, f.lon], { icon: icon });
                    addPopupEvents(marker, f);
                    markers.addLayer(marker);
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

    // Initial load
    loadFindings();

    // Reload on drag or zoom (not autoPan — which only fires moveend)
    map.on('dragend', loadFindings);
    map.on('zoomend', loadFindings);

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

    // Search — Nominatim geocoding + client filter
    var searchTimeout;

    if (searchInput) {
        searchInput.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                clearTimeout(searchTimeout);
                performSearch();
            }
        });

        searchInput.addEventListener('input', function () {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(function () {
                var q = searchInput.value.trim();
                if (q.length < 2) {
                    loadFindings();
                    return;
                }
                performSearch();
            }, 500);
        });
    }

    function performSearch() {
        var q = searchInput.value.trim();
        if (q.length < 2) {
            loadFindings();
            return;
        }

        // Filter visible markers by location_name
        loadFindings();

        // Geocode via server proxy and fly to result
        fetch('/api/geocode?q=' + encodeURIComponent(q))
            .then(function (r) { return r.json(); })
            .then(function (data) {
                var results = data.results || [];
                if (results.length > 0) {
                    var lat = parseFloat(results[0].lat);
                    var lon = parseFloat(results[0].lon);
                    map.setView([lat, lon], 12);
                    // Reload markers after fly animation completes
                    map.once('moveend', loadFindings);
                }
            })
            .catch(function () {});
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
