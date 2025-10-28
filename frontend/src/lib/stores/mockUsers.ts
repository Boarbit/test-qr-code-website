// import { browser } from '$app/environment';
// import { derived, get, writable } from 'svelte/store';

// export type MockUser = {
//   id: string;
//   name: string;
//   role: string;
//   permissions: string[];
//   is_admin: boolean;
// };

// const STORAGE_KEY = 'paqs-selected-user';

// const mockUsersStore = writable<MockUser[]>([]);
// const activeUserIdStore = writable<string | null>(null);

// if (browser) {
//   const storedId = window.localStorage.getItem(STORAGE_KEY);
//   if (storedId) {
//     activeUserIdStore.set(storedId);
//   }
// }

// const activeUserStore = derived([mockUsersStore, activeUserIdStore], ([$users, $activeId]) => {
//   if (!$users.length) {
//     return null;
//   }

//   const fallback = $users[0];
//   if (!$activeId) {
//     return fallback;
//   }

//   return $users.find((user) => user.id === $activeId) ?? fallback;
// });

// export const usersStore = {
//   subscribe: mockUsersStore.subscribe,
//   setUsers(list: MockUser[]) {
//     mockUsersStore.set(list);

//     const currentId = get(activeUserIdStore);
//     const hasCurrent = currentId && list.some((user) => user.id === currentId);
//     const nextId = hasCurrent ? currentId! : list[0]?.id ?? null;

//     activeUserIdStore.set(nextId);

//     if (browser && nextId) {
//       window.localStorage.setItem(STORAGE_KEY, nextId);
//     }
//   },
//   updateUser(updated: MockUser) {
//     const current = get(mockUsersStore);
//     const next = current.map((user) => (user.id === updated.id ? updated : user));
//     mockUsersStore.set(next);
//   }
// };

// export const activeUser = {
//   subscribe: activeUserStore.subscribe
// };

// export const activeUserId = {
//   subscribe: activeUserIdStore.subscribe,
//   set(id: string) {
//     activeUserIdStore.set(id);
//     if (browser) {
//       window.localStorage.setItem(STORAGE_KEY, id);
//     }
//   }
// };

// export function hasPermission(user: MockUser | null, permission: string): boolean {
//   return Boolean(user?.permissions?.includes(permission));
//}


import { browser } from '$app/environment';
import { writable, derived, get } from 'svelte/store';

export type MockUser = {
  id: string;
  name: string;
  role: string;
  permissions: string[];
  is_admin: boolean;
};

const STORAGE_KEY = 'paqs-selected-user';

// ---------------------------
// Reactive stores
// ---------------------------
export const mockUsersStore = writable<MockUser[]>([]);
export const activeUserIdStore = writable<string | null>(null);

// Load saved active user id from localStorage
if (browser) {
  const storedId = window.localStorage.getItem(STORAGE_KEY);
  if (storedId) {
    activeUserIdStore.set(storedId);
  }
}

// ---------------------------
// Derived: active user
// ---------------------------
export const activeUserStore = derived(
  [mockUsersStore, activeUserIdStore],
  ([$users, $activeId]) => {
    if (!$users.length || !$activeId) {
      return null;
    }

    return $users.find((u) => u.id === $activeId) ?? null;
  }
);

// ---------------------------
// Derived: user lists
// ---------------------------
export const personaOptions = derived(mockUsersStore, $users => $users);
export const manageableUsers = derived(mockUsersStore, $users =>
  $users.filter(u => !u.is_admin)
);

// Derived: selected user by id
export const selectedUser = (selectedUserId: string | null) =>
  derived(mockUsersStore, $users =>
    $users.find(u => u.id === selectedUserId) ?? null
  );

// ---------------------------
// Store helpers
// ---------------------------
export const usersStore = {
  subscribe: mockUsersStore.subscribe,

  setUsers(list: MockUser[]) {
    mockUsersStore.set(list);

    const currentId = get(activeUserIdStore);
    const hasCurrent = currentId && list.some((u) => u.id === currentId);
    const nextId = hasCurrent ? currentId : null;

    activeUserIdStore.set(nextId);

    if (browser) {
      if (nextId) {
        window.localStorage.setItem(STORAGE_KEY, nextId);
      } else {
        window.localStorage.removeItem(STORAGE_KEY);
      }
    }
  },

  updateUser(updated: MockUser) {
    mockUsersStore.update(users =>
      users.map(u => (u.id === updated.id ? updated : u))
    );
  }
};

export const activeUser = {
  subscribe: activeUserStore.subscribe
};

export const activeUserId = {
  subscribe: activeUserIdStore.subscribe,
  set(id: string | null) {
    activeUserIdStore.set(id);
    if (browser) {
      if (id) {
        window.localStorage.setItem(STORAGE_KEY, id);
      } else {
        window.localStorage.removeItem(STORAGE_KEY);
      }
    }
  },
  clear() {
    this.set(null);
  }
};

// ---------------------------
// Permission helper
// ---------------------------
export function hasPermission(user: MockUser | null, permission: string): boolean {
  return Boolean(user?.permissions?.includes(permission));
}
