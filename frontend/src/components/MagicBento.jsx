import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { gsap } from 'gsap';
import './MagicBento.css';

/**
 * Magic Bento (React Bits), reworked as an app-wide effect instead of a demo grid.
 *
 *   <MagicBento …settings>…app…</MagicBento>   mounted once, in App.jsx
 *
 * It provides the settings to every <Card> (via useMagicBento) and runs one
 * global spotlight. Each Card calls useMagicCard() to get the per-card effects:
 * floating particles on hover, a click ripple, and optional tilt / magnetism.
 * The cursor-following border glow is pure CSS, driven by the --glow-* variables
 * the spotlight writes onto every `.magic-bento-card`.
 *
 * Effects switch off on small screens and for prefers-reduced-motion.
 */

const DEFAULT_PARTICLE_COUNT = 12;
const DEFAULT_SPOTLIGHT_RADIUS = 300;
const DEFAULT_GLOW_COLOR = '132, 0, 255';
const MOBILE_BREAKPOINT = 768;
const CARD_SELECTOR = '.magic-bento-card';

const MagicBentoContext = createContext(null);

/** Current Magic Bento settings, or null when no provider is mounted. */
export const useMagicBento = () => useContext(MagicBentoContext);

const createParticleElement = (x, y, color = DEFAULT_GLOW_COLOR) => {
  const el = document.createElement('div');
  el.className = 'particle';
  el.style.cssText = `
    position: absolute;
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: rgba(${color}, 1);
    box-shadow: 0 0 6px rgba(${color}, 0.6);
    pointer-events: none;
    z-index: 100;
    left: ${x}px;
    top: ${y}px;
  `;
  return el;
};

const calculateSpotlightValues = radius => ({
  proximity: radius * 0.5,
  fadeDistance: radius * 0.75
});

const updateCardGlowProperties = (card, mouseX, mouseY, glow, radius) => {
  const rect = card.getBoundingClientRect();
  const relativeX = ((mouseX - rect.left) / rect.width) * 100;
  const relativeY = ((mouseY - rect.top) / rect.height) * 100;

  card.style.setProperty('--glow-x', `${relativeX}%`);
  card.style.setProperty('--glow-y', `${relativeY}%`);
  card.style.setProperty('--glow-intensity', glow.toString());
  card.style.setProperty('--glow-radius', `${radius}px`);
};

function useMediaQuery(query) {
  const [matches, setMatches] = useState(() => window.matchMedia(query).matches);

  useEffect(() => {
    const mql = window.matchMedia(query);
    const onChange = () => setMatches(mql.matches);
    onChange();
    mql.addEventListener('change', onChange);
    return () => mql.removeEventListener('change', onChange);
  }, [query]);

  return matches;
}

/**
 * Per-card effects. Attach to a positioned, overflow-hidden element via `ref`.
 * `magic` is the object returned by useMagicBento(); null/disabled = no-op.
 */
export function useMagicCard(ref, magic) {
  const enabled = Boolean(magic?.enabled);
  const enableStars = Boolean(magic?.enableStars);
  const enableTilt = Boolean(magic?.enableTilt);
  const enableMagnetism = Boolean(magic?.enableMagnetism);
  const clickEffect = Boolean(magic?.clickEffect);
  const particleCount = magic?.particleCount ?? DEFAULT_PARTICLE_COUNT;
  const glowColor = magic?.glowColor ?? DEFAULT_GLOW_COLOR;

  useEffect(() => {
    const element = ref.current;
    if (!enabled || !element) return;

    let isHovered = false;
    let particleTemplates = null;
    let liveParticles = [];
    let timeouts = [];
    let magnetismTween = null;

    const initializeParticles = () => {
      if (particleTemplates) return;
      const { width, height } = element.getBoundingClientRect();
      particleTemplates = Array.from({ length: particleCount }, () =>
        createParticleElement(Math.random() * width, Math.random() * height, glowColor)
      );
    };

    const clearParticles = () => {
      timeouts.forEach(clearTimeout);
      timeouts = [];
      magnetismTween?.kill();

      liveParticles.forEach(particle => {
        // Stop the endless drift/pulse tweens first, otherwise they keep
        // ticking on detached nodes after every hover.
        gsap.killTweensOf(particle);
        gsap.to(particle, {
          scale: 0,
          opacity: 0,
          duration: 0.3,
          ease: 'back.in(1.7)',
          onComplete: () => particle.remove()
        });
      });
      liveParticles = [];
    };

    const animateParticles = () => {
      if (!enableStars || !isHovered) return;
      initializeParticles();

      particleTemplates.forEach((particle, index) => {
        const timeoutId = setTimeout(() => {
          if (!isHovered) return;

          const clone = particle.cloneNode(true);
          element.appendChild(clone);
          liveParticles.push(clone);

          gsap.fromTo(clone, { scale: 0, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.3, ease: 'back.out(1.7)' });

          gsap.to(clone, {
            x: (Math.random() - 0.5) * 100,
            y: (Math.random() - 0.5) * 100,
            rotation: Math.random() * 360,
            duration: 2 + Math.random() * 2,
            ease: 'none',
            repeat: -1,
            yoyo: true
          });

          gsap.to(clone, {
            opacity: 0.3,
            duration: 1.5,
            ease: 'power2.inOut',
            repeat: -1,
            yoyo: true
          });
        }, index * 100);

        timeouts.push(timeoutId);
      });
    };

    const handleMouseEnter = () => {
      isHovered = true;
      animateParticles();

      if (enableTilt) {
        gsap.to(element, {
          rotateX: 5,
          rotateY: 5,
          duration: 0.3,
          ease: 'power2.out',
          transformPerspective: 1000
        });
      }
    };

    const handleMouseLeave = () => {
      isHovered = false;
      clearParticles();

      if (enableTilt) {
        gsap.to(element, { rotateX: 0, rotateY: 0, duration: 0.3, ease: 'power2.out' });
      }

      if (enableMagnetism) {
        gsap.to(element, { x: 0, y: 0, duration: 0.3, ease: 'power2.out' });
      }
    };

    const handleMouseMove = e => {
      if (!enableTilt && !enableMagnetism) return;

      const rect = element.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;

      if (enableTilt) {
        gsap.to(element, {
          rotateX: ((y - centerY) / centerY) * -10,
          rotateY: ((x - centerX) / centerX) * 10,
          duration: 0.1,
          ease: 'power2.out',
          transformPerspective: 1000
        });
      }

      if (enableMagnetism) {
        magnetismTween = gsap.to(element, {
          x: (x - centerX) * 0.05,
          y: (y - centerY) * 0.05,
          duration: 0.3,
          ease: 'power2.out'
        });
      }
    };

    const handleClick = e => {
      if (!clickEffect) return;

      const rect = element.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      const maxDistance = Math.max(
        Math.hypot(x, y),
        Math.hypot(x - rect.width, y),
        Math.hypot(x, y - rect.height),
        Math.hypot(x - rect.width, y - rect.height)
      );

      const ripple = document.createElement('div');
      ripple.style.cssText = `
        position: absolute;
        width: ${maxDistance * 2}px;
        height: ${maxDistance * 2}px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(${glowColor}, 0.4) 0%, rgba(${glowColor}, 0.2) 30%, transparent 70%);
        left: ${x - maxDistance}px;
        top: ${y - maxDistance}px;
        pointer-events: none;
        z-index: 1000;
      `;

      element.appendChild(ripple);

      gsap.fromTo(
        ripple,
        { scale: 0, opacity: 1 },
        {
          scale: 1,
          opacity: 0,
          duration: 0.8,
          ease: 'power2.out',
          onComplete: () => ripple.remove()
        }
      );
    };

    element.addEventListener('mouseenter', handleMouseEnter);
    element.addEventListener('mouseleave', handleMouseLeave);
    element.addEventListener('mousemove', handleMouseMove);
    element.addEventListener('click', handleClick);

    return () => {
      isHovered = false;
      element.removeEventListener('mouseenter', handleMouseEnter);
      element.removeEventListener('mouseleave', handleMouseLeave);
      element.removeEventListener('mousemove', handleMouseMove);
      element.removeEventListener('click', handleClick);
      clearParticles();
    };
  }, [ref, enabled, enableStars, enableTilt, enableMagnetism, clickEffect, particleCount, glowColor]);
}

/**
 * One spotlight for the whole page: a soft glow that follows the cursor, plus
 * per-card --glow-* variables (position + intensity) that feed the border glow.
 * Reads every `.magic-bento-card` currently in the document.
 */
const GlobalSpotlight = ({ spotlightRadius = DEFAULT_SPOTLIGHT_RADIUS, glowColor = DEFAULT_GLOW_COLOR }) => {
  useEffect(() => {
    const spotlight = document.createElement('div');
    spotlight.className = 'global-spotlight';
    spotlight.style.cssText = `
      position: fixed;
      width: 800px;
      height: 800px;
      border-radius: 50%;
      pointer-events: none;
      background: radial-gradient(circle,
        rgba(${glowColor}, 0.15) 0%,
        rgba(${glowColor}, 0.08) 15%,
        rgba(${glowColor}, 0.04) 25%,
        rgba(${glowColor}, 0.02) 40%,
        rgba(${glowColor}, 0.01) 65%,
        transparent 70%
      );
      z-index: 200;
      opacity: 0;
      transform: translate(-50%, -50%);
      mix-blend-mode: screen;
    `;
    document.body.appendChild(spotlight);

    const { proximity, fadeDistance } = calculateSpotlightValues(spotlightRadius);
    let frame = 0;
    let lastEvent = null;

    const clearGlow = () => {
      document.querySelectorAll(CARD_SELECTOR).forEach(card => {
        card.style.setProperty('--glow-intensity', '0');
      });
      gsap.to(spotlight, { opacity: 0, duration: 0.3, ease: 'power2.out', overwrite: 'auto' });
    };

    const update = () => {
      frame = 0;
      const e = lastEvent;
      if (!e) return;

      let minDistance = Infinity;

      document.querySelectorAll(CARD_SELECTOR).forEach(card => {
        const cardRect = card.getBoundingClientRect();
        if (!cardRect.width || !cardRect.height) return; // hidden card

        const centerX = cardRect.left + cardRect.width / 2;
        const centerY = cardRect.top + cardRect.height / 2;
        const distance =
          Math.hypot(e.clientX - centerX, e.clientY - centerY) - Math.max(cardRect.width, cardRect.height) / 2;
        const effectiveDistance = Math.max(0, distance);

        minDistance = Math.min(minDistance, effectiveDistance);

        let glowIntensity = 0;
        if (effectiveDistance <= proximity) {
          glowIntensity = 1;
        } else if (effectiveDistance <= fadeDistance) {
          glowIntensity = (fadeDistance - effectiveDistance) / (fadeDistance - proximity);
        }

        updateCardGlowProperties(card, e.clientX, e.clientY, glowIntensity, spotlightRadius);
      });

      gsap.to(spotlight, { left: e.clientX, top: e.clientY, duration: 0.1, ease: 'power2.out', overwrite: 'auto' });

      const targetOpacity =
        minDistance <= proximity
          ? 0.8
          : minDistance <= fadeDistance
            ? ((fadeDistance - minDistance) / (fadeDistance - proximity)) * 0.8
            : 0;

      gsap.to(spotlight, {
        opacity: targetOpacity,
        duration: targetOpacity > 0 ? 0.2 : 0.5,
        ease: 'power2.out',
        overwrite: 'auto'
      });
    };

    const handleMouseMove = e => {
      lastEvent = e;
      if (!frame) frame = requestAnimationFrame(update);
    };

    const handleMouseLeave = () => {
      lastEvent = null;
      clearGlow();
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.documentElement.addEventListener('mouseleave', handleMouseLeave);

    return () => {
      if (frame) cancelAnimationFrame(frame);
      document.removeEventListener('mousemove', handleMouseMove);
      document.documentElement.removeEventListener('mouseleave', handleMouseLeave);
      gsap.killTweensOf(spotlight);
      spotlight.remove();
      document.querySelectorAll(CARD_SELECTOR).forEach(card => {
        card.style.setProperty('--glow-intensity', '0');
      });
    };
  }, [spotlightRadius, glowColor]);

  return null;
};

const MagicBento = ({
  children,
  enableStars = true,
  enableSpotlight = true,
  enableBorderGlow = true,
  disableAnimations = false,
  spotlightRadius = DEFAULT_SPOTLIGHT_RADIUS,
  particleCount = DEFAULT_PARTICLE_COUNT,
  enableTilt = false,
  glowColor = DEFAULT_GLOW_COLOR,
  clickEffect = true,
  enableMagnetism = true
}) => {
  const isMobile = useMediaQuery(`(max-width: ${MOBILE_BREAKPOINT}px)`);
  const reducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)');
  const enabled = !disableAnimations && !isMobile && !reducedMotion;

  const value = useMemo(
    () => ({
      enabled,
      enableStars,
      enableBorderGlow,
      enableTilt,
      enableMagnetism,
      clickEffect,
      particleCount,
      glowColor
    }),
    [enabled, enableStars, enableBorderGlow, enableTilt, enableMagnetism, clickEffect, particleCount, glowColor]
  );

  return (
    <MagicBentoContext.Provider value={value}>
      {enabled && enableSpotlight && <GlobalSpotlight spotlightRadius={spotlightRadius} glowColor={glowColor} />}
      {children}
    </MagicBentoContext.Provider>
  );
};

export default MagicBento;
