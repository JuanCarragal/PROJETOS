import React, { useEffect, useState } from 'react';

export const ParallaxBackground: React.FC = () => {
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  useEffect(() => {
    let animationFrameId: number;

    const handleMouseMove = (e: MouseEvent) => {
      // Normalize from -1 to 1 based on viewport center
      const x = (e.clientX / window.innerWidth - 0.5) * 2;
      const y = (e.clientY / window.innerHeight - 0.5) * 2;

      cancelAnimationFrame(animationFrameId);
      animationFrameId = requestAnimationFrame(() => {
        setMousePos({ x, y });
      });
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <div className="parallax-bg-root" aria-hidden="true">
      {/* Subtle Dot Grid */}
      <div className="parallax-grid" />

      {/* Glow Orb 1 - Indigo/Purple (Top-Left) */}
      <div
        className="parallax-orb orb-indigo"
        style={{
          transform: `translate3d(${mousePos.x * 28}px, ${mousePos.y * 22}px, 0)`,
        }}
      />

      {/* Glow Orb 2 - Emerald/Teal (Bottom-Right) */}
      <div
        className="parallax-orb orb-emerald"
        style={{
          transform: `translate3d(${mousePos.x * -35}px, ${mousePos.y * -28}px, 0)`,
        }}
      />

      {/* Glow Orb 3 - Cyan/Sky (Center-Right) */}
      <div
        className="parallax-orb orb-cyan"
        style={{
          transform: `translate3d(${mousePos.x * 18}px, ${mousePos.y * -15}px, 0)`,
        }}
      />
    </div>
  );
};

export default ParallaxBackground;
