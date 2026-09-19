import { BrowserRouter } from 'react-router-dom';
import AppRoutes from '@/routes/AppRoutes';
import { AuthProvider } from '@/context/AuthContext';
import AppBackground from '@/components/backgrounds/AppBackground';

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppBackground />
        <div style={{ position: 'relative', zIndex: 1 }}>
          <AppRoutes />
        </div>
      </AuthProvider>
    </BrowserRouter>
  );
}
