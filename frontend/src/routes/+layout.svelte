<!-- <script lang="ts">
  import { onMount } from 'svelte';
  import { get } from 'svelte/store';
  import favicon from '$lib/assets/favicon.svg';
  import { page } from '$app/stores';
  import { API_URL, MOCK_USER_HEADER, PERMISSIONS, ROLES } from '$lib/config';
  import { themeStore, toggleTheme } from '$lib/stores/theme';
  import { usersStore, activeUser, activeUserId, hasPermission } from '$lib/stores/mockUsers';
  import type { MockUser } from '$lib/stores/mockUsers';

  const pageStore = page;
  const theme = themeStore;
  let { children } = $props();

  let loadingUsers = $state(false);
  let usersError = $state('');
  let selectedUserId = $state('');
  let roleError = $state('');
  let roleSuccess = $state('');
  let roleBusy = $state(false);
  let availableRoles = $state([...ROLES]);
  let manageTargetId = $state('');

  
 
 
  let manageTarget = $state<MockUser | null>(null);

  onMount(async () => {
    if (get(usersStore).length) {
      return;
    }

    loadingUsers = true;
    usersError = '';

    try {
      const res = await fetch(`${API_URL}/users`);
      if (!res.ok) {
        throw new Error('Failed to load users');
      }

      const data = await res.json();
      if (Array.isArray(data)) {
        usersStore.setUsers(data);
      }

      const rolesRes = await fetch(`${API_URL}/roles`);
      if (rolesRes.ok) {
        const rolesData = await rolesRes.json();
        if (Array.isArray(rolesData) && rolesData.length) {
          availableRoles = rolesData;
        }
      }
    } catch (error) {
      console.error(error);
      usersError = 'Unable to load mock users';
    } finally {
      loadingUsers = false;
    }
  });

  let activePersona = $derived(get(activeUser) ?? null);
  let canCreate = $derived(hasPermission(activePersona, PERMISSIONS.create));
  let canAssign = $derived(Boolean(activePersona?.is_admin));
  let personaOptions = $derived(get(usersStore));
  let manageableUsers = $derived(personaOptions.filter((user) => !user.is_admin));
  let selectedUser = $derived(personaOptions.find((user) => user.id === selectedUserId) ?? null);

  // activePersona = $derived(get(activeUser) ?? null);
  // canCreate = $derived(hasPermission(activePersona, PERMISSIONS.create));
  // canAssign = $derived(Boolean(activePersona?.is_admin));
  // personaOptions = $derived(get(usersStore));
  // manageableUsers = $derived(personaOptions.filter((user) => !user.is_admin));
  // selectedUser = $derived(personaOptions.find((user) => user.id === selectedUserId) ?? null);

   $effect(() => {
    const nextId = activePersona?.id ?? '';
    if (nextId && selectedUserId !== nextId) {
      selectedUserId = nextId;
      roleError = '';
      roleSuccess = '';
    }
  });

  $effect(() => {
    if (!canAssign) {
      manageTargetId = '';
      manageTarget = null;
    } else {
      if (!manageTargetId || !manageableUsers.some((user) => user.id === manageTargetId)) {
        manageTargetId = manageableUsers[0]?.id ?? '';
      }
      manageTarget = manageableUsers.find((user) => user.id === manageTargetId) ?? null;
    }
    });

  function authHeaders() {
    const user = get(activeUser);
    if (!user) {
      throw new Error('Select a persona first.');
    }

    return {
      [MOCK_USER_HEADER]: user.id
    };
  }

  function handlePersonaChange(event: Event) {
    const nextId = (event.currentTarget as HTMLSelectElement).value;
    if (!nextId) {
      return;
    }

    activeUserId.set(nextId);
    selectedUserId = nextId;
    roleError = '';
    roleSuccess = '';
  }

  function handleManageTargetChange(event: Event) {
    manageTargetId = (event.currentTarget as HTMLSelectElement).value;
    roleError = '';
    roleSuccess = '';
  }

  async function handleRoleChange(event: Event) {
    const nextRole = (event.currentTarget as HTMLSelectElement).value;
    if (!manageTargetId || !nextRole) {
      return;
    }

    roleError = '';
    roleSuccess = '';
    roleBusy = true;

    try {
      const headers = {
        'Content-Type': 'application/json',
        ...authHeaders()
      };

      const res = await fetch(`${API_URL}/users/${manageTargetId}/role`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ role: nextRole })
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || 'Failed to update access level');
      }

      const updated = await res.json();
      usersStore.updateUser(updated);
      roleSuccess = `${updated.name} is now ${updated.role}`;
    } catch (error) {
      console.error(error);
      roleError = error instanceof Error ? error.message : 'Failed to update access level';
    } finally {
      roleBusy = false;
    }
  }

  $: $usersStore; // $usersStore is the current value of usersStore
  $: hasUsers = $usersStore.length > 0;

</script>

<svelte:head>
  <link rel="icon" href={favicon} />
</svelte:head>

<header class="site-header">
  <div class="header-inner">
    <a class="brand" href="/">PAQS</a>
    <nav class="nav">
      <a
        class="nav-link"
        href="/"
        class:active={$pageStore.url.pathname === '/'}
      >Dashboard</a>
      {#if $canCreate}
        <a
          class="nav-link"
          href="/create"
          class:active={$pageStore.url.pathname.startsWith('/create')}
        >Create Container</a>
      {/if}
    </nav>
    <div class="header-actions">
      <button
        class="theme-toggle"
        type="button"
        onclick={toggleTheme}
        aria-label={$theme === 'dark' ? 'Use light theme' : 'Use dark theme'}
      >
        <span class="theme-toggle__icon" aria-hidden="true">
          {#if $theme === 'dark'}
            🌙
          {:else}
            ☀️
          {/if}
        </span>
        <span class="theme-toggle__label">{$theme === 'dark' ? 'Dark' : 'Light'}</span>
      </button>
      <div class="user-switcher">
        {#if loadingUsers}
          <span class="user-switcher__status">Loading personas…</span>
        {:else if usersError}
          <span class="user-switcher__status user-switcher__status--error">{usersError}</span>
        {:else if personaOptions.length}
          <label>
            <span class="user-switcher__label">Persona</span>
            <select value={selectedUserId} onchange={handlePersonaChange}>
              {#each personaOptions as user}
                <option value={user.id}>
                  {user.name} — {user.role}
                </option>
              {/each}
            </select>
          </label>
        {:else}
          <span class="user-switcher__status user-switcher__status--muted">No personas found</span>
        {/if}
      </div>
      {#if $canAssign}
        <div class="admin-panel">
          <span class="admin-panel__title">Manage access</span>
          {#if manageableUsers.length}
            <label>
              <span class="admin-panel__label">Persona</span>
              <select value={manageTargetId} onchange={handleManageTargetChange}>
                {#each manageableUsers as user}
                  <option value={user.id}>{user.name} — {user.role}</option>
                {/each}
              </select>
            </label>
            <label>
              <span class="admin-panel__label">Access level</span>
              <select onchange={handleRoleChange} disabled={roleBusy || !manageTarget}>
                {#each availableRoles as role}
                  <option value={role} selected={manageTarget?.role === role}>{role}</option>
                {/each}
              </select>
            </label>
            {#if roleError}
              <span class="admin-panel__status admin-panel__status--error">{roleError}</span>
            {:else if roleSuccess}
              <span class="admin-panel__status">{roleSuccess}</span>
            {/if}
          {:else}
            <span class="admin-panel__status">No other personas available to update.</span>
          {/if}
        </div>
      {/if}
    </div>
  </div>
</header>

<div class="layout-content">
  {@render children?.()}
</div>

<style>
  :global(:root) {
    /* original warm palette */
    --color-bg-warm: #eff5f2;
    --color-text-warm: #221f26;
    --color-text-muted-warm: #4f5d58;
    --color-header-bg-warm: #384055;
    --color-header-hover-warm: #4a5168;
    --color-header-active-warm: #eff5f2;
    --color-primary-warm: #3c7a6b;
    --color-primary-hover-warm: #4e8d7d;
    --color-primary-pressed-warm: #2c5f54;
    --color-secondary-warm: #384055;
    --color-secondary-hover-warm: #4a5168;
    --color-border-warm: #b8d1c9;
    --color-card-warm: #cfe1da;
    --color-card-alt-warm: #d9e0ed;
    --color-card-tertiary-warm: #e6f0ec;
    --color-chip-warm: #8ab3a4;
    --color-divider-warm: #d9e6e2;
    --color-input-bg-warm: rgba(239, 245, 242, 0.7);
    --color-surface-overlay-warm: rgba(79, 90, 107, 0.08);
    --shadow-card-warm: 0 12px 24px rgba(39, 32, 39, 0.1);
    --color-button-disabled-warm: rgba(53, 59, 81, 0.4);

    /* refreshed teal complement palette */
    --color-bg: var(--color-bg-warm);
    --color-text: var(--color-text-warm);
    --color-text-muted: var(--color-text-muted-warm);
    --color-header-bg: #343d4c;
    --color-header-hover: #455266;
    --color-header-active: #f1f6f5;
    --color-primary: #2f7a72;
    --color-primary-hover: #40948b;
    --color-primary-pressed: #225e58;
    --color-secondary: #4d6675;
    --color-secondary-hover: #5b7787;
    --color-border: #b6d3cd;
    --color-card-warm-current: #d4e4de;
    --color-card-alt: #dde6f1;
    --color-card-tertiary: #e9f2ef;
    --color-chip: #5fa9a2;
    --color-divider: #d4e6e1;
    --color-input-bg: rgba(239, 245, 242, 0.72);
    --color-surface-overlay: rgba(47, 122, 114, 0.12);
    --shadow-card: 0 12px 24px rgba(32, 56, 54, 0.12);
    --color-button-disabled: rgba(52, 83, 80, 0.45);

    /* aliases so existing components keep working */
    --color-card-warm: var(--color-card-warm-current);
  }

  :global(:root[data-theme='dark']) {
    --color-bg-dark-warm: #10171a;
    --color-text-dark-warm: #e6f1ef;
    --color-text-muted-dark-warm: #9fb0ab;
    --color-header-bg-dark-warm: #151f2a;
    --color-header-hover-dark-warm: #1f2b38;
    --color-header-active-dark-warm: #f0f8f5;
    --color-primary-dark-warm: #4fa792;
    --color-primary-hover-dark-warm: #62b4a0;
    --color-primary-pressed-dark-warm: #3a8d7a;
    --color-secondary-dark-warm: #1f2b38;
    --color-secondary-hover-dark-warm: #293947;
    --color-border-dark-warm: #304048;
    --color-card-warm-dark: #192327;
    --color-card-alt-dark-warm: #1d2a30;
    --color-card-tertiary-dark-warm: #142025;
    --color-chip-dark-warm: #3f8775;
    --color-divider-dark-warm: #293941;
    --color-input-bg-dark-warm: rgba(24, 34, 38, 0.85);
    --color-surface-overlay-dark-warm: rgba(45, 66, 74, 0.35);
    --shadow-card-dark-warm: 0 12px 28px rgba(0, 0, 0, 0.6);
    --color-button-disabled-dark-warm: rgba(80, 90, 105, 0.4);

    --color-bg: #0e1516;
    --color-text: #e1f2f0;
    --color-text-muted: #90bab4;
    --color-header-bg: #11252a;
    --color-header-hover: #183339;
    --color-header-active: #d0f0eb;
    --color-primary: #2f7a72;
    --color-primary-hover: #3f958d;
    --color-primary-pressed: #1f5a54;
    --color-secondary: #1a2f35;
    --color-secondary-hover: #234149;
    --color-border: #234647;
    --color-card-warm-current: #142225;
    --color-card-alt: #192c30;
    --color-card-tertiary: #122025;
    --color-chip: #4a958d;
    --color-divider: #1f3c40;
    --color-input-bg: rgba(16, 26, 27, 0.85);
    --color-surface-overlay: rgba(47, 122, 114, 0.25);
    --shadow-card: 0 14px 32px rgba(0, 0, 0, 0.55);
    --color-button-disabled: rgba(64, 96, 96, 0.45);

    --color-card-warm: var(--color-card-warm-current);
  }

  :global(body) {
    margin: 0;
    background: var(--color-bg);
    color: var(--color-text);
    font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    transition: background 0.25s ease, color 0.25s ease;
  }

  .site-header {
    background: var(--color-header-bg);
    color: #f6f6f6;
    border-bottom: 1px solid var(--color-header-hover);
    position: sticky;
    top: 0;
    z-index: 10;
  }

  .header-inner {
    max-width: 1100px;
    margin: 0 auto;
    padding: 16px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 24px;
  }

  .brand {
    font-weight: 700;
    font-size: 1.15rem;
    letter-spacing: 0.02em;
    color: #f6f6f6;
    text-decoration: none;
  }

  .nav {
    display: flex;
    gap: 16px;
  }

  .nav-link {
    color: rgba(246, 246, 246, 0.75);
    text-decoration: none;
    font-weight: 500;
    padding-bottom: 2px;
    border-bottom: 2px solid transparent;
    transition: color 0.2s ease, border-color 0.2s ease;
  }

  .nav-link:hover {
    color: var(--color-header-active);
    border-color: rgba(246, 246, 246, 0.4);
  }

  .nav-link.active {
    color: var(--color-header-active);
    border-color: var(--color-header-active);
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .theme-toggle {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: transparent;
    border: 1px solid rgba(246, 246, 246, 0.35);
    border-radius: 999px;
    padding: 6px 12px;
    color: var(--color-header-active);
    font-size: 0.95rem;
    cursor: pointer;
    transition: background 0.2s ease, border-color 0.2s ease, color 0.2s ease;
  }

  .theme-toggle:hover {
    background: rgba(246, 246, 246, 0.12);
    border-color: rgba(246, 246, 246, 0.6);
  }

  .theme-toggle:focus-visible {
    outline: 2px solid var(--color-header-active);
    outline-offset: 2px;
  }

  .theme-toggle__icon {
    font-size: 1.15rem;
    line-height: 1;
  }

  .user-switcher {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 4px;
    color: var(--color-header-active);
    font-size: 0.85rem;
  }

  .login-link {
    color: var(--color-header-active);
    font-weight: 600;
    text-decoration: none;
    padding: 6px 0;
  }

  .login-link:hover {
    text-decoration: underline;
  }

  .user-switcher label {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }

  .user-switcher__label {
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }

  .user-switcher select {
    min-width: 200px;
    border-radius: 999px;
    padding: 6px 12px;
    border: 1px solid rgba(246, 246, 246, 0.35);
    background: rgba(246, 246, 246, 0.12);
    color: var(--color-header-active);
    font-weight: 500;
  }

  .user-switcher select:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }

  .admin-panel {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
    padding: 8px 12px;
    border-radius: 12px;
    border: 1px solid rgba(246, 246, 246, 0.35);
    background: rgba(246, 246, 246, 0.08);
    color: var(--color-header-active);
    min-width: 220px;
  }

  .admin-panel__title {
    font-size: 0.85rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }

  .admin-panel__label {
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .admin-panel label {
    display: flex;
    flex-direction: column;
    gap: 4px;
    width: 100%;
  }

  .admin-panel select {
    border-radius: 8px;
    border: 1px solid rgba(246, 246, 246, 0.35);
    background: rgba(30, 36, 48, 0.4);
    color: var(--color-header-active);
    padding: 6px 10px;
    width: 100%;
  }

  .admin-panel select:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .admin-panel__status {
    font-size: 0.75rem;
    color: rgba(246, 246, 246, 0.75);
  }

  .admin-panel__status--error {
    color: #ffb4a2;
    font-weight: 600;
  }

  .logout-button {
    border: 1px solid rgba(246, 246, 246, 0.35);
    background: transparent;
    color: var(--color-header-active);
    border-radius: 999px;
    padding: 6px 12px;
    font-size: 0.9rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s ease, border-color 0.2s ease;
  }

  .logout-button:hover {
    background: rgba(246, 246, 246, 0.12);
    border-color: rgba(246, 246, 246, 0.6);
  }

  .user-switcher select:focus-visible {
    outline: 2px solid var(--color-header-active);
    outline-offset: 2px;
  }

  .user-switcher__status {
    font-size: 0.85rem;
    color: rgba(246, 246, 246, 0.7);
  }

  .user-switcher__status--muted {
    color: rgba(246, 246, 246, 0.5);
  }

  .user-switcher__status--error {
    color: #ffb4a2;
    font-weight: 600;
  }

  .layout-content {
    min-height: 100vh;
  }

  @media (max-width: 640px) {
    .header-inner {
      flex-direction: column;
      align-items: flex-start;
    }

    .nav {
      width: 100%;
      justify-content: space-between;
    }

    .header-actions {
      width: 100%;
      justify-content: flex-end;
    }
  }
</style> -->

<!-- <script lang="ts">
  import { onMount } from 'svelte';
  import { get } from 'svelte/store';
  import { page } from '$app/stores';
  import { API_URL, MOCK_USER_HEADER, PERMISSIONS, ROLES } from '$lib/config';
  import { themeStore, toggleTheme } from '$lib/stores/theme';
  import { usersStore, activeUser, activeUserId, hasPermission } from '$lib/stores/mockUsers';
  import type { MockUser } from '$lib/stores/mockUsers';
  import favicon from '$lib/assets/favicon.svg';

  const pageStore = page;
  const theme = themeStore;
  let { children } = $props();

  // ---------------------------
  // State variables
  // ---------------------------
  let loadingUsers = $state(false);
  let usersError = $state('');
  let selectedUserId = $state('');
  let roleError = $state('');
  let roleSuccess = $state('');
  let roleBusy = $state(false);
  let availableRoles = $state([...ROLES]);
  let manageTargetId = $state('');
  let manageTarget = $state<MockUser | null>(null);

  // ---------------------------
  // Derived/reactive variables
  // ---------------------------
  // let activePersona = $state<MockUser | null>(null);

  // $effect(() => {
  //   // update activePersona whenever activeUser store changes
  //   activePersona = get(activeUser);
  // });

  // let canCreate = $derived(() => hasPermission(activePersona, PERMISSIONS.create));
  // let canAssign = $derived(() => Boolean(activePersona?.is_admin));
  // let personaOptions = $derived(() => get(usersStore)); // personaOptions() returns MockUser[]
  // let manageableUsers = $derived(() => personaOptions().filter(u => !u.is_admin));
  // let selectedUser = $derived(() =>
  //   personaOptions().find(u => u.id === selectedUserId) ?? null
  // );
  // Reactive variables
let activePersona = $derived(activeUser);
let canCreate = $derived(() => hasPermission(activePersona(), PERMISSIONS.create));
let canAssign = $derived(() => Boolean(activePersona()?.is_admin));
let personaOptions = $derived(usersStore); // reacts to store changes
let manageableUsers = $derived(() => personaOptions().filter(u => !u.is_admin));
let selectedUser = $derived(() =>
  personaOptions().find(u => u.id === selectedUserId) ?? null
);

  // ---------------------------
  // Reactive effects
  // ---------------------------
  $effect(() => {
    const nextId = activePersona?.id ?? '';
    if (nextId && selectedUserId !== nextId) {
      selectedUserId = nextId;
      roleError = '';
      roleSuccess = '';
    }
  });

  $effect(() => {
    if (!canAssign) {
      manageTargetId = '';
      manageTarget = null;
    } else {
      if (!manageTargetId || !manageableUsers().some(u => u.id === manageTargetId)) {
        manageTargetId = manageableUsers()[0]?.id ?? '';
      }
      manageTarget = manageableUsers().find(u => u.id === manageTargetId) ?? null;
    }
  });

  // ---------------------------
  // Fetch users and roles
  // ---------------------------
  onMount(async () => {
    if (get(usersStore).length) return;

    loadingUsers = true;
    usersError = '';

    try {
      const res = await fetch(`${API_URL}/users`);
      if (!res.ok) throw new Error('Failed to load users');

      const data = await res.json();
      if (Array.isArray(data)) usersStore.setUsers(data);

      const rolesRes = await fetch(`${API_URL}/roles`);
      if (rolesRes.ok) {
        const rolesData = await rolesRes.json();
        if (Array.isArray(rolesData) && rolesData.length) availableRoles = rolesData;
      }
    } catch (error) {
      console.error(error);
      usersError = 'Unable to load mock users';
    } finally {
      loadingUsers = false;
    }
  });

  // ---------------------------
  // Helper functions
  // ---------------------------
  function authHeaders() {
    const user = get(activeUser);
    if (!user) throw new Error('Select a persona first.');
    return { [MOCK_USER_HEADER]: user.id };
  }

  function handlePersonaChange(event: Event) {
    const nextId = (event.currentTarget as HTMLSelectElement).value;
    if (!nextId) return;
    activeUserId.set(nextId);
    selectedUserId = nextId;
    roleError = '';
    roleSuccess = '';
  }

  function handleManageTargetChange(event: Event) {
    manageTargetId = (event.currentTarget as HTMLSelectElement).value;
    roleError = '';
    roleSuccess = '';
  }

  async function handleRoleChange(event: Event) {
    const nextRole = (event.currentTarget as HTMLSelectElement).value;
    if (!manageTargetId || !nextRole) return;

    roleError = '';
    roleSuccess = '';
    roleBusy = true;

    try {
      const headers = {
        'Content-Type': 'application/json',
        ...authHeaders()
      };

      const res = await fetch(`${API_URL}/users/${manageTargetId}/role`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ role: nextRole })
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || 'Failed to update access level');
      }

      const updated = await res.json();
      usersStore.updateUser(updated);
      roleSuccess = `${updated.name} is now ${updated.role}`;
    } catch (error) {
      console.error(error);
      roleError = error instanceof Error ? error.message : 'Failed to update access level';
    } finally {
      roleBusy = false;
    }
  }
</script> -->

<script lang="ts">
import { onMount } from 'svelte';
import { get, derived } from 'svelte/store';
import { page } from '$app/stores';
import { goto } from '$app/navigation';
import { API_URL, MOCK_USER_HEADER, PERMISSIONS, ROLES } from '$lib/config';
import { themeStore, toggleTheme } from '$lib/stores/theme';
import { usersStore, activeUser, activeUserId, hasPermission } from '$lib/stores/mockUsers';
import type { MockUser } from '$lib/stores/mockUsers';
import favicon from '$lib/assets/favicon.svg';

const pageStore = page;
const theme = themeStore;
let { children } = $props();

// ---------------------------
// State variables
// ---------------------------
let loadingUsers = $state(false);
let usersError = $state('');
let selectedUserId = $state('');
let roleError = $state('');
let roleSuccess = $state('');
let roleBusy = $state(false);
let availableRoles = $state([...ROLES]);
let manageTargetId = $state('');
let manageTarget = $state<MockUser | null>(null);

// ---------------------------
// Derived/reactive variables
// ---------------------------

// activePersona is a derived store from activeUser
let activePersona = activeUser;

// canCreate / canAssign use $activePersona to unwrap
let canCreate = derived(activePersona, $ap => hasPermission($ap, PERMISSIONS.create));
let canAssign = derived(activePersona, $ap => Boolean($ap?.is_admin));
let isAuthenticated = derived(activePersona, ($ap) => Boolean($ap));
let personaOptions = derived(usersStore, ($users) => $users);
let manageableUsers = derived(personaOptions, ($options) =>
  $options.filter((u) => !u.is_admin)
);
let hasLoadedPersonas = derived(personaOptions, ($options) => $options.length > 0);
let selectedUser = $derived(() => $personaOptions.find((u) => u.id === selectedUserId) ?? null);

// ---------------------------
// Reactive effects
// ---------------------------
$effect(() => {
  const nextId = $activePersona?.id ?? '';
  if (!nextId) {
    selectedUserId = '';
    return;
  }
  if (selectedUserId !== nextId) {
    selectedUserId = nextId;
    roleError = '';
    roleSuccess = '';
  }
});

$effect(() => {
  //console.log($canAssign);
  if (!$canAssign) {
    manageTargetId = '';
    manageTarget = null;
  } else {
    if (!manageTargetId || !$manageableUsers.some((u) => u.id === manageTargetId)) {
      manageTargetId = $manageableUsers[0]?.id ?? '';
    }
    manageTarget = $manageableUsers.find((u) => u.id === manageTargetId) ?? null;
  }
});

$effect(() => {
  if (typeof window === 'undefined') return;

  const authenticated = $isAuthenticated;
  const onLoginPage = $pageStore.url.pathname.startsWith('/login');
  const personasReady = $hasLoadedPersonas && !loadingUsers;

  if (personasReady && !authenticated && !onLoginPage) {
    goto('/login');
    return;
  }

  if (authenticated && onLoginPage) {
    goto('/');
  }
});

// ---------------------------
// Fetch users and roles
// ---------------------------
onMount(async () => {
  if (get(usersStore).length) return;

  loadingUsers = true;
  usersError = '';

  try {
    const res = await fetch(`${API_URL}/users`);
    if (!res.ok) throw new Error('Failed to load users');

    const data = await res.json();
    if (Array.isArray(data)) usersStore.setUsers(data);

    const rolesRes = await fetch(`${API_URL}/roles`);
    if (rolesRes.ok) {
      const rolesData = await rolesRes.json();
      if (Array.isArray(rolesData) && rolesData.length) availableRoles = rolesData;
    }
  } catch (error) {
    console.error(error);
    usersError = 'Unable to load mock users';
  } finally {
    loadingUsers = false;
  }
});

// ---------------------------
// Helper functions
// ---------------------------
function authHeaders() {
  const user = get(activeUser);
  if (!user) throw new Error('Select a persona first.');
  return { [MOCK_USER_HEADER]: user.id };
}

function handlePersonaChange(event: Event) {
  const nextId = (event.currentTarget as HTMLSelectElement).value;
  if (!nextId) return;
  activeUserId.set(nextId);
  selectedUserId = nextId;
  roleError = '';
  roleSuccess = '';
}

function handleLogout() {
  activeUserId.clear();
  selectedUserId = '';
  manageTargetId = '';
  manageTarget = null;
  roleError = '';
  roleSuccess = '';
  if ($pageStore.url.pathname !== '/login') {
    goto('/login');
  }
}

function handleManageTargetChange(event: Event) {
  manageTargetId = (event.currentTarget as HTMLSelectElement).value;
  roleError = '';
  roleSuccess = '';
}

async function handleRoleChange(event: Event) {
  const nextRole = (event.currentTarget as HTMLSelectElement).value;
  if (!manageTargetId || !nextRole) return;

  roleError = '';
  roleSuccess = '';
  roleBusy = true;

  try {
    const headers = { 'Content-Type': 'application/json', ...authHeaders() };

    const res = await fetch(`${API_URL}/users/${manageTargetId}/role`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ role: nextRole })
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || 'Failed to update access level');
    }

    const updated = await res.json();
    usersStore.updateUser(updated);
    roleSuccess = `${updated.name} is now ${updated.role}`;
  } catch (error) {
    console.error(error);
    roleError = error instanceof Error ? error.message : 'Failed to update access level';
  } finally {
    roleBusy = false;
  }
}
</script>

<svelte:head>
  <link rel="icon" href={favicon} />
</svelte:head>

<header class="site-header">
  <div class="header-inner">
    <a class="brand" href="/">PAQS</a>
    <nav class="nav">
      <a
        class="nav-link"
        href="/"
        class:active={$pageStore.url.pathname === '/'}
      >Dashboard</a>
      {#if $canCreate}
        <a
          class="nav-link"
          href="/create"
          class:active={$pageStore.url.pathname.startsWith('/create')}
        >Create Container</a>
      {/if}
    </nav>
    <div class="header-actions">
      <button
        class="theme-toggle"
        type="button"
        onclick={toggleTheme}
        aria-label={$theme === 'dark' ? 'Use light theme' : 'Use dark theme'}
      >
        <span class="theme-toggle__icon" aria-hidden="true">
          {#if $theme === 'dark'}
            🌙
          {:else}
            ☀️
          {/if}
        </span>
        <span class="theme-toggle__label">{$theme === 'dark' ? 'Dark' : 'Light'}</span>
      </button>

      {#if loadingUsers}
        <span class="user-switcher__status">Loading personas…</span>
      {:else if usersError}
        <span class="user-switcher__status user-switcher__status--error">{usersError}</span>
      {:else if !$isAuthenticated}
        <a class="login-link" href="/login">Login</a>
      {:else}
        <div class="user-switcher">
          <label>
            <span class="user-switcher__label">Persona</span>
            <select value={selectedUserId} onchange={handlePersonaChange}>
              {#each $personaOptions as user}
                <option value={user.id}>{user.name} — {user.role}</option>
              {/each}
            </select>
          </label>
        </div>

        {#if $canAssign}
          <div class="admin-panel">
            <span class="admin-panel__title">Manage access</span>
            {#if $manageableUsers.length}
              <label>
                <span class="admin-panel__label">Persona</span>
                <select value={manageTargetId} onchange={handleManageTargetChange}>
                  {#each $manageableUsers as user}
                    <option value={user.id}>{user.name} — {user.role}</option>
                  {/each}
                </select>
              </label>
              <label>
                <span class="admin-panel__label">Access level</span>
                <select onchange={handleRoleChange} disabled={roleBusy || !manageTarget}>
                  {#each availableRoles as role}
                    <option value={role} selected={manageTarget?.role === role}>{role}</option>
                  {/each}
                </select>
              </label>
              {#if roleError}
                <span class="admin-panel__status admin-panel__status--error">{roleError}</span>
              {:else if roleSuccess}
                <span class="admin-panel__status">{roleSuccess}</span>
              {/if}
            {:else}
              <span class="admin-panel__status">No other personas available to update.</span>
            {/if}
          </div>
        {/if}

        <button type="button" class="logout-button" onclick={handleLogout}>
          Log out
        </button>
      {/if}
    </div>
  </div>
</header>

<div class="layout-content">
  {@render children?.()}
</div>

<style>
  :global(:root) {
    --color-bg-warm: #eff5f2;
    --color-text-warm: #221f26;
    --color-text-muted-warm: #4f5d58;
    --color-header-bg-warm: #384055;
    --color-header-hover-warm: #4a5168;
    --color-header-active-warm: #eff5f2;
    --color-primary-warm: #3c7a6b;
    --color-primary-hover-warm: #4e8d7d;
    --color-primary-pressed-warm: #2c5f54;
    --color-secondary-warm: #384055;
    --color-secondary-hover-warm: #4a5168;
    --color-border-warm: #b8d1c9;
    --color-card-warm-warm: #cfe1da;
    --color-card-alt-warm: #d9e0ed;
    --color-card-tertiary-warm: #e6f0ec;
    --color-chip-warm: #8ab3a4;
    --color-divider-warm: #d9e6e2;
    --color-input-bg-warm: rgba(239, 245, 242, 0.7);
    --color-surface-overlay-warm: rgba(79, 90, 107, 0.08);
    --shadow-card-warm: 0 12px 24px rgba(39, 32, 39, 0.1);
    --color-button-disabled-warm: rgba(53, 59, 81, 0.4);

    --color-bg: var(--color-bg-warm);
    --color-text: var(--color-text-warm);
    --color-text-muted: var(--color-text-muted-warm);
    --color-header-bg: #343d4c;
    --color-header-hover: #455266;
    --color-header-active: #f1f6f5;
    --color-primary: #2f7a72;
    --color-primary-hover: #40948b;
    --color-primary-pressed: #225e58;
    --color-secondary: #4d6675;
    --color-secondary-hover: #5b7787;
    --color-border: #b6d3cd;
    --color-card-warm-current: #d4e4de;
    --color-card-alt: #dde6f1;
    --color-card-tertiary: #e9f2ef;
    --color-chip: #5fa9a2;
    --color-divider: #d4e6e1;
    --color-input-bg: rgba(239, 245, 242, 0.72);
    --color-surface-overlay: rgba(47, 122, 114, 0.12);
    --shadow-card: 0 12px 24px rgba(32, 56, 54, 0.12);
    --color-button-disabled: rgba(52, 83, 80, 0.45);
    --color-card-warm: var(--color-card-warm-current);
  }

  :global(:root[data-theme='dark']) {
    --color-bg-dark-warm: #10171a;
    --color-text-dark-warm: #e6f1ef;
    --color-text-muted-dark-warm: #9fb0ab;
    --color-header-bg-dark-warm: #151f2a;
    --color-header-hover-dark-warm: #1f2b38;
    --color-header-active-dark-warm: #f0f8f5;
    --color-primary-dark-warm: #4fa792;
    --color-primary-hover-dark-warm: #62b4a0;
    --color-primary-pressed-dark-warm: #3a8d7a;
    --color-secondary-dark-warm: #1f2b38;
    --color-secondary-hover-dark-warm: #293947;
    --color-border-dark-warm: #304048;
    --color-card-warm-dark: #192327;
    --color-card-alt-dark-warm: #1d2a30;
    --color-card-tertiary-dark-warm: #142025;
    --color-chip-dark-warm: #3f8775;
    --color-divider-dark-warm: #293941;
    --color-input-bg-dark-warm: rgba(24, 34, 38, 0.85);
    --color-surface-overlay-dark-warm: rgba(45, 66, 74, 0.35);
    --shadow-card-dark-warm: 0 12px 28px rgba(0, 0, 0, 0.6);
    --color-button-disabled-dark-warm: rgba(80, 90, 105, 0.4);

    --color-bg: #0e1516;
    --color-text: #e1f2f0;
    --color-text-muted: #90bab4;
    --color-header-bg: #11252a;
    --color-header-hover: #183339;
    --color-header-active: #d0f0eb;
    --color-primary: #2f7a72;
    --color-primary-hover: #3f958d;
    --color-primary-pressed: #1f5a54;
    --color-secondary: #1a2f35;
    --color-secondary-hover: #234149;
    --color-border: #234647;
    --color-card-warm-current: #142225;
    --color-card-alt: #192c30;
    --color-card-tertiary: #122025;
    --color-chip: #4a958d;
    --color-divider: #1f3c40;
    --color-input-bg: rgba(16, 26, 27, 0.85);
    --color-surface-overlay: rgba(47, 122, 114, 0.25);
    --shadow-card: 0 14px 32px rgba(0, 0, 0, 0.55);
    --color-button-disabled: rgba(64, 96, 96, 0.45);
    --color-card-warm: var(--color-card-warm-current);
  }

  :global(body) {
    margin: 0;
    background: var(--color-bg);
    color: var(--color-text);
    font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    transition: background 0.25s ease, color 0.25s ease;
  }

  .site-header {
    background: var(--color-header-bg);
    color: #f6f6f6;
    border-bottom: 1px solid var(--color-header-hover);
    position: sticky;
    top: 0;
    z-index: 10;
  }

  .header-inner {
    max-width: 1100px;
    margin: 0 auto;
    padding: 16px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 24px;
  }

  .brand {
    font-weight: 700;
    font-size: 1.15rem;
    letter-spacing: 0.02em;
    color: #f6f6f6;
    text-decoration: none;
  }

  .nav {
    display: flex;
    gap: 16px;
  }

  .nav-link {
    color: rgba(246, 246, 246, 0.75);
    text-decoration: none;
    font-weight: 500;
    padding-bottom: 2px;
    border-bottom: 2px solid transparent;
    transition: color 0.2s ease, border-color 0.2s ease;
  }

  .nav-link:hover {
    color: var(--color-header-active);
    border-color: rgba(246, 246, 246, 0.4);
  }

  .nav-link.active {
    color: var(--color-header-active);
    border-color: var(--color-header-active);
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .theme-toggle {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: transparent;
    border: 1px solid rgba(246, 246, 246, 0.35);
    border-radius: 999px;
    padding: 6px 12px;
    color: var(--color-header-active);
    font-size: 0.95rem;
    cursor: pointer;
    transition: background 0.2s ease, border-color 0.2s ease, color 0.2s ease;
  }

  .theme-toggle:hover {
    background: rgba(246, 246, 246, 0.12);
    border-color: rgba(246, 246, 246, 0.6);
  }

  .theme-toggle:focus-visible {
    outline: 2px solid var(--color-header-active);
    outline-offset: 2px;
  }

  .theme-toggle__icon {
    font-size: 1.15rem;
    line-height: 1;
  }

  .user-switcher {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 4px;
    color: var(--color-header-active);
    font-size: 0.85rem;
  }

  .user-switcher label {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }

  .user-switcher__label {
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }

  .user-switcher select {
    min-width: 200px;
    border-radius: 999px;
    padding: 6px 12px;
    border: 1px solid rgba(246, 246, 246, 0.35);
    background: rgba(246, 246, 246, 0.12);
    color: var(--color-header-active);
    font-weight: 500;
  }

  .user-switcher select:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }

  .admin-panel {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
    padding: 8px 12px;
    border-radius: 12px;
    border: 1px solid rgba(246, 246, 246, 0.35);
    background: rgba(246, 246, 246, 0.08);
    color: var(--color-header-active);
    min-width: 220px;
  }

  .admin-panel__title {
    font-size: 0.85rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }

  .admin-panel__label {
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .admin-panel label {
    display: flex;
    flex-direction: column;
    gap: 4px;
    width: 100%;
  }

  .admin-panel select {
    border-radius: 8px;
    border: 1px solid rgba(246, 246, 246, 0.35);
    background: rgba(30, 36, 48, 0.4);
    color: var(--color-header-active);
    padding: 6px 10px;
    width: 100%;
  }

  .admin-panel select:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .admin-panel__status {
    font-size: 0.75rem;
    color: rgba(246, 246, 246, 0.75);
  }

  .admin-panel__status--error {
    color: #ffb4a2;
    font-weight: 600;
  }

  .user-switcher select:focus-visible {
    outline: 2px solid var(--color-header-active);
    outline-offset: 2px;
  }

  .user-switcher__status {
    font-size: 0.85rem;
    color: rgba(246, 246, 246, 0.7);
  }

  .user-switcher__status--muted {
    color: rgba(246, 246, 246, 0.5);
  }

  .user-switcher__status--error {
    color: #ffb4a2;
    font-weight: 600;
  }

  .layout-content {
    min-height: 100vh;
  }

  @media (max-width: 640px) {
    .header-inner {
      flex-direction: column;
      align-items: flex-start;
    }

    .nav {
      width: 100%;
      justify-content: space-between;
    }

    .header-actions {
      width: 100%;
      justify-content: flex-end;
    }
  }
</style>
