'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import { 
  LayoutDashboard, 
  UploadCloud, 
  ShieldAlert, 
  History, 
  Sun, 
  Moon, 
  ChevronLeft, 
  ChevronRight 
} from 'lucide-react';

export default function Sidebar() {
  const pathname = usePathname();
  const [pendingCount, setPendingCount] = useState<number>(0);
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [isCollapsed, setIsCollapsed] = useState<boolean>(false);

  // Load theme & collapse status from localStorage on mount
  useEffect(() => {
    const savedTheme = localStorage.getItem('theme') as 'light' | 'dark' | null;
    if (savedTheme) {
      setTheme(savedTheme);
      if (savedTheme === 'dark') {
        document.body.classList.add('dark');
      } else {
        document.body.classList.remove('dark');
      }
    } else {
      document.body.classList.remove('dark');
    }

    const savedCollapse = localStorage.getItem('sidebar-collapsed') === 'true';
    setIsCollapsed(savedCollapse);
    document.documentElement.style.setProperty('--sidebar-w', savedCollapse ? '80px' : '260px');
  }, []);

  // Fetch pending review counts
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

  const toggleTheme = () => {
    const nextTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(nextTheme);
    localStorage.setItem('theme', nextTheme);
    if (nextTheme === 'dark') {
      document.body.classList.add('dark');
    } else {
      document.body.classList.remove('dark');
    }
  };

  const toggleCollapse = () => {
    const nextCollapsed = !isCollapsed;
    setIsCollapsed(nextCollapsed);
    localStorage.setItem('sidebar-collapsed', String(nextCollapsed));
    document.documentElement.style.setProperty('--sidebar-w', nextCollapsed ? '80px' : '260px');
  };

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
    <aside className={`sidebar ${isCollapsed ? 'collapsed' : ''}`}>
      {/* Clickable Logo Section Navigating to Dashboard */}
      <Link href="/" className="logo-section" style={{ textDecoration: 'none' }}>
        <svg 
          viewBox="0 0 24 24" 
          width="24" 
          height="24" 
          stroke="currentColor" 
          strokeWidth="2.5" 
          fill="none" 
          strokeLinecap="round" 
          strokeLinejoin="round" 
          style={{ 
            color: 'var(--accent)', 
            filter: 'drop-shadow(0 0 8px var(--accent-glow))',
            transition: 'transform 0.2s ease'
          }}
          className="logo-svg"
        >
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          <path d="M12 8v4" />
          <circle cx="12" cy="16" r="0.5" fill="currentColor" />
        </svg>
        {!isCollapsed && <span className="logo-text">CeaseGuard</span>}
      </Link>

      <nav style={{ flex: 1 }}>
        <ul className="nav-links">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <li key={item.href} className={`nav-item ${isActive ? 'active' : ''}`}>
                <Link href={item.href} title={isCollapsed ? item.label : undefined}>
                  <Icon size={18} />
                  {!isCollapsed && <span>{item.label}</span>}
                  {item.badge !== undefined && (
                    <span className="nav-badge">{item.badge}</span>
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Theme Toggler */}
      <div 
        className="theme-toggle-container"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: isCollapsed ? 'center' : 'space-between',
          padding: '8px 12px',
          borderRadius: '8px',
          backgroundColor: 'var(--panel-strong)',
          border: '1px solid var(--border)',
          marginBottom: '16px',
          cursor: 'pointer',
          transition: 'all 0.2s ease',
        }} 
        onClick={toggleTheme}
        title="Toggle color theme"
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {theme === 'light' ? (
            <Sun size={14} style={{ color: 'var(--accent)' }} />
          ) : (
            <Moon size={14} style={{ color: 'var(--accent)' }} />
          )}
          <span className="theme-toggle-text" style={{ fontSize: '10px', fontWeight: 700, fontFamily: 'Geist Mono, monospace', color: 'var(--text)' }}>
            {theme === 'light' ? 'LIGHT MODE' : 'DARK MODE'}
          </span>
        </div>
        <div className="theme-toggle-switch" style={{
          width: '24px',
          height: '14px',
          borderRadius: '99px',
          backgroundColor: theme === 'light' ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.15)',
          position: 'relative',
          transition: 'all 0.2s ease',
        }}>
          <div style={{
            width: '10px',
            height: '10px',
            borderRadius: '50%',
            backgroundColor: theme === 'light' ? 'var(--accent)' : '#ffffff',
            position: 'absolute',
            top: '2px',
            left: theme === 'light' ? '2px' : '12px',
            transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
          }} />
        </div>
      </div>

      {/* Combined Status and Collapse section */}
      {isCollapsed ? (
        <button
          onClick={toggleCollapse}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '28px',
            height: '28px',
            borderRadius: '6px',
            color: 'var(--muted)',
            backgroundColor: 'var(--panel-strong)',
            border: '1px solid var(--border)',
            cursor: 'pointer',
            alignSelf: 'center',
            marginBottom: '16px',
            transition: 'all 0.2s ease',
          }}
          className="nav-item-collapse-btn"
          title="Expand Sidebar"
        >
          <ChevronRight size={14} />
        </button>
      ) : (
        <div className="status-section" style={{ 
          fontSize: '11px', 
          fontFamily: 'Geist Mono, monospace', 
          color: 'var(--muted)',
          borderTop: '1px solid var(--border)',
          paddingTop: '16px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <div>
            <div>STATUS: ACTIVE</div>
            <div>V: 2.1.0-GEMINI</div>
          </div>
          <button
            onClick={toggleCollapse}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '24px',
              height: '24px',
              borderRadius: '4px',
              color: 'var(--muted)',
              backgroundColor: 'var(--panel-strong)',
              border: '1px solid var(--border)',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
            className="nav-item-collapse-btn"
            title="Collapse Sidebar"
          >
            <ChevronLeft size={12} />
          </button>
        </div>
      )}
    </aside>
  );
}
