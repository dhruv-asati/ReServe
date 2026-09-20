import DarkVeil from './DarkVeil';

/**
 * Fixed, full-viewport DarkVeil background rendered once at the app root
 * (see App.jsx) so it sits behind every route/page instead of being
 * re-mounted per page.
 */
export default function AppBackground() {
  return (
    <div
      aria-hidden="true"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 0,
        pointerEvents: 'none',
      }}
    >
      <DarkVeil
        hueShift={0}
        noiseIntensity={0}
        scanlineIntensity={0}
        speed={1.5}
        scanlineFrequency={0.5}
        warpAmount={0}
      />
    </div>
  );
}
