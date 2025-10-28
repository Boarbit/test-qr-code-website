export const API_URL = 'http://localhost:8000';
export const MOCK_USER_HEADER = 'X-Mock-User';
export const PERMISSIONS = {
  view: 'view',
  update: 'update',
  create: 'create',
  assign: 'assign'
} as const;

export const ROLES = ['Viewer', 'Editor', 'Creator', 'Admin'] as const;
