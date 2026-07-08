import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { supabase } from '../lib/supabase';

export default function JobDetailPage() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchJob();
  }, [jobId]);

  const fetchJob = async () => {
    try {
      const { data: jobData, error } = await supabase
        .from('tracked_jobs')
        .select('*, applications(*)')
        .eq('id', jobId)
        .single();
        
      if (error) throw error;
      setData(jobData);
    } catch (err) {
      console.error("Error fetching job details:", err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>Loading...</div>;
  }

  if (!data) {
    return <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>Job not found.</div>;
  }

  const { title, company, score, source, url, missing_skills, description, reasons, tailored_resume } = data;
  const skills = tailored_resume?.skills || [];
  
  let scoreColor = '#ef4444'; // Red
  if (score >= 70) scoreColor = '#16a34a'; // Green
  else if (score >= 50) scoreColor = '#eab308'; // Yellow

  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto', height: 'calc(100vh - 70px)', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '24px' }}>
        <button 
          onClick={() => navigate('/tracker')} 
          style={{ background: 'var(--bg-panel)', color: 'var(--text-main)', border: '1px solid var(--border-color)', padding: '8px 16px', borderRadius: '8px', cursor: 'pointer', fontWeight: 600 }}
        >
          ← Back to Tracker
        </button>
        <h1 style={{ fontSize: '24px', margin: 0 }}>{company}</h1>
      </div>

      <div style={{ display: 'flex', gap: '24px', flex: 1, overflow: 'hidden' }}>
        {/* Left Panel */}
        <div style={{ width: '45%', display: 'flex', flexDirection: 'column', gap: '24px', overflowY: 'auto', paddingRight: '8px' }}>
          
          <div className="glass-panel" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
              <div>
                <h2 style={{ margin: '0 0 8px 0', fontSize: '20px' }}>{title}</h2>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                  {source && <span style={{ background: 'var(--cyan-glow)', color: 'var(--cyan)', padding: '4px 8px', borderRadius: '4px', fontSize: '12px', fontWeight: 'bold', textTransform: 'uppercase' }}>{source}</span>}
                  <button 
                    onClick={() => window.open(url, '_blank')}
                    style={{ background: '#3b82f6', color: '#fff', border: 'none', padding: '6px 12px', borderRadius: '6px', fontSize: '12px', cursor: 'pointer', fontWeight: 'bold' }}
                  >
                    Direct Apply Link ↗
                  </button>
                </div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '32px', fontWeight: 'bold', color: scoreColor, lineHeight: 1 }}>{score}%</div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Match Score</div>
              </div>
            </div>

            {reasons && (
              <div style={{ background: 'rgba(255,255,255,0.05)', padding: '12px', borderRadius: '8px', marginBottom: '24px', fontSize: '14px', borderLeft: `4px solid ${scoreColor}` }}>
                {reasons}
              </div>
            )}

            <div style={{ marginBottom: '24px' }}>
              <h3 style={{ fontSize: '16px', margin: '0 0 12px 0', color: 'var(--text-main)' }}>Present Skills</h3>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {skills.map((s, i) => (
                  <span key={i} style={{ background: 'rgba(22, 163, 74, 0.1)', color: '#16a34a', border: '1px solid rgba(22, 163, 74, 0.2)', padding: '4px 10px', borderRadius: '16px', fontSize: '13px' }}>
                    {s}
                  </span>
                ))}
                {(!skills || skills.length === 0) && <span style={{ color: 'var(--text-muted)', fontSize: '14px' }}>No skills identified.</span>}
              </div>
            </div>

            <div>
              <h3 style={{ fontSize: '16px', margin: '0 0 12px 0', color: 'var(--text-main)' }}>Missing Skills</h3>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {missing_skills && missing_skills.map((s, i) => (
                  <span key={i} style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', border: '1px solid rgba(239, 68, 68, 0.2)', padding: '4px 10px', borderRadius: '16px', fontSize: '13px' }}>
                    {s}
                  </span>
                ))}
                {(!missing_skills || missing_skills.length === 0) && <span style={{ color: 'var(--text-muted)', fontSize: '14px' }}>No missing skills!</span>}
              </div>
            </div>
          </div>

          <div className="glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
             <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
               <h3 style={{ margin: 0, fontSize: '18px' }}>Job Description</h3>
               <button 
                  onClick={() => window.open(`/api/resume/${jobId}`, '_blank')}
                  style={{ background: 'var(--bg-panel)', color: 'var(--text-main)', border: '1px solid var(--border-color)', padding: '6px 12px', borderRadius: '6px', fontSize: '12px', cursor: 'pointer', fontWeight: 'bold' }}
                >
                  Download Resume ↓
                </button>
             </div>
             
             {description ? (
               <div style={{ whiteSpace: 'pre-wrap', fontSize: '14px', color: 'var(--text-main)', background: 'var(--bg-panel)', padding: '16px', borderRadius: '8px', maxHeight: '400px', overflowY: 'auto' }}>
                 {description}
               </div>
             ) : (
               <div style={{ color: 'var(--text-muted)', fontSize: '14px', fontStyle: 'italic' }}>No description available for this job.</div>
             )}
          </div>

        </div>

        {/* Right Panel */}
        <div style={{ width: '55%', height: '100%', background: 'var(--bg-panel)', borderRadius: '16px', border: '1px solid var(--border-color)', overflow: 'hidden' }}>
          <iframe 
            src={`/api/resume/${jobId}`} 
            style={{ width: '100%', height: '100%', border: 'none' }}
            title="Resume PDF"
          />
        </div>

      </div>
    </div>
  );
}
