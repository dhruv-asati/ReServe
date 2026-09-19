import { Outlet } from 'react-router-dom';

/**
 * Shell for unauthenticated routes (landing, login, register).
 * Deliberately chrome-free — each public page owns its own composition.
 */
export default function PublicLayout() {
  return (
    <div className="min-h-screen bg-transparent">
      <Outlet />
    </div>
  );
}
