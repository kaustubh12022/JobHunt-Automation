import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, FileText, CheckCircle2, Link as LinkIcon, RotateCcw, Download, Briefcase, Building2, Check, ArrowRight, Plus, ListChecks } from 'lucide-react';

export default function ManualTailor() {
  const [jobs, setJobs] = useState([]);
  
  // Form state
  const [jobTitle, setJobTitle] = useState('');
  const [company, setCompany] = useState('');
  const [jobLink, setJobLink] = useState('');
  const [jobDescription, setJobDescription] = useState('');
  const [formError, setFormError] = useState(null);

  // Active job for review
  const [activeJobId, setActiveJobId] = useState(null);
  
  const [isScoringAll, setIsScoringAll] = useState(false);

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
      status: 'pending', // pending | scoring | scored | generating | result | error
      scoreData: null,
      selectedSkills: [],
      pdfUrl: null,
      error: null
    };
    
    setJobs(prev => [...prev, newJob]);
    
    // Reset form
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
    
    // Mark them as scoring
    setJobs(prev => prev.map(j => 
      (j.status === 'pending' || j.status === 'error') ? { ...j, status: 'scoring', error: null } : j
    ));

    // We can process them in parallel
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
      <div style={{ marginBottom: '32px' }}>
        <h1 style={{ fontSize: '28px', fontWeight: 800, margin: '0 0 8px 0', background: 'linear-gradient(90deg, #fff, #94a3b8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
          Batch AI Resume Tailor
        </h1>
        <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '15px' }}>
          Queue multiple job descriptions, score them at once, and generate tailored resumes individually.
        </p>
      </div>

      <div style={{ flex: 1, display: 'flex', gap: '32px', height: '100%' }}>
        
        {/* LEFT COLUMN: Input Form or Active Job Review */}
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

        {/* RIGHT COLUMN: Queue */}
        <div className="glass-panel" style={{ flex: 1, padding: '32px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 style={{ fontSize: '20px', margin: 0, color: 'white', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ListChecks size={22} className="text-cyan" /> Job Queue ({jobs.length})
            </h2>
            <button 
              onClick={handleScoreAll} 
              disabled={isScoringAll || jobs.filter(j => j.status === 'pending' || j.status === 'error').length === 0}
              style={{ background: 'var(--cyan)', color: '#000', padding: '10px 20px', borderRadius: '8px', fontWeight: 'bold', fontSize: '14px', border: 'none', cursor: 'pointer', opacity: (isScoringAll || jobs.filter(j => j.status === 'pending' || j.status === 'error').length === 0) ? 0.5 : 1 }}
            >
              {isScoringAll ? 'Scoring...' : 'Score All Pending'}
            </button>
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
    </div>
  );
}
