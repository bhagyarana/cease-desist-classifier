'use client';

import { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';

export default function GridHelper() {
  const [gridOn, setGridOn] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    // Keydown listener for 'g'
    const handleKeyDown = (e: KeyboardEvent) => {
      if (
        e.key.toLowerCase() === 'g' && 
        !(e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement)
      ) {
        setGridOn((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  useEffect(() => {
    if (gridOn) {
      document.body.classList.add('grid-on');
    } else {
      document.body.classList.remove('grid-on');
    }
  }, [gridOn]);

  useEffect(() => {
    // Optical ink alignment for headings
    const alignHeadings = () => {
      const headings = document.querySelectorAll('h1, h2, h3');
      headings.forEach((el) => {
        const text = el.textContent?.trim() || '';
        if (!text) return;
        const firstChar = text[0];
        const htmlEl = el as HTMLElement;

        // Apply optical adjustments based on the starting character
        if (['“', '\"', '‘', '\''].includes(firstChar)) {
          htmlEl.style.textIndent = '-0.45em';
        } else if (['T', 'V', 'W', 'Y'].includes(firstChar)) {
          htmlEl.style.textIndent = '-0.07em';
        } else if (firstChar === 'A') {
          htmlEl.style.textIndent = '-0.05em';
        } else if (['O', 'C', 'G', 'Q'].includes(firstChar)) {
          htmlEl.style.textIndent = '-0.03em';
        } else {
          htmlEl.style.textIndent = '0';
        }
      });
    };

    alignHeadings();
    const timer = setTimeout(alignHeadings, 150);
    return () => clearTimeout(timer);
  }, [pathname]);

  return (
    <>
      <button 
        className="grid-toggle-btn" 
        onClick={() => setGridOn(!gridOn)}
        title="Toggle Swiss Modular Grid Overlay (Press 'G')"
      >
        <span style={{ 
          display: 'inline-block', 
          width: '8px', 
          height: '8px', 
          borderRadius: '50%', 
          backgroundColor: gridOn ? '#10b981' : '#ef4444',
          transition: 'background-color 0.2s ease'
        }} />
        GRID: {gridOn ? 'ON' : 'OFF'} [G]
      </button>

      <div className="guides">
        <div className="guides-cols">
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="guides-col" />
          ))}
        </div>
      </div>
    </>
  );
}
