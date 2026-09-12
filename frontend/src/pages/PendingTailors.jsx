import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FileText, ChevronDown, ChevronUp, Check, Download, BrainCircuit } from 'lucide-react';
import { api } from '../lib/api';

export default function PendingTailors() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedJobId, setExpandedJobId] = useState(null);
  const [selectedSkills, setSelectedSkills] = useState({});
  const [generating, setGenerating] = useState({});
  const [generatedPdf, setGeneratedPdf] = useState({});

  useEffect(() => {
    fetchPendingJobs();
  }, []);

  const fetchPendingJobs = async () => {
    try {
      const res = await api('/api/pending-tailors');
      const data = await res.json();
      setJobs(data);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const toggleJob = (jobId) => {
    setExpandedJobId(prev => (prev === jobId ? null : jobId));
  };

  const toggleSkill = (jobId, skill) => {
    setSelectedSkills(prev => {
      const jobSkills = prev[jobId] || [];
      if (jobSkills.includes(skill)) {
        return { ...prev, [jobId]: jobSkills.filter(s => s !== skill) };
      } else {
        return { ...prev, [jobId]: [...jobSkills, skill] };
      }
    });
  };

  const handleGenerate = async (job) => {
    setGenerating(prev => ({ ...prev, [job.id]: true }));
    try {
      const res = await api('/api/manual-tailor/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: job.id, run_id: job.run_id, url: job.url, job_title: job.title,
          company: job.company,
          job_description: job.description,
          score: job.score,
          missing_skills: job.missing_skills,
          extracted_requirements: job.extracted_requirements,
          is_testing_role: job.is_testing_role,
          selected_skills: selectedSkills[job.id] || []
        })
      });
      const data = await res.json();
      if (res.ok) {
        setGeneratedPdf(prev => ({ ...prev, [job.id]: data.pdf_url }));
        // also mark as done in local state or refetch
      } else {
        alert(data.error);
      }
    } catch (e) {
      console.error(e);
      alert('Error generating resume');
    }
    setGenerating(prev => ({ ...prev, [job.id]: false }));
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1000px', margin: '0 auto' }}>
      <h1 style={{ fontSize: '28px', fontWeight: 800, marginBottom: '24px', color: 'white' }}>Pending Resumes</h1>
      {loading ? (
        <div style={{ color: 'var(--text-muted)' }}>Loading...</div>
      ) : jobs.length === 0 ? (
        <div style={{ padding: '40px', textAlign: 'center', background: 'var(--bg-panel)', borderRadius: '16px', border: '1px solid var(--border-color)' }}>
          <FileText size={48} style={{ color: 'var(--text-muted)', margin: '0 auto 16px auto' }} />
          <h3 style={{ margin: 0, color: 'white' }}>No Pending Jobs</h3>
          <p style={{ color: 'var(--text-muted)', margin: '8px 0 0 0' }}>All scored jobs have resumes generated!</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {jobs.map(job => {
            const isExpanded = expandedJobId === job.id;
            const skills = job.missing_skills || [];
            const isGenerating = generating[job.id];
            const pdfUrl = generatedPdf[job.id];

            return (
              <div key={job.id} style={{ background: 'var(--bg-panel)', borderRadius: '16px', border: '1px solid var(--border-color)', overflow: 'hidden' }}>
                <div 
                  onClick={() => toggleJob(job.id)}
                  style={{ padding: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer', background: isExpanded ? 'rgba(255,255,255,0.02)' : 'transparent' }}
                >
                  <div>
                    <h3 style={{ margin: '0 0 4px 0', fontSize: '18px', color: 'white' }}>{job.title}</h3>
                    <div style={{ color: 'var(--cyan)', fontWeight: 600, fontSize: '14px' }}>{job.company} &bull; Score: {job.score}</div>
                  </div>
                  <div>
                    {isExpanded ? <ChevronUp /> : <ChevronDown />}
                  </div>
                </div>

                <AnimatePresence>
                  {isExpanded && (
                    <motion.div initial={{ height: 0 }} animate={{ height: 'auto' }} exit={{ height: 0 }} style={{ overflow: 'hidden' }}>
                      <div style={{ padding: '0 20px 20px 20px', borderTop: '1px solid var(--border-color)' }}>
                        <p style={{ color: 'var(--text-main)', fontSize: '14px', lineHeight: 1.6, marginTop: '16px' }}>
                          {job.description ? (job.description.substring(0, 200) + '...') : 'No description available.'}
                        </p>

                        <div style={{ marginTop: '20px' }}>
                          <h4 style={{ margin: '0 0 12px 0', color: 'white', fontSize: '15px' }}>Missing Skills (Select to inject)</h4>
                          {skills.length > 0 ? (
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                              {skills.map(skill => {
                                const isSelected = (selectedSkills[job.id] || []).includes(skill);
                                return (
                                  <div 
                                    key={skill}
                                    onClick={() => toggleSkill(job.id, skill)}
                                    style={{
                                      padding: '8px 16px',
                                      borderRadius: '100px',
                                      background: isSelected ? 'rgba(34, 211, 238, 0.2)' : 'rgba(255,255,255,0.05)',
                                      border: isSelected ? '1px solid var(--cyan)' : '1px solid var(--border-color)',
                                      color: isSelected ? 'white' : 'var(--text-muted)',
                                      cursor: 'pointer',
                                      display: 'flex', alignItems: 'center', gap: '8px',
                                      fontSize: '13px', fontWeight: 500
                                    }}
                                  >
                                    {isSelected && <Check size={14} color="var(--cyan)" />}
                                    {skill}
                                  </div>
                                );
                              })}
                            </div>
                          ) : (
                            <div style={{ color: '#10b981', fontSize: '14px', background: 'rgba(16,185,129,0.1)', padding: '12px', borderRadius: '8px' }}>
                              Perfect match! No missing skills detected.
                            </div>
                          )}
                        </div>

                        <div style={{ marginTop: '24px', display: 'flex', gap: '16px' }}>
                          {!pdfUrl ? (
                            <button 
                              onClick={() => handleGenerate(job)}
                              disabled={isGenerating}
                              style={{ 
                                padding: '12px 24px', background: 'linear-gradient(135deg, var(--cyan), #3b82f6)', 
                                color: '#000', border: 'none', borderRadius: '8px', fontWeight: 700, 
                                cursor: isGenerating ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', gap: '8px',
                                opacity: isGenerating ? 0.7 : 1
                              }}
                            >
                              {isGenerating ? 'Generating...' : <><BrainCircuit size={18} /> Generate Tailored Resume</>}
                            </button>
                          ) : (
                            <a 
                              href={pdfUrl} target="_blank" rel="noreferrer"
                              style={{ 
                                padding: '12px 24px', background: '#10b981', 
                                color: '#000', textDecoration: 'none', borderRadius: '8px', fontWeight: 700, 
                                display: 'flex', alignItems: 'center', gap: '8px'
                              }}
                            >
                              <Download size={18} /> Download PDF
                            </a>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
