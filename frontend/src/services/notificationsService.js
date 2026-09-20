import { api, USE_MOCKS } from './api';

/**
 * Notification endpoints (app/api/notifications.py).
 *
 * Notifications only exist for a signed-in backend user, so with mocks on
 * (`VITE_USE_MOCKS` not 'false') there is nothing to fetch: the list resolves
 * empty instead of making a request that would 401.
 */

const EMPTY_LIST = {
  items: [],
  total: 0,
  skip: 0,
  limit: 20,
  has_more: false,
  unread_count: 0,
};

/** GET /notifications -> { items, total, skip, limit, has_more, unread_count } */
export function listNotifications(params = {}) {
  if (USE_MOCKS) return Promise.resolve({ ...EMPTY_LIST });
  return api.get('/notifications', { params }).then((response) => response.data);
}

/** PATCH /notifications/{id}/read -> the updated notification. Idempotent. */
export function markNotificationRead(id) {
  if (USE_MOCKS) return Promise.resolve(null);
  return api.patch(`/notifications/${encodeURIComponent(id)}/read`).then((response) => response.data);
}

/** PATCH /notifications/read-all -> { updated, unread_count }. */
export function markAllNotificationsRead() {
  if (USE_MOCKS) return Promise.resolve({ updated: 0, unread_count: 0 });
  return api.patch('/notifications/read-all').then((response) => response.data);
}
