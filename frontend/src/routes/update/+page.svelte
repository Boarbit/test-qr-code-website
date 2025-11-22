<script lang="ts">
  'use legacy';
  import { get } from 'svelte/store';
  import { API_URL, MOCK_USER_HEADER, PERMISSIONS } from '$lib/config';
  import QrScanner from '$lib/components/QrScanner.svelte';
  import { activeUser, hasPermission } from '$lib/stores/mockUsers';
  import type { MockUser } from '$lib/stores/mockUsers';

  type ItemDetailArray = Array<{ label: string; value: string }>;
  type ItemDetails = Record<string, string> | ItemDetailArray;

  type ContainerItem = {
    name: string;
    quantity: number;
    details?: ItemDetails;
  };

  type ContainerDto = {
    qr_code: string;
    name: string;
    contents: ContainerItem[];
  };

  type ItemExtraField = {
    id: number;
    label: string;
    value: string;
  };

  type ItemForm = {
    id: number;
    name: string;
    quantity: string;
    extras: ItemExtraField[];
  };

  type ContainerItemDto = {
    name: string;
    quantity: number;
    details?: Record<string, string>;
  };

  const userStore = activeUser;
  const DETAIL_FIELD_OPTIONS = ['Condition', 'Volume', 'Size', 'Notes', 'Color', 'Value', 'Serial Number'] as const;
  const DETAIL_PLACEHOLDERS: Record<string, string> = {
    Condition: 'e.g. Mint',
    Volume: 'e.g. 2.5 L',
    Size: 'e.g. 12" x 8"',
    Notes: 'e.g. Handle with care',
    Color: 'e.g. Red',
    Value: 'e.g. $150',
    'Serial Number': 'e.g. SN1234'
  };

  let itemId = 0;
  let extraFieldId = 0;

  let qrInput = '';
  let loadedQr = '';
  let containerName = '';
  let items: ItemForm[] = [createEmptyItem()];

  let activePersona: MockUser | null = null;
  let canView = false;
  let canUpdate = false;

  let loading = false;
  let loadError = '';
  let loadSuccess = '';
  let loadSequence = 0;

  let updating = false;
  let updateError = '';
  let updateSuccess = '';

  $: activePersona = $activeUser ?? null;
  $: canView = hasPermission(activePersona, PERMISSIONS.view);
  $: canUpdate = hasPermission(activePersona, PERMISSIONS.update);

  function authHeaders() {
    const user = get(userStore);
    if (!user) {
      throw new Error('Select a persona before continuing.');
    }

    return {
      [MOCK_USER_HEADER]: user.id
    };
  }

  function createEmptyItem(): ItemForm {
    return {
      id: nextItemId(),
      name: '',
      quantity: '',
      extras: []
    };
  }

  function nextItemId() {
    itemId += 1;
    return itemId;
  }

  function nextExtraFieldId() {
    extraFieldId += 1;
    return extraFieldId;
  }

  function extrasFromDetails(details?: ItemDetails): ItemExtraField[] {
    if (!details) {
      return [];
    }

    const entries = Array.isArray(details)
      ? details.map(({ label, value }) => [label ?? '', value ?? ''] as [string, string])
      : Object.entries(details).map(([label, value]) => [label ?? '', value ?? ''] as [string, string]);

    return entries
      .map(([label, value]) => ({
        id: nextExtraFieldId(),
        label: label || DETAIL_FIELD_OPTIONS[0],
        value: value == null ? '' : String(value)
      }))
      .filter((extra) => extra.label.trim());
  }

  function detailPlaceholder(label: string) {
    const normalized = label || DETAIL_FIELD_OPTIONS[0];
    return DETAIL_PLACEHOLDERS[normalized] ?? 'Value';
  }

  function convertItem(item: ContainerItem): ItemForm {
    return {
      id: nextItemId(),
      name: item.name ?? '',
      quantity: item.quantity != null ? `${item.quantity}` : '',
      extras: extrasFromDetails(item.details)
    };
  }

  function handleScannerResult(text: string) {
    const trimmed = text.trim();
    if (!trimmed) {
      return;
    }

    qrInput = trimmed;
    void loadContainer(trimmed);
  }

  async function loadContainer(forcedCode?: string) {
    const target = (forcedCode ?? qrInput).trim();
    if (!target) {
      loadError = 'Enter or scan a QR code to load the container.';
      loadSuccess = '';
      return;
    }

    if (!canView) {
      loadError = 'You do not have permission to view containers.';
      loadSuccess = '';
      return;
    }

    const requestId = ++loadSequence;
    loading = true;
    loadError = '';
    updateError = '';
    updateSuccess = '';

    try {
      const res = await fetch(`${API_URL}/containers/${encodeURIComponent(target)}`, {
        headers: authHeaders()
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || 'Container not found.');
      }

      const data: ContainerDto = await res.json();
      if (requestId === loadSequence) {
        applyLoadedContainer(data);
        loadSuccess = `Loaded container ${data.name || data.qr_code}.`;
      }
    } catch (err) {
      if (requestId === loadSequence) {
        loadError = err instanceof Error ? err.message : 'Failed to load container.';
      }
    } finally {
      if (requestId === loadSequence) {
        loading = false;
      }
    }
  }

  function applyLoadedContainer(container: ContainerDto) {
    loadedQr = container.qr_code;
    containerName = container.name ?? '';
    qrInput = container.qr_code;
    items = container.contents?.length ? container.contents.map(convertItem) : [createEmptyItem()];
  }

  function resetEditor() {
    loadedQr = '';
    containerName = '';
    items = [createEmptyItem()];
    qrInput = '';
    loadError = '';
    loadSuccess = '';
    updateError = '';
    updateSuccess = '';
  }

  function addItem() {
    items = [...items, createEmptyItem()];
  }

  function removeItem(index: number) {
    if (items.length === 1) {
      items = [createEmptyItem()];
      return;
    }
    items = items.filter((_, i) => i !== index);
  }

  function updateItemName(index: number, value: string) {
    items = items.map((item, i) => (i === index ? { ...item, name: value } : item));
  }

  function updateItemQuantity(index: number, value: string) {
    items = items.map((item, i) => (i === index ? { ...item, quantity: value } : item));
  }

  function addItemDetail(index: number) {
    items = items.map((item, i) =>
      i === index
        ? {
            ...item,
            extras: [
              ...item.extras,
              { id: nextExtraFieldId(), label: DETAIL_FIELD_OPTIONS[0], value: '' }
            ]
          }
        : item
    );
  }

  function updateItemDetailLabel(index: number, detailId: number, value: string) {
    items = items.map((item, i) => {
      if (i !== index) {
        return item;
      }
      return {
        ...item,
        extras: item.extras.map((extra) =>
          extra.id === detailId ? { ...extra, label: value } : extra
        )
      };
    });
  }

  function updateItemDetailValue(index: number, detailId: number, value: string) {
    items = items.map((item, i) => {
      if (i !== index) {
        return item;
      }
      return {
        ...item,
        extras: item.extras.map((extra) =>
          extra.id === detailId ? { ...extra, value } : extra
        )
      };
    });
  }

  function removeItemDetail(index: number, detailId: number) {
    items = items.map((item, i) => {
      if (i !== index) {
        return item;
      }
      return {
        ...item,
        extras: item.extras.filter((extra) => extra.id !== detailId)
      };
    });
  }

  function sanitizedItems(): ContainerItemDto[] {
    return items
      .map((item) => {
        const trimmedName = item.name.trim();
        const safeQuantity = toSafeQuantity(item.quantity);

        const detailEntries = item.extras
          .map((extra) => {
            const label = (extra.label || DETAIL_FIELD_OPTIONS[0]).trim();
            const value = extra.value.trim();
            return label && value ? [label, value] : null;
          })
          .filter((pair): pair is [string, string] => Boolean(pair));

        const sanitized: ContainerItemDto = {
          name: trimmedName,
          quantity: safeQuantity
        };

        if (detailEntries.length) {
          sanitized.details = Object.fromEntries(detailEntries);
        }

        const hasAny = Boolean(trimmedName || safeQuantity > 0 || detailEntries.length);
        return { sanitized, hasAny };
      })
      .filter(({ hasAny }) => hasAny)
      .map(({ sanitized }) => sanitized);
  }

  function toSafeQuantity(raw: string): number {
    const trimmed = raw.trim();
    if (!trimmed) {
      return 0;
    }

    const parsed = Number.parseInt(trimmed, 10);
    if (Number.isFinite(parsed) && parsed >= 0) {
      return parsed;
    }

    return 0;
  }

  async function submitUpdate() {
    if (!canUpdate) {
      updateError = 'You do not have permission to update containers.';
      updateSuccess = '';
      return;
    }

    const targetQr = loadedQr.trim();
    if (!targetQr) {
      updateError = 'Load a container before saving updates.';
      updateSuccess = '';
      return;
    }

    const trimmedName = containerName.trim();
    if (!trimmedName) {
      updateError = 'Enter a container name.';
      updateSuccess = '';
      return;
    }

    const contents = sanitizedItems();
    if (!contents.length) {
      updateError = 'Add at least one item or quantity before saving.';
      updateSuccess = '';
      return;
    }

    const payload = {
      qr_code: targetQr,
      name: trimmedName,
      contents
    };

    updating = true;
    updateError = '';
    updateSuccess = '';

    try {
      const headers = {
        'Content-Type': 'application/json',
        ...authHeaders()
      };

      const res = await fetch(`${API_URL}/containers/${encodeURIComponent(targetQr)}`, {
        method: 'PUT',
        headers,
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || 'Failed to update container.');
      }

      const data: ContainerDto = await res.json();
      applyLoadedContainer(data);
      updateSuccess = 'Container updated successfully.';
    } catch (err) {
      updateError = err instanceof Error ? err.message : 'Failed to update container.';
    } finally {
      updating = false;
    }
  }
</script>

<main class="update-page">
  <h1>Update a Container</h1>
  <p class="intro">
    Scan a QR code to load the latest contents, adjust the items, and push your updates back to PAQS.
  </p>

  <section class="card lookup-card">
    <div class="lookup-header">
      <div>
        <h2>Find the container</h2>
        <p class="muted">Scan or enter a QR code to fetch the current layout.</p>
      </div>
      {#if loadedQr}
        <button type="button" class="link-button" onclick={resetEditor}>
          Clear selection
        </button>
      {/if}
    </div>

    <div class="input-group">
      <label for="qr-input">QR code</label>
      <div class="qr-input-row">
        <input
          id="qr-input"
          type="text"
          placeholder="e.g. QR-RED-DRAWER"
          value={qrInput}
          oninput={(event) => {
            qrInput = (event.currentTarget as HTMLInputElement).value;
          }}
        />
        <button type="button" class="primary" onclick={() => loadContainer()} disabled={loading || !canView}>
          {loading ? 'Loading…' : 'Load'}
        </button>
      </div>
    </div>

    <QrScanner
      title="Scan a QR code"
      description="Use your device camera to quickly load a container."
      on:detect={(event) => handleScannerResult(event.detail.text)}
    >
      <svelte:fragment slot="tips">
        <ul>
          <li>Allow camera access, then align the QR label inside the frame.</li>
          <li>We’ll load the matching container as soon as the code is detected.</li>
          <li>Use “Clear selection” if you need to switch containers mid-way.</li>
        </ul>
      </svelte:fragment>
    </QrScanner>

    {#if loadError}
      <p class="status error">{loadError}</p>
    {:else if loadSuccess}
      <p class="status success">{loadSuccess}</p>
    {/if}

    {#if !canView}
      <p class="permission-banner">
        This persona cannot view container data. Switch personas from the header to continue.
      </p>
    {/if}
  </section>

  {#if loadedQr}
    <section class="card editor-card">
      <div class="editor-header">
        <div>
          <h2>{containerName || 'Unnamed container'}</h2>
          <p class="muted">QR: {loadedQr}</p>
        </div>
      </div>

      {#if updateError}
        <p class="status error">{updateError}</p>
      {:else if updateSuccess}
        <p class="status success">{updateSuccess}</p>
      {/if}

      {#if !canUpdate}
        <p class="permission-banner">
          You can review the loaded container, but only editor personas can save updates.
        </p>
      {/if}

      <fieldset class="edit-fieldset" disabled={!canUpdate}>
        <div class="input-group">
          <label for="container-name">Container name</label>
          <input
            id="container-name"
            type="text"
            placeholder="e.g. Red Drawer"
            value={containerName}
            oninput={(event) => {
              containerName = (event.currentTarget as HTMLInputElement).value;
            }}
          />
        </div>

        {#each items as item, index (item.id)}
          <div class="content-card">
            <div class="item-header">
              <h3>Item {index + 1}</h3>
              {#if items.length > 1}
                <button type="button" class="remove-item" onclick={() => removeItem(index)}>
                  Remove
                </button>
              {/if}
            </div>

            <div class="input-group">
              <label>Name</label>
              <input
                type="text"
                value={item.name}
                placeholder="Item name"
                oninput={(event) => updateItemName(index, (event.currentTarget as HTMLInputElement).value)}
              />
            </div>

            <div class="input-group">
              <label>Quantity</label>
              <input
                type="number"
                min="0"
                step="1"
                inputmode="numeric"
                value={item.quantity}
                placeholder="0"
                oninput={(event) => updateItemQuantity(index, (event.currentTarget as HTMLInputElement).value)}
              />
            </div>

            {#each item.extras as extra (extra.id)}
              <div class="detail-card">
                <div class="detail-header">
                  <span>Detail</span>
                  <button type="button" class="remove-detail" onclick={() => removeItemDetail(index, extra.id)}>
                    Remove
                  </button>
                </div>
                <div class="detail-grid">
                  <select
                    value={extra.label || DETAIL_FIELD_OPTIONS[0]}
                    onchange={(event) =>
                      updateItemDetailLabel(index, extra.id, (event.currentTarget as HTMLSelectElement).value)
                    }
                  >
                    {#each DETAIL_FIELD_OPTIONS as option}
                      <option value={option}>{option}</option>
                    {/each}
                  </select>
                  <input
                    type="text"
                    placeholder={detailPlaceholder(extra.label)}
                    value={extra.value}
                    oninput={(event) =>
                      updateItemDetailValue(index, extra.id, (event.currentTarget as HTMLInputElement).value)
                    }
                  />
                </div>
              </div>
            {/each}

            <button type="button" class="add-detail" onclick={() => addItemDetail(index)}>
              + Add detail
            </button>
          </div>
        {/each}

        <div class="form-actions">
          <button type="button" class="secondary" onclick={addItem}>
            + Add item
          </button>
          <button type="button" class="primary" onclick={submitUpdate} disabled={updating}>
            {updating ? 'Saving…' : 'Save updates'}
          </button>
        </div>
      </fieldset>
    </section>
  {:else}
    <section class="placeholder-card">
      <p>Load a container to review and edit its contents.</p>
    </section>
  {/if}
</main>

<style>
  .update-page {
    max-width: 960px;
    margin: 0 auto;
    padding: 32px 16px 64px;
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .intro {
    margin: 0;
    color: var(--color-text-muted);
    text-align: center;
  }

  .card {
    background: var(--color-card-alt);
    border: 1px solid var(--color-border);
    border-radius: 16px;
    padding: 24px;
    box-shadow: var(--shadow-card);
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .lookup-header,
  .editor-header {
    display: flex;
    justify-content: space-between;
    gap: 16px;
    align-items: flex-start;
  }

  .muted {
    margin: 4px 0 0;
    color: var(--color-text-muted);
    font-size: 0.95rem;
  }

  .link-button {
    border: none;
    background: none;
    color: var(--color-primary);
    font-weight: 600;
    cursor: pointer;
    padding: 0;
  }

  .input-group {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  input,
  select {
    border: 1px solid var(--color-border);
    border-radius: 10px;
    padding: 10px 12px;
    background: var(--color-card);
    color: inherit;
  }

  .qr-input-row {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }

  .qr-input-row input {
    flex: 1;
    min-width: 200px;
  }

  button {
    border: none;
    border-radius: 999px;
    padding: 10px 18px;
    font-weight: 600;
    cursor: pointer;
    background: var(--color-card);
    color: inherit;
  }

  button.primary {
    background: var(--color-primary);
    color: #fff;
  }

  button.secondary {
    background: var(--color-secondary);
    color: #fff;
  }

  button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .status {
    margin: 0;
    padding: 12px 16px;
    border-radius: 10px;
    font-weight: 600;
  }

  .status.error {
    background: rgba(229, 57, 53, 0.15);
    color: var(--color-danger, #c62828);
  }

  .status.success {
    background: rgba(76, 175, 80, 0.18);
    color: var(--color-success, #2e7d32);
  }

  .permission-banner {
    margin: 0;
    padding: 12px 16px;
    border-radius: 10px;
    background: rgba(255, 193, 7, 0.2);
    color: var(--color-warning, #a15c00);
    font-weight: 600;
  }

  .edit-fieldset {
    border: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 18px;
  }

  .content-card {
    background: var(--color-card-tertiary);
    border: 1px solid var(--color-divider);
    border-radius: 12px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .item-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
  }

  .remove-item,
  .remove-detail {
    background: rgba(229, 57, 53, 0.15);
    color: var(--color-danger, #c62828);
  }

  .detail-card {
    border: 1px dashed var(--color-border);
    border-radius: 10px;
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .detail-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .detail-grid {
    display: grid;
    grid-template-columns: minmax(140px, 200px) 1fr;
    gap: 10px;
  }

  .add-detail {
    align-self: flex-start;
    background: transparent;
    color: var(--color-primary);
    padding: 0;
  }

  .form-actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
  }

  .placeholder-card {
    text-align: center;
    padding: 24px;
    border: 1px dashed var(--color-border);
    border-radius: 16px;
    color: var(--color-text-muted);
  }

  fieldset:disabled {
    opacity: 0.7;
  }

  @media (max-width: 640px) {
    .detail-grid {
      grid-template-columns: 1fr;
    }

    .form-actions {
      flex-direction: column;
      align-items: stretch;
    }
  }
</style>
