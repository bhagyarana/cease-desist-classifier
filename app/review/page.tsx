'use client';

import { useEffect, useState } from 'react';
import { 
  ShieldAlert, 
  CheckCircle, 
  Clock, 
  AlertTriangle, 
  ChevronRight, 
  FileText, 
  Send, 
  Sparkles 
} from 'lucide-react';

interface ReviewItem {
  entry_id: string;
  document_id: string;
  filename: string;
  timestamp: string;
  classification: {
    label: string;
    confidence: number;
    citation: string;
    edge_case_flag: boolean;
  };
  language: {
    language: string;
    confidence: number;
  };
  agent_trace: string[];
  text: string;
  pdf_path: string;
}

interface SimilarCase {
  document_id: string;
  summary: string;
  similarity: number;
}

export default function ReviewPage() {
  const [queue, setQueue] = useState<ReviewItem[]>([]);
  const [selectedItem, setSelectedItem] = useState<ReviewItem | null>(null);
  const [similarCases, setSimilarCases] = useState<SimilarCase[]>([]);
  const [loadingSimilar, setLoadingSimilar] = useState(false);
  const [loading, setLoading] = useState(true);
  
  const [decision, setDecision] = useState<'CEASE' | 'IRRELEVANT' | 'DEFER' | null>(null);
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const fetchQueue = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/reviews');
      if (res.ok) {
        const data = await res.json();
        setQueue(data);
        if (data.length > 0) {
          setSelectedItem(data[0]);
        } else {
          setSelectedItem(null);
        }
      }
    } catch (err) {
      // Catch silently for initial load
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, []);

  useEffect(() => {
    if (!selectedItem) {
      setSimilarCases([]);
      return;
    }
    
    const fetchSimilarity = async () => {
      setLoadingSimilar(true);
      try {
        const res = await fetch(`/api/reviews/${selectedItem.document_id}/similarity`);
        if (res.ok) {
          const data = await res.json();
          setSimilarCases(data);
        }
      } catch (err) {
        // Catch silently
      } finally {
        setLoadingSimilar(false);
      }
    };
    
    setDecision(null);
    setNotes('');
    setSuccessMsg(null);
    fetchSimilarity();
  }, [selectedItem]);

  const handleSubmitReview = async () => {
    if (!selectedItem || !decision) return;
    
    setSubmitting(true);
    try {
      const res = await fetch(`/api/reviews/${selectedItem.document_id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          decision,
          note: notes,
          operator_id: 'web-operator'
        }),
      });
      
      if (res.ok) {
        setSuccessMsg(`Document resolved as ${decision}.`);
        const remaining = queue.filter(item => item.document_id !== selectedItem.document_id);
        setQueue(remaining);
        
        setTimeout(() => {
          setSuccessMsg(null);
          if (remaining.length > 0) {
            setSelectedItem(remaining[0]);
          } else {
            setSelectedItem(null);
          }
        }, 1200);
      } else {
        alert('Failed to submit override.');
      }
    } catch (err) {
      // Catch silently
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <div style={{ marginBottom: '32px' }}>
        <p className="mono" style={{ color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '8px' }}>
          Human-in-the-Loop workstation
        </p>
        <h1>Review Workspace</h1>
        <p style={{ color: 'var(--muted)', fontSize: '15px' }}>
          {queue.length > 0 
            ? `Review workstation has ${queue.length} case(s) requiring manual intervention.` 
            : 'Zero pending documents in the queue.'}
        </p>
      </div>

      {loading ? (
        <div style={{ padding: '80px 0', textAlign: 'center', color: 'var(--muted)', fontFamily: 'Geist Mono, monospace' }}>
          INITIALIZING WORKSTATION...
        </div>
      ) : queue.length === 0 ? (
        <div className="panel" style={{ padding: '60px 40px', textAlign: 'center' }}>
          <CheckCircle size={48} style={{ color: 'var(--success)', marginBottom: '16px' }} />
          <h2>All caught up!</h2>
          <p style={{ color: 'var(--muted)', marginTop: '8px' }}>
            There are no cease-and-desist alerts pending operator review right now.
          </p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: '24px', alignItems: 'start' }}>
          
          {/* Column 1: Queue Sidebar */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div className="mono" style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--muted)', paddingLeft: '8px' }}>
              Pending Queue ({queue.length})
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '70vh', overflowY: 'auto' }}>
              {queue.map((item) => {
                const isSelected = selectedItem?.document_id === item.document_id;
                return (
                  <button
                    key={item.document_id}
                    onClick={() => setSelectedItem(item)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '12px',
                      padding: '12px 16px',
                      borderRadius: '8px',
                      border: '1px solid',
                      borderColor: isSelected ? 'var(--accent)' : 'var(--border)',
                      backgroundColor: isSelected ? 'var(--panel-strong)' : 'var(--item-inactive-bg)',
                      textAlign: 'left',
                      cursor: 'pointer',
                      width: '100%',
                      transition: 'all 0.2s ease',
                    }}
                  >
                    <div style={{
                      width: '10px',
                      height: '10px',
                      borderRadius: '50%',
                      backgroundColor: item.classification.label === 'CEASE' ? 'var(--danger)' : 'var(--warning)',
                    }} />
                    <div style={{ flex: 1, overflow: 'hidden' }}>
                      <div style={{ fontWeight: 600, fontSize: '12px', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap', color: 'var(--text)' }}>
                        {item.filename}
                      </div>
                      <div className="mono" style={{ fontSize: '9px', color: 'var(--muted)' }}>
                        {item.classification.label} ({(item.classification.confidence * 100).toFixed(0)}%)
                      </div>
                    </div>
                    <ChevronRight size={14} style={{ color: 'var(--muted)' }} />
                  </button>
                );
              })}
            </div>
          </div>

          {/* Column 2: Document Workspace Detail */}
          {selectedItem && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', flex: 1, minWidth: 0 }}>
              
              {/* Workspace Row 1: File Information Header */}
              <div className="panel" style={{ margin: 0 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                  <div style={{ overflow: 'hidden', marginRight: '16px' }}>
                    <h2 style={{ fontSize: '18px', marginBottom: '4px', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                      {selectedItem.filename}
                    </h2>
                    <div className="mono" style={{ fontSize: '11px', color: 'var(--muted)' }}>
                      DOC ID: {selectedItem.document_id}
                    </div>
                  </div>
                  <span className="pill pill-uncertain" style={{ flexShrink: 0 }}>
                    Needs Review
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', borderTop: '1px solid var(--border)', paddingTop: '16px' }}>
                  <div>
                    <div style={{ fontSize: '10px', fontFamily: 'Geist Mono, monospace', color: 'var(--muted)', marginBottom: '2px' }}>Classifier Verdict</div>
                    <span className="mono" style={{ fontWeight: 600, color: 'var(--danger)' }}>{selectedItem.classification.label}</span>
                  </div>
                  <div>
                    <div style={{ fontSize: '10px', fontFamily: 'Geist Mono, monospace', color: 'var(--muted)', marginBottom: '2px' }}>Confidence Score</div>
                    <span className="mono" style={{ fontWeight: 600 }}>{(selectedItem.classification.confidence * 100).toFixed(0)}%</span>
                  </div>
                  <div>
                    <div style={{ fontSize: '10px', fontFamily: 'Geist Mono, monospace', color: 'var(--muted)', marginBottom: '2px' }}>Language / Syntax</div>
                    <span className="mono" style={{ fontWeight: 600 }}>{selectedItem.language.language.toUpperCase()}</span>
                  </div>
                </div>
              </div>

              {/* Workspace Row 2: Text Evidence (Left) vs Decisional Override Form (Right) */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: '24px', alignItems: 'start' }}>
                
                {/* Left side: Extracted Text */}
                <div className="panel" style={{ margin: 0, display: 'flex', flexDirection: 'column', height: '420px' }}>
                  <h3 className="panel-title" style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                    <FileText size={16} />
                    Extracted Text Content
                  </h3>
                  <div style={{ 
                    flex: 1, 
                    overflowY: 'auto', 
                    padding: '14px', 
                    border: '1px solid var(--border)', 
                    borderRadius: '8px', 
                    backgroundColor: 'var(--panel-strong)',
                    fontFamily: 'Geist Mono, monospace',
                    fontSize: '11px',
                    lineHeight: '18px',
                    whiteSpace: 'pre-wrap',
                    color: 'var(--text)'
                  }}>
                    {selectedItem.text || "No text extracted."}
                  </div>
                </div>

                {/* Right side: Decisional Override Action Form */}
                <div className="panel" style={{ margin: 0, height: '420px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                  <h3 style={{ marginBottom: '12px', fontSize: '16px' }}>Decisional Override</h3>
                  
                  {successMsg ? (
                    <div style={{
                      padding: '24px 16px',
                      backgroundColor: 'var(--success-bg)',
                      border: '1px solid var(--success)',
                      color: 'var(--success)',
                      borderRadius: '8px',
                      textAlign: 'center',
                      flex: 1,
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'center',
                    }}>
                      <CheckCircle size={24} style={{ display: 'block', margin: '0 auto 8px' }} />
                      <span style={{ fontSize: '13px', fontWeight: 600 }}>{successMsg}</span>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', flex: 1, justifyContent: 'space-between' }}>
                      
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        <div style={{ fontSize: '11px', fontFamily: 'Geist Mono, monospace', color: 'var(--muted)' }}>
                          Select action
                        </div>
                        
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                          <button
                            onClick={() => setDecision('CEASE')}
                            className={`btn ${decision === 'CEASE' ? 'btn-danger' : 'btn-outline'}`}
                            style={{ width: '100%', justifyContent: 'flex-start', gap: '12px', padding: '8px 12px', fontSize: '12px' }}
                          >
                            <span style={{ 
                              width: '8px', 
                              height: '8px', 
                              borderRadius: '50%', 
                              backgroundColor: decision === 'CEASE' ? '#ffffff' : 'var(--danger)' 
                            }} />
                            Approve as CEASE & DESIST
                          </button>

                          <button
                            onClick={() => setDecision('IRRELEVANT')}
                            className={`btn ${decision === 'IRRELEVANT' ? 'btn-primary' : 'btn-outline'}`}
                            style={{ width: '100%', justifyContent: 'flex-start', gap: '12px', padding: '8px 12px', fontSize: '12px' }}
                          >
                            <span style={{ 
                              width: '8px', 
                              height: '8px', 
                              borderRadius: '50%', 
                              backgroundColor: decision === 'IRRELEVANT' ? '#ffffff' : 'var(--success)' 
                            }} />
                            Archive as IRRELEVANT
                          </button>

                          <button
                            onClick={() => setDecision('DEFER')}
                            className={`btn ${decision === 'DEFER' ? 'btn-warning' : 'btn-outline'}`}
                            style={{ width: '100%', justifyContent: 'flex-start', gap: '12px', padding: '8px 12px', fontSize: '12px' }}
                          >
                            <span style={{ 
                              width: '8px', 
                              height: '8px', 
                              borderRadius: '50%', 
                              backgroundColor: decision === 'DEFER' ? '#ffffff' : 'var(--warning)' 
                            }} />
                            Defer for Later Review
                          </button>
                        </div>
                      </div>

                      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        <label className="mono" style={{ fontSize: '11px', color: 'var(--muted)' }}>
                          Operator justification note
                        </label>
                        <textarea
                          value={notes}
                          onChange={(e) => setNotes(e.target.value)}
                          placeholder="Provide reasoning for override..."
                          className="text-input"
                          style={{ height: '75px', resize: 'none', fontSize: '12px', padding: '8px 12px' }}
                        />
                      </div>

                      <button
                        onClick={handleSubmitReview}
                        disabled={!decision || submitting}
                        className="btn btn-primary"
                        style={{ 
                          width: '100%', 
                          opacity: (!decision || submitting) ? 0.6 : 1, 
                          cursor: (!decision || submitting) ? 'not-allowed' : 'pointer',
                          gap: '8px',
                          padding: '10px'
                        }}
                      >
                        <Send size={14} />
                        <span style={{ fontSize: '13px' }}>{submitting ? 'Submitting...' : 'Submit Override'}</span>
                      </button>

                    </div>
                  )}
                </div>

              </div>

              {/* Workspace Row 3: Similar Recommendations & Inbound Context Trigger */}
              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px', alignItems: 'start' }}>
                
                {/* Left side: RAG Similarities (takes wide space) */}
                <div className="panel" style={{ margin: 0 }}>
                  <h3 className="panel-title" style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '15px', marginBottom: '8px' }}>
                    <Sparkles size={16} style={{ color: 'var(--accent)' }} />
                    RAG Vector Similarities
                  </h3>
                  <p style={{ color: 'var(--muted)', fontSize: '12px', marginBottom: '16px' }}>
                    Top similar historical cases stored in vector index database.
                  </p>

                  {loadingSimilar ? (
                    <div style={{ fontFamily: 'Geist Mono, monospace', fontSize: '11px', color: 'var(--muted)', padding: '12px 0' }}>
                      SEARCHING VECTOR ARCHIVE...
                    </div>
                  ) : similarCases.length === 0 ? (
                    <div style={{ fontSize: '12px', color: 'var(--muted)', fontStyle: 'italic', padding: '12px 0' }}>
                      No matching vector embeddings found in database.
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
                      {similarCases.map((caseItem, idx) => (
                        <div 
                          key={caseItem.document_id + idx}
                          style={{
                            padding: '12px',
                            borderRadius: '8px',
                            backgroundColor: 'var(--panel-strong)',
                            border: '1px solid var(--border)',
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                            <span className="mono" style={{ fontSize: '11px', fontWeight: 'bold' }}>
                              DOC: {caseItem.document_id.slice(0, 10)}...
                            </span>
                            <span className="mono" style={{ fontSize: '11px', color: 'var(--accent)', fontWeight: 'bold' }}>
                              Similarity: {(caseItem.similarity * 100).toFixed(0)}%
                            </span>
                          </div>
                          <p style={{ fontSize: '12px', color: 'var(--muted)', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical' }}>
                            {caseItem.summary}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Right side: Escalation Trigger Context */}
                {selectedItem.classification.citation && (
                  <div className="panel" style={{ margin: 0, minHeight: '135px' }}>
                    <div className="mono" style={{ fontSize: '10px', color: 'var(--muted)', marginBottom: '8px' }}>
                      Escalation Trigger Context
                    </div>
                    <div style={{
                      padding: '12px',
                      backgroundColor: 'var(--accent-light)',
                      borderLeft: '3px solid var(--accent)',
                      fontSize: '12px',
                      lineHeight: '18px',
                      color: 'var(--text)',
                      borderRadius: '4px',
                      fontStyle: 'italic'
                    }}>
                      "{selectedItem.classification.citation}"
                    </div>
                  </div>
                )}

              </div>

            </div>
          )}
        </div>
      )}
    </div>
  );
}
