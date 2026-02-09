<script lang="ts">
  'use legacy';
  import { get } from 'svelte/store';
  import { API_URL, MOCK_USER_HEADER, PERMISSIONS } from '$lib/config';
  import { activeUser, hasPermission } from '$lib/stores/mockUsers';
  import type { MockUser } from '$lib/stores/mockUsers';

  const EXPORT_CONTAINER_FIELDS = [
    { key: 'qr_code', label: 'QR code' },
    { key: 'name', label: 'Container name' }
  ] as const;
  const EXPORT_ITEM_FIELDS = [
    { key: 'name', label: 'Item name' },
    { key: 'quantity', label: 'Item quantity' }
  ] as const;
  const DETAIL_SUGGESTIONS = ['Condition', 'Volume', 'Size', 'Notes', 'Color', 'Value', 'Serial Number'];
  type DetailMode = 'auto' | 'custom' | 'none';
  type ContainerSummary = {
    qr_code: string;
    name: string;
  };

  const userStore = activeUser;

  let activePersona: MockUser | null = null;
  let canView = false;

  let exportContainerFields = EXPORT_CONTAINER_FIELDS.map((field) => field.key);
  let exportItemFields = EXPORT_ITEM_FIELDS.map((field) => field.key);
  let exportDetailMode: DetailMode = 'auto';
  let exportDetailInput = '';
  let exportNameFilter = '';
  let exportQuantityFilter = '';
  let exportDetailFilterKey = '';
  let exportDetailFilterValue = '';
  let exportBusy = false;
  let exportError = '';
  let exportSuccess = '';
  let availableContainers: ContainerSummary[] = [];
  let selectedContainerQrs: string[] = [];
  let containersLoading = false;
  let containersError = '';
  let containersLoaded = false;

  $: activePersona = $activeUser ?? null;
  $: canView = hasPermission(activePersona, PERMISSIONS.view);
  $: {
    if (canView && activePersona?.id && !containersLoaded && !containersLoading) {
      void loadContainers();
    }
  }

  function authHeaders() {
    const user = get(userStore);
    if (!user) {
      throw new Error('Select a persona before exporting.');
    }

    return {
      [MOCK_USER_HEADER]: user.id
    };
  }

  function toggleField(list: string[], key: string) {
    return list.includes(key) ? list.filter((entry) => entry !== key) : [...list, key];
  }

  function splitDetailInput(value: string) {
    return value
      .split(',')
      .map((token) => token.trim())
      .filter((token) => Boolean(token));
  }

  async function loadContainers() {
    containersLoading = true;
    containersError = '';

    try {
      const res = await fetch(`${API_URL}/containers`, {
        headers: authHeaders()
      });
      if (!res.ok) {
        throw new Error('Unable to load containers');
      }

      const data = await res.json();
      if (Array.isArray(data)) {
        availableContainers = data.map((container) => ({
          qr_code: container.qr_code,
          name: container.name
        }));
      } else {
        availableContainers = [];
      }
      containersLoaded = true;
    } catch (err) {
      containersError = err instanceof Error ? err.message : 'Unable to load containers';
    } finally {
      containersLoading = false;
    }
  }

  async function downloadExport() {
    if (!canView) {
      exportError = 'You do not have permission to export containers.';
      exportSuccess = '';
      return;
    }

    const customDetailKeys = exportDetailMode === 'custom' ? splitDetailInput(exportDetailInput) : [];
    if (exportDetailMode === 'custom' && !customDetailKeys.length) {
      exportError = 'Enter at least one detail label or switch to auto detail columns.';
      exportSuccess = '';
      return;
    }

    if (
      !exportContainerFields.length &&
      !exportItemFields.length &&
      (exportDetailMode === 'none' || (exportDetailMode === 'custom' && !customDetailKeys.length))
    ) {
      exportError = 'Select at least one column before exporting.';
      exportSuccess = '';
      return;
    }

    exportBusy = true;
    exportError = '';
    exportSuccess = '';

    try {
      const params = new URLSearchParams();

      if (exportContainerFields.length) {
        exportContainerFields.forEach((field) => params.append('container_fields', field));
      } else {
        params.append('container_fields', '');
      }

      if (exportItemFields.length) {
        exportItemFields.forEach((field) => params.append('item_fields', field));
      } else {
        params.append('item_fields', '');
      }

      if (exportDetailMode === 'custom') {
        customDetailKeys.forEach((key) => params.append('detail_keys', key));
      } else if (exportDetailMode === 'none') {
        params.append('detail_keys', '');
      }

      if (exportNameFilter.trim()) {
        params.append('item_filter', `name:${exportNameFilter.trim()}`);
      }

      if (exportQuantityFilter.trim()) {
        params.append('item_filter', `quantity:${exportQuantityFilter.trim()}`);
      }

      if (exportDetailFilterKey.trim() && exportDetailFilterValue.trim()) {
        params.append(
          'item_filter',
          `detail.${exportDetailFilterKey.trim()}:${exportDetailFilterValue.trim()}`
        );
      }

      if (selectedContainerQrs.length) {
        selectedContainerQrs.forEach((qr) => params.append('container_qr', qr));
      }

      const query = params.toString();
      const url = query ? `${API_URL}/containers/export?${query}` : `${API_URL}/containers/export`;

      const res = await fetch(url, {
        headers: authHeaders()
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || 'Export failed');
      }

      if (typeof window === 'undefined') {
        exportSuccess = 'CSV generated.';
        return;
      }

      const blob = await res.blob();
      const downloadUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `containers-${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(downloadUrl);
      exportSuccess = 'CSV download started.';
    } catch (err) {
      exportError = err instanceof Error ? err.message : 'Failed to export containers.';
    } finally {
      exportBusy = false;
    }
  }
</script>

<main class="export-page">
  <h1>Export Containers</h1>
  <p class="intro">
    Build a CSV of all containers or filter down to just the rows and columns you care about.
  </p>

  <section class="card">
    <div class="section-header">
      <div>
        <h2>Containers</h2>
        <p class="muted">
          Optionally pick specific containers to export. Leave all unchecked to include everything.
        </p>
      </div>
    </div>

    {#if containersLoading}
      <p class="muted">Loading containers...</p>
    {:else if containersError}
      <p class="error">{containersError}</p>
    {:else if availableContainers.length}
      <div class="container-list">
        {#each availableContainers as container}
          <label class="checkbox">
            <input
              type="checkbox"
              checked={selectedContainerQrs.includes(container.qr_code)}
              onchange={() => {
                selectedContainerQrs = toggleField(selectedContainerQrs, container.qr_code);
              }}
            />
            <span class="container-label">
              <span class="container-qr">{container.qr_code}</span>
              <span class="container-name">{container.name}</span>
            </span>
          </label>
        {/each}
      </div>
    {:else}
      <p class="muted">No containers available to export yet.</p>
    {/if}
  </section>

  <section class="card">
    <div class="section-header">
      <div>
        <h2>Columns</h2>
        <p class="muted">Choose which container and item fields to include.</p>
      </div>
    </div>

    <div class="fields-grid">
      <div>
        <p class="field-label">Container</p>
        {#each EXPORT_CONTAINER_FIELDS as field}
          <label class="checkbox">
            <input
              type="checkbox"
              checked={exportContainerFields.includes(field.key)}
              onchange={() => {
                exportContainerFields = toggleField(exportContainerFields, field.key);
              }}
            />
            <span>{field.label}</span>
          </label>
        {/each}
      </div>
      <div>
        <p class="field-label">Items</p>
        {#each EXPORT_ITEM_FIELDS as field}
          <label class="checkbox">
            <input
              type="checkbox"
              checked={exportItemFields.includes(field.key)}
              onchange={() => {
                exportItemFields = toggleField(exportItemFields, field.key);
              }}
            />
            <span>{field.label}</span>
          </label>
        {/each}
      </div>
    </div>
  </section>

  <section class="card">
    <h2>Detail columns</h2>
    <p class="muted">
      Include item detail metadata automatically or specify which labels you want.
    </p>
    <label class="radio">
      <input
        type="radio"
        name="detail-mode"
        value="auto"
        checked={exportDetailMode === 'auto'}
        onchange={() => {
          exportDetailMode = 'auto';
        }}
      />
      <span>Include all detected detail labels</span>
    </label>
    <label class="radio">
      <input
        type="radio"
        name="detail-mode"
        value="custom"
        checked={exportDetailMode === 'custom'}
        onchange={() => {
          exportDetailMode = 'custom';
        }}
      />
      <span>Only these labels</span>
    </label>
    {#if exportDetailMode === 'custom'}
      <input
        type="text"
        placeholder='Comma-separated (e.g. Color, "Serial Number")'
        value={exportDetailInput}
        oninput={(event) => {
          exportDetailInput = (event.currentTarget as HTMLInputElement).value;
        }}
      />
      <p class="muted small">Suggestions: {DETAIL_SUGGESTIONS.join(', ')}</p>
    {/if}
    <label class="radio">
      <input
        type="radio"
        name="detail-mode"
        value="none"
        checked={exportDetailMode === 'none'}
        onchange={() => {
          exportDetailMode = 'none';
        }}
      />
      <span>Exclude detail columns</span>
    </label>
  </section>

  {#if false}
    <section class="card">
      <h2>Filter items</h2>
      <p class="muted">
        Filters apply before we generate the CSV so you only download the rows you need.
      </p>
      <div class="filters-grid">
        <label>
          <span>Item name contains</span>
          <input
            type="text"
            value={exportNameFilter}
            oninput={(event) => {
              exportNameFilter = (event.currentTarget as HTMLInputElement).value;
            }}
          />
        </label>
        <label>
          <span>Quantity equals</span>
          <input
            type="number"
            min="0"
            inputmode="numeric"
            value={exportQuantityFilter}
            oninput={(event) => {
              exportQuantityFilter = (event.currentTarget as HTMLInputElement).value;
            }}
          />
        </label>
        <label>
          <span>Detail key</span>
          <input
            type="text"
            value={exportDetailFilterKey}
            oninput={(event) => {
              exportDetailFilterKey = (event.currentTarget as HTMLInputElement).value;
            }}
          />
        </label>
        <label>
          <span>Detail value contains</span>
          <input
            type="text"
            value={exportDetailFilterValue}
            oninput={(event) => {
              exportDetailFilterValue = (event.currentTarget as HTMLInputElement).value;
            }}
          />
        </label>
      </div>
      <p class="muted small">
        Detail filters map to <code>detail.&lt;key&gt;</code> entries (e.g. key <em>Color</em>, value <em>Red</em>).
      </p>
    </section>
  {/if}

  <section class="card">
    <h2>Download CSV</h2>
    <p class="muted">Confirm your selections then start the download.</p>

    {#if exportError}
      <p class="error">{exportError}</p>
    {:else if exportSuccess}
      <p class="success">{exportSuccess}</p>
    {/if}

    <button type="button" class="primary export-button" onclick={downloadExport} disabled={exportBusy || !canView}>
      {exportBusy ? 'Preparing…' : 'Download CSV'}
    </button>

    {#if !canView}
      <p class="muted small">Switch to a persona with view access to export data.</p>
    {/if}
  </section>
</main>

<style>
  .export-page {
    max-width: 900px;
    margin: 0 auto;
    padding: 40px 20px 80px;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  h1 {
    text-align: center;
    margin-bottom: 6px;
  }

  .intro {
    text-align: center;
    margin-bottom: 24px;
    color: var(--color-text-muted);
  }

  .card {
    border-radius: 16px;
    padding: 24px;
    border: 1px solid var(--color-border);
    box-shadow: var(--shadow-card);
    background: var(--color-card-alt);
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .fields-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 24px;
  }

  .container-list {
    display: grid;
    gap: 10px;
    max-height: 280px;
    overflow: auto;
    padding-right: 4px;
  }

  .container-label {
    display: inline-flex;
    flex-direction: column;
    gap: 2px;
  }

  .container-qr {
    font-weight: 600;
  }

  .container-name {
    font-size: 0.85rem;
    color: var(--color-text-muted);
  }

  .field-label {
    font-weight: 600;
    margin-bottom: 6px;
  }

  .checkbox,
  .radio {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.95rem;
  }

  input[type='text'],
  input[type='number'] {
    border: 1px solid var(--color-border);
    border-radius: 8px;
    padding: 8px 10px;
    background: var(--color-card);
    color: inherit;
    width: 100%;
  }

  /* .filters-grid {
    display: grid;
    gap: 12px;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  } */

  .small {
    font-size: 0.85rem;
  }

  button.export-button {
    align-self: flex-start;
  }

  .error {
    color: var(--color-danger, #c62828);
    font-weight: 600;
  }

  .success {
    color: var(--color-success, #2e7d32);
    font-weight: 600;
  }
</style>
