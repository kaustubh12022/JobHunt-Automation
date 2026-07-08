import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, FileText, CheckCircle2, ChevronRight, RotateCcw, Download, Briefcase, Building2, Check, ArrowRight } from 'lucide-react';

export default function ManualTailor() {
  const [step, setStep] = useState('input'); // input | scoring | scored | generating | result
  
  // Form state
  const [jobTitle, setJobTitle] = useState('');
  const [company, setCompany] = useState('');
  const [jobDescription, setJobDescription] = useState('');
  
  // API result state
  const [scoreData, setScoreData] = useState(null);
  const [selectedSkills, setSelectedSkills] = useState([]);
  const [pdfUrl, setPdfUrl] = useState(null);
  const [error, setError] = useState(null);

  const handleAnalyze = async () => {
    if (!jobDescription.trim()) {
      setError("Job Description is required");
      return;
    }
    setError(null);
    setStep('scoring');
    
    try {
      const res = await fetch('/api/manual-tailor/score', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_title: jobTitle,
          company: company,
          job_description: jobDescription
        })
      });
      
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to score job");
      
      setScoreData(data);
      setSelectedSkills([]);
      setStep('scored');
    } catch (err) {
      setError(err.message);
      setStep('input');
    }
  };

  const handleSkillToggle = (skill) => {
    setSelectedSkills(prev => 
      prev.includes(skill) ? prev.filter(s => s !== skill) : [...prev, skill]
    );
  };

  const handleGenerate = async () => {
    setError(null);
    setStep('generating');
    
    try {
      const res = await fetch('/api/manual-tailor/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_title: jobTitle,
          company: company,
          job_description: jobDescription,
          score: scoreData.score,
          missing_skills: scoreData.missing_skills,
          extracted_requirements: scoreData.extracted_requirements,
          is_testing_role: scoreData.is_testing_role,
          selected_skills: selectedSkills
        })
      });
      
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to generate resume");
      
      setPdfUrl(data.pdf_url);
      setStep('result');
    } catch (err) {
      setError(err.message);
      setStep('scored');
    }
  };

  const handleStartOver = () => {
    setJobTitle('');
    setCompany('');
    setJobDescription('');
    setScoreData(null);
    setSelectedSkills([]);
    setPdfUrl(null);
    setError(null);
    setStep('input');
  };

  const slideVariants = {
    initial: { opacity: 0, x: 20 },
    animate: { opacity: 1, x: 0 },
    exit: { opacity: 0, x: -20 }
  };

  return (
    <div style={{ padding: '32px 24px', maxWidth: '1400px', margin: '0 auto', minHeight: 'calc(100vh - 70px)', display: 'flex', flexDirection: 'column' }}>
      
      {/* Header Area */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
        <div>
          <h1 style={{ fontSize: '28px', fontWeight: 800, margin: '0 0 8px 0', background: 'linear-gradient(90deg, #fff, #94a3b8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            AI Resume Tailor
          </h1>
          <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '15px' }}>
            Custom-fit your resume for any job description in seconds.
          </p>
        </div>

        {/* Progress Tracker */}
        <div style={{ display: 'flex', gap: '24px', alignItems: 'center', background: 'var(--bg-panel)', padding: '12px 24px', borderRadius: '100px', border: '1px solid var(--border-color)', boxShadow: 'var(--shadow-md)' }}>
          <StepIndicator active={step === 'input'} completed={['scoring', 'scored', 'generating', 'result'].includes(step)} number={1} label="Input" />
          <div style={{ height: '2px', width: '32px', background: 'var(--border-color)' }} />
          <StepIndicator active={['scoring', 'scored'].includes(step)} completed={['generating', 'result'].includes(step)} number={2} label="Analysis" />
          <div style={{ height: '2px', width: '32px', background: 'var(--border-color)' }} />
          <StepIndicator active={['generating', 'result'].includes(step)} completed={step === 'result'} number={3} label="Result" />
        </div>
      </div>

      {error && (
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#fca5a5', padding: '16px', borderRadius: '12px', marginBottom: '24px', border: '1px solid rgba(239,68,68,0.3)', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <CheckCircle2 size={20} />
          {error}
        </motion.div>
      )}

      <div style={{ flex: 1, display: 'flex', gap: '32px', height: '100%' }}>
        
        {/* Left Side (Dynamic Content) */}
        <div style={{ flex: step === 'result' ? '0 0 450px' : 1, display: 'flex', flexDirection: 'column', transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)', position: 'relative' }}>
          <AnimatePresence mode="wait">
            
            {step === 'input' && (
              <motion.div key="input" variants={slideVariants} initial="initial" animate="animate" exit="exit" className="glass-panel" style={{ padding: '32px', flex: 1, display: 'flex', flexDirection: 'column', gap: '24px' }}>
                <div style={{ display: 'flex', gap: '24px' }}>
                  <div style={{ flex: 1 }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px', fontSize: '14px', color: 'var(--text-main)', fontWeight: 600 }}>
                      <Briefcase size={16} className="text-cyan" /> Job Title <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>(Optional)</span>
                    </label>
                    <input type="text" value={jobTitle} onChange={e => setJobTitle(e.target.value)} style={{ width: '100%', padding: '12px 16px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-color)', color: 'white', borderRadius: '12px', fontSize: '15px', transition: 'border-color 0.2s', outline: 'none' }} onFocus={e => e.target.style.borderColor = 'var(--cyan)'} onBlur={e => e.target.style.borderColor = 'var(--border-color)'} placeholder="e.g. Senior Frontend Engineer" />
                  </div>
                  <div style={{ flex: 1 }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px', fontSize: '14px', color: 'var(--text-main)', fontWeight: 600 }}>
                      <Building2 size={16} className="text-cyan" /> Company <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>(Optional)</span>
                    </label>
                    <input type="text" value={company} onChange={e => setCompany(e.target.value)} style={{ width: '100%', padding: '12px 16px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-color)', color: 'white', borderRadius: '12px', fontSize: '15px', transition: 'border-color 0.2s', outline: 'none' }} onFocus={e => e.target.style.borderColor = 'var(--cyan)'} onBlur={e => e.target.style.borderColor = 'var(--border-color)'} placeholder="e.g. OpenAI" />
                  </div>
                </div>
                
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px', fontSize: '14px', color: 'var(--text-main)', fontWeight: 600 }}>
                    <FileText size={16} className="text-cyan" /> Job Description <span style={{ color: '#ef4444' }}>*</span>
                  </label>
                  <textarea value={jobDescription} onChange={e => setJobDescription(e.target.value)} style={{ width: '100%', flex: 1, minHeight: '300px', padding: '16px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-color)', color: 'white', borderRadius: '12px', resize: 'none', fontSize: '14px', lineHeight: 1.6, transition: 'border-color 0.2s', outline: 'none' }} onFocus={e => e.target.style.borderColor = 'var(--cyan)'} onBlur={e => e.target.style.borderColor = 'var(--border-color)'} placeholder="Paste the full job description here..." />
                </div>
                
                <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} onClick={handleAnalyze} style={{ background: 'var(--cyan)', color: '#000', padding: '16px', borderRadius: '12px', fontWeight: 'bold', fontSize: '16px', border: 'none', cursor: 'pointer', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px', boxShadow: '0 4px 14px rgba(34, 211, 238, 0.4)' }}>
                  <Sparkles size={20} /> Analyze Requirements
                </motion.button>
              </motion.div>
            )}

            {step === 'scoring' && (
              <motion.div key="scoring" variants={slideVariants} initial="initial" animate="animate" exit="exit" className="glass-panel" style={{ padding: '48px', flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '24px' }}>
                <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 2, ease: "linear" }} style={{ color: 'var(--cyan)' }}>
                  <Sparkles size={48} />
                </motion.div>
                <div style={{ textAlign: 'center' }}>
                  <h2 style={{ fontSize: '24px', margin: '0 0 12px 0', color: 'white' }}>Analyzing Job Description</h2>
                  <p style={{ color: 'var(--text-muted)', fontSize: '15px', maxWidth: '350px', margin: 0, lineHeight: 1.5 }}>
                    Our AI is extracting core requirements and comparing them against your master resume...
                  </p>
                </div>
              </motion.div>
            )}

            {step === 'scored' && scoreData && (
              <motion.div key="scored" variants={slideVariants} initial="initial" animate="animate" exit="exit" className="glass-panel" style={{ padding: '32px', flex: 1, display: 'flex', flexDirection: 'column', gap: '32px', overflowY: 'auto' }}>
                
                {/* Score Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', background: 'rgba(0,0,0,0.2)', padding: '24px', borderRadius: '16px', border: '1px solid rgba(255,255,255,0.05)' }}>
                  <div style={{ flex: 1, paddingRight: '24px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                      <Sparkles size={18} className="text-cyan" />
                      <h2 style={{ margin: 0, fontSize: '20px', color: 'white' }}>AI Analysis Complete</h2>
                    </div>
                    <p style={{ fontSize: '15px', color: 'var(--text-muted)', margin: 0, lineHeight: 1.6 }}>{scoreData.reason}</p>
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '48px', fontWeight: 800, color: scoreData.score >= 70 ? '#10b981' : scoreData.score >= 50 ? '#f59e0b' : '#ef4444', lineHeight: 1, textShadow: '0 4px 12px rgba(0,0,0,0.5)' }}>
                      {scoreData.score}%
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px', marginTop: '4px' }}>Match</div>
                  </div>
                </div>

                {/* Match Areas */}
                {scoreData.extracted_requirements && (
                  <div>
                    <h3 style={{ fontSize: '16px', margin: '0 0 12px 0', color: 'white', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <CheckCircle2 size={16} className="text-cyan" /> Key Requirements Found
                    </h3>
                    <div style={{ background: 'rgba(0,0,0,0.2)', padding: '16px', borderRadius: '12px', fontSize: '14px', lineHeight: 1.6, color: 'var(--text-muted)', border: '1px solid rgba(255,255,255,0.05)' }}>
                      {scoreData.extracted_requirements}
                    </div>
                  </div>
                )}

                {/* Missing Skills */}
                <div style={{ flex: 1 }}>
                  <h3 style={{ fontSize: '16px', margin: '0 0 8px 0', color: 'white', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <FileText size={16} className="text-cyan" /> Missing Skills
                  </h3>
                  <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '16px', lineHeight: 1.5 }}>
                    Select any skills below that you actually possess. The AI will seamlessly weave them into your generated resume.
                  </p>
                  
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '12px' }}>
                    {scoreData.missing_skills?.map((skill, idx) => (
                      <motion.label key={idx} whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} style={{ display: 'flex', alignItems: 'center', gap: '12px', background: selectedSkills.includes(skill) ? 'rgba(34, 211, 238, 0.1)' : 'rgba(0,0,0,0.2)', padding: '16px', borderRadius: '12px', cursor: 'pointer', border: selectedSkills.includes(skill) ? '1px solid var(--cyan)' : '1px solid rgba(255,255,255,0.05)', transition: 'all 0.2s' }}>
                        <div style={{ width: '20px', height: '20px', borderRadius: '6px', border: selectedSkills.includes(skill) ? 'none' : '2px solid var(--text-muted)', background: selectedSkills.includes(skill) ? 'var(--cyan)' : 'transparent', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                          {selectedSkills.includes(skill) && <Check size={14} color="#000" strokeWidth={3} />}
                        </div>
                        <span style={{ fontSize: '15px', color: selectedSkills.includes(skill) ? 'white' : 'var(--text-main)', fontWeight: selectedSkills.includes(skill) ? 600 : 400 }}>{skill}</span>
                      </motion.label>
                    ))}
                    {(!scoreData.missing_skills || scoreData.missing_skills.length === 0) && (
                      <div style={{ gridColumn: '1 / -1', padding: '24px', background: 'rgba(16, 185, 129, 0.1)', color: '#10b981', borderRadius: '12px', textAlign: 'center', border: '1px solid rgba(16,185,129,0.2)' }}>
                        ✨ No missing skills! You are a perfect match for this role.
                      </div>
                    )}
                  </div>
                </div>

                {/* Actions */}
                <div style={{ display: 'flex', gap: '16px', marginTop: 'auto', paddingTop: '16px' }}>
                  <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} onClick={() => setStep('input')} style={{ padding: '16px 24px', background: 'rgba(0,0,0,0.3)', color: 'white', border: '1px solid var(--border-color)', borderRadius: '12px', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <RotateCcw size={18} /> Back
                  </motion.button>
                  <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} onClick={handleGenerate} style={{ flex: 1, background: 'linear-gradient(135deg, var(--cyan), #3b82f6)', color: '#000', border: 'none', padding: '16px', borderRadius: '12px', fontWeight: 800, fontSize: '16px', cursor: 'pointer', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px', boxShadow: '0 8px 20px rgba(34, 211, 238, 0.3)' }}>
                    Generate Tailored Resume <ArrowRight size={20} />
                  </motion.button>
                </div>
              </motion.div>
            )}

            {step === 'generating' && (
              <motion.div key="generating" variants={slideVariants} initial="initial" animate="animate" exit="exit" className="glass-panel" style={{ padding: '48px', flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '24px' }}>
                <motion.div animate={{ scale: [1, 1.1, 1], opacity: [0.5, 1, 0.5] }} transition={{ repeat: Infinity, duration: 2 }} style={{ color: 'var(--cyan)' }}>
                  <FileText size={48} />
                </motion.div>
                <div style={{ textAlign: 'center' }}>
                  <h2 style={{ fontSize: '24px', margin: '0 0 12px 0', color: 'white' }}>Crafting Your Resume</h2>
                  <p style={{ color: 'var(--text-muted)', fontSize: '15px', maxWidth: '350px', margin: 0, lineHeight: 1.5 }}>
                    DeepSeek is dynamically weaving your selected skills into accomplishments. Rendering PDF...
                  </p>
                </div>
              </motion.div>
            )}

            {step === 'result' && (
              <motion.div key="result" variants={slideVariants} initial="initial" animate="animate" exit="exit" className="glass-panel" style={{ padding: '32px', display: 'flex', flexDirection: 'column', gap: '32px', height: '100%' }}>
                
                <div style={{ textAlign: 'center', marginBottom: '8px' }}>
                  <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '64px', height: '64px', borderRadius: '50%', background: 'rgba(16, 185, 129, 0.1)', color: '#10b981', marginBottom: '16px' }}>
                    <CheckCircle2 size={32} />
                  </div>
                  <h2 style={{ margin: '0 0 8px 0', fontSize: '28px', color: 'white' }}>Resume Ready!</h2>
                  <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '15px' }}>
                    Your tailored PDF has been generated successfully.
                  </p>
                </div>

                {selectedSkills.length > 0 && (
                  <div style={{ background: 'rgba(0,0,0,0.2)', padding: '20px', borderRadius: '16px', border: '1px solid rgba(255,255,255,0.05)' }}>
                    <h3 style={{ fontSize: '14px', margin: '0 0 12px 0', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1px' }}>Injected Skills</h3>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                      {selectedSkills.map((s, i) => (
                        <span key={i} style={{ background: 'rgba(34, 211, 238, 0.1)', color: 'var(--cyan)', border: '1px solid rgba(34,211,238,0.2)', padding: '6px 12px', borderRadius: '100px', fontSize: '13px', fontWeight: 600 }}>
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <motion.a whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} href={pdfUrl} target="_blank" rel="noreferrer" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px', background: 'linear-gradient(135deg, var(--cyan), #3b82f6)', color: '#000', textDecoration: 'none', padding: '16px', borderRadius: '12px', fontWeight: 800, fontSize: '16px', boxShadow: '0 8px 20px rgba(34, 211, 238, 0.3)' }}>
                    <Download size={20} /> Download PDF
                  </motion.a>
                  <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} onClick={handleStartOver} style={{ background: 'rgba(0,0,0,0.3)', color: 'white', border: '1px solid var(--border-color)', padding: '16px', borderRadius: '12px', fontWeight: 600, cursor: 'pointer', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px' }}>
                    <RotateCcw size={18} /> Start Another Tailor
                  </motion.button>
                </div>
              </motion.div>
            )}

          </AnimatePresence>
        </div>

        {/* Right Side (PDF Preview) - Only visible on Result step */}
        <AnimatePresence>
          {step === 'result' && pdfUrl && (
            <motion.div initial={{ opacity: 0, x: 20, width: 0 }} animate={{ opacity: 1, x: 0, width: '100%' }} exit={{ opacity: 0, x: 20, width: 0 }} style={{ flex: 1.5, background: 'var(--bg-panel)', borderRadius: '24px', border: '1px solid var(--border-color)', overflow: 'hidden', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)' }}>
              <iframe src={pdfUrl} style={{ width: '100%', height: '100%', border: 'none' }} title="Tailored Resume Preview" />
            </motion.div>
          )}
        </AnimatePresence>

      </div>
    </div>
  );
}

// Helper component for the step indicator
function StepIndicator({ active, completed, number, label }) {
  const isActiveOrCompleted = active || completed;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', opacity: isActiveOrCompleted ? 1 : 0.5, transition: 'opacity 0.3s' }}>
      <div style={{ width: '28px', height: '28px', borderRadius: '50%', background: completed ? 'var(--cyan)' : active ? 'rgba(34, 211, 238, 0.2)' : 'rgba(255,255,255,0.1)', border: active && !completed ? '2px solid var(--cyan)' : 'none', color: completed ? '#000' : 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '13px', fontWeight: 'bold' }}>
        {completed ? <Check size={16} strokeWidth={3} /> : number}
      </div>
      <span style={{ fontSize: '14px', fontWeight: isActiveOrCompleted ? 600 : 400, color: isActiveOrCompleted ? 'white' : 'var(--text-muted)' }}>
        {label}
      </span>
    </div>
  );
}
