'use client';

import { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { UploadCloud, ShieldAlert, CheckCircle, Clock, AlertTriangle, RefreshCw } from 'lucide-react';

interface IngestStep {
  id: string;
  label: string;
  status: 'idle' | 'running' | 'done' | 'failed';
}

export default function IngestPage() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [steps, setSteps] = useState<IngestStep[]>([
    { id: '1', label: 'Extracting PDF layout and textual content', status: 'idle' },
    { id: '2', label: 'Analyzing document language and syntax patterns', status: 'idle' },
    { id: '3', label: 'Running Gemini classification & structured output extraction', status: 'idle' },
    { id: '4', label: 'Performing Cosine similarity vector search & RAG audit', status: 'idle' },
    { id: '5', label: 'Determining optimal routing (Archive / Datastore / Escalation)', status: 'idle' },
  ]);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.type === 'application/pdf') {
        setFile(droppedFile);
        setError(null);
      } else {
        setError('Please drop a valid PDF file.');
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const startPipeline = async () => {
    if (!file) return;

    setUploading(true);
    setResult(null);
    setError(null);
    
    setSteps([
      { id: '1', label: 'Extracting PDF layout and textual content', status: 'running' },
      { id: '2', label: 'Analyzing document language and syntax patterns', status: 'idle' },
      { id: '3', label: 'Running Gemini classification & structured output extraction', status: 'idle' },
      { id: '4', label: 'Performing Cosine similarity vector search & RAG audit', status: 'idle' },
      { id: '5', label: 'Determining optimal routing (Archive / Datastore / Escalation)', status: 'idle' },
    ]);

    const formData = new FormData();
    formData.append('file', file);

    const apiPromise = fetch('/api/ingest', {
      method: 'POST',
      body: formData,
    });

    const updateStep = (id: string, newStatus: 'running' | 'done' | 'failed') => {
      setSteps((prev) =>
        prev.map((step) => (step.id === id ? { ...step, status: newStatus } : step))
      );
    };

    try {
      // Step 1: Ingesting text
      await new Promise((r) => setTimeout(r, 600));
      updateStep('1', 'done');
      updateStep('2', 'running');

      // Step 2: Language analysis
      await new Promise((r) => setTimeout(r, 500));
      updateStep('2', 'done');
      updateStep('3', 'running');

      // Step 3: Classifier execution
      await new Promise((r) => setTimeout(r, 900));
      updateStep('3', 'done');
      updateStep('4', 'running');

      // Step 4: RAG search
      await new Promise((r) => setTimeout(r, 600));
      updateStep('4', 'done');
      updateStep('5', 'running');

      const response = await apiPromise;
      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Internal server error');
      }
      const data = await response.json();
      
      updateStep('5', 'done');
      await new Promise((r) => setTimeout(r, 300));
      setResult(data);
    } catch (err: any) {
      setSteps((prev) =>
        prev.map((step) => (step.status === 'running' ? { ...step, status: 'failed' } : step))
      );
      setError(err.message || 'Failed to ingest document.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      <div style={{ marginBottom: '40px' }}>
        <p className="mono" style={{ color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '8px' }}>
          Document Ingestion Portal
        </p>
        <h1>Ingest legal correspondence</h1>
        <p style={{ color: 'var(--muted)', fontSize: '16px', maxWidth: '600px' }}>
          Upload C&D letters to pass them through CeaseGuard's classification and routing agent swarm.
        </p>
      </div>

      <div className="band">
        {/* Left Side: Upload Zone / Processing status - Spans 7 Columns */}
        <div className="panel" style={{ gridColumn: 'span 7', minHeight: '400px' }}>
          {!uploading && !result && (
            <div>
              <div 
                className="dropzone"
                onDragOver={handleDragOver}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                style={{ padding: '60px 20px', marginBottom: '24px' }}
              >
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  onChange={handleFileChange} 
                  accept="application/pdf" 
                  style={{ display: 'none' }} 
                />
                <UploadCloud size={48} style={{ color: 'var(--muted)', marginBottom: '16px' }} />
                <h3 style={{ marginBottom: '8px' }}>Drag & Drop PDF or Click to browse</h3>
                <p style={{ color: 'var(--muted)', fontSize: '12px' }}>Only .pdf formats are supported (Max 10MB)</p>
              </div>

              {file && (
                <div style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'space-between',
                  padding: '16px', 
                  backgroundColor: 'rgba(15, 118, 110, 0.04)', 
                  border: '1px solid var(--accent)', 
                  borderRadius: '8px',
                  marginBottom: '24px'
                }}>
                  <div>
                    <span style={{ fontWeight: 600 }}>Selected: </span>
                    <span className="mono" style={{ fontSize: '13px' }}>{file.name}</span>
                    <span style={{ fontSize: '12px', color: 'var(--muted)', marginLeft: '8px' }}>
                      ({(file.size / 1024 / 1024).toFixed(2)} MB)
                    </span>
                  </div>
                  <button className="btn btn-primary" onClick={startPipeline}>
                    Process Document
                  </button>
                </div>
              )}
              
              {error && (
                <div style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: '12px',
                  padding: '16px', 
                  backgroundColor: 'var(--danger-bg)', 
                  border: '1px solid var(--danger)', 
                  color: 'var(--danger)',
                  borderRadius: '8px'
                }}>
                  <AlertTriangle size={18} />
                  <span>{error}</span>
                </div>
              )}
            </div>
          )}

          {uploading && (
            <div>
              <h3 style={{ marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '12px' }}>
                <RefreshCw className="spin" size={20} style={{ color: 'var(--accent)' }} />
                Analyzing Document Pipeline...
              </h3>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {steps.map((step) => (
                  <div 
                    key={step.id} 
                    className={`checklist-item ${
                      step.status === 'running' ? 'active' : step.status === 'done' ? 'done' : ''
                    }`}
                    style={{ 
                      opacity: step.status === 'idle' ? 0.5 : 1,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '12px',
                      padding: '12px 0',
                      borderBottom: '1px solid var(--border)'
                    }}
                  >
                    <div className="checklist-circle">
                      {step.status === 'done' && (
                        <span style={{ color: '#10b981', fontSize: '12px', fontWeight: 'bold' }}>✓</span>
                      )}
                      {step.status === 'failed' && (
                        <span style={{ color: '#ef4444', fontSize: '12px', fontWeight: 'bold' }}>✗</span>
                      )}
                    </div>
                    <span style={{ 
                      fontSize: '13px', 
                      fontWeight: step.status === 'running' ? 600 : 400,
                      color: step.status === 'failed' ? 'var(--danger)' : 'var(--text)'
                    }}>
                      {step.label}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {result && (
            <div>
              <div style={{ textAlign: 'center', marginBottom: '32px' }}>
                <div style={{
                  width: '64px',
                  height: '64px',
                  borderRadius: '50%',
                  backgroundColor: result.status === 'needs_review' ? 'var(--warning-bg)' : 'var(--success-bg)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: '16px'
                }}>
                  {result.status === 'needs_review' ? (
                    <Clock size={32} style={{ color: 'var(--warning)' }} />
                  ) : (
                    <CheckCircle size={32} style={{ color: 'var(--success)' }} />
                  )}
                </div>
                <h2>
                  {result.status === 'needs_review' 
                    ? 'Escalated to Operator Review' 
                    : 'Ingested & Classified Successfully'}
                </h2>
                <p className="mono" style={{ color: 'var(--muted)', fontSize: '12px' }}>
                  ID: {result.document_id}
                </p>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '32px' }}>
                <div style={{ padding: '16px', backgroundColor: 'var(--panel-strong)', borderRadius: '8px', border: '1px solid var(--border)' }}>
                  <div style={{ fontSize: '11px', textTransform: 'uppercase', fontFamily: 'Geist Mono, monospace', color: 'var(--muted)', marginBottom: '4px' }}>
                    Agent Verdict
                  </div>
                  <span className={`pill ${
                    result.classification.label === 'CEASE' ? 'pill-cease' : result.classification.label === 'IRRELEVANT' ? 'pill-irrelevant' : 'pill-uncertain'
                  }`}>
                    {result.classification.label}
                  </span>
                </div>

                <div style={{ padding: '16px', backgroundColor: 'var(--panel-strong)', borderRadius: '8px', border: '1px solid var(--border)' }}>
                  <div style={{ fontSize: '11px', textTransform: 'uppercase', fontFamily: 'Geist Mono, monospace', color: 'var(--muted)', marginBottom: '4px' }}>
                    Confidence Score
                  </div>
                  <span className="mono" style={{ fontSize: '18px', fontWeight: 700 }}>
                    {(result.classification.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              </div>

              {result.classification.citation && (
                <div className="panel" style={{ padding: '16px', backgroundColor: 'var(--panel-strong)', marginBottom: '24px' }}>
                  <div style={{ fontSize: '11px', textTransform: 'uppercase', fontFamily: 'Geist Mono, monospace', color: 'var(--muted)', marginBottom: '8px' }}>
                    Extracted Legal Citation
                  </div>
                  <p style={{ fontStyle: 'italic', margin: 0, fontSize: '13px' }}>
                    "{result.classification.citation}"
                  </p>
                </div>
              )}

              <div style={{ display: 'flex', gap: '16px', justifyContent: 'flex-end' }}>
                <button className="btn btn-outline" onClick={() => { setResult(null); setFile(null); }}>
                  Upload Another Document
                </button>
                {result.status === 'needs_review' ? (
                  <button className="btn btn-warning" onClick={() => router.push('/review')}>
                    Go to Review workstation
                  </button>
                ) : (
                  <button className="btn btn-primary" onClick={() => router.push('/')}>
                    Return to Dashboard
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Right Side: Educational panel - Spans 5 Columns */}
        <div className="panel" style={{ gridColumn: 'span 5' }}>
          <h3 style={{ marginBottom: '16px' }}>The CeaseGuard Pipeline</h3>
          <p style={{ color: 'var(--muted)', fontSize: '13px', marginBottom: '24px' }}>
            CeaseGuard implements a stateful agentic workflow to ensure high-accuracy classification.
          </p>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{ display: 'flex', gap: '12px' }}>
              <span className="mono" style={{ color: 'var(--accent)', fontWeight: 'bold' }}>01</span>
              <div>
                <h4 style={{ fontSize: '14px', marginBottom: '4px' }}>Extract & Verify</h4>
                <p style={{ fontSize: '12px', color: 'var(--muted)', margin: 0 }}>
                  Extracts raw text, flags unreadable documents, and translates content back to English using Google Gemini model functions.
                </p>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '12px' }}>
              <span className="mono" style={{ color: 'var(--accent)', fontWeight: 'bold' }}>02</span>
              <div>
                <h4 style={{ fontSize: '14px', marginBottom: '4px' }}>Swarm Classification</h4>
                <p style={{ fontSize: '12px', color: 'var(--muted)', margin: 0 }}>
                  Gemini API categorizes the document under 12-column grid-aligned compliance schemas with detailed reasoning citations.
                </p>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '12px' }}>
              <span className="mono" style={{ color: 'var(--accent)', fontWeight: 'bold' }}>03</span>
              <div>
                <h4 style={{ fontSize: '14px', marginBottom: '4px' }}>Judge Verification</h4>
                <p style={{ fontSize: '12px', color: 'var(--muted)', margin: 0 }}>
                  An independent LLM Judge reviews high-risk classifications and sample records to audit accuracy before final write.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
