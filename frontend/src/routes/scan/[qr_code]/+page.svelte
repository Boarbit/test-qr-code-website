<script lang="ts">
  'use legacy';
  import { get } from 'svelte/store';
  import { page } from '$app/stores';
  import { API_URL, MOCK_USER_HEADER, PERMISSIONS } from '$lib/config';
  import { activeUser, hasPermission } from '$lib/stores/mockUsers';
  import type { MockUser } from '$lib/stores/mockUsers';

  type ItemDetailArray = Array<{ label: string; value: string }>;
  type ItemDetails = Record<string, string> | ItemDetailArray;

  type Item = {
    name: string;
    quantity: number;
    details?: ItemDetails;
  };

  type ContainerDto = {
    qr_code: string;
    name: string;
    contents: Item[];
  };

  const pageStore = page;
  const userStore = activeUser;

  let container: ContainerDto | null = null;
  let error = '';
  let loading = true;

  let activePersona: MockUser | null = null;
  let canView = false;
  let canDelete = false;
  let qrCode = '';
  let loadSequence = 0;
  let deleteLoading = false;
  let deleteError = '';
  let deleteSuccess = '';

  $: activePersona = $activeUser ?? null;
  $: qrCode = $pageStore.params.qr_code ?? '';
  $: canView = Boolean(activePersona && hasPermission(activePersona, PERMISSIONS.view));
  $: canDelete = Boolean(
    activePersona &&
      (hasPermission(activePersona, PERMISSIONS.update) || hasPermission(activePersona, PERMISSIONS.create))
  );

  $: {
    const code = qrCode;
    const persona = activePersona;
    deleteError = '';
    deleteSuccess = '';

    if (!code) {
      container = null;
      error = '';
      loading = false;
    } else {
      const requestId = ++loadSequence;
      loadContainer(code, persona, requestId);
    }
  }

  async function loadContainer(code: string, persona: MockUser | null, requestId: number) {
    loading = true;
    error = '';
    container = null;

    try {
      if (!persona) {
        throw new Error('Select a persona before loading containers.');
      }

      if (!hasPermission(persona, PERMISSIONS.view)) {
        throw new Error('You do not have permission to view containers.');
      }

      const res = await fetch(`${API_URL}/containers/${code}`, {
        headers: authHeaders()
      });

      if (!res.ok) {
        throw new Error('Container not found');
      }

      const data: ContainerDto = await res.json();
      if (requestId === loadSequence) {
        container = data;
      }
    } catch (err) {
      if (requestId === loadSequence) {
        error = err instanceof Error ? err.message : 'Failed to load container';
      }
    } finally {
      if (requestId === loadSequence) {
        loading = false;
      }
    }
  }

  function authHeaders() {
    const user = get(userStore);
    if (!user) {
      throw new Error('Select a persona before loading containers.');
    }

    return {
      [MOCK_USER_HEADER]: user.id
    };
  }

  function normalizeDetailEntries(details?: ItemDetails) {
    if (!details) {
      return [];
    }

    if (Array.isArray(details)) {
      return details
        .map(({ label, value }) => [label?.trim(), value?.trim()] as [string, string])
        .filter(([label, value]) => Boolean(label) && Boolean(value));
    }

    return Object.entries(details)
      .map(([label, value]) => [label.trim(), value?.trim() ?? ''])
      .filter(([label, value]) => Boolean(label) && Boolean(value));
  }

  async function deleteCurrentContainer() {
    if (!canDelete || !container?.qr_code) {
      return;
    }

    const trimmed = container.qr_code.trim();
    if (!trimmed) {
      return;
    }

    deleteLoading = true;
    deleteError = '';
    deleteSuccess = '';

    try {
      const res = await fetch(`${API_URL}/containers/${encodeURIComponent(trimmed)}`, {
        method: 'DELETE',
        headers: authHeaders()
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || 'Failed to delete container');
      }

      deleteSuccess = `Container ${trimmed} deleted.`;
      container = null;
    } catch (err) {
      deleteError = err instanceof Error ? err.message : 'Failed to delete container';
    } finally {
      deleteLoading = false;
    }
  }

  function extraEntries(item: Item) {
    const extras: [string, string][] = [];

    for (const [key, value] of Object.entries(item)) {
      if (key === 'name' || key === 'quantity' || key === 'details') continue;
      const rendered = value == null ? '' : String(value);
      if (rendered.trim()) {
        extras.push([
          key
            .replace(/_/g, ' ')
            .replace(/\b\w/g, (char) => char.toUpperCase()),
          rendered
        ]);
      }
    }

    extras.push(...normalizeDetailEntries(item.details));

    return extras;
  }
</script>

<style>
  h2 {
    text-align: center;
    margin-top: 32px;
    margin-bottom: 24px;
    font-size: 1.8em;
    color: var(--color-text);
  }

  .container-card {
    background: var(--color-card-alt);
    border: 1px solid var(--color-border);
    border-radius: 12px;
    padding: 24px;
    max-width: 700px;
    margin: 16px auto;
    box-shadow: var(--shadow-card);
    transition: transform 0.2s;
  }
  .container-card:hover {
    transform: scale(1.02);
  }

  .container-title {
    text-align: center;
    margin-bottom: 12px;
  }

  .container-name {
    font-weight: bold;
    font-size: 1.6em;
    color: var(--color-text);
    margin: 0;
  }

  .container-qr {
    margin: 4px 0 0;
    color: var(--color-text-muted);
  }

  .content-card {
    background: var(--color-card-tertiary);
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 16px;
    border-left: 4px solid var(--color-primary);
    border: 1px solid var(--color-divider);
  }

  .content-name {
    font-weight: bold;
    font-size: 1.2em;
    margin-bottom: 6px;
    color: var(--color-text);
  }

  .content-quantity {
    font-style: italic;
    margin-bottom: 8px;
    color: var(--color-text-muted);
  }

  .item-details {
    margin: 8px 0 0;
    display: grid;
    gap: 6px;
  }

  .item-detail-row {
    display: grid;
    grid-template-columns: minmax(120px, 1fr) 2fr;
    gap: 6px;
    padding: 6px 10px;
    background: var(--color-card);
    border-radius: 8px;
  }

  .item-detail-row dt {
    margin: 0;
    font-weight: 600;
    color: var(--color-text);
  }

  .item-detail-row dd {
    margin: 0;
    color: var(--color-text-muted);
  }

  .loading,
  .error,
  .no-data {
    text-align: center;
    font-size: 1.1em;
    margin-top: 32px;
  }

  .loading {
    color: var(--color-secondary);
  }

  .error {
    color: var(--color-primary);
    font-weight: bold;
  }

  .success {
    color: var(--color-success, #2e7d32);
    font-weight: bold;
  }

  .no-data {
    color: var(--color-text-muted);
    font-style: italic;
  }

  button.danger {
    border: none;
    border-radius: 999px;
    padding: 10px 18px;
    font-weight: 600;
    background: var(--color-danger, #c62828);
    color: #fff;
    cursor: pointer;
  }

  button.danger:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
</style>


<h2>PAQS Scan Result</h2>

{#if loading}
  <p class="loading">Loading container data...</p>
{:else if error}
  <p class="error">{error}</p>
{:else if container}
  <div class="container-card">
    <div class="container-title">
      <p class="container-name">{container.name}</p>
      <p class="container-qr">QR: {container.qr_code}</p>
    </div>

    {#if deleteError}
      <p class="error">{deleteError}</p>
    {:else if deleteSuccess}
      <p class="success">{deleteSuccess}</p>
    {/if}

    {#each container.contents as item}
      <div class="content-card">
        {@const extras = extraEntries(item)}
        <div class="content-name">{item.name}</div>
        <div class="content-quantity">Quantity: {item.quantity}</div>
        {#if extras.length}
          <dl class="item-details">
            {#each extras as [label, value]}
              <div class="item-detail-row">
                <dt>{label}</dt>
                <dd>{value}</dd>
              </div>
            {/each}
          </dl>
        {/if}
      </div>
    {/each}

    {#if canDelete}
      <button
        type="button"
        class="danger"
        onclick={() => {
          if (typeof window === 'undefined' || window.confirm(`Delete container ${container?.qr_code}?`)) {
            void deleteCurrentContainer();
          }
        }}
        disabled={deleteLoading}
      >
        {deleteLoading ? 'Deleting…' : 'Delete container'}
      </button>
    {/if}
  </div>
{:else}
  <p class="no-data">No container data found.</p>
{/if}
