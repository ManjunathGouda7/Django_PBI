/**
 * Power BI Studio - Interactive Engine
 */

document.addEventListener('DOMContentLoaded', () => {
    // Global State
    const state = {
        dashboards: [],
        datasets: [],
        activeDashboardId: null,
        activeDatasetId: null,
        activeDashboard: null,
        activeDataset: null,
        selectedWidgetId: null,
        activeVisualType: 'scatter',
        userThemeSelected: null,
        activeSlicers: {}, // e.g. { "Region": ["North America"] }
        chartInstances: {}, // Store Chart.js objects by widget id
        dataView: {
            page: 1,
            pageSize: 50,
            search: '',
            sortCol: '',
            sortDir: 'asc'
        }
    };

    // DOM Elements
    const elements = {
        dashboardSelect: document.getElementById('dashboard-select'),
        datasetSelect: document.getElementById('dataset-select'),
        themeSelect: document.getElementById('theme-select'),
        btnGetData: document.getElementById('btn-get-data'),
        btnNewDashboard: document.getElementById('btn-new-dashboard'),
        btnExportPdf: document.getElementById('btn-export-pdf'),
        
        // Navigation Views
        navReport: document.getElementById('nav-report-view'),
        navData: document.getElementById('nav-data-view'),
        navModel: document.getElementById('nav-model-view'),
        viewReport: document.getElementById('view-report'),
        viewData: document.getElementById('view-data'),
        viewModel: document.getElementById('view-model'),

        // Fields Pane
        fieldsTreeContainer: document.getElementById('fields-tree-container'),
        fieldCountBadge: document.getElementById('field-count-badge'),
        fieldSearchInput: document.getElementById('field-search-input'),

        // Canvas & Slicers
        canvasGrid: document.getElementById('canvas-grid'),
        slicerPillsContainer: document.getElementById('slicer-pills-container'),
        btnClearSlicers: document.getElementById('btn-clear-slicers'),

        // Visual Customizer Right Pane
        vizTypePicker: document.getElementById('viz-type-picker'),
        vizTitleInput: document.getElementById('viz-title-input'),
        vizXSelect: document.getElementById('viz-x-select'),
        vizYSelect: document.getElementById('viz-y-select'),
        vizGroupSelect: document.getElementById('viz-group-select'),
        btnSaveWidget: document.getElementById('btn-save-widget'),
        lblSaveWidget: document.getElementById('lbl-save-widget'),
        btnDeleteWidget: document.getElementById('btn-delete-widget'),

        // Data View Tab
        dvDatasetTitle: document.getElementById('dv-dataset-title'),
        dvRowBadge: document.getElementById('dv-row-badge'),
        dvSearchInput: document.getElementById('dv-search-input'),
        dvTableHead: document.getElementById('dv-table-head'),
        dvTableBody: document.getElementById('dv-table-body'),
        dvPageInfo: document.getElementById('dv-page-info'),
        dvPrevPage: document.getElementById('dv-prev-page'),
        dvNextPage: document.getElementById('dv-next-page'),

        // Modals
        modalGetData: document.getElementById('modal-get-data'),
        closeModalData: document.getElementById('close-modal-data'),
        uploadForm: document.getElementById('upload-dataset-form'),
        uploadNameInput: document.getElementById('upload-name-input'),
        uploadFileInput: document.getElementById('upload-file-input'),
        sampleDatasetsContainer: document.getElementById('sample-datasets-container'),
        
        tabBtnFile: document.getElementById('tab-btn-file'),
        tabBtnMongo: document.getElementById('tab-btn-mongo'),
        mongoForm: document.getElementById('mongo-dataset-form'),
        mongoNameInput: document.getElementById('mongo-name-input'),
        mongoUrlInput: document.getElementById('mongo-url-input'),
        mongoDbNameInput: document.getElementById('mongo-dbname-input'),
        mongoCollInput: document.getElementById('mongo-coll-input'),
        btnPushMongoJson: document.getElementById('btn-push-mongo-json'),

        modalNewDashboard: document.getElementById('modal-new-dashboard'),
        closeModalDashboard: document.getElementById('close-modal-dashboard'),
        createDashboardForm: document.getElementById('create-dashboard-form'),
        newDbTitle: document.getElementById('new-db-title'),
        newDbDatasetSelect: document.getElementById('new-db-dataset-select'),
        newDbTheme: document.getElementById('new-db-theme'),

        // Right pane tabs & filter panel
        tabVizPane: document.getElementById('tab-viz-pane'),
        tabFilterPane: document.getElementById('tab-filter-pane'),
        panelViz: document.getElementById('panel-viz'),
        panelFilters: document.getElementById('panel-filters'),
        filterCardsContainer: document.getElementById('filter-cards-container'),
        btnClearAllFilters: document.getElementById('btn-clear-all-filters'),
        btnResetVizForm: document.getElementById('btn-reset-viz-form'),
        vizModeStatus: document.getElementById('viz-mode-status')
    };

    // Initialize App
    init();

    async function init() {
        bindEvents();
        await fetchDatasets();
        await fetchDashboards();
        initDataChatController();
    }

    function bindEvents() {
        // Navigation Switcher
        elements.navReport.addEventListener('click', () => switchView('report'));
        elements.navData.addEventListener('click', () => switchView('data'));
        if (elements.navModel) elements.navModel.addEventListener('click', () => switchView('model'));


        if (elements.btnResetVizForm) {
            elements.btnResetVizForm.addEventListener('click', resetWidgetForm);
        }

        // Right pane tab switcher (Visualizations / Filters)
        if (elements.tabVizPane && elements.tabFilterPane) {
            elements.tabVizPane.addEventListener('click', () => switchRightPane('viz'));
            elements.tabFilterPane.addEventListener('click', () => switchRightPane('filters'));
        }
        if (elements.btnClearAllFilters) {
            elements.btnClearAllFilters.addEventListener('click', clearAllPageFilters);
        }

        // Select Change
        elements.dashboardSelect.addEventListener('change', (e) => loadDashboard(e.target.value));
        elements.datasetSelect.addEventListener('change', (e) => setDataset(e.target.value));
        elements.themeSelect.addEventListener('change', (e) => {
            state.userThemeSelected = e.target.value;
            applyTheme(e.target.value);
        });

        // Modals
        elements.btnGetData.addEventListener('click', () => openModal(elements.modalGetData));
        elements.closeModalData.addEventListener('click', () => closeModal(elements.modalGetData));
        
        elements.btnNewDashboard.addEventListener('click', () => {
            populateNewDashboardModal();
            openModal(elements.modalNewDashboard);
        });
        elements.closeModalDashboard.addEventListener('click', () => closeModal(elements.modalNewDashboard));

        // Modal Tabs
        if (elements.tabBtnFile && elements.tabBtnMongo) {
            elements.tabBtnFile.addEventListener('click', (e) => {
                e.preventDefault();
                elements.tabBtnFile.classList.add('active');
                elements.tabBtnMongo.classList.remove('active');
                elements.uploadForm.style.display = 'flex';
                elements.mongoForm.style.display = 'none';
            });

            elements.tabBtnMongo.addEventListener('click', (e) => {
                e.preventDefault();
                elements.tabBtnMongo.classList.add('active');
                elements.tabBtnFile.classList.remove('active');
                elements.uploadForm.style.display = 'none';
                elements.mongoForm.style.display = 'flex';
            });
        }

        // Form Submissions
        elements.uploadForm.addEventListener('submit', handleDatasetUpload);
        elements.mongoForm.addEventListener('submit', handleMongoSubmit);
        if (elements.btnPushMongoJson) {
            elements.btnPushMongoJson.addEventListener('click', handlePushMongoJson);
        }
        elements.createDashboardForm.addEventListener('submit', handleCreateDashboard);

        // Export PDF / Image Snapshot
        elements.btnExportPdf.addEventListener('click', async () => {
            const canvasGrid = document.getElementById('canvas-grid');
            if (!canvasGrid) return;
            try {
                const btn = elements.btnExportPdf;
                const origText = btn.innerHTML;
                btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Exporting...';

                const canvas = await html2canvas(canvasGrid, {
                    scale: 2,
                    useCORS: true,
                    backgroundColor: getComputedStyle(document.documentElement).getPropertyValue('--bg-main').trim() || '#1e293b'
                });

                const link = document.createElement('a');
                const title = state.activeDashboard ? state.activeDashboard.title.replace(/\s+/g, '_') : 'Report';
                link.download = `PowerBI_${title}_Export.png`;
                link.href = canvas.toDataURL('image/png');
                link.click();

                btn.innerHTML = origText;
            } catch (err) {
                console.error("Export error:", err);
                if (state.activeDashboardId) {
                    window.open(`/export/${state.activeDashboardId}/`, '_blank');
                }
            }
        });

        // Clear Slicers
        elements.btnClearSlicers.addEventListener('click', clearAllSlicers);

        // Viz Type Picker Buttons
        elements.vizTypePicker.querySelectorAll('.viz-type-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                elements.vizTypePicker.querySelectorAll('.viz-type-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                state.activeVisualType = btn.dataset.type;
                if (state.selectedWidgetId) {
                    saveWidget();
                }
            });
        });

        // Save / Delete Widget
        elements.btnSaveWidget.addEventListener('click', saveWidget);
        elements.btnDeleteWidget.addEventListener('click', deleteSelectedWidget);

        // Instant Auto-Update on Dropdown Change
        if (elements.vizXSelect) elements.vizXSelect.addEventListener('change', () => { if (state.selectedWidgetId) saveWidget(); });
        if (elements.vizYSelect) elements.vizYSelect.addEventListener('change', () => { if (state.selectedWidgetId) saveWidget(); });
        if (elements.vizGroupSelect) elements.vizGroupSelect.addEventListener('change', () => { if (state.selectedWidgetId) saveWidget(); });

        // Data View Controls
        elements.dvSearchInput.addEventListener('input', debounce(() => {
            state.dataView.search = elements.dvSearchInput.value.trim();
            state.dataView.page = 1;
            loadDataViewRows();
        }, 300));

        elements.dvPrevPage.addEventListener('click', () => {
            if (state.dataView.page > 1) {
                state.dataView.page--;
                loadDataViewRows();
            }
        });

        elements.dvNextPage.addEventListener('click', () => {
            state.dataView.page++;
            loadDataViewRows();
        });

        // Field search filter
        elements.fieldSearchInput.addEventListener('input', (e) => filterFieldsList(e.target.value));

        // Ribbon Navigation Tabs
        const rGetData = document.getElementById('ribbon-btn-getdata');
        if (rGetData) rGetData.addEventListener('click', () => openModal(elements.modalGetData));
        const rRefresh = document.getElementById('ribbon-btn-refresh');
        if (rRefresh) rRefresh.addEventListener('click', () => loadDashboard(state.activeDashboardId));
        const rSlicers = document.getElementById('ribbon-btn-slicers');
        if (rSlicers) rSlicers.addEventListener('click', clearAllSlicers);
        const rTheme = document.getElementById('ribbon-btn-theme');
        if (rTheme) rTheme.addEventListener('click', () => elements.themeSelect.focus());
        const rPdf = document.getElementById('ribbon-btn-pdf');
        if (rPdf) rPdf.addEventListener('click', () => {
            if (state.activeDashboardId) window.open(`/export/${state.activeDashboardId}/`, '_blank');
        });

        // Advanced Enterprise Feature Ribbon Buttons
        const rAutoDb = document.getElementById('ribbon-btn-autodb');
        if (rAutoDb) rAutoDb.addEventListener('click', triggerAutoBuildDashboard);

        const rExcel = document.getElementById('ribbon-btn-excel');
        if (rExcel) rExcel.addEventListener('click', () => {
            if (state.activeDatasetId) {
                window.location.href = `/export-excel/${state.activeDatasetId}/`;
            } else {
                alert("Please select a dataset first to export Excel workbook.");
            }
        });

        const rKiosk = document.getElementById('ribbon-btn-kiosk');
        if (rKiosk) rKiosk.addEventListener('click', toggleKioskMode);

        // Data Cleaning & Measures Modal Triggers
        const mCleanOpen = document.getElementById('btn-open-clean-modal');
        const mCleanClose = document.getElementById('close-modal-clean');
        const mCleanModal = document.getElementById('modal-clean-data');
        if (mCleanOpen && mCleanModal) mCleanOpen.addEventListener('click', () => openModal(mCleanModal));
        if (mCleanClose && mCleanModal) mCleanClose.addEventListener('click', () => closeModal(mCleanModal));

        const mMeasureOpen = document.getElementById('btn-open-measure-modal');
        const mMeasureClose = document.getElementById('close-modal-measure');
        const mMeasureModal = document.getElementById('modal-add-measure');
        if (mMeasureOpen && mMeasureModal) mMeasureOpen.addEventListener('click', () => openModal(mMeasureModal));
        if (mMeasureClose && mMeasureModal) mMeasureClose.addEventListener('click', () => closeModal(mMeasureModal));

        const mJoinOpen = document.getElementById('btn-open-join-modal');
        const mJoinClose = document.getElementById('close-modal-join');
        const mJoinModal = document.getElementById('modal-join-datasets');
        if (mJoinOpen && mJoinModal) mJoinOpen.addEventListener('click', () => {
            populateJoinDatasetsModal();
            openModal(mJoinModal);
        });
        if (mJoinClose && mJoinModal) mJoinClose.addEventListener('click', () => closeModal(mJoinModal));

        // Form Handlers
        const formClean = document.getElementById('clean-dataset-form');
        if (formClean) formClean.addEventListener('submit', handleCleanDataset);

        const formMeasure = document.getElementById('add-measure-form');
        if (formMeasure) formMeasure.addEventListener('submit', handleAddMeasure);

        const formJoin = document.getElementById('join-datasets-form');
        if (formJoin) formJoin.addEventListener('submit', handleJoinDatasets);

        // Anomaly Filter button
        const btnFilterAnomalies = document.getElementById('btn-filter-anomalies');
        if (btnFilterAnomalies) btnFilterAnomalies.addEventListener('click', toggleAnomalyFilter);
    }


    function switchView(viewName) {
        if (viewName === 'report') {
            elements.navReport.classList.add('active');
            elements.navData.classList.remove('active');
            if (elements.navModel) elements.navModel.classList.remove('active');
            elements.viewReport.classList.add('active');
            elements.viewData.classList.remove('active');
            if (elements.viewModel) elements.viewModel.style.display = 'none';
        } else if (viewName === 'data') {
            elements.navReport.classList.remove('active');
            elements.navData.classList.add('active');
            if (elements.navModel) elements.navModel.classList.remove('active');
            elements.viewReport.classList.remove('active');
            elements.viewData.classList.add('active');
            if (elements.viewModel) elements.viewModel.style.display = 'none';
            loadDataViewRows();
        } else if (viewName === 'model') {
            elements.navReport.classList.remove('active');
            elements.navData.classList.remove('active');
            if (elements.navModel) elements.navModel.classList.add('active');
            elements.viewReport.classList.remove('active');
            elements.viewData.classList.remove('active');
            if (elements.viewModel) {
                elements.viewModel.style.display = 'flex';
                elements.viewModel.classList.add('active');
            }
            loadModelViewSchema();
        }
    }


    function switchRightPane(pane) {
        if (pane === 'viz') {
            elements.tabVizPane.classList.add('active');
            elements.tabFilterPane.classList.remove('active');
            elements.panelViz.classList.add('active');
            elements.panelFilters.classList.remove('active');
        } else {
            elements.tabFilterPane.classList.add('active');
            elements.tabVizPane.classList.remove('active');
            elements.panelFilters.classList.add('active');
            elements.panelViz.classList.remove('active');
            // Build filter cards if not yet built for this dataset
            if (state.activeDatasetId && elements.filterCardsContainer.querySelector('.filter-card') === null) {
                buildFiltersPane();
            }
        }
    }

    function openModal(modal) { modal.classList.add('active'); }
    function closeModal(modal) { modal.classList.remove('active'); }

    // API Calls
    async function fetchDatasets() {
        try {
            const res = await fetch('/api/datasets/');
            const data = await res.json();
            state.datasets = data.datasets || [];
            
            renderDatasetDropdowns();
            renderSampleDatasetsModal();

            if (state.datasets.length > 0 && !state.activeDatasetId) {
                setDataset(state.datasets[0].id);
            }
        } catch (err) {
            console.error("Failed to fetch datasets", err);
        }
    }

    async function fetchDashboards() {
        try {
            const res = await fetch('/api/dashboards/');
            const data = await res.json();
            state.dashboards = data.dashboards || [];

            renderDashboardDropdown();

            if (state.dashboards.length > 0 && !state.activeDashboardId) {
                loadDashboard(state.dashboards[0].id);
            }
        } catch (err) {
            console.error("Failed to fetch dashboards", err);
        }
    }

    function renderDatasetDropdowns() {
        let html = '';
        state.datasets.forEach(ds => {
            html += `<option value="${ds.id}">${ds.name} (${ds.row_count} rows)</option>`;
        });
        elements.datasetSelect.innerHTML = html;
        elements.newDbDatasetSelect.innerHTML = '<option value="">Select Dataset</option>' + html;

        const chatSelect = document.getElementById('chat-dataset-select');
        if (chatSelect) {
            chatSelect.innerHTML = html || '<option value="">No Datasets</option>';
            if (state.activeDatasetId) chatSelect.value = state.activeDatasetId;
        }

        if (state.activeDatasetId) {
            elements.datasetSelect.value = state.activeDatasetId;
        }
    }

    function renderDashboardDropdown() {
        let html = '';
        state.dashboards.forEach(db => {
            html += `<option value="${db.id}">${db.title}</option>`;
        });
        elements.dashboardSelect.innerHTML = html || '<option value="">No Dashboards</option>';
        if (state.activeDashboardId) {
            elements.dashboardSelect.value = state.activeDashboardId;
        }
    }

    function renderSampleDatasetsModal() {
        let html = '';
        state.datasets.filter(d => d.is_sample).forEach(ds => {
            html += `
                <div class="sample-card-item" data-id="${ds.id}">
                    <h5><i class="fa-solid fa-table text-accent"></i> ${ds.name}</h5>
                    <p>${ds.description || 'Pre-loaded business dataset.'}</p>
                </div>`;
        });
        elements.sampleDatasetsContainer.innerHTML = html;

        elements.sampleDatasetsContainer.querySelectorAll('.sample-card-item').forEach(card => {
            card.addEventListener('click', () => {
                setDataset(card.dataset.id);
                closeModal(elements.modalGetData);
            });
        });
    }

    function setDataset(datasetId) {
        state.activeDatasetId = parseInt(datasetId);
        elements.datasetSelect.value = state.activeDatasetId;
        state.activeDataset = state.datasets.find(d => d.id === state.activeDatasetId);
        
        if (state.activeDataset) {
            renderFieldsTree();
            populateFieldBuckets();
            // Reset filter pane so it rebuilds for new dataset
            if (elements.filterCardsContainer) {
                elements.filterCardsContainer.innerHTML = '<div class="empty-state">Select a dataset to see filters</div>';
            }
            // If filters panel is currently active, rebuild immediately
            if (elements.panelFilters && elements.panelFilters.classList.contains('active')) {
                buildFiltersPane();
            }
            if (elements.viewData.classList.contains('active')) {
                loadDataViewRows();
            }
            if (elements.viewModel && elements.viewModel.style.display !== 'none') {
                loadModelViewSchema();
            }
        }
    }

    async function loadDashboard(dashboardId, slicersUpdated = false) {
        if (!dashboardId) return;
        state.activeDashboardId = parseInt(dashboardId);

        try {
            const queryParams = new URLSearchParams();
            if (Object.keys(state.activeSlicers).length > 0) {
                queryParams.append('slicers', JSON.stringify(state.activeSlicers));
            }

            const res = await fetch(`/api/dashboards/${state.activeDashboardId}/?${queryParams.toString()}`);
            if (!res.ok) {
                state.activeDashboardId = null;
                await fetchDashboards();
                return;
            }
            const data = await res.json();
            state.activeDashboard = data;
            elements.dashboardSelect.value = state.activeDashboardId;

            // Apply Theme (preserve user selected theme across filter updates)
            if (state.userThemeSelected) {
                applyTheme(state.userThemeSelected);
                elements.themeSelect.value = state.userThemeSelected;
            } else if (data.theme && !slicersUpdated) {
                applyTheme(data.theme);
                elements.themeSelect.value = data.theme;
            }

            // Sync dataset if different
            if (data.dataset && data.dataset.id !== state.activeDatasetId) {
                setDataset(data.dataset.id);
            }

            renderCanvasWidgets(data.widgets || []);
            renderSlicerPills();

        } catch (err) {
            console.error("Failed to load dashboard", err);
            state.activeDashboardId = null;
            await fetchDashboards();
        }
    }

    function applyTheme(themeName) {
        document.documentElement.setAttribute('data-theme', themeName);
    }

    // ===================================================
    // FILTERS PANE — Power BI "Filters on this page"
    // ===================================================

    // Columns to show as filters (categorical only; exclude pure numeric/timestamp cols)
    const FILTER_COL_BLACKLIST = ['Timestamp [Sec]', '_id', 'id', 'State [Cal/PT]'];

    function buildFiltersPane() {
        if (!state.activeDataset || !state.activeDataset.column_schema) return;
        const schema = state.activeDataset.column_schema;

        // Key columns for Power BI filter cards
        const targetCols = ['Board', 'PowerMode', 'Power', 'DUT', 'CRX', 'Position', 'RUN'];

        // Pick categorical columns matching targetCols or non-blacklisted categorical cols
        const allFilterCols = schema
            .map(c => c.name)
            .filter(n => !FILTER_COL_BLACKLIST.includes(n) && (targetCols.includes(n) || schema.find(c => c.name === n)?.type === 'categorical'));

        const uniqueFilterCols = [...new Set(allFilterCols)];

        if (uniqueFilterCols.length === 0) {
            elements.filterCardsContainer.innerHTML = '<div class="empty-state">No categorical columns found for filtering.</div>';
            return;
        }

        elements.filterCardsContainer.innerHTML = '';
        uniqueFilterCols.forEach(colName => {
            const card = createFilterCard(colName);
            elements.filterCardsContainer.appendChild(card);
        });

        // Update card summaries from existing slicers
        updateAllFilterCardSummaries();
    }

    function createFilterCard(colName) {
        const card = document.createElement('div');
        card.className = 'filter-card';
        card.dataset.col = colName;

        const isActive = state.activeSlicers[colName] && state.activeSlicers[colName].length > 0;
        if (isActive) card.classList.add('filter-active', 'expanded');

        const summary = getFilterSummaryText(colName);

        card.innerHTML = `
            <div class="filter-card-header">
                <div class="filter-card-meta">
                    <span class="filter-col-name">${colName}</span>
                    <span class="filter-col-summary">${summary}</span>
                </div>
                <div class="filter-card-btns">
                    <button class="filter-eraser-btn" title="Clear filter for ${colName}">
                        <i class="fa-solid fa-eraser"></i>
                    </button>
                    <button class="filter-chevron" title="Expand/Collapse">
                        <i class="fa-solid fa-chevron-down"></i>
                    </button>
                </div>
            </div>
            <div class="filter-card-body">
                <div class="filter-loading"><i class="fa-solid fa-spinner fa-spin"></i> Loading values...</div>
            </div>`;

        // Toggle expand on header click
        const header = card.querySelector('.filter-card-header');
        header.addEventListener('click', (e) => {
            if (e.target.closest('.filter-eraser-btn')) return;
            const wasExpanded = card.classList.contains('expanded');
            card.classList.toggle('expanded');
            if (!wasExpanded) {
                loadFilterCardOptions(card, colName);
            }
        });

        // Clear (eraser) button
        card.querySelector('.filter-eraser-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            clearFilterForCol(colName);
        });

        // If already active, expand and load options
        if (isActive) {
            loadFilterCardOptions(card, colName);
        }

        return card;
    }

    async function loadFilterCardOptions(card, colName) {
        const bodyEl = card.querySelector('.filter-card-body');

        bodyEl.innerHTML = '<div class="filter-loading"><i class="fa-solid fa-spinner fa-spin"></i> Loading values...</div>';

        try {
            const queryParams = new URLSearchParams({ col: colName });
            if (Object.keys(state.activeSlicers).length > 0) {
                queryParams.append('slicers', JSON.stringify(state.activeSlicers));
            }

            const res = await fetch(`/api/datasets/${state.activeDatasetId}/filter-values/?${queryParams.toString()}`);
            const data = await res.json();
            const rawValues = data.values || [];
            const activeVals = state.activeSlicers[colName] || [];

            // Standardize values list: [{value: 'val', count: 123}]
            const items = rawValues.map(item => {
                if (typeof item === 'object' && item !== null) {
                    return { value: String(item.value), count: item.count };
                }
                return { value: String(item), count: null };
            });

            let html = `
                <div class="filter-card-controls">
                    <select class="filter-mode-select">
                        <option value="basic">Basic filtering</option>
                    </select>
                    <div class="filter-search-box">
                        <i class="fa-solid fa-magnifying-glass search-icon"></i>
                        <input type="text" class="filter-search-input" placeholder="Search">
                    </div>
                </div>
            `;

            const allSelected = (activeVals.length > 0 && activeVals.length === items.length) || activeVals.length === 0;

            html += `
                <label class="filter-option-item select-all-option">
                    <input type="checkbox" class="select-all-cb" ${allSelected ? 'checked' : ''}>
                    <span class="filter-option-label">Select all</span>
                </label>
            `;

            items.forEach(item => {
                const checked = activeVals.length === 0 || activeVals.includes(item.value) ? 'checked' : '';
                const countDisplay = item.count !== null && item.count !== undefined ? item.count.toLocaleString() : '';
                html += `
                    <label class="filter-option-item">
                        <input type="checkbox" class="val-cb" value="${item.value}" ${checked}>
                        <span class="filter-option-label">${item.value}</span>
                        ${countDisplay ? `<span class="filter-option-count">${countDisplay}</span>` : ''}
                    </label>`;
            });

            if (items.length === 0) {
                html = '<div class="filter-loading">No values found</div>';
            }

            bodyEl.innerHTML = html;

            const selectAllCb = bodyEl.querySelector('.select-all-cb');
            const searchInput = bodyEl.querySelector('.filter-search-input');

            // Search filter
            if (searchInput) {
                searchInput.addEventListener('input', () => {
                    const q = searchInput.value.toLowerCase();
                    bodyEl.querySelectorAll('.filter-option-item:not(.select-all-option)').forEach(item => {
                        const labelText = item.querySelector('.filter-option-label').textContent.toLowerCase();
                        item.style.display = labelText.includes(q) ? 'flex' : 'none';
                    });
                });
            }

            // Select All listener
            if (selectAllCb) {
                selectAllCb.addEventListener('change', () => {
                    const isChecked = selectAllCb.checked;
                    bodyEl.querySelectorAll('.val-cb').forEach(cb => {
                        if (cb.parentElement.style.display !== 'none') {
                            cb.checked = isChecked;
                        }
                    });
                    applyFilterFromCard(card, colName);
                });
            }

            // Individual checkbox listeners
            bodyEl.querySelectorAll('.val-cb').forEach(cb => {
                cb.addEventListener('change', () => {
                    const valCbs = [...bodyEl.querySelectorAll('.val-cb')];
                    const visibleValCbs = valCbs.filter(c => c.parentElement.style.display !== 'none');
                    if (selectAllCb) {
                        selectAllCb.checked = visibleValCbs.length > 0 && visibleValCbs.every(c => c.checked);
                    }
                    applyFilterFromCard(card, colName);
                });
            });

        } catch (err) {
            console.error("Filter loading error:", err);
            bodyEl.innerHTML = '<div class="filter-loading">Error loading values</div>';
        }
    }

    function applyFilterFromCard(card, colName) {
        const checked = [...card.querySelectorAll('.val-cb:checked')].map(cb => cb.value);
        const totalCbs = card.querySelectorAll('.val-cb').length;

        // If no items are checked, or ALL items are checked, no filter is active (is All)
        if (checked.length === 0 || (totalCbs > 0 && checked.length === totalCbs)) {
            delete state.activeSlicers[colName];
            card.classList.remove('filter-active');
        } else {
            state.activeSlicers[colName] = checked;
            card.classList.add('filter-active');
        }

        updateFilterCardSummary(card, colName);
        loadDashboard(state.activeDashboardId, true);
        renderSlicerPills();
    }

    function clearFilterForCol(colName) {
        delete state.activeSlicers[colName];
        const card = elements.filterCardsContainer.querySelector(`.filter-card[data-col="${CSS.escape(colName)}"]`);
        if (card) {
            card.classList.remove('filter-active');
            card.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
            updateFilterCardSummary(card, colName);
        }
        loadDashboard(state.activeDashboardId, true);
        renderSlicerPills();
    }

    function clearAllPageFilters() {
        state.activeSlicers = {};
        // Uncheck all checkboxes in all cards
        elements.filterCardsContainer.querySelectorAll('.filter-card').forEach(card => {
            card.classList.remove('filter-active');
            card.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
            const colName = card.dataset.col;
            updateFilterCardSummary(card, colName);
        });
        loadDashboard(state.activeDashboardId);
        renderSlicerPills();
    }

    function getFilterSummaryText(colName) {
        const vals = state.activeSlicers[colName];
        if (!vals || vals.length === 0) return 'is (All)';
        if (vals.length === 1) return `is ${vals[0]}`;
        if (vals.length <= 3) return `is ${vals.join(', ')}`;
        return `is ${vals.slice(0, 2).join(', ')}, or ${vals.length - 2} more`;
    }

    function updateFilterCardSummary(card, colName) {
        const summaryEl = card.querySelector('.filter-col-summary');
        if (summaryEl) summaryEl.textContent = getFilterSummaryText(colName);
    }

    function updateAllFilterCardSummaries() {
        elements.filterCardsContainer.querySelectorAll('.filter-card').forEach(card => {
            const colName = card.dataset.col;
            updateFilterCardSummary(card, colName);
            if (state.activeSlicers[colName] && state.activeSlicers[colName].length > 0) {
                card.classList.add('filter-active');
            } else {
                card.classList.remove('filter-active');
            }
            // If card is expanded, refresh option counts
            if (card.classList.contains('expanded')) {
                loadFilterCardOptions(card, colName);
            }
        });
    }

    // ===================================================
    // END FILTERS PANE
    // ===================================================

    function renderFieldsTree() {
        if (!state.activeDataset || !state.activeDataset.column_schema) return;
        const schema = state.activeDataset.column_schema;

        elements.fieldCountBadge.textContent = `${schema.length} columns`;

        let html = '';
        schema.forEach(col => {
            let iconClass = 'field-icon-categorical';
            let iconSymbol = 'Aa';
            if (col.type === 'numeric') {
                iconClass = 'field-icon-numeric';
                iconSymbol = '#';
            } else if (col.type === 'date') {
                iconClass = 'field-icon-date';
                iconSymbol = '📅';
            }

            html += `
                <div class="field-item" data-name="${col.name}" data-type="${col.type}">
                    <span class="${iconClass}">${iconSymbol}</span>
                    <span class="field-name">${col.name}</span>
                </div>`;
        });

        elements.fieldsTreeContainer.innerHTML = html;

        // Click on field item auto-populates bucket dropdowns
        elements.fieldsTreeContainer.querySelectorAll('.field-item').forEach(item => {
            item.addEventListener('click', () => {
                const name = item.dataset.name;
                const type = item.dataset.type;

                if (type === 'numeric') {
                    elements.vizYSelect.value = name;
                } else {
                    elements.vizXSelect.value = name;
                }
            });
        });
    }

    function filterFieldsList(query) {
        const q = query.toLowerCase();
        elements.fieldsTreeContainer.querySelectorAll('.field-item').forEach(item => {
            const text = item.dataset.name.toLowerCase();
            if (text.includes(q)) {
                item.style.display = 'flex';
            } else {
                item.style.display = 'none';
            }
        });
    }

    function populateFieldBuckets() {
        if (!state.activeDataset || !state.activeDataset.column_schema) return;
        const schema = state.activeDataset.column_schema;

        let xOpts = '<option value="">Select X-Axis / Category Field</option>';
        let yOpts = '<option value="">Select Y-Axis / Value Field</option>';
        let gOpts = '<option value="">Select Legend / Group Field (e.g. Board)</option>';

        schema.forEach(col => {
            let symbol = col.type === 'numeric' ? '#' : (col.type === 'date' ? '📅' : 'Aa');
            xOpts += `<option value="${col.name}">${symbol} ${col.name}</option>`;
            yOpts += `<option value="${col.name}">${symbol} ${col.name}</option>`;
            gOpts += `<option value="${col.name}">${symbol} ${col.name}</option>`;
        });

        elements.vizXSelect.innerHTML = xOpts;
        elements.vizYSelect.innerHTML = yOpts;
        if (elements.vizGroupSelect) elements.vizGroupSelect.innerHTML = gOpts;
    }

    // Render Visual Widgets on Canvas
    function renderCanvasWidgets(widgets) {
        // Destroy existing Chart.js instances
        Object.values(state.chartInstances).forEach(chart => chart.destroy());
        state.chartInstances = {};

        elements.canvasGrid.innerHTML = '';

        if (widgets.length === 0) {
            elements.canvasGrid.innerHTML = `
                <div style="grid-column: span 12; text-align: center; padding: 4rem; color: var(--text-dim);">
                    <i class="fa-solid fa-chart-line" style="font-size: 3rem; margin-bottom: 1rem;"></i>
                    <h3>Canvas is Empty</h3>
                    <p>Select fields on the right pane and click <strong>Add Visual to Canvas</strong>.</p>
                </div>`;
            return;
        }

        widgets.forEach(w => {
            const card = document.createElement('div');
            card.className = `visual-card ${state.selectedWidgetId === w.id ? 'selected' : ''}`;
            const colSpan = (widgets.length === 1 || ['scatter', 'table', 'line', 'area'].includes(w.visual_type)) ? 12 : (w.width || 6);
            const rowSpan = (widgets.length === 1 && w.visual_type === 'scatter') ? 7 : (w.height || 5);
            card.style.gridColumn = `span ${colSpan}`;
            card.style.gridRow = `span ${rowSpan}`;
            card.dataset.widgetId = w.id;


            card.innerHTML = `
                <div class="visual-card-header">
                    <span class="visual-card-title">${w.title}</span>
                    <div class="visual-card-actions">
                        <button class="card-action-btn btn-edit" title="Edit Visual"><i class="fa-solid fa-pen"></i></button>
                        <button class="card-action-btn btn-del" title="Delete Visual"><i class="fa-solid fa-times"></i></button>
                    </div>
                </div>
                <div class="visual-card-body">
                    <canvas id="canvas-widget-${w.id}"></canvas>
                </div>`;

            elements.canvasGrid.appendChild(card);

            // Bind card actions
            card.addEventListener('click', (e) => {
                if (!e.target.closest('.card-action-btn')) {
                    selectWidgetForEditing(w);
                }
            });

            card.querySelector('.btn-edit').addEventListener('click', () => selectWidgetForEditing(w));
            card.querySelector('.btn-del').addEventListener('click', () => deleteWidget(w.id));

            // Render Chart inside canvas
            setTimeout(() => {
                renderWidgetChart(`canvas-widget-${w.id}`, w);
            }, 50);
        });
    }

    function renderWidgetChart(canvasId, widget) {
        const canvasEl = document.getElementById(canvasId);
        if (!canvasEl) return;
        const chartData = widget.chart_data;

        if (widget.visual_type === 'kpi') {
            const bodyEl = canvasEl.parentElement;
            bodyEl.innerHTML = `
                <div class="kpi-container">
                    <div class="kpi-big-number">${chartData.kpi_value !== undefined ? chartData.kpi_value.toLocaleString() : '0'}</div>
                    <div class="kpi-metric-name">${chartData.kpi_label || 'Metric'}</div>
                </div>`;
            return;
        }

        if (widget.visual_type === 'table') {
            const bodyEl = canvasEl.parentElement;
            let tableHtml = '<div style="overflow:auto; height:100%;"><table class="pbi-grid-table"><thead><tr>';
            (chartData.table_headers || []).forEach(h => tableHtml += `<th>${h}</th>`);
            tableHtml += '</tr></thead><tbody>';
            (chartData.raw_table || []).slice(0, 15).forEach(row => {
                tableHtml += '<tr>';
                Object.values(row).forEach(v => tableHtml += `<td>${v}</td>`);
                tableHtml += '</tr>';
            });
            tableHtml += '</tbody></table></div>';
            bodyEl.innerHTML = tableHtml;
            return;
        }

        if (widget.visual_type === 'scatter') {
            const palette = ['#00A4EF', '#1E3A8A', '#F97316', '#10B981', '#F59E0B', '#8B5CF6', '#EC4899', '#06B6D4', '#64748B'];
            const datasets = (chartData.datasets || []).map((ds, idx) => ({
                label: ds.label,
                data: ds.data,
                backgroundColor: ds.color || palette[idx % palette.length],
                borderColor: 'transparent',
                borderWidth: 0,
                pointRadius: 2.8,
                pointHoverRadius: 6,
                pointHitRadius: 7
            }));

            const chartObj = new Chart(canvasEl, {
                type: 'scatter',
                data: { datasets: datasets },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: false,
                    normalized: true,
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top',
                            align: 'start',
                            labels: {
                                color: '#94a3b8',
                                font: { size: 11, weight: '600' },
                                boxWidth: 10,
                                usePointStyle: true
                            }
                        },
                        zoom: {
                            zoom: {
                                wheel: { enabled: true },
                                drag: { enabled: true, backgroundColor: 'rgba(0, 164, 239, 0.25)', borderColor: '#00A4EF', borderWidth: 1 },
                                mode: 'xy'
                            },
                            pan: { enabled: true, mode: 'xy' }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(255, 255, 255, 0.96)',
                            titleColor: '#0f172a',
                            bodyColor: '#1e293b',
                            borderColor: '#cbd5e1',
                            borderWidth: 1,
                            padding: 10,
                            cornerRadius: 4,
                            displayColors: false,
                            bodyFont: { family: 'monospace', size: 12, weight: '600' },
                            callbacks: {
                                title: function() { return ''; },
                                label: function(context) {
                                    const groupColName = chartData.group_col || widget.group_by || 'Board';
                                    const xAxisName = widget.x_axis || 'Rectified Power [W]';
                                    const yAxisName = widget.y_axis || 'PFO [mW]';
                                    const boardName = context.dataset.label || 'N/A';
                                    const xVal = context.parsed.x;
                                    const yVal = context.parsed.y;

                                    return [
                                        `           ${groupColName}  ${boardName}`,
                                        `${xAxisName}  ${xVal}`,
                                        `        ${yAxisName}  ${yVal}`
                                    ];
                                }
                            }
                        }
                    },
                    onClick: (evt, activeElements) => {
                        if (activeElements && activeElements.length > 0) {
                            const datasetIndex = activeElements[0].datasetIndex;
                            const clickedLabel = chartObj.data.datasets[datasetIndex].label;
                            const groupColName = chartData.group_col || widget.group_by || 'Board';
                            if (clickedLabel) {
                                state.activeSlicers[groupColName] = [clickedLabel];
                                loadDashboard(state.activeDashboardId, true);
                                renderSlicerPills();
                                updateAllFilterCardSummaries();
                            }
                        }
                    },
                    scales: {
                        x: {
                            title: { display: true, text: widget.x_axis || 'Rectified Power [W]', color: '#94a3b8' },
                            grid: { color: 'rgba(255, 255, 255, 0.06)' }
                        },
                        y: {
                            title: { display: true, text: widget.y_axis || 'PFO [mW]', color: '#94a3b8' },
                            grid: { color: 'rgba(255, 255, 255, 0.06)' }
                        }
                    }
                }
            });

            // Double click to reset zoom
            canvasEl.addEventListener('dblclick', () => {
                if (chartObj.resetZoom) chartObj.resetZoom();
            });

            state.chartInstances[widget.id] = chartObj;
            return;
        }

        let chartType = widget.visual_type;
        let indexAxis = 'x';
        if (chartType === 'column') { chartType = 'bar'; indexAxis = 'x'; }
        if (chartType === 'bar') { chartType = 'bar'; indexAxis = 'y'; }
        if (chartType === 'area') { chartType = 'line'; }
        if (chartType === 'donut') { chartType = 'doughnut'; }

        const themeColors = ['#38bdf8', '#10b981', '#f59e0b', '#a855f7', '#ec4899', '#14b8a6', '#64748b'];

        const chartObj = new Chart(canvasEl, {
            type: chartType,
            data: {
                labels: chartData.labels || [],
                datasets: [{
                    label: widget.title,
                    data: chartData.datasets ? chartData.datasets[0].data : [],
                    backgroundColor: (chartType === 'pie' || chartType === 'doughnut') ? themeColors : 'rgba(56, 189, 248, 0.7)',
                    borderColor: (chartType === 'pie' || chartType === 'doughnut') ? '#1e293b' : '#38bdf8',
                    borderWidth: 1.5,
                    fill: (widget.visual_type === 'area')
                }]
            },
            options: {
                indexAxis: indexAxis,
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: (chartType === 'pie' || chartType === 'doughnut') }
                },
                onClick: (event, elementsArr) => {
                    if (elementsArr.length > 0) {
                        const index = elementsArr[0].index;
                        const clickedLabel = chartData.labels[index];
                        const xCol = chartData.x_col;

                        if (xCol && clickedLabel) {
                            toggleCrossFilterSlicer(xCol, clickedLabel);
                        }
                    }
                }
            }
        });

        state.chartInstances[widget.id] = chartObj;
    }

    // Cross-Filtering Slicers logic
    function toggleCrossFilterSlicer(col, val) {
        if (!state.activeSlicers[col]) {
            state.activeSlicers[col] = [val];
        } else {
            const idx = state.activeSlicers[col].indexOf(val);
            if (idx > -1) {
                state.activeSlicers[col].splice(idx, 1);
                if (state.activeSlicers[col].length === 0) {
                    delete state.activeSlicers[col];
                }
            } else {
                state.activeSlicers[col].push(val);
            }
        }
        loadDashboard(state.activeDashboardId, true);
    }

    function renderSlicerPills() {
        const container = elements.slicerPillsContainer;
        const keys = Object.keys(state.activeSlicers);

        if (keys.length === 0) {
            container.innerHTML = `<span class="no-slicers-text">No active filters (click chart elements to cross-filter)</span>`;
            return;
        }

        let html = '';
        keys.forEach(col => {
            const vals = state.activeSlicers[col];
            vals.forEach(v => {
                html += `
                    <div class="slicer-pill">
                        <span><strong>${col}:</strong> ${v}</span>
                        <i class="fa-solid fa-times" data-col="${col}" data-val="${v}"></i>
                    </div>`;
            });
        });

        container.innerHTML = html;

        container.querySelectorAll('i').forEach(icon => {
            icon.addEventListener('click', () => {
                toggleCrossFilterSlicer(icon.dataset.col, icon.dataset.val);
            });
        });
    }

    function clearAllSlicers() {
        state.activeSlicers = {};
        loadDashboard(state.activeDashboardId);
    }

    // Widget Edit / Save / Delete
    function selectWidgetForEditing(widget) {
        state.selectedWidgetId = widget.id;
        state.activeVisualType = widget.visual_type || 'scatter';

        elements.vizTitleInput.value = widget.title || '';
        elements.vizXSelect.value = widget.x_axis || '';
        elements.vizYSelect.value = widget.y_axis || '';
        if (elements.vizGroupSelect) elements.vizGroupSelect.value = widget.group_by || '';

        elements.vizTypePicker.querySelectorAll('.viz-type-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.type === widget.visual_type);
        });

        elements.lblSaveWidget.textContent = "Update Selected Visual";
        elements.btnDeleteWidget.style.display = "block";
        if (elements.btnResetVizForm) elements.btnResetVizForm.style.display = "inline-block";
        if (elements.vizModeStatus) {
            elements.vizModeStatus.innerHTML = `<i class="fa-solid fa-pen-to-square text-accent"></i> Editing: "${widget.title || 'Visual'}"`;
        }

        if (state.activeDashboard && state.activeDashboard.widgets) {
            renderCanvasWidgets(state.activeDashboard.widgets);
        }
    }

    function resetWidgetForm() {
        state.selectedWidgetId = null;
        elements.vizTitleInput.value = '';
        elements.lblSaveWidget.textContent = "Add Visual to Canvas";
        elements.btnDeleteWidget.style.display = "none";
        if (elements.btnResetVizForm) elements.btnResetVizForm.style.display = "none";
        if (elements.vizModeStatus) {
            elements.vizModeStatus.innerHTML = `<i class="fa-solid fa-plus text-primary"></i> Mode: New Visual`;
        }
        if (state.activeDashboard && state.activeDashboard.widgets) {
            renderCanvasWidgets(state.activeDashboard.widgets);
        }
    }

    async function saveWidget() {
        if (!state.activeDashboardId && elements.dashboardSelect.value) {
            state.activeDashboardId = parseInt(elements.dashboardSelect.value);
        }

        if (!state.activeDashboardId) {
            alert("Please select or create a dashboard first.");
            return;
        }

        const existingWidget = state.activeDashboard ? (state.activeDashboard.widgets || []).find(w => w.id === state.selectedWidgetId) : null;

        let xAxisVal = elements.vizXSelect.value;
        let yAxisVal = elements.vizYSelect.value;
        let groupVal = elements.vizGroupSelect ? elements.vizGroupSelect.value : '';

        if (!xAxisVal && existingWidget) xAxisVal = existingWidget.x_axis;
        if (!yAxisVal && existingWidget) yAxisVal = existingWidget.y_axis;
        if (!groupVal && existingWidget) groupVal = existingWidget.group_by;

        if (!xAxisVal && state.activeDataset && state.activeDataset.column_schema) {
            xAxisVal = state.activeDataset.column_schema[0].name;
        }
        if (!yAxisVal && state.activeDataset && state.activeDataset.column_schema) {
            const numCol = state.activeDataset.column_schema.find(c => c.type === 'numeric');
            yAxisVal = numCol ? numCol.name : (state.activeDataset.column_schema[1] ? state.activeDataset.column_schema[1].name : '');
        }

        const isFullWidthType = ['scatter', 'table', 'line', 'area'].includes(state.activeVisualType);
        const payload = {
            title: elements.vizTitleInput.value.trim() || `${state.activeVisualType.toUpperCase()} Chart`,
            visual_type: state.activeVisualType,
            x_axis: xAxisVal,
            y_axis: yAxisVal,
            group_by: groupVal,
            aggregation: 'AVG',
            width: isFullWidthType ? 12 : (existingWidget && existingWidget.width ? existingWidget.width : 6),
            height: isFullWidthType ? 7 : (existingWidget && existingWidget.height ? existingWidget.height : 5)
        };


        try {
            let res;
            let targetWidgetId = state.selectedWidgetId;

            if (targetWidgetId) {
                // Update existing widget
                res = await fetch(`/api/widgets/${targetWidgetId}/`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
            } else {
                // Create new widget
                res = await fetch(`/api/dashboards/${state.activeDashboardId}/widgets/`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (res.ok) {
                    const newWidgetData = await res.json();
                    if (newWidgetData && newWidgetData.id) {
                        targetWidgetId = newWidgetData.id;
                    }
                }
            }

            state.selectedWidgetId = targetWidgetId;
            await loadDashboard(state.activeDashboardId, true);

            // Re-sync UI state for the selected widget
            const currentWidget = state.activeDashboard ? (state.activeDashboard.widgets || []).find(w => w.id === state.selectedWidgetId) : null;
            if (currentWidget) {
                selectWidgetForEditing(currentWidget);
            }

        } catch (err) {
            console.error("Failed to save widget", err);
        }
    }

    async function deleteWidget(widgetId) {
        if (!confirm("Are you sure you want to delete this visual card?")) return;
        try {
            await fetch(`/api/widgets/${widgetId}/`, { method: 'DELETE' });
            resetWidgetForm();
            loadDashboard(state.activeDashboardId);
        } catch (err) {
            console.error("Failed to delete widget", err);
        }
    }

    function deleteSelectedWidget() {
        if (state.selectedWidgetId) {
            deleteWidget(state.selectedWidgetId);
        }
    }

    // Data View Tab Pagination & Grid
    async function loadDataViewRows() {
        if (!state.activeDatasetId) return;

        const ds = state.activeDataset;
        elements.dvDatasetTitle.textContent = ds ? ds.name : 'Dataset View';

        const queryParams = new URLSearchParams({
            page: state.dataView.page,
            page_size: state.dataView.pageSize,
            search: state.dataView.search,
            sort_col: state.dataView.sortCol,
            sort_dir: state.dataView.sortDir
        });

        try {
            const res = await fetch(`/api/datasets/${state.activeDatasetId}/rows/?${queryParams.toString()}`);
            const data = await res.json();

            elements.dvRowBadge.textContent = `${data.total_rows.toLocaleString()} Total Rows`;
            elements.dvPageInfo.textContent = `Page ${data.page} of ${data.total_pages}`;

            // Render Table Head
            let headHtml = '<tr>';
            (data.columns || []).forEach(col => {
                headHtml += `<th onclick="sortTable('${col}')">${col} <i class="fa-solid fa-sort"></i></th>`;
            });
            headHtml += '</tr>';
            elements.dvTableHead.innerHTML = headHtml;

            // Render Table Body
            let bodyHtml = '';
            (data.rows || []).forEach(row => {
                bodyHtml += '<tr>';
                Object.values(row).forEach(val => {
                    bodyHtml += `<td>${val}</td>`;
                });
                bodyHtml += '</tr>';
            });
            elements.dvTableBody.innerHTML = bodyHtml || '<tr><td colspan="100">No matching records found.</td></tr>';

        } catch (err) {
            console.error("Failed to load data view rows", err);
        }
    }

    window.sortTable = (colName) => {
        if (state.dataView.sortCol === colName) {
            state.dataView.sortDir = state.dataView.sortDir === 'asc' ? 'desc' : 'asc';
        } else {
            state.dataView.sortCol = colName;
            state.dataView.sortDir = 'asc';
        }
        loadDataViewRows();
    };

    // Upload Dataset Form
    async function handleDatasetUpload(e) {
        e.preventDefault();
        const formData = new FormData();
        formData.append('name', elements.uploadNameInput.value);
        formData.append('file', elements.uploadFileInput.files[0]);

        try {
            const res = await fetch('/api/datasets/', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (data.error) {
                alert(data.error);
                return;
            }

            closeModal(elements.modalGetData);
            elements.uploadForm.reset();
            await fetchDatasets();
            setDataset(data.dataset.id);
            if (window.openDataChatWithPrompt) {
                window.openDataChatWithPrompt('Summarize this dataset');
            }
        } catch (err) {
            console.error("Failed uploading dataset", err);
        }
    }

    // Connect MongoDB Server Collection Form
    async function handleMongoSubmit(e) {
        e.preventDefault();
        const payload = {
            name: elements.mongoNameInput.value.trim(),
            connection_url: elements.mongoUrlInput.value.trim(),
            db_name: elements.mongoDbNameInput.value.trim(),
            collection_name: elements.mongoCollInput.value.trim()
        };

        try {
            const res = await fetch('/api/datasets/mongodb/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.error) {
                alert(data.error);
                return;
            }

            closeModal(elements.modalGetData);
            elements.mongoForm.reset();
            await fetchDatasets();
            setDataset(data.dataset.id);
        } catch (err) {
            console.error("Failed connecting to MongoDB", err);
            alert("Failed connecting to MongoDB: " + err.message);
        }
    }

    async function handlePushMongoJson() {
        const payload = {
            connection_url: elements.mongoUrlInput.value.trim() || 'mongodb://192.168.100.123:27017',
            db_name: elements.mongoDbNameInput.value.trim() || 'GRL',
            collection_name: elements.mongoCollInput.value.trim() || '25MPLA'
        };

        if (!confirm(`Push data/GRL.25MPLA.json file into MongoDB server (${payload.connection_url}) -> Database: ${payload.db_name}, Collection: ${payload.collection_name}?`)) {
            return;
        }

        elements.btnPushMongoJson.disabled = true;
        elements.btnPushMongoJson.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Pushing JSON data to MongoDB...`;

        try {
            const res = await fetch('/api/mongodb/push_json/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (data.error) {
                alert("Error pushing JSON data: " + data.error);
            } else {
                alert(data.message || "Data pushed successfully!");
            }
        } catch (err) {
            alert("Error: " + err.message);
        } finally {
            elements.btnPushMongoJson.disabled = false;
            elements.btnPushMongoJson.innerHTML = `<i class="fa-solid fa-upload"></i> Push data/GRL.25MPLA.json to MongoDB`;
        }
    }

    // Populate New Dashboard Modal
    function populateNewDashboardModal() {
        elements.newDbTitle.value = '';
        renderDatasetDropdowns();
    }

    async function handleCreateDashboard(e) {
        e.preventDefault();
        const payload = {
            title: elements.newDbTitle.value,
            dataset_id: parseInt(elements.newDbDatasetSelect.value),
            theme: elements.newDbTheme.value
        };

        try {
            const res = await fetch('/api/dashboards/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            closeModal(elements.modalNewDashboard);
            await fetchDashboards();
            loadDashboard(data.id);
        } catch (err) {
            console.error("Failed creating dashboard", err);
        }
    }

    // Helper Utility
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Export CSV Ribbon Handler
    const ribbonCsvBtn = document.getElementById('ribbon-btn-csv');
    if (ribbonCsvBtn) {
        ribbonCsvBtn.addEventListener('click', () => {
            if (state.activeDatasetId) {
                window.location.href = `/export-csv/${state.activeDatasetId}/`;
            } else {
                alert("Please select a dataset first to export CSV data.");
            }
        });
    }

    // ==========================================================================
    // AI DATA CHAT ASSISTANT CONTROLLER
    // ==========================================================================
    function initDataChatController() {
        const chatDrawer = document.getElementById('pbi-chat-drawer');
        const chatFab = document.getElementById('pbi-chat-fab');
        const closeChatDrawer = document.getElementById('close-chat-drawer');
        const chatSelect = document.getElementById('chat-dataset-select');
        const chatActiveDsName = document.getElementById('chat-active-ds-name');
        const chatMessages = document.getElementById('chat-drawer-messages');
        const chatInput = document.getElementById('chat-input-textarea');
        const chatSendBtn = document.getElementById('chat-send-btn');
        const chatUploadBtn = document.getElementById('chat-upload-direct-btn');
        const chatDirectFileInput = document.getElementById('chat-direct-file-input');

        if (!chatDrawer) return;

        window.openDataChatWithPrompt = function(promptText) {
            chatDrawer.classList.add('open');
            updateChatDatasetBadge();
            if (promptText) {
                sendChatMessage(promptText);
            }
        };

        // Toggle Drawer
        if (chatFab) {
            chatFab.addEventListener('click', () => {
                chatDrawer.classList.toggle('open');
                updateChatDatasetBadge();
            });
        }

        if (closeChatDrawer) {
            closeChatDrawer.addEventListener('click', () => {
                chatDrawer.classList.remove('open');
            });
        }

        if (chatSelect) {
            chatSelect.addEventListener('change', (e) => {
                const selectedId = parseInt(e.target.value);
                if (selectedId) {
                    setDataset(selectedId);
                    updateChatDatasetBadge();
                }
            });
        }

        // Direct File Upload in Chat Drawer
        if (chatUploadBtn && chatDirectFileInput) {
            chatUploadBtn.addEventListener('click', () => chatDirectFileInput.click());
            chatDirectFileInput.addEventListener('change', async (e) => {
                const file = e.target.files[0];
                if (!file) return;

                const formData = new FormData();
                formData.append('name', file.name.replace(/\.[^/.]+$/, ""));
                formData.append('file', file);

                appendChatMessage('assistant', `<i class="fa-solid fa-spinner fa-spin text-accent"></i> Uploading <strong>${escapeHtml(file.name)}</strong>...`);

                try {
                    const response = await fetch('/api/datasets/', {
                        method: 'POST',
                        body: formData
                    });
                    const resData = await response.json();
                    if (response.ok && resData.dataset) {
                        await fetchDatasets();
                        setDataset(resData.dataset.id);
                        if (chatSelect) chatSelect.value = resData.dataset.id;
                        updateChatDatasetBadge();
                        sendChatMessage('Summarize this dataset');
                    } else {
                        appendChatMessage('assistant', `⚠️ Failed to upload file: ${resData.error || 'Unknown error'}`);
                    }
                } catch (err) {
                    appendChatMessage('assistant', `⚠️ Upload error: ${err.message}`);
                }
                chatDirectFileInput.value = '';
            });
        }

        // Send Buttons & Enter Key
        if (chatSendBtn && chatInput) {
            chatSendBtn.addEventListener('click', () => sendChatMessage());
            chatInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendChatMessage();
                }
            });
        }

        // Event delegation for Quick Prompt Chips
        if (chatMessages) {
            chatMessages.addEventListener('click', (e) => {
                const chip = e.target.closest('.quick-prompt-chip');
                if (chip && chip.dataset.prompt) {
                    sendChatMessage(chip.dataset.prompt);
                }
            });
        }

        function updateChatDatasetBadge() {
            const currentDs = state.datasets.find(d => d.id === (state.activeDatasetId || (chatSelect ? parseInt(chatSelect.value) : null)));
            if (chatActiveDsName) {
                chatActiveDsName.textContent = currentDs ? `${currentDs.name} (${currentDs.row_count} rows)` : 'Select Dataset';
            }
            if (chatSelect && state.activeDatasetId) {
                chatSelect.value = state.activeDatasetId;
            }
        }

        function sendChatMessage(overrideText) {
            const queryText = overrideText || (chatInput ? chatInput.value.trim() : '');
            if (!queryText) return;

            if (chatInput) chatInput.value = '';

            const dsId = state.activeDatasetId || (chatSelect ? parseInt(chatSelect.value) : null);
            if (!dsId) {
                appendChatMessage('assistant', '⚠️ Please select or upload a dataset first to start chatting.');
                return;
            }

            appendChatMessage('user', queryText);

            const typingId = 'typing-' + Date.now();
            const typingHtml = `<div class="chat-msg-row assistant-msg" id="${typingId}">
                <div class="chat-avatar"><i class="fa-solid fa-robot"></i></div>
                <div class="chat-msg-bubble"><i class="fa-solid fa-spinner fa-spin text-accent"></i> Analyzing dataset...</div>
            </div>`;
            chatMessages.insertAdjacentHTML('beforeend', typingHtml);
            chatMessages.scrollTop = chatMessages.scrollHeight;

            fetch(`/api/datasets/${dsId}/chat/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: queryText })
            })
            .then(res => res.json())
            .then(data => {
                document.getElementById(typingId)?.remove();
                if (data.status === 'success' && data.data) {
                    renderChatResponse(data.data);
                } else {
                    appendChatMessage('assistant', `⚠️ ${data.error || 'Failed to process chat query.'}`);
                }
            })
            .catch(err => {
                document.getElementById(typingId)?.remove();
                appendChatMessage('assistant', `⚠️ Request error: ${err.message}`);
            });
        }

        function appendChatMessage(role, content, isRawHtml = false) {
            if (!chatMessages) return;
            const isUser = role === 'user';
            const avatarIcon = isUser ? 'fa-user' : 'fa-robot';
            const formattedContent = isRawHtml ? content : escapeHtml(content);

            const msgHtml = `
                <div class="chat-msg-row ${isUser ? 'user-msg' : 'assistant-msg'}">
                    <div class="chat-avatar"><i class="fa-solid ${avatarIcon}"></i></div>
                    <div class="chat-msg-bubble">${formattedContent}</div>
                </div>`;
            chatMessages.insertAdjacentHTML('beforeend', msgHtml);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        function renderChatResponse(res) {
            let bubbleHtml = `<div class="chat-response-text">${formatMarkdown(res.response)}</div>`;

            if (res.kpis && res.kpis.length > 0) {
                bubbleHtml += `<div class="chat-kpis-grid">`;
                res.kpis.forEach(k => {
                    bubbleHtml += `<div class="chat-kpi-card">
                        <div class="kpi-lbl">${escapeHtml(k.label)}</div>
                        <div class="kpi-val">${escapeHtml(String(k.value))}</div>
                    </div>`;
                });
                bubbleHtml += `</div>`;
            }

            if (res.table && res.table.headers && res.table.rows && res.table.rows.length > 0) {
                bubbleHtml += `<div class="chat-table-wrapper"><table class="chat-table"><thead><tr>`;
                res.table.headers.forEach(h => {
                    bubbleHtml += `<th>${escapeHtml(h)}</th>`;
                });
                bubbleHtml += `</tr></thead><tbody>`;
                res.table.rows.forEach(r => {
                    bubbleHtml += `<tr>`;
                    res.table.headers.forEach(h => {
                        bubbleHtml += `<td>${escapeHtml(String(r[h] !== undefined ? r[h] : ''))}</td>`;
                    });
                    bubbleHtml += `</tr>`;
                });
                bubbleHtml += `</tbody></table></div>`;
            }

            if (res.suggested_prompts && res.suggested_prompts.length > 0) {
                bubbleHtml += `<div class="chat-quick-prompts-container">`;
                res.suggested_prompts.forEach(p => {
                    bubbleHtml += `<button class="quick-prompt-chip" data-prompt="${escapeHtml(p)}"><i class="fa-solid fa-lightbulb text-warning"></i> ${escapeHtml(p)}</button>`;
                });
                bubbleHtml += `</div>`;
            }

            appendChatMessage('assistant', bubbleHtml, true);
        }

        function formatMarkdown(str) {
            if (!str) return '';
            return escapeHtml(str)
                .replace(/\n/g, '<br>')
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/`([^`]+)`/g, '<code>$1</code>');
        }

        function escapeHtml(str) {
            if (!str) return '';
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;');
        }

        // Connect Top Ribbon Search Bar ("Ask Telemetry AI") to Data Chat
        const aiQaInput = document.getElementById('input-ai-qa');
        if (aiQaInput) {
            aiQaInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    const q = aiQaInput.value.trim();
                    if (!q) return;
                    chatDrawer.classList.add('open');
                    updateChatDatasetBadge();
                    sendChatMessage(q);
                }
            });
        }
    }

    // --------------------------------------------------------------------------
    // ENTERPRISE ADVANCED FEATURES: AI Auto-DB, Anomalies, Wrangler, Joiner
    // --------------------------------------------------------------------------
    async function triggerAutoBuildDashboard() {
        if (!state.activeDatasetId) {
            alert("Please select a dataset first to auto-build an AI dashboard.");
            return;
        }

        const rAutoDb = document.getElementById('ribbon-btn-autodb');
        const origText = rAutoDb ? rAutoDb.innerHTML : '';
        if (rAutoDb) rAutoDb.innerHTML = '<i class="fa-solid fa-spinner fa-spin text-warning"></i> Building AI Studio...';

        try {
            const res = await fetch(`/api/datasets/${state.activeDatasetId}/auto-dashboard/`, { method: 'POST' });
            const data = await res.json();
            if (data.dashboard_id) {
                await fetchDashboards();
                loadDashboard(data.dashboard_id);
                switchView('report');
                alert(`🎉 AI Dashboard "${data.title}" generated successfully!`);
            } else {
                alert(`⚠️ ${data.error || 'Failed to auto-generate dashboard.'}`);
            }
        } catch (err) {
            alert(`⚠️ Error auto-building dashboard: ${err.message}`);
        } finally {
            if (rAutoDb) rAutoDb.innerHTML = origText;
        }
    }

    async function handleCleanDataset(e) {
        e.preventDefault();
        if (!state.activeDatasetId) return;

        const fillMethod = document.getElementById('clean-null-select')?.value;
        const removeDuplicates = document.getElementById('clean-dup-check')?.checked;
        const dropNulls = document.getElementById('clean-dropnull-check')?.checked;

        try {
            const res = await fetch(`/api/datasets/${state.activeDatasetId}/clean/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ fill_method: fillMethod, remove_duplicates: removeDuplicates, drop_nulls: dropNulls })
            });
            const data = await res.json();
            if (res.ok) {
                closeModal(document.getElementById('modal-clean-data'));
                await fetchDatasets();
                setDataset(state.activeDatasetId);
                alert(`✨ Data Cleaning Completed! ${data.message}`);
            } else {
                alert(`⚠️ Cleaning Error: ${data.error}`);
            }
        } catch (err) {
            alert(`⚠️ Error cleaning dataset: ${err.message}`);
        }
    }

    async function handleAddMeasure(e) {
        e.preventDefault();
        if (!state.activeDatasetId) return;

        const name = document.getElementById('measure-name-input')?.value;
        const formula = document.getElementById('measure-formula-input')?.value;

        try {
            const res = await fetch(`/api/datasets/${state.activeDatasetId}/measures/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name, formula: formula })
            });
            const data = await res.json();
            if (res.ok) {
                closeModal(document.getElementById('modal-add-measure'));
                document.getElementById('add-measure-form')?.reset();
                await fetchDatasets();
                setDataset(state.activeDatasetId);
                alert(`➕ Calculated measure '${data.name}' added successfully!`);
            } else {
                alert(`⚠️ Measure Error: ${data.error}`);
            }
        } catch (err) {
            alert(`⚠️ Error adding measure: ${err.message}`);
        }
    }

    function populateJoinDatasetsModal() {
        const ds1Select = document.getElementById('join-ds1-select');
        const ds2Select = document.getElementById('join-ds2-select');
        if (!ds1Select || !ds2Select) return;

        let optionsHtml = '';
        state.datasets.forEach(ds => {
            optionsHtml += `<option value="${ds.id}">${ds.name} (${ds.row_count} rows)</option>`;
        });
        ds1Select.innerHTML = optionsHtml;
        ds2Select.innerHTML = optionsHtml;
        if (state.activeDatasetId) {
            ds1Select.value = state.activeDatasetId;
        }
    }

    async function handleJoinDatasets(e) {
        e.preventDefault();
        const name = document.getElementById('join-name-input')?.value;
        const ds1Id = document.getElementById('join-ds1-select')?.value;
        const ds2Id = document.getElementById('join-ds2-select')?.value;
        const key1 = document.getElementById('join-key1-input')?.value;
        const key2 = document.getElementById('join-key2-input')?.value;
        const joinType = document.getElementById('join-type-select')?.value;

        try {
            const res = await fetch('/api/datasets/join/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: name,
                    dataset1_id: ds1Id,
                    dataset2_id: ds2Id,
                    key_col1: key1,
                    key_col2: key2,
                    join_type: joinType
                })
            });
            const data = await res.json();
            if (res.ok && data.dataset) {
                closeModal(document.getElementById('modal-join-datasets'));
                document.getElementById('join-datasets-form')?.reset();
                await fetchDatasets();
                setDataset(data.dataset.id);
                alert(`🔗 Datasets merged successfully! Created '${data.dataset.name}' (${data.dataset.row_count} rows).`);
            } else {
                alert(`⚠️ Dataset Merge Error: ${data.error}`);
            }
        } catch (err) {
            alert(`⚠️ Error merging datasets: ${err.message}`);
        }
    }

    function toggleKioskMode() {
        state.isKiosk = !state.isKiosk;
        if (state.isKiosk) {
            document.body.requestFullscreen?.().catch(() => {});
            document.body.classList.add('kiosk-mode');
            alert("📺 Executive Kiosk Presentation Mode Activated! Press ESC to exit.");
        } else {
            document.exitFullscreen?.().catch(() => {});
            document.body.classList.remove('kiosk-mode');
        }
    }
});


