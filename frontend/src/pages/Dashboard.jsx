import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Play, Activity, CheckCircle, Database, BrainCircuit, FileSignature, Filter, Loader2, XCircle, ChevronDown, ChevronUp } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const initialPipelineState = {
  running: false,
  mode: 'idle',
  phase: 'idle',
  status_text: '',
  scan: { total_found: 0, current_platform: '', current_city: '', combos_done: 0, combos_total: 0, live_jobs: [] },
  filter: { before: 0, after: 0, dropped: {}, dropped_jobs: [] },
  score: { total: 0, scored: 0, avg_score: 0, above_threshold: 0, shortlisted: 0, live_scores: [] },
  tailor: { total: 0, completed: 0, failed: 0, current_company: '' },
  result: { resumes_generated: 0, output_dir: '' },
};

function AnimatedToggle({ active, onClick, label }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer' }} onClick={onClick}>
      <div className={`toggle-switch ${active ? 'active' : ''}`}>
        <div className="toggle-knob" />
      </div>
      <span style={{ color: active ? 'var(--text-main)' : 'var(--text-muted)', fontWeight: 500, transition: 'color 0.2s' }}>
        {label}
      </span>
    </div>
  );
}

function IdleView({ onStart }) {
  const [platforms, setPlatforms] = useState(['linkedin', 'indeed']);
  const [testMode, setTestMode] = useState(false);

  const togglePlatform = (p) => {
    setPlatforms(prev => prev.includes(p) ? prev.filter(x => x !== p) : [...prev, p]);
  };

  return (
    <div className="glass-panel" style={{ padding: '48px', maxWidth: '600px', margin: '40px auto', textAlign: 'center' }}>
      <motion.div initial={{ y: -10, opacity: 0 }} animate={{ y: 0, opacity: 1 }} style={{ marginBottom: '40px' }}>
        <h1 style={{ fontSize: '32px', margin: '0 0 8px', color: 'var(--text-main)', fontWeight: 700 }}>AutoApply Pipeline</h1>
        <p style={{ color: 'var(--text-muted)' }}>Configure your run parameters below</p>
      </motion.div>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', alignItems: 'center', margin: '0 auto 48px' }}>
        <AnimatedToggle active={platforms.includes('linkedin')} onClick={() => togglePlatform('linkedin')} label="LinkedIn" />
        <AnimatedToggle active={platforms.includes('indeed')} onClick={() => togglePlatform('indeed')} label="Indeed" />
        <div style={{ width: '100%', height: '1px', background: 'var(--border-color)', margin: '10px 0' }} />
        <AnimatedToggle active={testMode} onClick={() => setTestMode(!testMode)} label="Test Mode (Fast run)" />
      </div>

      <button className="btn-primary" onClick={() => onStart(platforms, testMode)} style={{ width: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px' }}>
        <Play size={20} fill="currentColor" /> Start Pipeline
      </button>
    </div>
  );
}

function ScanView({ state }) {
  const jobs = state?.scan?.live_jobs || [];
  const p = state?.scan?.current_params;
  const currentCycle = p ? p.cycle_label : (jobs.length > 0 ? jobs[0].cycle : (state?.status_text?.includes('Cycle') ? state.status_text : 'Initializing...'));
  
  return (
    <div className="glass-panel" style={{ padding: '32px', maxWidth: '800px', margin: '20px auto', minHeight: '600px', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div>
          <h2 style={{ margin: '0 0 8px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Activity size={24} color="var(--primary)" /> Scraping Jobs
          </h2>
          <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '14px', fontWeight: 'bold' }}>{currentCycle}</p>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '36px', fontWeight: 'bold', color: 'var(--primary)' }}>{state?.scan?.total_found || 0}</div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Found Overall</div>
        </div>
      </div>
      
      {p && (
        <motion.div 
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          style={{ background: 'linear-gradient(135deg, #2563eb, #1e40af)', color: '#fff', borderRadius: '12px', padding: '20px', marginBottom: '24px', boxShadow: '0 4px 12px rgba(37, 99, 235, 0.2)' }}
        >
          <div style={{ fontSize: '12px', color: '#93c5fd', fontWeight: 600, marginBottom: '12px', letterSpacing: '0.05em' }}>LIVE MONITORING CYCLE</div>
          <div style={{ display: 'flex', gap: '32px', fontSize: '16px', fontWeight: 500 }}>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '11px', color: '#bfdbfe', textTransform: 'uppercase', marginBottom: '4px' }}>Job Role</span>
              <span>{p.term}</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '11px', color: '#bfdbfe', textTransform: 'uppercase', marginBottom: '4px' }}>Location</span>
              <span>{p.loc}</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '11px', color: '#bfdbfe', textTransform: 'uppercase', marginBottom: '4px' }}>Job Type</span>
              <span>{p.jt}</span>
            </div>
          </div>
        </motion.div>
      )}
      
      <div style={{ flex: 1, overflowY: 'auto', borderRadius: '8px', border: '1px solid var(--border-color)', maxHeight: '400px' }}>
        <table className="data-table">
          <thead style={{ background: '#f1f5f9', position: 'sticky', top: 0, zIndex: 1 }}>
            <tr>
              <th>Job Title</th>
              <th>Company</th>
              <th>Platform</th>
            </tr>
          </thead>
          <tbody>
            <AnimatePresence>
              {jobs.map((job, idx) => (
                <motion.tr 
                  key={`${job.title}-${job.company}-${idx}`}
                  initial={{ opacity: 0, y: -10, backgroundColor: 'rgba(37, 99, 235, 0.1)' }}
                  animate={{ opacity: 1, y: 0, backgroundColor: 'transparent' }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.3 }}
                >
                  <td><div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '250px', fontWeight: 500 }}>{job.title}</div></td>
                  <td>{job.company}</td>
                  <td>
                    <span style={{ padding: '4px 8px', background: '#e2e8f0', borderRadius: '4px', fontSize: '11px', fontWeight: 'bold' }}>
                      {job.platform?.toUpperCase()}
                    </span>
                  </td>
                </motion.tr>
              ))}
            </AnimatePresence>
            {jobs.length === 0 && (
              <tr><td colSpan="3" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '32px' }}>Waiting for results...</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function FilterView({ state }) {
  const dropped = state?.filter?.dropped_jobs || [];
  
  return (
    <div className="glass-panel" style={{ padding: '32px', maxWidth: '1000px', margin: '20px auto', minHeight: '600px', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h2 style={{ margin: '0 0 8px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Filter size={24} color="var(--warning)" /> Data Cleansing
          </h2>
          <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '14px' }}>{state?.status_text || 'Applying pandas filters...'}</p>
        </div>
        <div style={{ textAlign: 'right', display: 'flex', gap: '24px' }}>
           <div>
            <div style={{ fontSize: '36px', fontWeight: 'bold', color: 'var(--text-muted)' }}>{state?.filter?.before || state?.scan?.total_found || 0}</div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Initial</div>
          </div>
          <div>
            <div style={{ fontSize: '36px', fontWeight: 'bold', color: 'var(--success)' }}>{state?.filter?.after || 0}</div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Remaining</div>
          </div>
        </div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', borderRadius: '8px', border: '1px solid var(--border-color)', maxHeight: '400px' }}>
        <table className="data-table">
          <thead style={{ background: '#f1f5f9', position: 'sticky', top: 0, zIndex: 1 }}>
            <tr>
              <th style={{ width: '40px' }}></th>
              <th>Job Info</th>
              <th>Reason Dropped</th>
            </tr>
          </thead>
          <tbody>
              {dropped.map((job, idx) => (
                <tr key={`drop-${idx}`}>
                  <td style={{ color: 'var(--danger)', textAlign: 'center' }}><XCircle size={16} /></td>
                  <td>
                    <div style={{ fontWeight: 500 }}>{job.title}</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{job.company}</div>
                  </td>
                  <td style={{ color: 'var(--danger)', fontSize: '12px' }}>{job.reason}</td>
                </tr>
              ))}
            {dropped.length === 0 && (
              <tr><td colSpan="3" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '32px' }}>{state?.phase === 'filtering' ? 'Analyzing dataset...' : 'No jobs dropped or tracking skipped.'}</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ScoreView({ state }) {
  const scores = state?.score?.live_scores || [];
  const [expandedId, setExpandedId] = useState(null);
  
  return (
    <div className="glass-panel" style={{ padding: '32px', maxWidth: '1000px', margin: '20px auto', minHeight: '600px', display: 'flex', flexDirection: 'column' }}>
      <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ margin: '0 0 8px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <BrainCircuit size={24} color="var(--primary)" /> AI Evaluation
          </h2>
          <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '14px' }}>{state?.status_text || 'Scoring relevant candidates...'}</p>
        </div>
        <div style={{ fontSize: '32px', fontWeight: 'bold' }}>
          <span style={{ color: 'var(--primary)' }}>{state?.score?.scored || 0}</span>
          <span style={{ color: 'var(--text-muted)', fontSize: '20px' }}> / {state?.filter?.after || 1}</span>
        </div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', borderRadius: '8px', border: '1px solid var(--border-color)', maxHeight: '400px' }}>
        <table className="data-table">
          <thead style={{ background: '#f1f5f9', position: 'sticky', top: 0, zIndex: 1 }}>
            <tr>
              <th>Status</th>
              <th>Job Info</th>
              <th style={{ textAlign: 'right' }}>Match Score</th>
            </tr>
          </thead>
          <tbody>
            {scores.map((s, idx) => (
              <React.Fragment key={idx}>
                <tr 
                  onClick={() => setExpandedId(expandedId === idx ? null : idx)}
                  style={{ 
                    cursor: 'pointer',
                    borderLeft: s.status === 'done' ? `4px solid ${s.score >= 50 ? 'var(--success)' : 'var(--danger)'}` : '4px solid var(--warning)' 
                  }}
                >
                  <td style={{ width: '60px', textAlign: 'center' }}>
                    {s.status === 'scoring' ? <Loader2 size={16} className="spin" color="var(--warning)" /> : <CheckCircle size={16} color={s.score >= 50 ? 'var(--success)' : 'var(--danger)'} />}
                  </td>
                  <td>
                    <div style={{ fontWeight: 600 }}>{s.title}</div>
                    <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>{s.company}</div>
                  </td>
                  <td style={{ textAlign: 'right', fontWeight: 'bold', fontSize: '16px', color: s.score >= 50 ? 'var(--success)' : 'var(--danger)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '8px' }}>
                      <span>{s.status === 'scoring' ? '--' : `${s.score}%`}</span>
                      {s.status === 'done' && (expandedId === idx ? <ChevronUp size={16} /> : <ChevronDown size={16} />)}
                    </div>
                  </td>
                </tr>
                {expandedId === idx && s.status === 'done' && (
                  <tr>
                    <td colSpan="3" style={{ padding: '12px 24px', background: '#f8fafc', borderLeft: `4px solid ${s.score >= 50 ? 'var(--success)' : 'var(--danger)'}`, fontSize: '14px', color: 'var(--text-main)' }}>
                      <strong>AI Explanation:</strong> {s.reason || 'No explanation available (cached from previous run).'}
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
            {scores.length === 0 && (
              <tr><td colSpan="3" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '32px' }}>Waiting for AI scoring to start...</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PersistentSnapshotView({ state, onReset }) {
  const scores = state?.score?.live_scores || [];
  const tailoredResults = state?.tailor?.results || [];
  const [expandedId, setExpandedId] = useState(null);

  return (
    <div className="glass-panel" style={{ padding: '32px', maxWidth: '1200px', margin: '20px auto', display: 'flex', flexDirection: 'column', height: 'calc(100vh - 80px)' }}>
      
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
           <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
             <Database size={24} color="var(--primary)" /> Persistent Snapshot
           </h2>
           <p style={{ margin: '4px 0 0', color: 'var(--text-muted)', fontSize: '14px' }}>
             {state.phase === 'tailoring' && 'Phase 3: Tailoring Resumes (Background)'}
             {state.phase === 'saving' && 'Phase 4: Persisting & Generating Excel (Background)'}
             {state.phase === 'done' && 'Phase 5: Complete'}
           </p>
        </div>
        
        {/* Banner for completion or status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', background: '#f8fafc', padding: '12px 24px', borderRadius: '32px', border: '1px solid var(--border-color)' }}>
           {state.phase === 'tailoring' && <><Loader2 className="spin" size={20} color="var(--warning)"/> <span style={{fontWeight: 500}}>Tailoring Resumes...</span></>}
           {state.phase === 'saving' && <><Loader2 className="spin" size={20} color="var(--primary)"/> <span style={{fontWeight: 500}}>Saving to Database...</span></>}
           {state.phase === 'done' && <><CheckCircle size={20} color="var(--success)"/> <span style={{fontWeight: 500, color: 'var(--success)'}}>Pipeline Complete</span></>}
        </div>
      </div>

      <div style={{ display: 'flex', gap: '24px', flex: 1, minHeight: 0 }}>
        
        {/* Module A: Scoring Audit */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', border: '1px solid var(--border-color)', borderRadius: '12px', background: '#fff', overflow: 'hidden' }}>
           <div style={{ padding: '16px 20px', background: '#f8fafc', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600 }}>
                <BrainCircuit size={18} color="var(--primary)" /> Module A: Scoring Audit
              </div>
              <div style={{ fontSize: '12px', background: 'var(--primary)', color: '#fff', padding: '2px 8px', borderRadius: '12px' }}>
                {scores.length} Evaluated
              </div>
           </div>
           <div style={{ flex: 1, overflowY: 'auto', padding: '0' }}>
              <table className="data-table" style={{ margin: 0, border: 'none' }}>
                <thead style={{ position: 'sticky', top: 0, background: '#f1f5f9', zIndex: 1 }}>
                  <tr>
                    <th style={{ paddingLeft: '20px' }}>Job Info</th>
                    <th style={{ textAlign: 'right', paddingRight: '20px' }}>Match Score</th>
                  </tr>
                </thead>
                <tbody>
                  {scores.map((s, idx) => (
                    <React.Fragment key={idx}>
                      <tr 
                        onClick={() => setExpandedId(expandedId === idx ? null : idx)}
                        style={{ cursor: 'pointer', borderLeft: `4px solid ${s.score >= 70 ? 'var(--success)' : (s.score >= 50 ? 'var(--warning)' : 'var(--danger)')}` }}
                      >
                        <td style={{ paddingLeft: '16px' }}>
                          <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>{s.title}</div>
                          <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '2px' }}>{s.company}</div>
                        </td>
                        <td style={{ textAlign: 'right', fontWeight: 'bold', fontSize: '16px', paddingRight: '20px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '12px' }}>
                            <span style={{ background: s.score >= 70 ? '#dcfce7' : (s.score >= 50 ? '#fef9c3' : '#fee2e2'), color: s.score >= 70 ? '#166534' : (s.score >= 50 ? '#854d0e' : '#991b1b'), padding: '4px 12px', borderRadius: '12px' }}>
                              {s.score}%
                            </span>
                            {expandedId === idx ? <ChevronUp size={16} color="var(--text-muted)" /> : <ChevronDown size={16} color="var(--text-muted)" />}
                          </div>
                        </td>
                      </tr>
                      {expandedId === idx && (
                        <tr>
                          <td colSpan="2" style={{ padding: '12px 20px', background: '#f8fafc', borderLeft: `4px solid ${s.score >= 70 ? 'var(--success)' : (s.score >= 50 ? 'var(--warning)' : 'var(--danger)')}`, fontSize: '13px', color: 'var(--text-main)' }}>
                            <strong>AI Explanation:</strong> {s.reason || 'No explanation available (cached from previous run).'}
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
           </div>
        </div>

        {/* Module B: Tailoring Audit */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', border: '1px solid var(--border-color)', borderRadius: '12px', background: '#fff', overflow: 'hidden' }}>
           <div style={{ padding: '16px 20px', background: '#f8fafc', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600 }}>
                <FileSignature size={18} color="var(--success)" /> Module B: Tailoring Audit
              </div>
              <div style={{ fontSize: '12px', background: 'var(--success)', color: '#fff', padding: '2px 8px', borderRadius: '12px' }}>
                {state.phase === 'tailoring' ? 'Processing...' : `${tailoredResults.length} Ready`}
              </div>
           </div>
           
           {state.phase === 'tailoring' ? (
             <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: '#fafaf9' }}>
                <Loader2 className="spin" size={32} color="var(--primary)" style={{ marginBottom: '16px' }} />
                <div style={{ fontWeight: 600, color: 'var(--text-main)', fontSize: '16px' }}>Generating Resumes...</div>
                <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>Awaiting Phase 3 resolution</div>
             </div>
           ) : (
             <div style={{ flex: 1, overflowY: 'auto', padding: '0' }}>
                <table className="data-table" style={{ margin: 0, border: 'none' }}>
                  <thead style={{ position: 'sticky', top: 0, background: '#f1f5f9', zIndex: 1 }}>
                    <tr>
                      <th style={{ paddingLeft: '20px' }}>Job Info</th>
                      <th style={{ textAlign: 'right', paddingRight: '20px' }}>Document</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tailoredResults.map((s, idx) => (
                        <tr key={idx}>
                          <td style={{ paddingLeft: '20px' }}>
                            <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>{s.title}</div>
                            <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '2px' }}>{s.company}</div>
                          </td>
                          <td style={{ textAlign: 'right', paddingRight: '20px' }}>
                              <button 
                                style={{ padding: '6px 16px', fontSize: '13px', background: 'var(--primary)', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 500, boxShadow: '0 2px 4px rgba(37, 99, 235, 0.2)' }}
                                onClick={() => window.open(`/api/resume/${s.id}`, '_blank')}
                              >
                                View PDF
                              </button>
                          </td>
                        </tr>
                    ))}
                    {tailoredResults.length === 0 && (
                        <tr>
                          <td colSpan="2" style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>No resumes generated</td>
                        </tr>
                    )}
                  </tbody>
                </table>
             </div>
           )}
        </div>

      </div>

      {/* Global Completion Banner */}
      <AnimatePresence>
        {state.phase === 'done' && (
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            style={{ marginTop: '24px', padding: '20px 24px', background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
          >
            <div>
              <h4 style={{ margin: 0, color: '#166534', fontSize: '18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <CheckCircle size={20} /> Pipeline Successfully Completed
              </h4>
              <p style={{ margin: '4px 0 0', fontSize: '14px', color: '#166534', opacity: 0.8 }}>
                {state.scan.total_found} Scraped • {state.filter.after} Evaluated • {tailoredResults.length} Resumes Generated
              </p>
            </div>
            <div style={{ display: 'flex', gap: '12px' }}>
              <button 
                style={{ padding: '10px 20px', background: '#fff', color: '#166534', border: '1px solid #16a34a', borderRadius: '8px', cursor: 'pointer', fontWeight: 600, fontSize: '14px' }}
                onClick={onReset}
              >
                Run Again
              </button>
              <button 
                style={{ padding: '10px 20px', background: '#16a34a', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 600, fontSize: '14px', boxShadow: '0 2px 4px rgba(22, 163, 74, 0.2)' }}
                onClick={() => window.location.href = '/tracker'}
              >
                View Application Tracker →
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function Dashboard() {
  const [state, setState] = useState(initialPipelineState);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch('/api/status');
        const data = await res.json();
        setState(data);
      } catch (e) {
        console.error('Status fetch error', e);
      }
    };
    fetchStatus();

    const eventSource = new EventSource('/api/stream');
    eventSource.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        setState(data);
      } catch (err) {
        console.error("Parse error", err);
      }
    };
    return () => eventSource.close();
  }, []);

  const handleStart = async (platforms, testMode) => {
    try {
      setError('');
      const endpoint = testMode ? '/api/test-start' : '/api/start';
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ platforms, dry_run: false }),
      });
      if (!res.ok) {
        const data = await res.json();
        setError(data.error || 'Failed to start');
      } else {
        setState(prev => ({ 
          ...prev, 
          phase: 'scanning', 
          mode: testMode ? 'test' : 'prod', 
          scan: { ...prev.scan, total_found: 0, live_jobs: [] },
          filter: { ...prev.filter, dropped_jobs: [] },
          score: { ...prev.score, live_scores: [] }
        }));
      }
    } catch (err) {
      setError('Connection failed. Is the backend running?');
    }
  };

  const handleAbort = async () => {
    try {
      await fetch('/api/stop', { method: 'POST' });
    } catch (err) {
      console.error('Failed to abort', err);
    }
  };

  return (
    <div style={{ padding: '24px', minHeight: '100vh', position: 'relative', background: 'var(--bg-deep)' }}>
      {error && (
        <div style={{ maxWidth: '800px', margin: '0 auto 24px', background: '#fef2f2', border: '1px solid var(--danger)', padding: '16px', borderRadius: '8px', color: 'var(--danger)', textAlign: 'center' }}>
          {error}
        </div>
      )}
      
      <AnimatePresence mode="wait">
        <motion.div 
          key={state.phase} 
          initial={{ opacity: 0, y: 10 }} 
          animate={{ opacity: 1, y: 0 }} 
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.3 }}
        >
          {state.phase === 'idle' && <IdleView onStart={handleStart} />}
          {state.phase === 'scanning' && <ScanView state={state} />}
          {state.phase === 'filtering' && <FilterView state={state} />}
          {state.phase === 'scoring' && <ScoreView state={state} />}
          {['tailoring', 'saving', 'done'].includes(state.phase) && <PersistentSnapshotView state={state} onReset={handleAbort} />}
        </motion.div>
      </AnimatePresence>

      {state.phase !== 'idle' && state.phase !== 'done' && (
        <div style={{ position: 'fixed', bottom: '32px', left: '50%', transform: 'translateX(-50%)' }}>
          <button onClick={handleAbort} className="btn-danger">
            Abort Pipeline
          </button>
        </div>
      )}
    </div>
  );
}
