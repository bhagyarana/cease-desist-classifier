'use client';

import { useEffect, useState } from 'react';
import { Search, AlertTriangle, RefreshCw } from 'lucide-react';

interface HistoryLog {
  id: number;
  entry_id: string;
  document_id: string;
  filename: string;
  timestamp: string;
  stage: string;
  classification: string;
  confidence: number;
  routing_destination: string | null;
  error: string | null;
  processing_time_ms: number;
}

export default function HistoryPage() {
  const [logs, setLogs] = useState<HistoryLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterClass, setFilterClass] = useState('ALL');

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/history');
      if (res.ok) {
        const data = await res.json();
        setLogs(data);
      }
    } catch (err) {
      // Catch silently
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const filteredLogs = logs.filter((log) => {
    const matchesSearch = 
      log.filename.toLowerCase().includes(search.toLowerCase()) ||
      log.document_id.toLowerCase().includes(search.toLowerCase()) ||
      (log.error && log.error.toLowerCase().includes(search.toLowerCase()));

    const matchesClass = 
      filterClass === 'ALL' || 
      log.classification === filterClass;

    return matchesSearch && matchesClass;
  });

  return (
    <div>
      <div style={{ marginBottom: '40px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <p className="mono" style={{ color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '8px' }}>
            System Audit Trail
          </p>
          <h1>Pipeline History Logs</h1>
          <p style={{ color: 'var(--muted)', fontSize: '15px' }}>
            Immutable logs of every transaction and routing decision executed by the agent swarm.
          </p>
        </div>
        
        <button className="btn btn-outline" onClick={fetchHistory} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <RefreshCw size={14} className={loading ? 'spin' : ''} />
          Refresh Log Feed
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="panel" style={{ padding: '16px', display: 'flex', gap: '16px', alignItems: 'center', flexWrap: 'wrap', marginBottom: '24px' }}>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', backgroundColor: 'var(--panel-strong)', border: '1px solid var(--border)', borderRadius: '8px', padding: '8px 16px', flex: 1, minWidth: '240px' }}>
          <Search size={16} style={{ color: 'var(--muted)' }} />
          <input
            type="text"
            placeholder="Search by filename, document ID, errors..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ border: 'none', outline: 'none', background: 'transparent', width: '100%', fontSize: '14px', color: 'var(--text)' }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span className="mono" style={{ fontSize: '11px', color: 'var(--muted)' }}>Filter Verdict:</span>
          <select
            value={filterClass}
            onChange={(e) => setFilterClass(e.target.value)}
            style={{ 
              padding: '10px 16px', 
              borderRadius: '8px', 
              border: '1px solid var(--border)', 
              backgroundColor: 'var(--panel-strong)', 
              color: 'var(--text)', 
              fontSize: '14px', 
              fontWeight: 500,
              outline: 'none',
              cursor: 'pointer'
            }}
          >
            <option value="ALL">All classifications</option>
            <option value="CEASE">CEASE & DESIST</option>
            <option value="IRRELEVANT">IRRELEVANT</option>
            <option value="UNCERTAIN">UNCERTAIN</option>
          </select>
        </div>

      </div>

      {/* Logs Table */}
      <div className="panel" style={{ padding: 0 }}>
        {loading ? (
          <div style={{ padding: '80px 0', textAlign: 'center', color: 'var(--muted)', fontFamily: 'Space Mono, monospace' }}>
            FETCHING SYSTEM TRANSACTION HISTORY...
          </div>
        ) : filteredLogs.length === 0 ? (
          <div style={{ padding: '60px 0', textAlign: 'center', color: 'var(--muted)', fontStyle: 'italic' }}>
            No transaction records found matching active criteria.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
              <thead>
                <tr style={{ backgroundColor: 'rgba(15, 118, 110, 0.03)', borderBottom: '1px solid var(--border)', fontFamily: 'Space Mono, monospace', fontSize: '11px', color: 'var(--muted)' }}>
                  <th style={{ padding: '16px 20px' }}>TIMESTAMP</th>
                  <th style={{ padding: '16px 20px' }}>DOCUMENT ID</th>
                  <th style={{ padding: '16px 20px' }}>FILENAME</th>
                  <th style={{ padding: '16px 20px' }}>PIPELINE STAGE</th>
                  <th style={{ padding: '16px 20px' }}>VERDICT</th>
                  <th style={{ padding: '16px 20px' }}>CONFIDENCE</th>
                  <th style={{ padding: '16px 20px' }}>LATENCY</th>
                  <th style={{ padding: '16px 20px' }}>ROUTING OUTCOME</th>
                </tr>
              </thead>
              <tbody>
                {filteredLogs.map((log, idx) => (
                  <tr 
                    key={log.entry_id + idx} 
                    style={{ 
                      borderBottom: idx < filteredLogs.length - 1 ? '1px solid var(--border)' : 'none',
                      backgroundColor: log.error ? 'var(--danger-bg)' : 'transparent',
                      transition: 'background-color 0.2s ease'
                    }}
                  >
                    <td className="mono" style={{ padding: '16px 20px', whiteSpace: 'nowrap', fontSize: '11px', color: 'var(--muted)' }}>
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td className="mono" style={{ padding: '16px 20px', whiteSpace: 'nowrap', fontSize: '11px' }}>
                      {log.document_id.slice(0, 12)}...
                    </td>
                    <td style={{ padding: '16px 20px', fontWeight: 600, maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {log.filename}
                    </td>
                    <td style={{ padding: '16px 20px' }}>
                      <span className="mono" style={{ fontSize: '11px', backgroundColor: 'rgba(0,0,0,0.05)', padding: '2px 6px', borderRadius: '4px' }}>
                        {log.stage}
                      </span>
                    </td>
                    <td style={{ padding: '16px 20px' }}>
                      {log.classification && (
                        <span className={`pill ${
                          log.classification === 'CEASE' ? 'pill-cease' : log.classification === 'IRRELEVANT' ? 'pill-irrelevant' : 'pill-uncertain'
                        }`}>
                          {log.classification}
                        </span>
                      )}
                    </td>
                    <td className="mono" style={{ padding: '16px 20px', color: 'var(--muted)' }}>
                      {log.confidence !== null ? `${(log.confidence * 100).toFixed(0)}%` : '-'}
                    </td>
                    <td className="mono" style={{ padding: '16px 20px', fontSize: '11px', color: 'var(--muted)' }}>
                      {log.processing_time_ms}ms
                    </td>
                    <td style={{ padding: '16px 20px' }}>
                      {log.error ? (
                        <span style={{ color: 'var(--danger)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <AlertTriangle size={14} />
                          Error: {log.error.slice(0, 30)}...
                        </span>
                      ) : (
                        <span className="mono" style={{ fontSize: '11px', color: 'var(--muted)' }}>
                          {log.routing_destination || 'None'}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
