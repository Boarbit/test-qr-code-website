<script lang="ts">
  'use legacy';
  import { onDestroy, onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { get } from 'svelte/store';
  import { API_URL } from '$lib/config';
  import {
    activeUser,
    activeUserId,
    mockUsersStore,
    usersStore
  } from '$lib/stores/mockUsers';
  import type { MockUser } from '$lib/stores/mockUsers';

  let personas: MockUser[] = [];
  let selectedId = '';
  let error = '';
  let loading = false;

  const unsubscribe = mockUsersStore.subscribe((list) => {
    personas = list;
  });

  onDestroy(unsubscribe);

  onMount(async () => {
    if (get(activeUser)) {
      goto('/');
      return;
    }

    if (!get(mockUsersStore).length) {
      try {
        loading = true;
        const res = await fetch(`${API_URL}/users`);
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data) && data.length) {
            usersStore.setUsers(data);
            return;
          }
        }
        error = 'Unable to load personas. Try again in a moment.';
      } catch (err) {
        console.error(err);
        error = 'Unable to load personas. Try again in a moment.';
      } finally {
        loading = false;
      }
    }
  });

  $: personasLoaded = personas.length > 0;

  function handleSelect(id: string) {
    selectedId = id;
    error = '';
  }

  async function loginWithSelected(event?: Event) {
    event?.preventDefault();
    if (!selectedId) {
      error = 'Choose a persona to continue.';
      return;
    }

    loading = true;
    try {
      activeUserId.set(selectedId);
      await goto('/');
    } finally {
      loading = false;
    }
  }
</script>

<main class="login-page">
  <section class="login-card">
    <h1>Choose a Persona</h1>
    <p class="muted">Pick a mock account to explore the PAQS experience.</p>

    {#if loading && !personasLoaded}
      <p class="status">Loading personas…</p>
    {:else if !personasLoaded}
      <p class="status status--error">No personas available. Try again later.</p>
    {:else}
      <form class="persona-form" onsubmit={loginWithSelected}>
        <div class="persona-list">
          {#each personas as persona}
            <button
              type="button"
              class={`persona-card${selectedId === persona.id ? ' selected' : ''}`}
              onclick={() => handleSelect(persona.id)}
            >
              <span class="persona-name">{persona.name}</span>
              <span class="persona-role">{persona.role}</span>
            </button>
          {/each}
        </div>

        {#if error}
          <p class="status status--error">{error}</p>
        {/if}

        <button type="submit" class="submit" disabled={!selectedId || loading}>
          {loading ? 'Signing in…' : 'Continue'}
        </button>
      </form>
    {/if}

    <a class="back-link" href="/">Back to dashboard</a>
  </section>
</main>

<style>
  .login-page {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--color-bg);
    padding: 48px 16px;
  }

  .login-card {
    max-width: 520px;
    width: 100%;
    background: var(--color-card-alt);
    border-radius: 16px;
    padding: 32px;
    border: 1px solid var(--color-border);
    box-shadow: var(--shadow-card);
    text-align: center;
  }

  h1 {
    margin: 0 0 12px;
    color: var(--color-text);
    font-size: 1.8rem;
  }

  .muted {
    margin: 0 0 24px;
    color: var(--color-text-muted);
  }

  .persona-form {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .persona-list {
    display: grid;
    gap: 12px;
  }

  .persona-card {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 16px;
    border-radius: 12px;
    border: 1px solid var(--color-border);
    background: var(--color-card-tertiary);
    color: var(--color-text);
    text-align: left;
    cursor: pointer;
    transition: border-color 0.2s ease, transform 0.1s ease;
  }

  .persona-card:hover {
    border-color: var(--color-primary);
    transform: translateY(-1px);
  }

  .persona-card.selected {
    border-color: var(--color-primary);
    background: var(--color-card-warm);
  }

  .persona-name {
    font-weight: 600;
    font-size: 1.05rem;
  }

  .persona-role {
    color: var(--color-text-muted);
    font-size: 0.95rem;
  }

  .status {
    font-size: 0.95rem;
    color: var(--color-text-muted);
    margin: 0;
  }

  .status--error {
    color: var(--color-error, #b6463c);
    font-weight: 600;
  }

  .submit {
    align-self: center;
    min-width: 180px;
    border-radius: 999px;
    padding: 12px 24px;
    background: var(--color-primary);
    color: var(--color-card, #ffffff);
    border: none;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s ease;
  }

  .submit:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .submit:not(:disabled):hover {
    background: var(--color-primary-hover);
  }

  .back-link {
    display: inline-block;
    margin-top: 24px;
    color: var(--color-secondary);
    text-decoration: none;
    font-weight: 500;
  }

  .back-link:hover {
    text-decoration: underline;
  }

  @media (max-width: 520px) {
    .login-card {
      padding: 24px;
    }
  }
</style>
