<script lang="ts">
  'use legacy';
  import { get } from 'svelte/store';
  import { page } from '$app/stores';
  import { API_URL, MOCK_USER_HEADER, PERMISSIONS } from '$lib/config';
  import { activeUser, hasPermission } from '$lib/stores/mockUsers';
  import type { MockUser } from '$lib/stores/mockUsers';

  type Item = {
    name: string;
    quantity: number;
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
  let qrCode = '';
  let loadSequence = 0;

  $: activePersona = $activeUser ?? null;
  $: qrCode = $pageStore.params.qr_code ?? '';
  $: canView = Boolean(activePersona && hasPermission(activePersona, PERMISSIONS.view));

  $: {
    const code = qrCode;
    const persona = activePersona;

    if (!code) {
      container = null;
      error = '';
      loading = false;
      return;
    }

    const requestId = ++loadSequence;
    loadContainer(code, persona, requestId);
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

  .no-data {
    color: var(--color-text-muted);
    font-style: italic;
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

    {#each container.contents as item}
      <div class="content-card">
        <div class="content-name">{item.name}</div>
        <div class="content-quantity">Quantity: {item.quantity}</div>
      </div>
    {/each}
  </div>
{:else}
  <p class="no-data">No container data found.</p>
{/if}
