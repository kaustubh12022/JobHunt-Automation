import React, { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, CheckCircle, Database, FileSignature, Filter, Loader2, XCircle, ChevronDown, ChevronUp } from 'lucide-react';

const initialPipelineState = {
  running: false,
  mode: 'idle',
  phase: 'idle',
  status_text: 'Waiting for pipeline to start...',
  scan_data: { total_found: 0, current_platform: '', current_city: '', combos_done: 0, combos_total: 0, live_jobs: [] },
  filter_data: { before: 0, after: 0, dropped: {}, dropped_jobs: [] },
  score_data: { total: 0, scored: 0, avg_score: 0, above_threshold: 0, shortlisted: 0, live_scores: [] },
  tailor_data: { total: 0, completed: 0, failed: 0, current_company: '', results: [] },
};

function ScanView({ state }) {
  const jobs = state.scan_data?.live_jobs || [];
  // Clean up raw status text
  const cleanStatus = (text) => text.replace(/---.*?---/g, '').trim();
  const statusText = state.status_text ? cleanStatus(state.status_text) : 'Waiting...';
  
  return (
    <div className="glass-panel" style={{ padding: '24px', maxWidth: '800px', margin: '20px auto', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div style={{ maxWidth: '70%' }}>
          <h2 style={{ margin: '0 0 6px 0', display: 'flex', alignItems: 'center', gap: '8px', color: '#ffffff', fontWeight: 700 }}>
            <Activity size={24} color="var(--primary)" /> Scraping Jobs
          </h2>
          <p style={{ margin: 0, color: '#e2e8f0', fontSize: '15px', fontWeight: 500 }}>{statusText}</p>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '36px', fontWeight: 800, color: '#60a5fa', lineHeight: 1 }}>{state.scan_data?.total_found || 0}</div>
          <div style={{ fontSize: '12px', color: '#cbd5e1', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.05em', marginTop: '4px' }}>Found</div>
        </div>
      </div>
      
      <div style={{ flex: 1, overflowY: 'auto', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.15)', maxHeight: '400px' }}>
        <table className="data-table">
          <thead style={{ background: 'rgba(25, 25, 35, 0.98)', position: 'sticky', top: 0, zIndex: 1, borderBottom: '1px solid rgba(255,255,255,0.15)' }}>
            <tr>
              <th style={{ color: '#f8fafc', fontWeight: 700 }}>Job Title</th>
              <th className="desktop-only" style={{ color: '#f8fafc', fontWeight: 700 }}>Company</th>
              <th className="desktop-only" style={{ color: '#f8fafc', fontWeight: 700 }}>Platform</th>
            </tr>
          </thead>
          <tbody>
            <AnimatePresence>
              {jobs.map((job, idx) => (
                <motion.tr 
                  key={`${job.title}-${job.company}-${idx}`}
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                >
                  <td style={{ maxWidth: '200px' }}>
                    <div style={{ fontWeight: 700, color: '#ffffff' }} className="text-truncate">{job.title}</div>
                    <div className="mobile-only text-truncate" style={{ fontSize: '12px', color: '#cbd5e1', marginTop: '2px', fontWeight: 500 }}>{job.company} • {job.platform}</div>
                  </td>
                  <td className="desktop-only text-truncate" style={{ maxWidth: '150px', color: '#e2e8f0', fontWeight: 500 }}>{job.company}</td>
                  <td className="desktop-only">
                    <span style={{ padding: '4px 10px', background: 'rgba(59, 130, 246, 0.2)', color: '#93c5fd', border: '1px solid rgba(59, 130, 246, 0.4)', borderRadius: '6px', fontSize: '11px', fontWeight: 700, letterSpacing: '0.04em' }}>
                      {job.platform?.toUpperCase()}
                    </span>
                  </td>
                </motion.tr>
              ))}
            </AnimatePresence>
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ScoreView({ state }) {
  const scores = state.score_data?.live_scores || [];
  
  // Clean up raw status text
  const cleanStatus = (text) => text ? text.replace(/---.*?---/g, '').trim() : '';

  return (
    <div className="glass-panel" style={{ padding: '24px', maxWidth: '800px', margin: '20px auto', display: 'flex', flexDirection: 'column' }}>
      <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ maxWidth: '70%' }}>
          <h2 style={{ margin: '0 0 8px 0', display: 'flex', alignItems: 'center', gap: '8px', color: '#ffffff', fontWeight: 700 }}>
            <Activity size={24} color="var(--primary)" /> AI Evaluation
          </h2>
          <p style={{ margin: 0, color: '#e2e8f0', fontSize: '15px', fontWeight: 500 }}>{cleanStatus(state.status_text)}</p>
        </div>
        <div style={{ fontSize: '32px', fontWeight: 800 }}>
          <span style={{ color: 'var(--primary)' }}>{state.score_data?.scored || 0}</span>
        </div>
      </div>
      <div style={{ flex: 1, overflowY: 'auto', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.15)', maxHeight: '400px' }}>
        <table className="data-table">
          <thead style={{ background: 'rgba(25, 25, 35, 0.98)', position: 'sticky', top: 0, zIndex: 1, borderBottom: '1px solid rgba(255,255,255,0.15)' }}>
            <tr>
              <th style={{ color: '#f8fafc', fontWeight: 700 }}>Status</th>
              <th style={{ color: '#f8fafc', fontWeight: 700 }}>Job Info</th>
              <th style={{ textAlign: 'right', color: '#f8fafc', fontWeight: 700 }}>Score</th>
            </tr>
          </thead>
          <tbody>
            {scores.map((s, idx) => (
              <tr key={idx} style={{ borderLeft: s.status === 'done' ? `4px solid ${s.score >= 50 ? 'var(--success)' : 'var(--danger)'}` : '4px solid var(--warning)' }}>
                <td style={{ width: '40px', textAlign: 'center' }}>
                  {s.status === 'scoring' ? <Loader2 size={16} className="spin" color="var(--warning)" /> : <CheckCircle size={16} color={s.score >= 50 ? 'var(--success)' : 'var(--danger)'} />}
                </td>
                <td style={{ maxWidth: '200px' }}>
                  <div style={{ fontWeight: 700, color: '#ffffff' }} className="text-truncate">{s.title}</div>
                  <div style={{ fontSize: '12px', color: '#cbd5e1', marginTop: '2px', fontWeight: 500 }} className="text-truncate">{s.company}</div>
                </td>
                <td style={{ textAlign: 'right', fontWeight: 'bold', color: s.score >= 50 ? '#34d399' : '#f87171' }}>
                  {s.status === 'scoring' ? '--' : `${s.score}%`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function LivePipeline() {
  const [state, setState] = useState(initialPipelineState);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 1. Fetch initial state
    const fetchState = async () => {
      const { data, error } = await supabase.from('live_pipeline').select('*').eq('id', 1).single();
      if (data) {
        setState({
          running: data.running,
          mode: data.mode,
          phase: data.phase,
          status_text: data.status_text,
          scan_data: data.scan_data || {},
          filter_data: data.filter_data || {},
          score_data: data.score_data || {},
          tailor_data: data.tailor_data || {},
        });
      }
      setLoading(false);
    };
    fetchState();

    // 2. Subscribe to realtime updates
    const channel = supabase.channel('live_pipeline_channel')
      .on('postgres_changes', { event: 'UPDATE', schema: 'public', table: 'live_pipeline' }, (payload) => {
        const data = payload.new;
        setState({
          running: data.running,
          mode: data.mode,
          phase: data.phase,
          status_text: data.status_text,
          scan_data: data.scan_data || {},
          filter_data: data.filter_data || {},
          score_data: data.score_data || {},
          tailor_data: data.tailor_data || {},
        });
      })
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  if (loading) return <div style={{ padding: '40px', textAlign: 'center' }}><Loader2 className="spin" /></div>;

  return (
    <div style={{ padding: '24px', minHeight: '100vh', background: 'var(--bg-deep)' }}>
      <h1 style={{ fontSize: '24px', marginBottom: '8px' }}>Live Pipeline</h1>
      
      {!state.running && state.phase === 'idle' ? (
        <div className="glass-panel" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
          Pipeline is currently idle. Start it from your local machine.
        </div>
      ) : (
        <AnimatePresence mode="wait">
          <motion.div key={state.phase} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
            {state.phase === 'scanning' && <ScanView state={state} />}
            {state.phase === 'scoring' && <ScoreView state={state} />}
            {['tailoring', 'saving'].includes(state.phase) && (
              <div className="glass-panel" style={{ padding: '40px', textAlign: 'center' }}>
                <Loader2 className="spin" size={32} style={{ margin: '0 auto 16px' }} color="var(--primary)" />
                <h2>{state.phase === 'tailoring' ? 'Tailoring Resumes...' : 'Saving to Database...'}</h2>
              </div>
            )}
            {state.phase === 'done' && (
              <div className="glass-panel" style={{ padding: '40px', textAlign: 'center' }}>
                <CheckCircle size={48} color="var(--success)" style={{ margin: '0 auto 16px' }} />
                <h2>Pipeline Complete!</h2>
                <button className="btn-primary" onClick={() => window.location.href = '/tracker'} style={{ marginTop: '16px' }}>View Tracker</button>
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      )}
    </div>
  );
}
