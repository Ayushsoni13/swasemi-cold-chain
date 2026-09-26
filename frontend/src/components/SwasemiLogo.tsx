import React from 'react';

interface SwasemiLogoProps {
  height?: number;
  className?: string;
  showTagline?: boolean;
}

export const SwasemiLogo: React.FC<SwasemiLogoProps> = ({
  height = 36,
  className = '',
  showTagline = false,
}) => {
  return (
    <div className={`swasemi-logo-container ${className}`} style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'flex-start', userSelect: 'none' }}>
      <div style={{ display: 'inline-flex', alignItems: 'baseline', fontFamily: 'Inter, system-ui, -apple-system, sans-serif', fontWeight: 900, lineHeight: 1 }}>
        <span style={{ color: '#0284c7', fontSize: `${height}px`, letterSpacing: '-0.02em', textShadow: '0 2px 8px rgba(2, 132, 199, 0.3)' }}>
          SWA
        </span>
        <span style={{ color: '#f97316', fontSize: `${height}px`, letterSpacing: '-0.02em', textShadow: '0 2px 8px rgba(249, 115, 22, 0.3)' }}>
          SEMi
        </span>
        <span style={{ color: '#f97316', fontSize: `${Math.max(10, Math.round(height * 0.35))}px`, verticalAlign: 'super', marginLeft: '2px', fontWeight: 700 }}>
          ®
        </span>
      </div>
      {showTagline && (
        <span style={{ fontSize: `${Math.max(10, Math.round(height * 0.28))}px`, color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', marginTop: '2px' }}>
          Cold-Chain Monitoring Platform
        </span>
      )}
    </div>
  );
};

export default SwasemiLogo;
