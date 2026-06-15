'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowRight, ShieldAlert, CheckCircle, Clock, Archive, FileText, Database } from 'lucide-react';

interface Metrics {
  total_processed: number;
  cease_count: number;
  archive_count: number;
  deferred_count: number;
  pending_reviews: number;
}

interface HistoryLog {
  id: number;
  entry_id: string;
  document_id: string;
  filename: string;
  timestamp: string;
  stage: string;
  classification: string;
  confidence: number;
  routing_destination: string;
}

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [history, setHistory] = useState<HistoryLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const [metricsRes, historyRes] = await Promise.all([
          fetch('/api/metrics'),
          fetch('/api/history')
        ]);
        if (metricsRes.ok) {
          const metricsData = await metricsRes.json();
          setMetrics(metricsData);
        }
        if (historyRes.ok) {
          const historyData = await historyRes.json();
          setHistory(historyData.slice(0, 5)); // Top 5 recent entries
        }
      } catch (err) {
        // Silent catch for startup
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <div style={{ marginBottom: '40px' }}>
        <p className="mono" style={{ color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '8px' }}>
          Overview & System Status
        </p>
        <h1>C&D Intelligence Center</h1>
        <p style={{ color: 'var(--muted)', fontSize: '16px', maxWidth: '600px' }}>
          Real-time ingestion pipeline, risk classification, and audit validation for incoming legal communications.
        </p>
      </div>

      {/* Metric Cards Grid */}
      <div className="metric-grid">
        <div className="metric-card" style={{ borderLeft: '4px solid var(--accent)' }}>
          <div className="metric-label">Total Ingested</div>
          <div className="metric-val">{loading ? '...' : metrics?.total_processed ?? 0}</div>
          <span style={{ fontSize: '11px', color: 'var(--muted)' }}>Cumulative throughput</span>
        </div>

        <div className="metric-card" style={{ borderLeft: '4px solid var(--danger)' }}>
          <div className="metric-label">Cease & Desist</div>
          <div className="metric-val">{loading ? '...' : metrics?.cease_count ?? 0}</div>
          <span style={{ fontSize: '11px', color: 'var(--muted)' }}>Identified risk letters</span>
        </div>

        <div className="metric-card" style={{ borderLeft: '4px solid var(--success)' }}>
          <div className="metric-label">Archived</div>
          <div className="metric-val">{loading ? '...' : metrics?.archive_count ?? 0}</div>
          <span style={{ fontSize: '11px', color: 'var(--muted)' }}>Irrelevant communications</span>
        </div>

        <div className="metric-card" style={{ borderLeft: '4px solid var(--warning)' }}>
          <div className="metric-label">Escalated</div>
          <div className="metric-val">{loading ? '...' : metrics?.pending_reviews ?? 0}</div>
          <span style={{ fontSize: '11px', color: 'var(--muted)' }}>Awaiting manual review</span>
        </div>
      </div>

      {/* Main Grid Layout Band (Swiss Grid) */}
      <div className="band">
        {/* Left Side: Recent Activity - Spans 8 Columns */}
        <div className="panel" style={{ gridColumn: 'span 8', minHeight: '360px' }}>
          <h3 className="panel-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Database size={18} style={{ color: 'var(--accent)' }} />
            Recent Pipeline Activity
          </h3>
          <p style={{ color: 'var(--muted)', fontSize: '13px', marginBottom: '24px' }}>
            Real-time feed of the latest classified documents flowing through the system.
          </p>

          {loading ? (
            <div style={{ padding: '40px 0', textAlign: 'center', color: 'var(--muted)', fontFamily: 'Geist Mono, monospace' }}>
              LOADING ACTIVITY STREAM...
            </div>
          ) : history.length === 0 ? (
            <div style={{ padding: '40px 0', textAlign: 'center', color: 'var(--muted)', border: '1px dashed var(--border)', borderRadius: '8px' }}>
              No documents processed yet. Go to the <Link href="/ingest" style={{ textDecoration: 'underline' }}>Ingest Console</Link> to upload.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {history.map((log) => (
                <div 
                  key={log.entry_id} 
                  style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'space-between',
                    padding: '12px 16px', 
                    borderRadius: '8px', 
                    backgroundColor: 'var(--panel-strong)',
                    border: '1px solid var(--border)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <div style={{
                      width: '32px',
                      height: '32px',
                      borderRadius: '6px',
                      backgroundColor: log.classification === 'CEASE' ? 'var(--danger-bg)' : log.classification === 'IRRELEVANT' ? 'var(--success-bg)' : 'var(--warning-bg)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}>
                      {log.classification === 'CEASE' ? (
                        <ShieldAlert size={16} style={{ color: 'var(--danger)' }} />
                      ) : log.classification === 'IRRELEVANT' ? (
                        <CheckCircle size={16} style={{ color: 'var(--success)' }} />
                      ) : (
                        <Clock size={16} style={{ color: 'var(--warning)' }} />
                      )}
                    </div>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '13px', color: 'var(--text)' }}>
                        {log.filename}
                      </div>
                      <div className="mono" style={{ fontSize: '10px', color: 'var(--muted)' }}>
                        ID: {log.document_id.slice(0, 8)}... | {new Date(log.timestamp).toLocaleTimeString()}
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span className={`pill ${
                      log.classification === 'CEASE' ? 'pill-cease' : log.classification === 'IRRELEVANT' ? 'pill-irrelevant' : 'pill-uncertain'
                    }`}>
                      {log.classification}
                    </span>
                    <span className="mono" style={{ fontSize: '11px', color: 'var(--muted)' }}>
                      {(log.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Side: Quick Action Links - Spans 4 Columns */}
        <div className="panel" style={{ gridColumn: 'span 4' }}>
          <h3 className="panel-title">System Actions</h3>
          <p style={{ color: 'var(--muted)', fontSize: '13px', marginBottom: '24px' }}>
            Direct access to operator workspace control panels.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <Link 
              href="/ingest" 
              className="btn btn-outline" 
              style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', textAlign: 'left', width: '100%' }}
            >
              <span style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <FileText size={18} />
                <span>Upload New PDF</span>
              </span>
              <ArrowRight size={16} />
            </Link>

            <Link 
              href="/review" 
              className="btn btn-outline" 
              style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center', 
                textAlign: 'left', 
                width: '100%',
                borderColor: (metrics?.pending_reviews ?? 0) > 0 ? 'var(--warning)' : 'var(--border)',
                backgroundColor: (metrics?.pending_reviews ?? 0) > 0 ? 'var(--warning-bg)' : 'transparent',
              }}
            >
              <span style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <ShieldAlert size={18} style={{ color: (metrics?.pending_reviews ?? 0) > 0 ? 'var(--warning)' : 'inherit' }} />
                <span>Review Workstation</span>
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {(metrics?.pending_reviews ?? 0) > 0 && (
                  <span className="nav-badge" style={{ position: 'static', margin: 0 }}>
                    {metrics?.pending_reviews} PENDING
                  </span>
                )}
                <ArrowRight size={16} />
              </span>
            </Link>

            <Link 
              href="/history" 
              className="btn btn-outline" 
              style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', textAlign: 'left', width: '100%' }}
            >
              <span style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <Archive size={18} />
                <span>History & Audit Trail</span>
              </span>
              <ArrowRight size={16} />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
