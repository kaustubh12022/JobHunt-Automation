import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, FileText, CheckCircle2, Link as LinkIcon, RotateCcw, Download, Briefcase, Building2, Check, ArrowRight, Plus, ListChecks, ExternalLink, AlertTriangle, Play, RefreshCw } from 'lucide-react';

export default function ManualTailor() {
  const [activeTab, setActiveTab] = useState('batch_urls'); // 'batch_urls' | 'single_manual'

  // Batch URLs State
  const [batchRawText, setBatchRawText] = useState('');
  const [minScoreThreshold, setMinScoreThreshold] = useState(60);
  const [isProcessingBatch, setIsProcessingBatch] = useState(false);
  const [batchResult, setBatchResult] = useState(null);
  const [batchError, setBatchError] = useState(null);

  // Single Job Manual Form State
  const [jobs, setJobs] = useState([]);
  const [jobTitle, setJobTitle] = useState('');
  const [company, setCompany] = useState('');
  const [jobLink, setJobLink] = useState('');
  const [jobDescription, setJobDescription] = useState('');
  const [formError, setFormError] = useState(null);
  const [activeJobId, setActiveJobId] = useState(null);
  const [isScoringAll, setIsScoringAll] = useState(false);
  const [isGeneratingAll, setIsGeneratingAll] = useState(false);

  // Handle Batch URLs Process
  const handleProcessBatch = async () => {
    if (!batchRawText.trim()) {
      setBatchError("Please paste at least one URL or a job broadcast message.");
      return;
    }
    setBatchError(null);
    setIsProcessingBatch(true);
    setBatchResult(null);

    try {
      const res = await fetch('/api/batch-urls/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: batchRawText,
          min_score: Number(minScoreThreshold) || 60
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to process batch URLs");
      setBatchResult(data);
    } catch (err) {
      setBatchError(err.message);
    } finally {
      setIsProcessingBatch(false);
    }
  };

  const handleAddJob = () => {
    if (!jobDescription.trim()) {
      setFormError("Job Description is required");
      return;
    }
    setFormError(null);
    
    const newJob = {
      id: Date.now().toString(),
      jobTitle,
      company,
      jobLink,
      jobDescription,
      status: 'pending',
      scoreData: null,
      selectedSkills: [],
      pdfUrl: null,
      error: null
    };
    
    setJobs(prev => [...prev, newJob]);
    setJobTitle('');
    setCompany('');
    setJobLink('');
    setJobDescription('');
  };

  const removeJob = (id) => {
    setJobs(prev => prev.filter(j => j.id !== id));
    if (activeJobId === id) setActiveJobId(null);
  };

  const handleScoreAll = async () => {
    setIsScoringAll(true);
    const pendingJobs = jobs.filter(j => j.status === 'pending' || j.status === 'error');
    setJobs(prev => prev.map(j => 
      (j.status === 'pending' || j.status === 'error') ? { ...j, status: 'scoring', error: null } : j
    ));

    await Promise.all(pendingJobs.map(async (job) => {
      try {
        const res = await fetch('/api/manual-tailor/score', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            job_title: job.jobTitle,
            company: job.company,
            job_description: job.jobDescription
          })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Failed to score job");
        setJobs(prev => prev.map(j => 
          j.id === job.id ? { ...j, status: 'scored', scoreData: data, selectedSkills: [] } : j
        ));
      } catch (err) {
        setJobs(prev => prev.map(j => 
          j.id === job.id ? { ...j, status: 'error', error: err.message } : j
        ));
      }
    }));
    setIsScoringAll(false);
  };

  const handleGenerateAll = async () => {
    setIsGeneratingAll(true);
    const jobsToGenerate = jobs.filter(j => j.status === 'scored');
    setJobs(prev => prev.map(j => 
      j.status === 'scored' ? { ...j, status: 'generating', error: null } : j
    ));

    try {
      const payload = {
        jobs: jobsToGenerate.map(job => ({
          id: job.id,
          job_title: job.jobTitle,
          company: job.company,
          url: job.jobLink,
          job_description: job.jobDescription,
          score: job.scoreData.score,
          missing_skills: job.scoreData.missing_skills,
          extracted_requirements: job.scoreData.extracted_requirements,
          is_testing_role: job.scoreData.is_testing_role,
          selected_skills: job.selectedSkills
        }))
      };

      const res = await fetch('/api/manual-tailor/generate-batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to generate resumes in batch");
      
      data.results.forEach(result => {
        setJobs(prev => prev.map(j => {
          if (j.id === result.id) {
            if (result.error) {
              return { ...j, status: 'scored', error: result.error };
            }
            return { ...j, status: 'result', pdfUrl: result.pdf_url };
          }
          return j;
        }));
      });
    } catch (err) {
      setJobs(prev => prev.map(j => 
        jobsToGenerate.find(g => g.id === j.id) ? { ...j, status: 'scored', error: err.message } : j
      ));
    }
    setIsGeneratingAll(false);
  };

  const handleSkillToggle = (jobId, skill) => {
    setJobs(prev => prev.map(j => {
      if (j.id === jobId) {
        const hasSkill = j.selectedSkills.includes(skill);
        return {
          ...j,
          selectedSkills: hasSkill ? j.selectedSkills.filter(s => s !== skill) : [...j.selectedSkills, skill]
        };
      }
      return j;
    }));
  };

  const handleGenerate = async (jobId) => {
    const job = jobs.find(j => j.id === jobId);
    if (!job) return;
    setJobs(prev => prev.map(j => j.id === jobId ? { ...j, status: 'generating', error: null } : j));
    
    try {
      const res = await fetch('/api/manual-tailor/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: job.id,
          job_title: job.jobTitle,
          company: job.company,
          url: job.jobLink,
          job_description: job.jobDescription,
          score: job.scoreData.score,
          missing_skills: job.scoreData.missing_skills,
          extracted_requirements: job.scoreData.extracted_requirements,
          is_testing_role: job.scoreData.is_testing_role,
          selected_skills: job.selectedSkills
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to generate resume");
      setJobs(prev => prev.map(j => j.id === jobId ? { ...j, status: 'result', pdfUrl: data.pdf_url } : j));
    } catch (err) {
      setJobs(prev => prev.map(j => j.id === jobId ? { ...j, status: 'scored', error: err.message } : j));
    }
  };

  const activeJob = jobs.find(j => j.id === activeJobId);

  return (
    <div style={{ padding: '32px 24px', maxWidth: '1600px', margin: '0 auto', minHeight: 'calc(100vh - 70px)', display: 'flex', flexDirection: 'column' }}>
      
      {/* Header */}
      <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h1 style={{ fontSize: '28px', fontWeight: 800, margin: '0 0 8px 0', background: 'linear-gradient(90deg, #fff, #94a3b8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            Batch AI Resume Tailor
          </h1>
          <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '15px' }}>
            Paste job broadcast links directly or queue custom job descriptions for automated ATS-compliant resume generation.
          </p>
        </div>

        {/* Tab Navigation */}
        <div style={{ display: 'flex', background: 'rgba(0,0,0,0.3)', padding: '4px', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
          <button
            onClick={() => setActiveTab('batch_urls')}
            style={{
              padding: '8px 18px',
              borderRadius: '8px',
              border: 'none',
              fontSize: '14px',
              fontWeight: 600,
              cursor: 'pointer',
              background: activeTab === 'batch_urls' ? 'var(--cyan)' : 'transparent',
              color: activeTab === 'batch_urls' ? '#000' : 'var(--text-muted)',
              transition: 'all 0.2s'
            }}
          >
            ⚡ Paste Batch URLs (Automated)
          </button>
          <button
            onClick={() => setActiveTab('single_manual')}
            style={{
              padding: '8px 18px',
              borderRadius: '8px',
              border: 'none',
              fontSize: '14px',
              fontWeight: 600,
              cursor: 'pointer',
              background: activeTab === 'single_manual' ? 'var(--cyan)' : 'transparent',
              color: activeTab === 'single_manual' ? '#000' : 'var(--text-muted)',
              transition: 'all 0.2s'
            }}
          >
            📝 Single Job Manual Form
          </button>
        </div>
      </div>

      {/* TAB 1: BATCH URLS AUTOMATED PIPELINE */}
      {activeTab === 'batch_urls' && (
        <div style={{ display: 'flex', gap: '32px', flex: 1 }}>
          
          {/* Left: Input Box */}
          <div className="glass-panel" style={{ flex: '0 0 520px', padding: '32px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <h2 style={{ fontSize: '18px', margin: 0, color: 'white', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <LinkIcon size={20} className="text-cyan" /> Paste Job URLs / Broadcast
            </h2>
            <p style={{ margin: 0, fontSize: '13px', color: 'var(--text-muted)' }}>
              Paste Telegram/WhatsApp job alerts or direct links. The pipeline extracts JDs, runs DeepSeek AI scoring, auto-weaves skills without manual checkboxes, and generates 1-page resumes for jobs scoring &ge; 60%.
            </p>

            {batchError && (
              <div style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#fca5a5', padding: '12px', borderRadius: '8px', border: '1px solid rgba(239,68,68,0.3)', fontSize: '14px' }}>
                {batchError}
              </div>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
              <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', color: 'var(--text-muted)' }}>
                Job Links or Message Text <span style={{ color: '#ef4444' }}>*</span>
              </label>
              <textarea
                value={batchRawText}
                onChange={e => setBatchRawText(e.target.value)}
                style={{
                  width: '100%',
                  flex: 1,
                  minHeight: '260px',
                  padding: '14px',
                  background: 'rgba(0,0,0,0.25)',
                  border: '1px solid var(--border-color)',
                  color: 'white',
                  borderRadius: '8px',
                  resize: 'none',
                  fontSize: '13.5px',
                  lineHeight: '1.5',
                  outline: 'none',
                  fontFamily: 'monospace'
                }}
                placeholder="Paste links or WhatsApp message here, e.g.:&#10;&#10;Wipro Recruitment 2026 Freshers&#10;https://freshersrecruitment.co.in/wipro-recruitment-2026-freshers/&#10;&#10;Honeywell Hiring 2026 Opportunity&#10;https://freshersrecruitment.co.in/honeywell-hiring-2026-opportunity/"
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'rgba(0,0,0,0.2)', padding: '12px 16px', borderRadius: '8px' }}>
              <div>
                <label style={{ fontSize: '13px', color: 'white', fontWeight: 600, display: 'block' }}>Minimum AI Match Score</label>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Only score &ge; threshold gets a resume</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={minScoreThreshold}
                  onChange={e => setMinScoreThreshold(e.target.value)}
                  style={{ width: '60px', padding: '6px 10px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)', color: 'var(--cyan)', borderRadius: '6px', textAlign: 'center', fontWeight: 'bold' }}
                />
                <span style={{ color: 'var(--text-muted)' }}>%</span>
              </div>
            </div>

            <button
              onClick={handleProcessBatch}
              disabled={isProcessingBatch}
              style={{
                background: isProcessingBatch ? 'rgba(34, 211, 238, 0.3)' : 'var(--cyan)',
                color: '#000',
                padding: '14px',
                borderRadius: '8px',
                fontWeight: 'bold',
                fontSize: '15px',
                border: 'none',
                cursor: isProcessingBatch ? 'not-allowed' : 'pointer',
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              {isProcessingBatch ? (
                <>
                  <RefreshCw size={18} className="animate-spin" /> Processing Batch (Extracting & Scoring)...
                </>
              ) : (
                <>
                  <Play size={18} /> Extract, Score & Tailor Resumes
                </>
              )}
            </button>
          </div>

          {/* Right: Results Dashboard */}
          <div className="glass-panel" style={{ flex: 1, padding: '32px', display: 'flex', flexDirection: 'column', gap: '20px', overflowY: 'auto' }}>
            {!batchResult && !isProcessingBatch && (
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '16px', color: 'var(--text-muted)' }}>
                <Briefcase size={48} opacity={0.3} />
                <h3 style={{ margin: 0, color: 'white', fontSize: '18px' }}>Batch Pipeline Ready</h3>
                <p style={{ margin: 0, textAlign: 'center', maxWidth: '450px', fontSize: '14px' }}>
                  Paste your broadcast message or job links on the left and click "Extract, Score & Tailor Resumes".
                  Resumes and Summary.pdf will be generated and saved directly to your Desktop.
                </p>
              </div>
            )}

            {isProcessingBatch && (
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '16px' }}>
                <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1.5, ease: "linear" }} style={{ color: 'var(--cyan)' }}>
                  <RefreshCw size={44} />
                </motion.div>
                <h3 style={{ color: 'white', margin: 0 }}>Automated Pipeline In Progress...</h3>
                <p style={{ color: 'var(--text-muted)', fontSize: '14px', textAlign: 'center', maxWidth: '400px' }}>
                  Extracting JDs, running DeepSeek AI scoring, auto-injecting candidate skills, and rendering 1-page ATS resumes...
                </p>
              </div>
            )}

            {batchResult && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                
                {/* KPI Cards */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
                  <div style={{ background: 'rgba(0,0,0,0.2)', padding: '16px', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
                    <div style={{ fontSize: '24px', fontWeight: 800, color: 'white' }}>{batchResult.total_urls}</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>LINKS ANALYZED</div>
                  </div>
                  <div style={{ background: 'rgba(16, 185, 129, 0.1)', padding: '16px', borderRadius: '10px', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
                    <div style={{ fontSize: '24px', fontWeight: 800, color: '#10b981' }}>{batchResult.shortlisted_jobs?.length || 0}</div>
                    <div style={{ fontSize: '12px', color: '#10b981' }}>RESUMES GENERATED (&ge;{minScoreThreshold}%)</div>
                  </div>
                  <div style={{ background: 'rgba(245, 158, 11, 0.1)', padding: '16px', borderRadius: '10px', border: '1px solid rgba(245, 158, 11, 0.3)' }}>
                    <div style={{ fontSize: '24px', fontWeight: 800, color: '#f59e0b' }}>{batchResult.low_score_jobs?.length || 0}</div>
                    <div style={{ fontSize: '12px', color: '#f59e0b' }}>LOW RELEVANCE (&lt;{minScoreThreshold}%)</div>
                  </div>
                  <div style={{ background: 'rgba(239, 68, 68, 0.1)', padding: '16px', borderRadius: '10px', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
                    <div style={{ fontSize: '24px', fontWeight: 800, color: '#ef4444' }}>{batchResult.failed_links?.length || 0}</div>
                    <div style={{ fontSize: '12px', color: '#ef4444' }}>FAILED / CATEGORY</div>
                  </div>
                </div>

                {/* Output Desktop Path Notification */}
                <div style={{ background: 'rgba(34, 211, 238, 0.1)', border: '1px solid rgba(34, 211, 238, 0.3)', padding: '14px 18px', borderRadius: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <span style={{ color: 'var(--cyan)', fontWeight: 600, fontSize: '14px' }}>📁 Saved Directly to Desktop: </span>
                    <span style={{ color: 'white', fontSize: '13px', fontFamily: 'monospace' }}>{batchResult.desktop_folder}</span>
                  </div>
                </div>

                {/* Shortlisted Jobs Section */}
                <div>
                  <h3 style={{ fontSize: '16px', color: 'white', margin: '0 0 12px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <CheckCircle2 size={18} color="#10b981" /> Shortlisted Roles & Tailored Resumes ({batchResult.shortlisted_jobs?.length || 0})
                  </h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {batchResult.shortlisted_jobs?.map((job, idx) => (
                      <div key={idx} style={{ background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-color)', padding: '16px', borderRadius: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <h4 style={{ margin: 0, color: 'white', fontSize: '15px' }}>{job.role}</h4>
                            <span style={{ background: '#10b981', color: '#000', fontSize: '11px', fontWeight: 800, padding: '2px 8px', borderRadius: '12px' }}>
                              {job.score}% MATCH
                            </span>
                          </div>
                          <div style={{ color: 'var(--text-muted)', fontSize: '13px', marginTop: '4px', display: 'flex', gap: '12px' }}>
                            <span>🏢 {job.company}</span>
                            <span>📄 {job.filename}</span>
                          </div>
                        </div>
                        <div style={{ display: 'flex', gap: '10px' }}>
                          {job.apply_link && (
                            <a href={job.apply_link} target="_blank" rel="noreferrer" style={{ background: 'rgba(255,255,255,0.1)', color: 'white', padding: '8px 14px', borderRadius: '8px', textDecoration: 'none', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                              Apply Now <ExternalLink size={14} />
                            </a>
                          )}
                        </div>
                      </div>
                    ))}
                    {(!batchResult.shortlisted_jobs || batchResult.shortlisted_jobs.length === 0) && (
                      <div style={{ color: 'var(--text-muted)', fontSize: '14px', padding: '12px' }}>
                        No roles met the &ge; {minScoreThreshold}% score threshold.
                      </div>
                    )}
                  </div>
                </div>

                {/* Low Score Roles Section */}
                {batchResult.low_score_jobs?.length > 0 && (
                  <div>
                    <h3 style={{ fontSize: '15px', color: '#f59e0b', margin: '0 0 10px 0' }}>
                      🔍 Filtered Roles (Score &lt; {minScoreThreshold}% – No Resume Generated)
                    </h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {batchResult.low_score_jobs.map((job, idx) => (
                        <div key={idx} style={{ background: 'rgba(0,0,0,0.15)', padding: '12px 16px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div>
                            <span style={{ color: 'white', fontWeight: 600, fontSize: '14px' }}>{job.company}</span>
                            <span style={{ color: 'var(--text-muted)', fontSize: '13px' }}> — {job.role}</span>
                            <p style={{ margin: '4px 0 0 0', color: 'var(--text-muted)', fontSize: '12px' }}>{job.reason}</p>
                          </div>
                          <span style={{ color: '#f59e0b', fontWeight: 700, fontSize: '14px' }}>{job.score}%</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Failed / Category Links Section */}
                {batchResult.failed_links?.length > 0 && (
                  <div>
                    <h3 style={{ fontSize: '15px', color: '#ef4444', margin: '0 0 10px 0', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <AlertTriangle size={16} /> Attention Required: Category / Inaccessible Links ({batchResult.failed_links.length})
                    </h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {batchResult.failed_links.map((fl, idx) => (
                        <div key={idx} style={{ background: 'rgba(239, 68, 68, 0.08)', padding: '12px 16px', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.2)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div style={{ maxWidth: '80%' }}>
                            <div style={{ color: 'white', fontWeight: 600, fontSize: '13.5px' }}>{fl.company} – {fl.title}</div>
                            <div style={{ color: '#fca5a5', fontSize: '12px', marginTop: '2px' }}>{fl.error_reason}</div>
                            <a href={fl.url} target="_blank" rel="noreferrer" style={{ color: 'var(--cyan)', fontSize: '12px', wordBreak: 'break-all' }}>{fl.url}</a>
                          </div>
                          <button
                            onClick={() => {
                              setActiveTab('single_manual');
                              setJobLink(fl.url);
                              setJobTitle(fl.title || '');
                              setCompany(fl.company || '');
                            }}
                            style={{ background: 'rgba(255,255,255,0.1)', color: 'white', padding: '6px 12px', borderRadius: '6px', border: 'none', fontSize: '12px', cursor: 'pointer' }}
                          >
                            Paste JD Manually &rarr;
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

              </div>
            )}
          </div>

        </div>
      )}

      {/* TAB 2: SINGLE JOB MANUAL FORM (EXISTING FLOW PRESERVED) */}
      {activeTab === 'single_manual' && (
        <div style={{ flex: 1, display: 'flex', gap: '32px', height: '100%' }}>
          {/* Left Column: Form / Active Job Review */}
          <div style={{ flex: '0 0 500px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
            <AnimatePresence mode="wait">
              {!activeJob ? (
                <motion.div key="form" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="glass-panel" style={{ padding: '32px', flex: 1, display: 'flex', flexDirection: 'column', gap: '20px' }}>
                  <h2 style={{ fontSize: '18px', margin: 0, color: 'white', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Plus size={20} className="text-cyan" /> Add to Queue
                  </h2>
                  
                  {formError && (
                    <div style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#fca5a5', padding: '12px', borderRadius: '8px', border: '1px solid rgba(239,68,68,0.3)', fontSize: '14px' }}>
                      {formError}
                    </div>
                  )}

                  <div style={{ display: 'flex', gap: '16px' }}>
                    <div style={{ flex: 1 }}>
                      <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', color: 'var(--text-muted)' }}>Job Title (Optional)</label>
                      <input type="text" value={jobTitle} onChange={e => setJobTitle(e.target.value)} style={{ width: '100%', padding: '10px 14px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-color)', color: 'white', borderRadius: '8px', fontSize: '14px', outline: 'none' }} placeholder="e.g. Frontend Engineer" />
                    </div>
                    <div style={{ flex: 1 }}>
                      <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', color: 'var(--text-muted)' }}>Company (Optional)</label>
                      <input type="text" value={company} onChange={e => setCompany(e.target.value)} style={{ width: '100%', padding: '10px 14px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-color)', color: 'white', borderRadius: '8px', fontSize: '14px', outline: 'none' }} placeholder="e.g. OpenAI" />
                    </div>
                  </div>

                  <div>
                    <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', color: 'var(--text-muted)' }}>Job Link / Apply Link</label>
                    <input type="text" value={jobLink} onChange={e => setJobLink(e.target.value)} style={{ width: '100%', padding: '10px 14px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-color)', color: 'white', borderRadius: '8px', fontSize: '14px', outline: 'none' }} placeholder="https://..." />
                  </div>
                  
                  <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                    <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', color: 'var(--text-muted)' }}>Job Description <span style={{ color: '#ef4444' }}>*</span></label>
                    <textarea value={jobDescription} onChange={e => setJobDescription(e.target.value)} style={{ width: '100%', flex: 1, minHeight: '150px', padding: '12px 14px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-color)', color: 'white', borderRadius: '8px', resize: 'none', fontSize: '14px', outline: 'none' }} placeholder="Paste the JD here..." />
                  </div>
                  
                  <button onClick={handleAddJob} style={{ background: 'var(--cyan)', color: '#000', padding: '14px', borderRadius: '8px', fontWeight: 'bold', fontSize: '15px', border: 'none', cursor: 'pointer', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px' }}>
                    <Plus size={18} /> Add Job to Queue
                  </button>
                </motion.div>
              ) : (
                <motion.div key="review" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="glass-panel" style={{ padding: '32px', flex: 1, display: 'flex', flexDirection: 'column', gap: '20px', overflowY: 'auto' }}>
                  <button onClick={() => setActiveJobId(null)} style={{ alignSelf: 'flex-start', background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', padding: 0 }}>
                    <RotateCcw size={16} /> Back to Add Form
                  </button>

                  <h2 style={{ fontSize: '20px', margin: '8px 0', color: 'white' }}>
                    {activeJob.jobTitle || 'Unknown Role'} @ {activeJob.company || 'Unknown'}
                  </h2>

                  {activeJob.status === 'scored' && activeJob.scoreData && (
                    <>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', background: 'rgba(0,0,0,0.2)', padding: '16px', borderRadius: '12px' }}>
                        <div style={{ fontSize: '36px', fontWeight: 800, color: activeJob.scoreData.score >= 70 ? '#10b981' : activeJob.scoreData.score >= 50 ? '#f59e0b' : '#ef4444' }}>
                          {activeJob.scoreData.score}%
                        </div>
                        <p style={{ margin: 0, fontSize: '14px', color: 'var(--text-muted)' }}>{activeJob.scoreData.reason}</p>
                      </div>

                      <div>
                        <h3 style={{ fontSize: '15px', margin: '0 0 8px 0', color: 'white' }}>Missing Skills (Select to inject)</h3>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                          {activeJob.scoreData.missing_skills?.map((skill, idx) => (
                            <div key={idx} onClick={() => handleSkillToggle(activeJob.id, skill)} style={{ padding: '8px 12px', background: activeJob.selectedSkills.includes(skill) ? 'rgba(34, 211, 238, 0.15)' : 'rgba(0,0,0,0.2)', border: activeJob.selectedSkills.includes(skill) ? '1px solid var(--cyan)' : '1px solid var(--border-color)', borderRadius: '8px', fontSize: '13px', color: activeJob.selectedSkills.includes(skill) ? 'white' : 'var(--text-main)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}>
                              {activeJob.selectedSkills.includes(skill) && <Check size={14} className="text-cyan" />}
                              {skill}
                            </div>
                          ))}
                          {(!activeJob.scoreData.missing_skills || activeJob.scoreData.missing_skills.length === 0) && (
                            <div style={{ width: '100%', padding: '16px', background: 'rgba(16, 185, 129, 0.1)', color: '#10b981', borderRadius: '8px', textAlign: 'center', border: '1px solid rgba(16,185,129,0.2)' }}>
                              ✨ No missing skills!
                            </div>
                          )}
                        </div>
                      </div>

                      <button onClick={() => handleGenerate(activeJob.id)} style={{ background: 'linear-gradient(135deg, var(--cyan), #3b82f6)', color: '#000', padding: '14px', borderRadius: '8px', fontWeight: 'bold', fontSize: '15px', border: 'none', cursor: 'pointer', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px', marginTop: 'auto' }}>
                        Generate Resume <ArrowRight size={18} />
                      </button>
                    </>
                  )}

                  {activeJob.status === 'generating' && (
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '16px' }}>
                      <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 2, ease: "linear" }} style={{ color: 'var(--cyan)' }}>
                        <FileText size={40} />
                      </motion.div>
                      <p style={{ color: 'var(--text-muted)' }}>Generating tailored resume...</p>
                    </div>
                  )}

                  {activeJob.status === 'result' && (
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '16px' }}>
                      <CheckCircle2 size={48} color="#10b981" />
                      <h3 style={{ color: 'white', margin: 0 }}>Resume Generated!</h3>
                      <a href={activeJob.pdfUrl} target="_blank" rel="noreferrer" style={{ background: 'rgba(255,255,255,0.1)', color: 'white', padding: '10px 16px', borderRadius: '8px', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <Download size={16} /> View/Download PDF
                      </a>
                    </div>
                  )}
                  
                  {activeJob.error && (
                    <div style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#fca5a5', padding: '12px', borderRadius: '8px' }}>
                      Error: {activeJob.error}
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Right Column: Queue */}
          <div className="glass-panel" style={{ flex: 1, padding: '32px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h2 style={{ fontSize: '20px', margin: 0, color: 'white', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <ListChecks size={22} className="text-cyan" /> Job Queue ({jobs.length})
              </h2>
              <div style={{ display: 'flex', gap: '12px' }}>
                <button 
                  onClick={handleScoreAll} 
                  disabled={isScoringAll || jobs.filter(j => j.status === 'pending' || j.status === 'error').length === 0}
                  style={{ background: 'var(--cyan)', color: '#000', padding: '10px 20px', borderRadius: '8px', fontWeight: 'bold', fontSize: '14px', border: 'none', cursor: 'pointer', opacity: (isScoringAll || jobs.filter(j => j.status === 'pending' || j.status === 'error').length === 0) ? 0.5 : 1 }}
                >
                  {isScoringAll ? 'Scoring...' : 'Score All Pending'}
                </button>
                <button 
                  onClick={handleGenerateAll} 
                  disabled={isGeneratingAll || jobs.filter(j => j.status === 'scored').length === 0}
                  style={{ background: 'linear-gradient(135deg, var(--cyan), #3b82f6)', color: '#000', padding: '10px 20px', borderRadius: '8px', fontWeight: 'bold', fontSize: '14px', border: 'none', cursor: 'pointer', opacity: (isGeneratingAll || jobs.filter(j => j.status === 'scored').length === 0) ? 0.5 : 1 }}
                >
                  {isGeneratingAll ? 'Generating...' : 'Generate All Scored'}
                </button>
              </div>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '12px', paddingRight: '4px' }}>
              {jobs.length === 0 ? (
                <div style={{ textAlign: 'center', color: 'var(--text-muted)', marginTop: '40px' }}>
                  No jobs in queue. Add some from the left panel.
                </div>
              ) : (
                jobs.map((job) => (
                  <div key={job.id} 
                       onClick={() => (job.status === 'scored' || job.status === 'generating' || job.status === 'result') && setActiveJobId(job.id)}
                       style={{ background: activeJobId === job.id ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.2)', border: activeJobId === job.id ? '1px solid var(--cyan)' : '1px solid var(--border-color)', padding: '16px', borderRadius: '12px', cursor: (job.status === 'scored' || job.status === 'generating' || job.status === 'result' || job.error) ? 'pointer' : 'default', transition: 'all 0.2s', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    
                    <div>
                      <h4 style={{ margin: '0 0 4px 0', color: 'white', fontSize: '16px' }}>{job.jobTitle || 'Unknown Role'}</h4>
                      <div style={{ display: 'flex', gap: '12px', color: 'var(--text-muted)', fontSize: '13px' }}>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><Building2 size={12} /> {job.company || 'Unknown Company'}</span>
                        {job.jobLink && <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><LinkIcon size={12} /> Has Link</span>}
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                      {job.status === 'pending' && <span style={{ color: 'var(--text-muted)', fontSize: '13px' }}>Pending</span>}
                      {job.status === 'scoring' && <motion.span animate={{ opacity: [0.5, 1, 0.5] }} transition={{ repeat: Infinity }} style={{ color: 'var(--cyan)', fontSize: '13px' }}>Scoring...</motion.span>}
                      {job.status === 'scored' && <span style={{ color: '#f59e0b', fontSize: '13px', fontWeight: 'bold' }}>Review & Gen</span>}
                      {job.status === 'generating' && <span style={{ color: 'var(--cyan)', fontSize: '13px' }}>Generating...</span>}
                      {job.status === 'result' && <span style={{ color: '#10b981', fontSize: '13px', fontWeight: 'bold' }}>Done</span>}
                      {job.error && <span style={{ color: '#ef4444', fontSize: '13px' }}>Error</span>}
                      
                      <button onClick={(e) => { e.stopPropagation(); removeJob(job.id); }} style={{ background: 'transparent', border: 'none', color: '#ef4444', cursor: 'pointer', padding: '4px', opacity: 0.7 }}>
                        ×
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
