/* ═══════════════════════════════════════════
   БРОШЕННАЯ ТЕХНИКА — Form Controller
   ═══════════════════════════════════════════ */

(function () {
    'use strict';

    var addBtn = document.getElementById('addBtn');
    var addPanel = document.getElementById('addPanel');
    var panelClose = document.getElementById('panelClose');
    var detailPanel = document.getElementById('detailPanel');
    var detailClose = document.getElementById('detailClose');
    var addForm = document.getElementById('addForm');
    var submitBtn = document.getElementById('submitBtn');
    var categoryChips = document.querySelectorAll('.chip');
    var categoryIdInput = document.getElementById('categoryId');
    var subTypeGroup = document.getElementById('subTypeGroup');
    var subTypeSelect = document.getElementById('subType');
    var description = document.getElementById('description');
    var charCount = document.getElementById('charCount');
    var latInput = document.getElementById('latInput');
    var lonInput = document.getElementById('lonInput');
    var coordDisplay = document.getElementById('coordDisplay');
    var geoBtn = document.getElementById('geoBtn');
    var photoInput = document.getElementById('photoInput');
    var uploadZone = document.getElementById('uploadZone');
    var previewGrid = document.getElementById('previewGrid');
    var uploadErrors = document.getElementById('uploadErrors');

    var subTypes = {
        '1': [
            { value: 'legkovoy', label: 'Легковой' },
            { value: 'gruzovoy', label: 'Грузовой' }
        ],
        '2': [{ value: '', label: 'Трактор / сельхоз' }],
        '3': [{ value: '', label: 'Прицеп / полуприцеп' }],
        '4': [{ value: '', label: 'Мотоцикл / мопед' }],
        '5': [{ value: '', label: 'Комбайн' }],
        '6': [{ value: '', label: 'Автобус / микроавтобус' }],
        '7': [{ value: '', label: 'Спецтехника' }],
        '8': [{ value: '', label: 'Другое' }]
    };

    var selectedFiles = [];

    // Open/close panels
    if (addBtn && addPanel) {
        addBtn.addEventListener('click', function () {
            addPanel.classList.add('open');
            if (detailPanel) detailPanel.classList.remove('open');
        });
    }

    if (panelClose) {
        panelClose.addEventListener('click', function () {
            addPanel.classList.remove('open');
        });
    }

    if (detailClose) {
        detailClose.addEventListener('click', function () {
            detailPanel.classList.remove('open');
        });
    }

    // Category chips
    categoryChips.forEach(function (chip) {
        chip.addEventListener('click', function () {
            categoryChips.forEach(function (c) { c.classList.remove('active'); });
            chip.classList.add('active');
            categoryIdInput.value = chip.dataset.id;

            var types = subTypes[chip.dataset.id];
            if (types && types.length > 1) {
                subTypeGroup.style.display = 'block';
                subTypeSelect.innerHTML = '<option value="">Выберите</option>';
                types.forEach(function (t) {
                    var opt = document.createElement('option');
                    opt.value = t.value;
                    opt.textContent = t.label;
                    subTypeSelect.appendChild(opt);
                });
            } else {
                subTypeGroup.style.display = 'none';
                subTypeSelect.value = '';
            }
        });
    });

    // Char count
    if (description) {
        description.addEventListener('input', function () {
            charCount.textContent = description.value.length;
        });
    }

    // Map click for coordinates
    if (coordDisplay) {
        window.__mapClickMode = true;
        window.__mapClickCallback = function (lat, lng) {
            latInput.value = lat.toFixed(6);
            lonInput.value = lng.toFixed(6);
            coordDisplay.textContent = lat.toFixed(6) + ', ' + lng.toFixed(6);
            showToast('Координаты установлены', 'success');
        };
    }

    // Geolocation
    if (geoBtn) {
        geoBtn.addEventListener('click', function () {
            if (!navigator.geolocation) {
                showToast('Геолокация не поддерживается', 'error');
                return;
            }
            geoBtn.textContent = 'Определение...';
            navigator.geolocation.getCurrentPosition(
                function (pos) {
                    latInput.value = pos.coords.latitude.toFixed(6);
                    lonInput.value = pos.coords.longitude.toFixed(6);
                    coordDisplay.textContent = pos.coords.latitude.toFixed(6) + ', ' + pos.coords.longitude.toFixed(6);
                    geoBtn.textContent = '📍 Моё местоположение';
                    if (window.__map) {
                        window.__map.setView([pos.coords.latitude, pos.coords.longitude], 14);
                    }
                },
                function (err) {
                    geoBtn.textContent = '📍 Моё местоположение';
                    showToast('Не удалось определить местоположение', 'error');
                },
                { enableHighAccuracy: true, timeout: 10000 }
            );
        });
    }

    // File upload
    if (photoInput) {
        photoInput.addEventListener('change', handleFiles);
    }

    if (uploadZone) {
        uploadZone.addEventListener('dragover', function (e) {
            e.preventDefault();
            uploadZone.classList.add('dragover');
        });
        uploadZone.addEventListener('dragleave', function () {
            uploadZone.classList.remove('dragover');
        });
        uploadZone.addEventListener('drop', function (e) {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
            if (e.dataTransfer.files) {
                addFiles(e.dataTransfer.files);
            }
        });
    }

    function handleFiles() {
        addFiles(photoInput.files);
        photoInput.value = '';
    }

    function addFiles(fileList) {
        var maxFiles = (window.__CONFIG && window.__CONFIG.MAX_FILES) || 6;
        var maxSize = 8 * 1024 * 1024;

        for (var i = 0; i < fileList.length; i++) {
            if (selectedFiles.length >= maxFiles) {
                showToast('Максимум ' + maxFiles + ' фото', 'error');
                break;
            }
            var file = fileList[i];
            if (file.size > maxSize) {
                showToast(file.name + ' слишком большой (макс 8 МБ)', 'error');
                continue;
            }
            var allowed = ['image/jpeg', 'image/png', 'image/webp'];
            if (allowed.indexOf(file.type) === -1) {
                showToast(file.name + ' — недопустимый формат', 'error');
                continue;
            }
            selectedFiles.push(file);
        }
        renderPreviews();
    }

    function renderPreviews() {
        previewGrid.innerHTML = '';
        selectedFiles.forEach(function (file, idx) {
            var div = document.createElement('div');
            div.className = 'preview-item';

            var img = document.createElement('img');
            img.src = URL.createObjectURL(file);
            div.appendChild(img);

            var removeBtn = document.createElement('button');
            removeBtn.className = 'preview-remove';
            removeBtn.textContent = '×';
            removeBtn.addEventListener('click', function () {
                selectedFiles.splice(idx, 1);
                renderPreviews();
            });
            div.appendChild(removeBtn);

            previewGrid.appendChild(div);
        });
    }

    // Form submit
    if (addForm) {
        addForm.addEventListener('submit', function (e) {
            e.preventDefault();

            var honeypot = addForm.querySelector('input[name="website"]');
            if (honeypot && honeypot.value) {
                showToast('Ошибка', 'error');
                return;
            }

            if (!categoryIdInput.value) {
                showToast('Выберите тип техники', 'error');
                return;
            }

            if (!latInput.value || !lonInput.value) {
                showToast('Укажите координаты (нажмите на карту)', 'error');
                return;
            }

            var formData = new FormData();
            formData.append('category_id', categoryIdInput.value);
            formData.append('sub_type', subTypeSelect.value);
            formData.append('description', description.value);
            formData.append('location_name', document.getElementById('locationName').value);
            formData.append('lat', latInput.value);
            formData.append('lon', lonInput.value);

            selectedFiles.forEach(function (file) {
                formData.append('photos', file);
            });

            submitBtn.disabled = true;
            submitBtn.querySelector('.submit-text').textContent = 'ОТПРАВКА...';

            fetch('/api/findings', {
                method: 'POST',
                body: formData
            })
                .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
                .then(function (result) {
                    if (result.ok && result.data.id) {
                        if (result.data.token) {
                            var tokens = JSON.parse(localStorage.getItem('editTokens') || '{}');
                            tokens[result.data.id] = result.data.token;
                            localStorage.setItem('editTokens', JSON.stringify(tokens));
                        }

                        var msg = 'Находка создана!';
                        if (result.data.moderation_notice) {
                            msg += ' ' + result.data.moderation_notice;
                        }
                        if (result.data.duplicate_warning) {
                            msg += ' ' + result.data.duplicate_warning;
                        }
                        showToast(msg, 'success');

                        addPanel.classList.remove('open');
                        addForm.reset();
                        selectedFiles = [];
                        renderPreviews();
                        categoryIdInput.value = '';
                        categoryChips.forEach(function (c) { c.classList.remove('active'); });
                        subTypeGroup.style.display = 'none';
                        coordDisplay.textContent = '—';
                        latInput.value = '';
                        lonInput.value = '';

                        if (window.__loadFindings) {
                            window.__loadFindings();
                        }

                        setTimeout(function () {
                            window.location.href = '/finding/' + result.data.id;
                        }, 1500);
                    } else {
                        var errMsg = result.data.error || result.data.errors || 'Ошибка отправки';
                        if (typeof errMsg === 'object') {
                            errMsg = Object.values(errMsg).flat().join(', ');
                        }
                        showToast(errMsg, 'error');
                    }
                })
                .catch(function () {
                    showToast('Ошибка сети', 'error');
                })
                .finally(function () {
                    submitBtn.disabled = false;
                    submitBtn.querySelector('.submit-text').textContent = 'ОТМЕТИТЬ НАХОДКУ';
                });
        });
    }

    function showToast(message, type) {
        var container = document.getElementById('toastContainer');
        if (!container) return;
        var toast = document.createElement('div');
        toast.className = 'toast ' + (type || '');
        toast.textContent = message;
        container.appendChild(toast);
        setTimeout(function () {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.3s';
            setTimeout(function () { toast.remove(); }, 300);
        }, 4000);
    }

    window.__showToast = showToast;

})();
