'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import { LayoutDashboard, UploadCloud, ShieldAlert, History } from 'lucide-react';

export default function Sidebar() {
  const pathname = usePathname();
  const [pendingCount, setPendingCount] = useState<number>(0);

  useEffect(() => {
    const fetchPending = async () => {
      try {
        const res = await fetch('/api/metrics');
        if (res.ok) {
          const data = await res.json();
          setPendingCount(data.pending_reviews || 0);
        }
      } catch (err) {
        // Fallback silently if api is starting up
      }
    };
    fetchPending();
    const interval = setInterval(fetchPending, 10000);
    return () => clearInterval(interval);
  }, []);

  const navItems = [
    { href: '/', label: 'Dashboard', icon: LayoutDashboard },
    { href: '/ingest', label: 'Ingest Console', icon: UploadCloud },
    { 
      href: '/review', 
      label: 'Review Workspace', 
      icon: ShieldAlert,
      badge: pendingCount > 0 ? pendingCount : undefined
    },
    { href: '/history', label: 'History & Logs', icon: History },
  ];

  return (
    <aside className="sidebar">
      <div className="logo-section">
        <div className="logo-icon" />
        <span className="logo-text">CeaseGuard</span>
      </div>

      <nav style={{ flex: 1 }}>
        <ul className="nav-links">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <li key={item.href} className={`nav-item ${isActive ? 'active' : ''}`}>
                <Link href={item.href}>
                  <Icon size={18} />
                  <span>{item.label}</span>
                  {item.badge !== undefined && (
                    <span className="nav-badge">{item.badge}</span>
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <div style={{ 
        fontSize: '11px', 
        fontFamily: 'Space Mono, monospace', 
        color: 'var(--muted)',
        borderTop: '1px solid var(--border)',
        paddingTop: '16px'
      }}>
        <div>STATUS: ACTIVE</div>
        <div>V: 2.1.0-GEMINI</div>
      </div>
    </aside>
  );
}
