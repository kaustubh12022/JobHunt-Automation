import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Play, Activity, CheckCircle, Database, BrainCircuit, FileSignature, Filter, Loader2, XCircle, ChevronDown, ChevronUp, Sparkles } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api';

const initialPipelineState = {
  running: false,
  mode: 'idle',
  phase: 'idle',
  status_text: '',
  scan: { total_found: 0, current_platform: '', current_city: '', combos_done: 0, combos_total: 0, live_jobs: [] },
  filter: { before: 0, after: 0, dropped: {}, dropped_jobs: [] },
  score: { total: 0, scored: 0, avg_score: 0, above_threshold: 0, shortlisted: 0, live_scores: [] },
  shortlisted_jobs: [],
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

function ModelSelect({ value, onChange, options, label }) {
  return (
    <div style={{ flex: 2, minWidth: '240px' }}>
      <div style={{ fontSize: '12px', color: '#cbd5e1', marginBottom: '6px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</div>
      <div style={{ position: 'relative' }}>
        <select
          value={value}
          onChange={e => onChange(e.target.value)}
          style={{
            width: '100%',
            padding: '11px 36px 11px 14px',
            background: 'rgba(255, 255, 255, 0.1)',
            border: '1px solid rgba(255, 255, 255, 0.25)',
            borderRadius: '10px',
            fontSize: '14px',
            color: '#ffffff',
            cursor: 'pointer',
            fontWeight: 600,
            outline: 'none',
            appearance: 'none',
            colorScheme: 'light',
            transition: 'border-color 0.2s',
          }}
        >
          {options.map(opt => (
            <option key={opt.value} value={opt.value} style={{ color: '#111827', background: '#ffffff', fontWeight: 600 }}>
              {opt.label}
            </option>
          ))}
        </select>
        <ChevronDown size={18} color="#cbd5e1" style={{ position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none' }} />
      </div>
    </div>
  );
}

function IdleView({ onStart }) {
  const [platforms, setPlatforms] = useState(['linkedin', 'indeed', 'workday', 'jsonld']);
  const [testMode, setTestMode] = useState(false);
  const [jobTypes, setJobTypes] = useState(['fulltime', 'internship']);
  
  // AI Model Settings
  const [scoringModel, setScoringModel] = useState('deepseek-chat');
  const [scoringThinking, setScoringThinking] = useState(false);
  const [tailoringModel, setTailoringModel] = useState('deepseek-chat');
  const [tailoringThinking, setTailoringThinking] = useState(true);

  const togglePlatform = (p) => {
    setPlatforms(prev => prev.includes(p) ? prev.filter(x => x !== p) : [...prev, p]);
  };
  
  const toggleJobType = (t) => {
    setJobTypes(prev => prev.includes(t) ? prev.filter(x => x !== t) : [...prev, t]);
  };

  return (
    <div className="glass-panel" style={{ padding: '48px', maxWidth: '680px', margin: '40px auto', textAlign: 'center' }}>
      <motion.div initial={{ y: -10, opacity: 0 }} animate={{ y: 0, opacity: 1 }} style={{ marginBottom: '40px' }}>
        <h1 style={{ fontSize: '32px', margin: '0 0 8px', color: 'var(--text-main)', fontWeight: 700 }}>AutoApply Pipeline</h1>
        <p style={{ color: 'var(--text-muted)' }}>Configure your run parameters below</p>
      </motion.div>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', alignItems: 'center', margin: '0 auto 32px' }}>
        <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', justifyContent: 'center' }}>
            <AnimatedToggle active={platforms.includes('linkedin')} onClick={() => togglePlatform('linkedin')} label="LinkedIn" />
            <AnimatedToggle active={platforms.includes('indeed')} onClick={() => togglePlatform('indeed')} label="Indeed" />
            <AnimatedToggle active={platforms.includes('workday')} onClick={() => togglePlatform('workday')} label="Workday" />
            <AnimatedToggle active={platforms.includes('jsonld')} onClick={() => togglePlatform('jsonld')} label="JSON-LD" />
        </div>
        
        <div style={{ width: '100%', height: '1px', background: 'var(--border-color)', margin: '10px 0' }} />
        
        <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap', justifyContent: 'center' }}>
            <AnimatedToggle active={jobTypes.includes('fulltime')} onClick={() => toggleJobType('fulltime')} label="Full-Time" />
            <AnimatedToggle active={jobTypes.includes('internship')} onClick={() => toggleJobType('internship')} label="Internships" />
        </div>
        
        <div style={{ width: '100%', height: '1px', background: 'var(--border-color)', margin: '10px 0' }} />
        <AnimatedToggle active={testMode} onClick={() => setTestMode(!testMode)} label="Test Mode (1 module cycle, top 3 resumes)" />
      </div>

      {/* AI Model Configuration */}
      <div style={{ 
        textAlign: 'left', 
        background: 'rgba(255, 255, 255, 0.04)', 
        borderRadius: '16px', 
        padding: '24px', 
        marginBottom: '32px',
        border: '1px solid rgba(255, 255, 255, 0.1)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
          <BrainCircuit size={18} color="var(--primary)" />
          <span style={{ fontWeight: 700, fontSize: '15px', color: '#f8fafc' }}>AI Model Configuration</span>
        </div>
        
        {/* Scoring Settings */}
        <div style={{ marginBottom: '20px' }}>
          <div style={{ fontSize: '13px', fontWeight: 700, color: '#f8fafc', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--primary)', display: 'inline-block' }} />
            AI Scoring
          </div>
          <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
            <ModelSelect 
              label="Model"
              value={scoringModel}
              onChange={setScoringModel}
              options={[
                { value: 'deepseek-chat', label: 'DeepSeek Chat (V3 - Fast Scoring)' },
                { value: 'deepseek-reasoner', label: 'DeepSeek Reasoner (R1)' },
              ]}
            />
            <div style={{ flex: '0 0 140px' }}>
              <div style={{ fontSize: '12px', color: '#cbd5e1', marginBottom: '6px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Thinking</div>
              <div 
                onClick={() => setScoringThinking(!scoringThinking)}
                style={{
                  display: 'flex', alignItems: 'center', gap: '10px', 
                  padding: '10px 14px', background: 'rgba(255, 255, 255, 0.08)', border: '1px solid rgba(255, 255, 255, 0.2)', 
                  borderRadius: '10px', cursor: 'pointer', transition: 'all 0.2s'
                }}
              >
                <div className={`toggle-switch ${scoringThinking ? 'active' : ''}`} style={{ transform: 'scale(0.8)' }}>
                  <div className="toggle-knob" />
                </div>
                <span style={{ fontSize: '14px', fontWeight: 700, color: scoringThinking ? '#60a5fa' : '#cbd5e1' }}>
                  {scoringThinking ? 'Enabled' : 'Disabled'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Tailoring Settings */}
        <div>
          <div style={{ fontSize: '13px', fontWeight: 700, color: '#f8fafc', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--success)', display: 'inline-block' }} />
            Resume Tailoring
          </div>
          <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
            <ModelSelect 
              label="Model"
              value={tailoringModel}
              onChange={setTailoringModel}
              options={[
                { value: 'deepseek-chat', label: 'DeepSeek Chat (V3 - Fast Tailoring)' },
                { value: 'deepseek-reasoner', label: 'DeepSeek Reasoner (R1 - Deep Tailoring)' },
              ]}
            />
            <div style={{ flex: '0 0 140px' }}>
              <div style={{ fontSize: '12px', color: '#cbd5e1', marginBottom: '6px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Thinking</div>
              <div 
                onClick={() => setTailoringThinking(!tailoringThinking)}
                style={{
                  display: 'flex', alignItems: 'center', gap: '10px',
                  padding: '10px 14px', background: 'rgba(255, 255, 255, 0.08)', border: '1px solid rgba(255, 255, 255, 0.2)',
                  borderRadius: '10px', cursor: 'pointer', transition: 'all 0.2s'
                }}
              >
                <div className={`toggle-switch ${tailoringThinking ? 'active' : ''}`} style={{ transform: 'scale(0.8)' }}>
                  <div className="toggle-knob" />
                </div>
                <span style={{ fontSize: '14px', fontWeight: 700, color: tailoringThinking ? '#34d399' : '#cbd5e1' }}>
                  {tailoringThinking ? 'Enabled' : 'Disabled'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <button className="btn-primary" onClick={() => onStart(platforms, testMode, { scoringModel, scoringThinking, tailoringModel, tailoringThinking }, jobTypes)} style={{ width: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px' }}>
        <Play size={20} fill="currentColor" /> Start Pipeline
      </button>
    </div>
  );
}

function ScanView({ state }) {
  const jobs = state?.scan?.live_jobs || [];
  const p = state?.scan?.current_params;
  const statusText = state?.status_text || 'Waiting to start...';
  
  return (
    <div className="glass-panel" style={{ padding: '32px', maxWidth: '850px', margin: '20px auto', minHeight: '600px', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h2 style={{ margin: '0 0 6px 0', display: 'flex', alignItems: 'center', gap: '8px', color: '#ffffff', fontSize: '24px', fontWeight: 700 }}>
            <Activity size={24} color="var(--primary)" /> Scraping Jobs
          </h2>
          <p style={{ margin: 0, color: '#e2e8f0', fontSize: '15px', fontWeight: 500 }}>{statusText}</p>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '38px', fontWeight: 800, color: '#60a5fa', lineHeight: 1 }}>{state?.scan?.total_found || 0}</div>
          <div style={{ fontSize: '12px', color: '#cbd5e1', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.05em', marginTop: '4px' }}>Found Overall</div>
        </div>
      </div>
      
      {p && (
        <motion.div 
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          style={{ background: 'linear-gradient(135deg, #1d4ed8, #1e3a8a)', color: '#fff', borderRadius: '14px', padding: '20px', marginBottom: '24px', boxShadow: '0 4px 16px rgba(30, 58, 138, 0.4)', border: '1px solid rgba(255,255,255,0.15)' }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
             <div style={{ fontSize: '12px', color: '#93c5fd', fontWeight: 700, letterSpacing: '0.06em' }}>LIVE MONITORING CYCLE</div>
             {p.current_cycle && p.total_cycles && (
                <div style={{ fontSize: '13px', fontWeight: 700, background: 'rgba(255,255,255,0.25)', color: '#ffffff', padding: '4px 14px', borderRadius: '20px' }}>
                  Cycle {p.current_cycle} of {p.total_cycles}
                </div>
             )}
          </div>

          {state?.scan?.is_waiting ? (
            <motion.div 
              initial={{ opacity: 0, y: -5 }}
              animate={{ opacity: 1, y: 0 }}
              style={{ background: 'rgba(245, 158, 11, 0.15)', border: '1px solid rgba(245, 158, 11, 0.6)', borderRadius: '8px', padding: '16px', display: 'flex', alignItems: 'center', gap: '16px' }}
            >
                <Loader2 className="spin" size={24} color="#fcd34d" />
                <div>
                   <div style={{ fontWeight: 700, fontSize: '15px', color: '#fcd34d' }}>Rate Limit Protection Pause</div>
                   <div style={{ fontSize: '14px', marginTop: '4px', color: '#fef08a', fontWeight: 500 }}>{statusText}</div>
                </div>
            </motion.div>
          ) : (
            <div style={{ display: 'flex', gap: '32px', fontSize: '16px', fontWeight: 600 }}>
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <span style={{ fontSize: '11px', color: '#93c5fd', textTransform: 'uppercase', marginBottom: '4px', fontWeight: 700 }}>Job Role</span>
                <span style={{ color: '#ffffff', fontWeight: 700 }}>{p.term}</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <span style={{ fontSize: '11px', color: '#93c5fd', textTransform: 'uppercase', marginBottom: '4px', fontWeight: 700 }}>Location</span>
                <span style={{ color: '#ffffff', fontWeight: 700 }}>{p.loc}</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <span style={{ fontSize: '11px', color: '#93c5fd', textTransform: 'uppercase', marginBottom: '4px', fontWeight: 700 }}>Job Type</span>
                <span style={{ color: '#ffffff', fontWeight: 700 }}>{p.jt}</span>
              </div>
            </div>
          )}
        </motion.div>
      )}
      
      <div style={{ flex: 1, overflowY: 'auto', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.15)', maxHeight: '400px' }}>
        <table className="data-table">
          <thead style={{ background: 'rgba(25, 25, 35, 0.98)', position: 'sticky', top: 0, zIndex: 1, borderBottom: '1px solid rgba(255,255,255,0.15)' }}>
            <tr>
              <th style={{ color: '#f8fafc', fontWeight: 700 }}>Job Title</th>
              <th style={{ color: '#f8fafc', fontWeight: 700 }}>Company</th>
              <th style={{ color: '#f8fafc', fontWeight: 700 }}>Platform</th>
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
                  <td><div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '280px', fontWeight: 700, color: '#ffffff' }}>{job.title}</div></td>
                  <td style={{ color: '#e2e8f0', fontWeight: 500 }}>{job.company}</td>
                  <td>
                    <span style={{ padding: '4px 10px', background: 'rgba(59, 130, 246, 0.2)', color: '#93c5fd', border: '1px solid rgba(59, 130, 246, 0.4)', borderRadius: '6px', fontSize: '11px', fontWeight: 700, letterSpacing: '0.04em' }}>
                      {job.platform?.toUpperCase()}
                    </span>
                  </td>
                </motion.tr>
              ))}
            </AnimatePresence>
            {jobs.length === 0 && (
              <tr><td colSpan="3" style={{ textAlign: 'center', color: '#cbd5e1', padding: '36px', fontSize: '15px' }}>Waiting for results...</td></tr>
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
          <h2 style={{ margin: '0 0 8px 0', display: 'flex', alignItems: 'center', gap: '8px', color: '#ffffff', fontSize: '24px', fontWeight: 700 }}>
            <Filter size={24} color="var(--warning)" /> Data Cleansing
          </h2>
          <p style={{ margin: 0, color: '#e2e8f0', fontSize: '15px', fontWeight: 500 }}>{state?.status_text || 'Applying pandas filters...'}</p>
        </div>
        <div style={{ textAlign: 'right', display: 'flex', gap: '24px' }}>
           <div>
            <div style={{ fontSize: '36px', fontWeight: 800, color: '#94a3b8' }}>{state?.filter?.before || state?.scan?.total_found || 0}</div>
            <div style={{ fontSize: '12px', color: '#cbd5e1', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.05em' }}>Initial</div>
          </div>
          <div>
            <div style={{ fontSize: '36px', fontWeight: 800, color: 'var(--success)' }}>{state?.filter?.after || 0}</div>
            <div style={{ fontSize: '12px', color: '#cbd5e1', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.05em' }}>Remaining</div>
          </div>
        </div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.15)', maxHeight: '400px' }}>
        <table className="data-table">
          <thead style={{ background: 'rgba(25, 25, 35, 0.98)', position: 'sticky', top: 0, zIndex: 1, borderBottom: '1px solid rgba(255,255,255,0.15)' }}>
            <tr>
              <th style={{ width: '40px' }}></th>
              <th style={{ color: '#f8fafc', fontWeight: 700 }}>Job Info</th>
              <th style={{ color: '#f8fafc', fontWeight: 700 }}>Reason Dropped</th>
            </tr>
          </thead>
          <tbody>
              {dropped.map((job, idx) => (
                <tr key={`drop-${idx}`}>
                  <td style={{ color: 'var(--danger)', textAlign: 'center' }}><XCircle size={16} /></td>
                  <td>
                    <div style={{ fontWeight: 700, color: '#ffffff' }}>{job.title}</div>
                    <div style={{ fontSize: '12px', color: '#cbd5e1', marginTop: '2px', fontWeight: 500 }}>{job.company}</div>
                  </td>
                  <td style={{ color: '#fca5a5', fontSize: '13px', fontWeight: 600 }}>{job.reason}</td>
                </tr>
              ))}
            {dropped.length === 0 && (
              <tr><td colSpan="3" style={{ textAlign: 'center', color: '#cbd5e1', padding: '36px', fontSize: '15px' }}>{state?.phase === 'filtering' ? 'Analyzing dataset...' : 'No jobs dropped or tracking skipped.'}</td></tr>
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
          <h2 style={{ margin: '0 0 8px 0', display: 'flex', alignItems: 'center', gap: '8px', color: '#ffffff', fontSize: '24px', fontWeight: 700 }}>
            <BrainCircuit size={24} color="var(--primary)" /> AI Evaluation
          </h2>
          <p style={{ margin: 0, color: '#e2e8f0', fontSize: '15px', fontWeight: 500 }}>{state?.status_text || 'Scoring relevant candidates...'}</p>
        </div>
        <div style={{ fontSize: '32px', fontWeight: 'bold' }}>
          <span style={{ color: 'var(--primary)', fontWeight: 800 }}>{state?.score?.scored || 0}</span>
          <span style={{ color: '#cbd5e1', fontSize: '20px', fontWeight: 600 }}> / {state?.filter?.after || 1}</span>
        </div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.15)', maxHeight: '400px' }}>
        <table className="data-table">
          <thead style={{ background: 'rgba(25, 25, 35, 0.98)', position: 'sticky', top: 0, zIndex: 1, borderBottom: '1px solid rgba(255,255,255,0.15)' }}>
            <tr>
              <th style={{ color: '#f8fafc', fontWeight: 700 }}>Status</th>
              <th style={{ color: '#f8fafc', fontWeight: 700 }}>Job Info</th>
              <th style={{ textAlign: 'right', color: '#f8fafc', fontWeight: 700 }}>Match Score</th>
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
                    <div style={{ fontWeight: 700, color: '#ffffff' }}>{s.title}</div>
                    <div style={{ fontSize: '13px', color: '#cbd5e1', marginTop: '2px', fontWeight: 500 }}>{s.company}</div>
                  </td>
                  <td style={{ textAlign: 'right', fontWeight: 'bold', fontSize: '16px', color: s.score >= 50 ? '#34d399' : '#f87171' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '8px' }}>
                      <span>{s.status === 'scoring' ? '--' : `${s.score}%`}</span>
                      {s.status === 'done' && (expandedId === idx ? <ChevronUp size={16} color="#cbd5e1" /> : <ChevronDown size={16} color="#cbd5e1" />)}
                    </div>
                  </td>
                </tr>
                {expandedId === idx && s.status === 'done' && (
                  <tr>
                    <td colSpan="3" style={{ padding: '16px 24px', background: 'rgba(255, 255, 255, 0.05)', borderLeft: `4px solid ${s.score >= 50 ? 'var(--success)' : 'var(--danger)'}`, fontSize: '14px', color: '#f8fafc', lineHeight: 1.6 }}>
                      <strong style={{ color: '#ffffff', fontWeight: 700 }}>AI Explanation:</strong> <span style={{ color: '#f1f5f9', fontWeight: 500 }}>{s.reason || 'No explanation available (cached from previous run).'}</span>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
            {scores.length === 0 && (
              <tr><td colSpan="3" style={{ textAlign: 'center', color: '#cbd5e1', padding: '36px', fontSize: '15px' }}>Waiting for AI scoring to start...</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ReviewView({ state, onGenerate, onAbort, isGenerating, isAborting }) {
  const jobs = state?.shortlisted_jobs || [];
  const [selectedJobIds, setSelectedJobIds] = useState(() => jobs.map(j => j.id));
  const [expandedJobId, setExpandedJobId] = useState(() => (jobs.length > 0 ? jobs[0].id : null));
  const [selectedSkills, setSelectedSkills] = useState({});
  const [customInput, setCustomInput] = useState({});
  const [customSkills, setCustomSkills] = useState({});

  useEffect(() => {
    if (jobs.length > 0 && selectedJobIds.length === 0) {
      setSelectedJobIds(jobs.map(j => j.id));
      if (!expandedJobId) setExpandedJobId(jobs[0].id);
    }
  }, [jobs]);

  const toggleJob = (jobId) => {
    setSelectedJobIds(prev =>
      prev.includes(jobId) ? prev.filter(id => id !== jobId) : [...prev, jobId]
    );
  };

  const toggleSelectAll = () => {
    if (selectedJobIds.length === jobs.length) {
      setSelectedJobIds([]);
    } else {
      setSelectedJobIds(jobs.map(j => j.id));
    }
  };

  const toggleSkill = (jobId, skill) => {
    const current = selectedSkills[jobId] || [];
    if (current.includes(skill)) {
      setSelectedSkills(prev => ({
        ...prev,
        [jobId]: current.filter(s => s !== skill)
      }));
    } else {
      setSelectedSkills(prev => ({
        ...prev,
        [jobId]: [...current, skill]
      }));
    }
  };

  const handleAddCustomSkill = (jobId) => {
    const text = (customInput[jobId] || '').trim();
    if (!text) return;
    const lower = text.toLowerCase();
    const currentCustom = customSkills[jobId] || [];
    const jobMissing = jobs.find(j => j.id === jobId)?.missing_skills || [];
    if (!jobMissing.some(s => s.toLowerCase() === lower) && !currentCustom.some(s => s.toLowerCase() === lower)) {
      setCustomSkills(prev => ({
        ...prev,
        [jobId]: [...(prev[jobId] || []), text]
      }));
    }
    setSelectedSkills(prev => {
      const current = prev[jobId] || [];
      if (!current.some(s => s.toLowerCase() === lower)) {
        return {
          ...prev,
          [jobId]: [...current, text]
        };
      }
      return prev;
    });
    setCustomInput(prev => ({ ...prev, [jobId]: '' }));
  };

  const handleStartTailoring = () => {
    const payload = selectedJobIds.map(jobId => ({
      id: jobId,
      selected_skills: selectedSkills[jobId] || []
    }));
    onGenerate(payload);
  };

  return (
    <div className="glass-panel" style={{ padding: '32px', maxWidth: '1100px', margin: '20px auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '10px', color: '#ffffff', fontWeight: 700, fontSize: '22px' }}>
            <Sparkles size={24} color="#60a5fa" /> Review Shortlisted Jobs
          </h2>
          <p style={{ margin: '6px 0 0', color: '#cbd5e1', fontSize: '14px', maxWidth: '650px', lineHeight: 1.5 }}>
            AI scoring is complete. Select which jobs to tailor resumes for. Click any job dropdown to view its role summary and select the missing skills you possess to naturally embed them into your tailored resume.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            onClick={handleStartTailoring}
            disabled={selectedJobIds.length === 0 || isGenerating}
            className="btn-primary"
            style={{
              padding: '12px 24px',
              fontSize: '15px',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              opacity: selectedJobIds.length === 0 ? 0.5 : 1,
              cursor: selectedJobIds.length === 0 ? 'not-allowed' : 'pointer'
            }}
          >
            {isGenerating ? <Loader2 className="spin" size={18} /> : <FileSignature size={18} />}
            Generate Resumes ({selectedJobIds.length} Selected)
          </button>
        </div>
      </div>

      {/* Filter / Bulk Actions Bar */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '12px 18px',
        background: 'rgba(255, 255, 255, 0.05)',
        borderRadius: '10px',
        marginBottom: '20px',
        border: '1px solid rgba(255, 255, 255, 0.1)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', color: '#f8fafc', fontWeight: 600, fontSize: '14px' }}>
            <input
              type="checkbox"
              checked={selectedJobIds.length === jobs.length && jobs.length > 0}
              onChange={toggleSelectAll}
              style={{ cursor: 'pointer', width: '16px', height: '16px', accentColor: 'var(--primary)' }}
            />
            <span>Select All Jobs ({selectedJobIds.length}/{jobs.length})</span>
          </label>
        </div>
        <div style={{ fontSize: '13px', color: '#94a3b8' }}>
          Tip: Missing skills you check will be injected into that specific job's resume.
        </div>
      </div>

      {/* Jobs List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {jobs.map((job, idx) => {
          const isSelected = selectedJobIds.includes(job.id);
          const isExpanded = expandedJobId === job.id;
          const missingList = [...(job.missing_skills || []), ...(customSkills[job.id] || [])];
          const checkedSkillsForJob = selectedSkills[job.id] || [];

          return (
            <div
              key={job.id || idx}
              style={{
                border: isExpanded ? '1px solid rgba(96, 165, 250, 0.5)' : '1px solid rgba(255, 255, 255, 0.12)',
                borderRadius: '12px',
                background: isExpanded ? 'rgba(25, 30, 45, 0.9)' : 'rgba(20, 20, 28, 0.85)',
                overflow: 'hidden',
                transition: 'all 0.2s ease'
              }}
            >
              {/* Job Header / Dropdown toggle */}
              <div
                style={{
                  padding: '16px 20px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  cursor: 'pointer',
                  background: isExpanded ? 'rgba(255, 255, 255, 0.04)' : 'transparent',
                  borderBottom: isExpanded ? '1px solid rgba(255, 255, 255, 0.1)' : 'none',
                  gap: '16px'
                }}
                onClick={() => setExpandedJobId(isExpanded ? null : job.id)}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flex: 1, minWidth: 0 }}>
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={(e) => {
                      e.stopPropagation();
                      toggleJob(job.id);
                    }}
                    style={{
                      width: '18px',
                      height: '18px',
                      cursor: 'pointer',
                      accentColor: 'var(--primary)'
                    }}
                  />
                  <div style={{ minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                      <span style={{ fontWeight: 700, color: '#ffffff', fontSize: '15px' }}>
                        {job.title}
                      </span>
                      {job.is_testing_role && (
                        <span style={{ fontSize: '11px', background: 'rgba(59, 130, 246, 0.2)', color: '#93c5fd', padding: '2px 8px', borderRadius: '6px', fontWeight: 600 }}>
                          QA / Testing
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: '13px', color: '#cbd5e1', marginTop: '2px', fontWeight: 500, display: 'flex', gap: '8px' }}>
                      <span>{job.company}</span>
                      {job.location && <span style={{ color: '#94a3b8' }}>• {job.location}</span>}
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                  <span style={{
                    background: job.score >= 70 ? 'rgba(16, 185, 129, 0.25)' : (job.score >= 50 ? 'rgba(245, 158, 11, 0.25)' : 'rgba(239, 68, 68, 0.25)'),
                    color: job.score >= 70 ? '#34d399' : (job.score >= 50 ? '#fbbf24' : '#f87171'),
                    border: `1px solid ${job.score >= 70 ? 'rgba(16, 185, 129, 0.5)' : (job.score >= 50 ? 'rgba(245, 158, 11, 0.5)' : 'rgba(239, 68, 68, 0.5)')}`,
                    padding: '4px 12px',
                    borderRadius: '12px',
                    fontWeight: 800,
                    fontSize: '13px'
                  }}>
                    {job.score}%
                  </span>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#94a3b8', fontSize: '13px', fontWeight: 600 }}>
                    <span>{isExpanded ? 'Hide' : 'Details'}</span>
                    {isExpanded ? <ChevronUp size={18} color="#94a3b8" /> : <ChevronDown size={18} color="#94a3b8" />}
                  </div>
                </div>
              </div>

              {/* Dropdown Content */}
              {isExpanded && (
                <div style={{ padding: '20px', background: 'rgba(15, 17, 26, 0.6)' }}>
                  {/* Single Sentence Explanation of What the Job Is */}
                  <div style={{
                    padding: '14px 18px',
                    background: 'rgba(30, 58, 138, 0.2)',
                    border: '1px solid rgba(59, 130, 246, 0.35)',
                    borderRadius: '10px',
                    marginBottom: '18px'
                  }}>
                    <div style={{ fontSize: '11px', fontWeight: 800, color: '#93c5fd', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '4px' }}>
                      Job Overview (1 Sentence)
                    </div>
                    <div style={{ fontSize: '14px', color: '#f8fafc', lineHeight: 1.55, fontWeight: 500 }}>
                      {job.summary || `${job.title} position at ${job.company}.`}
                    </div>
                  </div>

                  {/* Missing Skills Section */}
                  <div style={{
                    padding: '18px',
                    background: 'rgba(255, 255, 255, 0.03)',
                    borderRadius: '10px',
                    border: '1px solid rgba(255, 255, 255, 0.08)'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
                      <div>
                        <div style={{ fontSize: '14px', fontWeight: 700, color: '#ffffff', display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span style={{ color: '#f59e0b' }}>⚡</span> Missing Skills
                        </div>
                        <div style={{ fontSize: '12px', color: '#cbd5e1', marginTop: '2px', fontWeight: 500 }}>
                          Select any skills below that you know. They will be automatically embedded into this tailored resume:
                        </div>
                      </div>
                      {checkedSkillsForJob.length > 0 && (
                        <div style={{ fontSize: '12px', color: '#34d399', fontWeight: 700, background: 'rgba(16, 185, 129, 0.15)', padding: '3px 10px', borderRadius: '8px', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
                          ✓ {checkedSkillsForJob.length} skill{checkedSkillsForJob.length > 1 ? 's' : ''} to embed
                        </div>
                      )}
                    </div>

                    {/* Checkboxes for missing skills */}
                    {missingList.length > 0 ? (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginBottom: '14px' }}>
                        {missingList.map((skill, sIdx) => {
                          const isChecked = checkedSkillsForJob.includes(skill);
                          return (
                            <label
                              key={sIdx}
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px',
                                padding: '8px 14px',
                                borderRadius: '8px',
                                cursor: 'pointer',
                                background: isChecked ? 'rgba(37, 99, 235, 0.3)' : 'rgba(255, 255, 255, 0.06)',
                                border: isChecked ? '1px solid #60a5fa' : '1px solid rgba(255, 255, 255, 0.15)',
                                color: isChecked ? '#ffffff' : '#cbd5e1',
                                fontSize: '13px',
                                fontWeight: isChecked ? 700 : 500,
                                transition: 'all 0.15s ease'
                              }}
                            >
                              <input
                                type="checkbox"
                                checked={isChecked}
                                onChange={() => toggleSkill(job.id, skill)}
                                style={{ cursor: 'pointer', accentColor: '#3b82f6', width: '15px', height: '15px' }}
                              />
                              <span>{skill}</span>
                            </label>
                          );
                        })}
                      </div>
                    ) : (
                      <div style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '12px', fontStyle: 'italic' }}>
                        No missing skills identified for this role. You can still add any custom skills you know below.
                      </div>
                    )}

                    {/* Add custom skill input */}
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center', maxWidth: '480px' }}>
                      <input
                        type="text"
                        placeholder="Add another skill you possess (e.g. Docker, Kafka, Azure)..."
                        value={customInput[job.id] || ''}
                        onChange={(e) => setCustomInput(prev => ({ ...prev, [job.id]: e.target.value }))}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            e.preventDefault();
                            handleAddCustomSkill(job.id);
                          }
                        }}
                        style={{
                          flex: 1,
                          padding: '9px 12px',
                          background: 'rgba(255, 255, 255, 0.08)',
                          border: '1px solid rgba(255, 255, 255, 0.2)',
                          borderRadius: '8px',
                          color: '#ffffff',
                          fontSize: '13px',
                          outline: 'none'
                        }}
                      />
                      <button
                        type="button"
                        onClick={() => handleAddCustomSkill(job.id)}
                        style={{
                          padding: '9px 16px',
                          background: 'rgba(255, 255, 255, 0.12)',
                          border: '1px solid rgba(255, 255, 255, 0.25)',
                          borderRadius: '8px',
                          color: '#ffffff',
                          fontSize: '13px',
                          fontWeight: 700,
                          cursor: 'pointer'
                        }}
                      >
                        + Add
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {jobs.length === 0 && (
          <div style={{ textAlign: 'center', padding: '40px', color: '#94a3b8', fontSize: '15px' }}>
            No shortlisted jobs available to review.
          </div>
        )}
      </div>

      {/* Bottom Actions */}
      <div style={{ marginTop: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid rgba(255, 255, 255, 0.1)', paddingTop: '20px' }}>
        <button
          onClick={onAbort}
          className="btn-danger"
          disabled={isAborting}
          style={{ padding: '10px 20px', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}
        >
          {isAborting ? <Loader2 className="spin" size={16} /> : <XCircle size={16} />}
          {isAborting ? 'Aborting...' : 'Abort Pipeline'}
        </button>

        <button
          onClick={handleStartTailoring}
          disabled={selectedJobIds.length === 0 || isGenerating}
          className="btn-primary"
          style={{
            padding: '12px 28px',
            fontSize: '15px',
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            opacity: selectedJobIds.length === 0 ? 0.5 : 1,
            cursor: selectedJobIds.length === 0 ? 'not-allowed' : 'pointer'
          }}
        >
          {isGenerating ? <Loader2 className="spin" size={18} /> : <FileSignature size={18} />}
          Generate Resumes ({selectedJobIds.length} Selected)
        </button>
      </div>
    </div>
  );
}

function PersistentSnapshotView({ state, onReset }) {
  const scores = state?.score?.live_scores || [];
  const tailoredResults = state?.tailor?.results || [];
  const [expandedId, setExpandedId] = useState(null);

  return (
    <div className="glass-panel snapshot-panel" style={{ padding: '32px', maxWidth: '1200px', margin: '20px auto', display: 'flex', flexDirection: 'column', height: 'calc(100vh - 80px)' }}>
      
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
           <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px', color: '#ffffff', fontWeight: 700 }}>
             <Database size={24} color="var(--primary)" /> Persistent Snapshot
           </h2>
           <p style={{ margin: '4px 0 0', color: '#cbd5e1', fontSize: '14px', fontWeight: 500 }}>
             {state.phase === 'tailoring' && 'Phase 3: Tailoring Resumes (Background)'}
             {state.phase === 'saving' && 'Phase 4: Persisting & Generating Excel (Background)'}
             {state.phase === 'done' && 'Phase 5: Complete'}
           </p>
        </div>
        
        {/* Banner for completion or status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', background: 'rgba(255, 255, 255, 0.08)', padding: '12px 24px', borderRadius: '32px', border: '1px solid rgba(255, 255, 255, 0.2)' }}>
           {state.phase === 'tailoring' && <><Loader2 className="spin" size={20} color="var(--warning)"/> <span style={{fontWeight: 700, color: '#fbbf24'}}>Tailoring Resumes...</span></>}
           {state.phase === 'saving' && <><Loader2 className="spin" size={20} color="var(--primary)"/> <span style={{fontWeight: 700, color: '#60a5fa'}}>Saving to Database...</span></>}
           {state.phase === 'done' && <><CheckCircle size={20} color="var(--success)"/> <span style={{fontWeight: 700, color: '#34d399'}}>Pipeline Complete</span></>}
        </div>
      </div>

      <div className="dashboard-modules" style={{ display: 'flex', gap: '24px', flex: 1, minHeight: 0 }}>
        
        {/* Module A: Scoring Audit */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', border: '1px solid rgba(255, 255, 255, 0.15)', borderRadius: '12px', background: 'rgba(20, 20, 28, 0.85)', overflow: 'hidden' }}>
           <div style={{ padding: '16px 20px', background: 'rgba(255, 255, 255, 0.06)', borderBottom: '1px solid rgba(255, 255, 255, 0.1)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 700, color: '#ffffff' }}>
                <BrainCircuit size={18} color="var(--primary)" /> Module A: Scoring Audit
              </div>
              <div style={{ fontSize: '12px', background: 'var(--primary)', color: '#fff', padding: '3px 10px', borderRadius: '12px', fontWeight: 700 }}>
                {scores.length} Evaluated
              </div>
           </div>
           <div style={{ flex: 1, overflowY: 'auto', padding: '0' }}>
              <table className="data-table" style={{ margin: 0, border: 'none' }}>
                <thead style={{ position: 'sticky', top: 0, background: 'rgba(25, 25, 35, 0.98)', zIndex: 1, borderBottom: '1px solid rgba(255,255,255,0.15)' }}>
                  <tr>
                    <th style={{ paddingLeft: '20px', color: '#f8fafc', fontWeight: 700 }}>Job Info</th>
                    <th style={{ textAlign: 'right', paddingRight: '20px', color: '#f8fafc', fontWeight: 700 }}>Match Score</th>
                  </tr>
                </thead>
                <tbody>
                  {scores.map((s, idx) => (
                    <React.Fragment key={idx}>
                      <tr 
                        onClick={() => setExpandedId(expandedId === idx ? null : idx)}
                        style={{ cursor: 'pointer', borderLeft: `4px solid ${s.score >= 70 ? 'var(--success)' : (s.score >= 50 ? 'var(--warning)' : 'var(--danger)')}` }}
                      >
                        <td style={{ paddingLeft: '20px' }}>
                          <div style={{ fontWeight: 700, color: '#ffffff' }}>{s.title}</div>
                          <div style={{ fontSize: '13px', color: '#cbd5e1', marginTop: '2px', fontWeight: 500 }}>{s.company}</div>
                        </td>
                        <td style={{ textAlign: 'right', fontWeight: 'bold', fontSize: '16px', paddingRight: '20px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '12px' }}>
                            <span style={{ 
                              background: s.score >= 70 ? 'rgba(16, 185, 129, 0.25)' : (s.score >= 50 ? 'rgba(245, 158, 11, 0.25)' : 'rgba(239, 68, 68, 0.25)'), 
                              color: s.score >= 70 ? '#34d399' : (s.score >= 50 ? '#fbbf24' : '#f87171'), 
                              border: `1px solid ${s.score >= 70 ? 'rgba(16, 185, 129, 0.5)' : (s.score >= 50 ? 'rgba(245, 158, 11, 0.5)' : 'rgba(239, 68, 68, 0.5)')}`,
                              padding: '4px 12px', borderRadius: '12px', fontWeight: 800 
                            }}>
                              {s.score}%
                            </span>
                            {expandedId === idx ? <ChevronUp size={16} color="#cbd5e1" /> : <ChevronDown size={16} color="#cbd5e1" />}
                          </div>
                        </td>
                      </tr>
                      {expandedId === idx && (
                        <tr>
                          <td colSpan="2" style={{ padding: '16px 20px', background: 'rgba(255, 255, 255, 0.05)', borderLeft: `4px solid ${s.score >= 70 ? 'var(--success)' : (s.score >= 50 ? 'var(--warning)' : 'var(--danger)')}`, fontSize: '14px', color: '#f8fafc', lineHeight: 1.6 }}>
                            <strong style={{ color: '#ffffff', fontWeight: 700 }}>AI Explanation:</strong> <span style={{ color: '#f1f5f9', fontWeight: 500 }}>{s.reason || 'No explanation available (cached from previous run).'}</span>
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
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', border: '1px solid rgba(255, 255, 255, 0.15)', borderRadius: '12px', background: 'rgba(20, 20, 28, 0.85)', overflow: 'hidden' }}>
           <div style={{ padding: '16px 20px', background: 'rgba(255, 255, 255, 0.06)', borderBottom: '1px solid rgba(255, 255, 255, 0.1)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 700, color: '#f8fafc' }}>
                <FileSignature size={18} color="var(--success)" /> Module B: Tailoring Audit
              </div>
              <div style={{ fontSize: '12px', background: 'var(--success)', color: '#fff', padding: '3px 10px', borderRadius: '12px', fontWeight: 700 }}>
                {state.phase === 'tailoring' ? 'Processing...' : `${tailoredResults.length} Ready`}
              </div>
           </div>
           
           {state.phase === 'tailoring' ? (
             <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'transparent' }}>
                <Loader2 className="spin" size={32} color="var(--primary)" style={{ marginBottom: '16px' }} />
                <div style={{ fontWeight: 700, color: '#f8fafc', fontSize: '16px' }}>Generating Resumes...</div>
                <div style={{ fontSize: '13px', color: '#cbd5e1', marginTop: '4px', fontWeight: 500 }}>Awaiting Phase 3 resolution</div>
             </div>
           ) : (
             <div style={{ flex: 1, overflowY: 'auto', padding: '0' }}>
                <table className="data-table" style={{ margin: 0, border: 'none' }}>
                  <thead style={{ position: 'sticky', top: 0, background: 'rgba(25, 25, 35, 0.98)', zIndex: 1, borderBottom: '1px solid rgba(255,255,255,0.15)' }}>
                    <tr>
                      <th style={{ paddingLeft: '20px', color: '#f8fafc', fontWeight: 700 }}>Job Info</th>
                      <th style={{ textAlign: 'right', paddingRight: '20px', color: '#f8fafc', fontWeight: 700 }}>Document</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tailoredResults.map((s, idx) => (
                        <tr key={idx}>
                          <td style={{ paddingLeft: '20px' }}>
                            <div style={{ fontWeight: 700, color: '#ffffff' }}>{s.title}</div>
                            <div style={{ fontSize: '13px', color: '#cbd5e1', marginTop: '2px', fontWeight: 500 }}>{s.company}</div>
                          </td>
                          <td style={{ textAlign: 'right', paddingRight: '20px' }}>
                              <button 
                                style={{ padding: '6px 16px', fontSize: '13px', background: 'var(--primary)', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 700, boxShadow: '0 2px 4px rgba(37, 99, 235, 0.2)' }}
                                onClick={() => window.open(`/api/resume/${s.id}`, '_blank')}
                              >
                                View PDF
                              </button>
                          </td>
                        </tr>
                    ))}
                    {tailoredResults.length === 0 && (
                        <tr>
                          <td colSpan="2" style={{ textAlign: 'center', padding: '36px', color: '#cbd5e1', fontWeight: 500, fontSize: '15px' }}>No resumes generated</td>
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
            style={{ marginTop: '24px', padding: '20px 24px', background: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.4)', borderRadius: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
          >
            <div>
              <h4 style={{ margin: 0, color: '#34d399', fontSize: '18px', display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 700 }}>
                <CheckCircle size={20} /> Pipeline Successfully Completed
              </h4>
              <p style={{ margin: '4px 0 0', fontSize: '14px', color: '#a7f3d0', fontWeight: 500 }}>
                {state.scan.total_found} Scraped • {state.filter.after} Evaluated • {tailoredResults.length} Resumes Generated
              </p>
            </div>
            <div style={{ display: 'flex', gap: '12px' }}>
              <button 
                style={{ padding: '10px 20px', background: 'rgba(255, 255, 255, 0.12)', color: '#ffffff', border: '1px solid rgba(255, 255, 255, 0.3)', borderRadius: '8px', cursor: 'pointer', fontWeight: 700, fontSize: '14px' }}
                onClick={onReset}
              >
                Run Again
              </button>
              <button 
                style={{ padding: '10px 20px', background: '#10b981', color: '#ffffff', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 700, fontSize: '14px', boxShadow: '0 2px 8px rgba(16, 185, 129, 0.3)' }}
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
        const res = await api('/api/status');
        const data = await res.json();
        setState(data);
      } catch (e) {
        console.error('Status fetch error', e);
      }
    };
    fetchStatus();

    const eventSource = new EventSource(import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/stream` : '/api/stream');
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

  const handleStart = async (platforms, testMode, aiSettings = {}, jobTypes = ['fulltime', 'internship']) => {
    try {
      setError('');
      const endpoint = testMode ? '/api/test-start' : '/api/start';
      const res = await api(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          platforms, 
          job_types: jobTypes,
          dry_run: false,
          scoring_model: aiSettings.scoringModel,
          scoring_thinking: aiSettings.scoringThinking,
          tailoring_model: aiSettings.tailoringModel,
          tailoring_thinking: aiSettings.tailoringThinking,
        }),
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

  const [isGenerating, setIsGenerating] = useState(false);
  const [isAborting, setIsAborting] = useState(false);

  const handleGenerateResumes = async (selectedJobsPayload) => {
    setIsGenerating(true);
    try {
      setError('');
      const res = await api('/api/generate-resumes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selected_jobs: selectedJobsPayload })
      });
      if (!res.ok) {
        const data = await res.json();
        setError(data.error || 'Failed to start resume generation');
      } else {
        setState(prev => ({
          ...prev,
          phase: 'tailoring',
          status_text: 'Tailoring resumes with your selected skills...'
        }));
      }
    } catch (err) {
      setError('Connection failed. Is the backend running?');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleAbort = async () => {
    setIsAborting(true);
    try {
      setState(prev => ({
        ...prev,
        running: false,
        phase: 'idle',
        status_text: 'Aborted by user.',
        shortlisted_jobs: [],
      }));
      await api('/api/stop', { method: 'POST' });
    } catch (err) {
      console.error('Failed to abort', err);
    } finally {
      setIsAborting(false);
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
          {state.phase === 'review' && (
            <ReviewView 
              state={state} 
              onGenerate={handleGenerateResumes} 
              onAbort={handleAbort} 
              isGenerating={isGenerating} 
              isAborting={isAborting}
            />
          )}
          {['tailoring', 'saving', 'done'].includes(state.phase) && <PersistentSnapshotView state={state} onReset={handleAbort} />}
        </motion.div>
      </AnimatePresence>

      {state.phase !== 'idle' && state.phase !== 'done' && state.phase !== 'review' && (
        <div style={{ position: 'fixed', bottom: '32px', left: '50%', transform: 'translateX(-50%)', zIndex: 9999 }}>
          <button onClick={handleAbort} className="btn-danger" disabled={isAborting} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {isAborting ? <Loader2 className="spin" size={16} /> : <XCircle size={16} />}
            {isAborting ? 'Aborting...' : 'Abort Pipeline'}
          </button>
        </div>
      )}
    </div>
  );
}
