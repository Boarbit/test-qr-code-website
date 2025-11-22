<script lang="ts">
  'use legacy';
  import { get } from 'svelte/store';
  import { API_URL, MOCK_USER_HEADER, PERMISSIONS } from '$lib/config';
  import QrScanner from '$lib/components/QrScanner.svelte';
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

  const userStore = activeUser;
  const SAMPLE_QR_CODES = ['QR123', 'QR456'];

  let qrInput = '';
  let container: ContainerDto | null = null;
  let manageLoading = false;
  let manageError = '';
  let manageSuccess = '';

  let searchQuery = '';
  let searchResults: ContainerDto[] = [];
  let searchLoading = false;
  let searchError = '';

  let activePersona: MockUser | null = null;
  let canView = false;
  let canCreate = false;
  let canDelete = false;

  let deleteLoading = false;
  let deleteTarget = '';
  let deleteError = '';
  let deleteSuccess = '';

  $: activePersona = $activeUser ?? null;
  $: canView = hasPermission(activePersona, PERMISSIONS.view);
  $: canCreate = hasPermission(activePersona, PERMISSIONS.create);
  $: canDelete = Boolean(
    hasPermission(activePersona, PERMISSIONS.update) || hasPermission(activePersona, PERMISSIONS.create)
  );

  function authHeaders() {
    const user = get(userStore);
    if (!user) {
      throw new Error('Select a persona before using the dashboard.');
    }

    return {
      [MOCK_USER_HEADER]: user.id
    };
  }

  async function fetchContainer(qr: string) {
    const trimmed = qr?.trim();
    if (!trimmed) {
      manageError = 'Enter a QR code to look up.';
      manageSuccess = '';
      container = null;
      return;
    }

    manageLoading = true;
    manageError = '';
    manageSuccess = '';
    container = null;
    deleteError = '';
    deleteSuccess = '';

    try {
      const res = await fetch(`${API_URL}/containers/${trimmed}`, {
        headers: authHeaders()
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || 'Container not found');
      }

      const data: ContainerDto = await res.json();
      container = data;
      qrInput = trimmed;
      manageSuccess = `Showing container ${data.name || trimmed}`;
    } catch (err) {
      manageError = err instanceof Error ? err.message : 'Lookup failed';
    } finally {
      manageLoading = false;
    }
  }

  async function searchContainers() {
    const query = searchQuery.trim();
    if (!query) {
      searchError = 'Enter a container name, item, quantity, or QR code to search.';
      searchResults = [];
      return;
    }

    searchLoading = true;
    searchError = '';
    searchResults = [];
    deleteError = '';
    deleteSuccess = '';

    try {
      const res = await fetch(`${API_URL}/containers?search=${encodeURIComponent(query)}`, {
        headers: authHeaders()
      });

      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length) {
          searchResults = data;
          return;
        }
      }

      const directRes = await fetch(`${API_URL}/containers/${query}`, {
        headers: authHeaders()
      });
      if (!directRes.ok) {
        throw new Error('No results found');
      }

      const single: ContainerDto = await directRes.json();
      searchResults = [single];
    } catch (err) {
      searchError = err instanceof Error ? err.message : 'Search failed';
    } finally {
      searchLoading = false;
    }
  }

  function qrCodeUrl(qr: string) {
    const user = get(userStore);
    const query = user ? `?mock_user=${encodeURIComponent(user.id)}` : '';
    return `${API_URL}/containers/${qr}/qrcode${query}`;
  }

  function formatFieldLabel(label: string) {
    return label
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (char) => char.toUpperCase());
  }

  function detailEntries(details?: ItemDetails) {
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

  function itemExtraFields(item: Item) {
    const extras: [string, string][] = [];

    for (const [key, value] of Object.entries(item)) {
      if (key === 'name' || key === 'quantity' || key === 'details') {
        continue;
      }

      const rendered = value == null ? '' : String(value);
      if (rendered.trim()) {
        extras.push([formatFieldLabel(key), rendered]);
      }
    }

    for (const [label, value] of detailEntries(item.details)) {
      extras.push([label, value]);
    }

    console.log('Item extras processed', { item, extras });

    return extras;
  }

  function handleScannerResult(result: string) {
    const trimmed = result.trim();
    if (!trimmed) {
      manageError = 'Scanning returned a blank QR code.';
      manageSuccess = '';
      return;
    }

    qrInput = trimmed;
    void fetchContainer(trimmed);
  }

  async function deleteContainerByQr(qr: string) {
    if (!canDelete) return;

    const trimmed = qr.trim();
    if (!trimmed) {
      return;
    }

    deleteLoading = true;
    deleteTarget = trimmed;
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

      if (container?.qr_code === trimmed) {
        container = null;
        manageSuccess = '';
      }

      searchResults = searchResults.filter((result) => result.qr_code !== trimmed);
      if (qrInput === trimmed) {
        qrInput = '';
      }

      deleteSuccess = `Container ${trimmed} deleted.`;
    } catch (err) {
      deleteError = err instanceof Error ? err.message : 'Failed to delete container';
    } finally {
      deleteLoading = false;
      deleteTarget = '';
    }
  }

  function requestDelete(qr: string) {
    if (!canDelete) {
      return;
    }
    if (typeof window !== 'undefined') {
      const confirmed = window.confirm(`Delete container ${qr}? This cannot be undone.`);
      if (!confirmed) {
        return;
      }
    }
    void deleteContainerByQr(qr);
  }

</script>

<main class="page">
  <h1>PAQS</h1>
  <p class="lead">“PEACE IN THE CHAOS”</p>
  <p class="sublead">QR-assisted packing and storage.</p>

  <div class="box-grid">
    <section class="card manage-card">
      <h2>View Items</h2>
      <p class="card-subtitle">Lookup an existing container and instantly see its contents.</p>

      <div class="lookup">
        <input
          type="text"
          placeholder="Enter or paste a QR code"
          value={qrInput}
          oninput={(event) => {
            qrInput = (event.currentTarget as HTMLInputElement).value;
          }}
        />
        <button type="button" onclick={() => fetchContainer(qrInput)}>View container</button>
      </div>

      <div class="quick-links">
        <span>Quick load:</span>
        {#each SAMPLE_QR_CODES as code}
          <button
            type="button"
            class="link-button"
            onclick={() => {
              qrInput = code;
              fetchContainer(code);
            }}
          >{code}</button>
        {/each}
      </div>

      {#if deleteError}
        <p class="error">{deleteError}</p>
      {:else if deleteSuccess}
        <p class="success">{deleteSuccess}</p>
      {/if}

      <QrScanner
        title="Scan to load a container"
        description="Use your camera to scan a QR label and auto-fill the code above."
        on:detect={(event) => handleScannerResult(event.detail.text)}
      >
        <svelte:fragment slot="tips">
          <ul>
            <li>Center the QR label and hold still until it focuses.</li>
            <li>Once detected, we’ll look up the container automatically.</li>
            <li>Need a sample? Try the quick load buttons above.</li>
          </ul>
        </svelte:fragment>
      </QrScanner>

      {#if manageLoading}
        <p class="info">Looking up container...</p>
      {:else if manageError}
        <p class="error">{manageError}</p>
      {:else if manageSuccess}
        <p class="success">{manageSuccess}</p>
      {/if}

      {#if container}
        <div class="container-preview">
          <h3>{container.name}</h3>
          <p class="qr-code-label">QR: {container.qr_code}</p>

          {#each container.contents as item}
            {@const extras = itemExtraFields(item)}
            <div class="content-card">
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
              onclick={() => requestDelete(container.qr_code)}
              disabled={deleteLoading && deleteTarget === container.qr_code}
            >
              {deleteLoading && deleteTarget === container.qr_code ? 'Deleting…' : 'Delete container'}
            </button>
          {/if}

        </div>
      {/if}

      <p class="cta">
        Need to add a new container?
        {#if canCreate}
          <a class="cta-link" href="/create">Create it here</a>.
        {:else}
          <span class="cta-link" aria-disabled="true">Ask someone with creator access</span>
        {/if}
      </p>
    </section>

    <section class="card search-card">
      <h2>Search All QR Codes</h2>
      <p class="card-subtitle">Find containers by label, contents, or QR code.</p>

      <div class="lookup">
        <input
          type="text"
          placeholder="Search containers..."
          value={searchQuery}
          oninput={(event) => {
            searchQuery = (event.currentTarget as HTMLInputElement).value;
          }}
        />
        <button type="button" onclick={searchContainers}>Search</button>
      </div>

      {#if searchLoading}
        <p class="info">Searching...</p>
      {:else if searchError}
        <p class="error">{searchError}</p>
      {/if}

      {#if searchResults.length}
        <ul class="search-results">
          {#each searchResults as result}
            <li>
              <div class="result-header">
                <div class="result-title">
                  <span class="result-name">{result.name}</span>
                  <span class="result-qr">{result.qr_code}</span>
                </div>
                <div class="result-actions">
                  <button
                    type="button"
                    class="link-button"
                    onclick={() => {
                      qrInput = result.qr_code;
                      fetchContainer(result.qr_code);
                    }}
                  >View details</button>
                  {#if canDelete}
                    <button
                      type="button"
                      class="danger-text"
                      onclick={() => requestDelete(result.qr_code)}
                      disabled={deleteLoading && deleteTarget === result.qr_code}
                    >
                      {deleteLoading && deleteTarget === result.qr_code ? 'Deleting…' : 'Delete'}
                    </button>
                  {/if}
                </div>
              </div>
              {#if result.contents?.length}
                {#each result.contents as item}
                  {@const extras = itemExtraFields(item)}
                  <div class="result-item">
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
              {:else}
                <p class="muted">No items stored yet.</p>
              {/if}
            </li>
          {/each}
        </ul>
      {/if}
    </section>

  </div>

  <section class="card instructions-card">
    <h2>How It Works</h2>
    <ol>
      <li>Create or scan a QR label for your container</li>
      <li>Add the container details and items on the Create page</li>
      <li>Print or attach the QR code to the container</li>
      <li>Come back here anytime to view or search your storage</li>
    </ol>
  </section>
</main>

<style>
  .page {
    max-width: 1100px;
    margin: 0 auto;
    padding: 48px 24px 80px;
  }

  h1 {
    text-align: center;
    font-size: 2.5rem;
    margin: 0;
    color: var(--color-text);
  }

  .lead {
    text-align: center;
    margin: 12px 0 12px;
    color: var(--color-text-muted);
    font-weight: 600;
    letter-spacing: 0.08em;
  }

  .sublead {
    text-align: center;
    margin: 0 0 40px;
    color: var(--color-text-muted);
  }

  .box-grid {
    display: grid;
    gap: 24px;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    margin-bottom: 32px;
  }

  .card {
    border-radius: 16px;
    padding: 24px;
    border: 1px solid var(--color-border);
    box-shadow: var(--shadow-card);
    color: var(--color-text);
  }

  .manage-card {
    background: var(--color-card-warm);
  }

  .search-card {
    background: var(--color-card-alt);
  }

  .instructions-card {
    background: var(--color-card-tertiary);
  }

  .card h2 {
    margin-top: 0;
    font-size: 1.7rem;
    color: var(--color-text);
  }

  .card-subtitle {
    margin-top: -8px;
    margin-bottom: 16px;
    color: var(--color-text-muted);
  }

  .lookup {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    align-items: center;
    margin-bottom: 16px;
  }

  input {
    flex: 1;
    min-width: 0;
    padding: 10px 12px;
    border-radius: 8px;
    border: 1px solid var(--color-border);
    font: inherit;
    color: var(--color-text);
    background: var(--color-input-bg);
  }

  button {
    background: var(--color-primary);
    color: #f6f6f6;
    border: none;
    border-radius: 8px;
    padding: 12px 22px;
    cursor: pointer;
    font-size: 1rem;
    transition: background 0.2s ease, transform 0.1s ease;
  }

  button:hover {
    background: var(--color-primary-hover);
    transform: translateY(-1px);
  }

  button:active {
    background: var(--color-primary-pressed);
  }

  button.secondary {
    background: var(--color-secondary);
    color: #f6f6f6;
  }

  button.danger {
    background: var(--color-danger, #c62828);
    color: #fff;
  }

  button.danger:hover {
    background: var(--color-danger-hover, #b71c1c);
  }

  button.danger-text {
    background: transparent;
    color: var(--color-danger, #c62828);
    border: none;
    padding: 6px 12px;
    font-size: 0.95rem;
    cursor: pointer;
  }

  button.danger-text:hover {
    text-decoration: underline;
  }

  button.secondary:hover {
    background: var(--color-secondary-hover);
  }

  button.link-button {
    background: transparent;
    color: var(--color-primary);
    padding: 6px 12px;
    border: none;
    font-size: 0.95rem;
    text-decoration: underline;
  }

  button.link-button:hover {
    color: var(--color-primary-hover);
    transform: none;
  }

  .quick-links {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
    margin-bottom: 12px;
    font-size: 0.95rem;
    color: var(--color-text-muted);
  }

  .info,
  .error,
  .success {
    margin: 12px 0;
    font-weight: 600;
  }

  .info {
    color: var(--color-secondary);
  }

  .error {
    color: var(--color-primary);
  }

  .success {
    color: var(--color-secondary-hover);
  }

  .container-preview {
    margin-top: 16px;
    border: 1px solid var(--color-border);
    border-radius: 12px;
    padding: 16px;
    background: var(--color-card-alt);
  }

  .container-preview h3 {
    margin: 0;
    font-size: 1.4rem;
    color: var(--color-text);
  }

  .qr-code-label {
    margin: 4px 0 12px;
    font-size: 0.95rem;
    color: var(--color-text-muted);
  }

  .content-card {
    margin-top: 16px;
    border-radius: 10px;
    padding: 12px;
    background: var(--color-card-warm);
    border: 1px solid var(--color-divider);
  }


  .content-name {
    font-weight: 600;
    margin-bottom: 4px;
    color: var(--color-text);
  }

  .content-quantity {
    color: var(--color-text-muted);
    margin-bottom: 8px;
  }

  .item-details {
    margin: 8px 0 0;
    display: grid;
    gap: 6px;
  }

  .item-detail-row {
    display: grid;
    grid-template-columns: minmax(100px, 1fr) 2fr;
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

  .muted {
    color: var(--color-text-muted);
    font-style: italic;
  }

  ul {
    margin: 8px 0 0 18px;
    padding: 0;
  }

  .cta {
    margin-top: 24px;
    font-size: 0.95rem;
    color: var(--color-text-muted);
  }

  .cta-link {
    font-weight: 600;
    color: var(--color-primary);
  }

  .cta-link:hover {
    color: var(--color-primary-hover);
  }

  .cta-link[aria-disabled='true'] {
    color: var(--color-text-muted);
    cursor: not-allowed;
    text-decoration: none;
  }

  .search-results {
    list-style: none;
    padding: 0;
    margin: 16px 0 0;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .search-results li {
    border: 1px solid var(--color-border);
    border-radius: 12px;
    padding: 12px 16px;
    background: var(--color-card-tertiary);
  }

  .result-actions {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  .result-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
    font-weight: 600;
  }

  .result-title {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .result-name {
    font-size: 1.05rem;
    color: var(--color-text);
  }

  .result-qr {
    font-size: 0.9rem;
    color: var(--color-text-muted);
  }

  .result-item {
    margin-top: 8px;
  }

  .instructions-card ol {
    margin: 16px 0 0 20px;
    padding: 0;
  }

  .instructions-card li {
    margin-bottom: 8px;
    font-weight: 500;
    color: var(--color-text);
  }

  @media (max-width: 600px) {
    .lookup {
      flex-direction: column;
      align-items: stretch;
    }

    button {
      width: 100%;
    }
  }
</style>
