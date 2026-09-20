import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import App from '@/App';
import { API_BASE_URL, checkApiConnection } from '@/services/api';
import '@/styles/index.css';

// Dev-only: say in the console whether the backend is reachable, so a wrong
// URL, a stopped server or a CORS problem is obvious before any page is wired up.
if (import.meta.env.DEV) {
  checkApiConnection().then((result) => {
    if (result.ok) {
      console.info(`[api] Connected to ${API_BASE_URL} (${result.environment}, v${result.version}).`);
    } else if (result.database_connected === false) {
      console.warn(`[api] ${API_BASE_URL} is up but its database is not reachable — check DATABASE_URL.`);
    } else {
      console.warn(`[api] ${result.error?.message}`);
    }
  });
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
