import { BrowserRouter } from 'react-router-dom';
import AppRoutes from '@/routes/AppRoutes';
import { AuthProvider } from '@/context/AuthContext';
import AppBackground from '@/components/backgrounds/AppBackground';
import MagicBento from '@/components/MagicBento';

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <MagicBento
          enableStars
          enableSpotlight
          enableBorderGlow
          enableTilt={false}
          enableMagnetism={false}
          clickEffect
          spotlightRadius={400}
          particleCount={12}
          glowColor="132, 0, 255"
          disableAnimations={false}
        >
          <AppBackground />
          <div style={{ position: 'relative', zIndex: 1 }}>
            <AppRoutes />
          </div>
        </MagicBento>
      </AuthProvider>
    </BrowserRouter>
  );
}
