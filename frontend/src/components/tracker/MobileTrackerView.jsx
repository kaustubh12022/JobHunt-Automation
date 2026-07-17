import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronDown, ChevronUp, Trash2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const STATUS_COLORS = {
  'generated': { bg: 'rgba(59, 130, 246, 0.1)', border: 'rgba(59, 130, 246, 0.3)', text: '#1e40af' },
  'applied': { bg: 'rgba(139, 92, 246, 0.1)', border: 'rgba(139, 92, 246, 0.3)', text: '#5b21b6' },
  'shortlisted': { bg: 'rgba(16, 185, 129, 0.1)', border: 'rgba(16, 185, 129, 0.3)', text: '#065f46' },
  'interview': { bg: 'rgba(245, 158, 11, 0.1)', border: 'rgba(245, 158, 11, 0.3)', text: '#92400e' },
  'offer': { bg: 'rgba(52, 211, 153, 0.2)', border: 'rgba(52, 211, 153, 0.5)', text: '#064e3b' },
  'accepted': { bg: 'rgba(217, 70, 239, 0.1)', border: 'rgba(217, 70, 239, 0.3)', text: '#86198f' },
  'rejected': { bg: 'rgba(239, 68, 68, 0.1)', border: 'rgba(239, 68, 68, 0.3)', text: '#991b1b' }
};

export default function MobileTrackerView({ applications, columns, onStatusChange, onDeleteApp }) {
  const navigate = useNavigate();
  // Group applications by status
  const grouped = columns.reduce((acc, col) => {
    acc[col.id] = applications.filter(app => app.status === col.id);
    return acc;
  }, {});

  // Initially expand sections that have items
  const [expanded, setExpanded] = useState(
    columns.reduce((acc, col) => {
      acc[col.id] = grouped[col.id].length > 0;
      return acc;
    }, {})
  );

  const toggleSection = (id) => setExpanded(prev => ({ ...prev, [id]: !prev[id] }));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', paddingBottom: '20px' }}>
      {columns.map(col => {
        const apps = grouped[col.id];
        const isExpanded = expanded[col.id];
        const colors = STATUS_COLORS[col.id] || { bg: '#f1f5f9', border: '#e2e8f0', text: '#334155' };
        
        if (apps.length === 0) return null; // Auto-hide empty sections

        return (
          <div key={col.id} style={{ background: 'var(--bg-panel)', borderRadius: '12px', border: `1px solid ${colors.border}`, overflow: 'hidden' }}>
            {/* Header */}
            <div 
              onClick={() => toggleSection(col.id)}
              style={{ 
                padding: '16px', background: colors.bg, display: 'flex', justifyContent: 'space-between', 
                alignItems: 'center', cursor: 'pointer', userSelect: 'none' 
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontWeight: 600, color: colors.text }}>{col.label}</span>
                <span style={{ background: 'rgba(0,0,0,0.1)', padding: '2px 8px', borderRadius: '12px', fontSize: '12px', color: colors.text }}>
                  {apps.length}
                </span>
              </div>
              {isExpanded ? <ChevronUp size={20} color={colors.text} /> : <ChevronDown size={20} color={colors.text} />}
            </div>

            {/* Content */}
            <AnimatePresence>
              {isExpanded && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  style={{ overflow: 'hidden' }}
                >
                  <div style={{ padding: '12px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {apps.map(app => {
                      const job = Array.isArray(app.tracked_jobs) ? app.tracked_jobs[0] : (app.tracked_jobs || {});
                      
                      return (
                        <div 
                          key={app.id} 
                          onClick={(e) => {
                            if (e.target.tagName !== 'SELECT' && e.target.closest('button') === null) {
                              navigate('/tracker/job/' + job.id);
                            }
                          }}
                          style={{ 
                            background: 'white', padding: '16px', borderRadius: '8px', 
                            boxShadow: '0 2px 4px rgba(0,0,0,0.05)', border: '1px solid #f1f5f9',
                            position: 'relative'
                          }}
                        >
                          <button 
                            onClick={(e) => { e.stopPropagation(); onDeleteApp(app.id); }}
                            style={{ position: 'absolute', top: '12px', right: '12px', background: 'transparent', border: 'none', color: '#ef4444', padding: '4px' }}
                          >
                            <Trash2 size={16} />
                          </button>

                          <div style={{ paddingRight: '24px' }}>
                            <div style={{ fontWeight: 600, fontSize: '15px', marginBottom: '4px', lineHeight: 1.3 }} className="text-truncate">
                              {job.title}
                            </div>
                            <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '12px' }} className="text-truncate">
                              {job.company}
                            </div>
                          </div>

                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                              <span className="badge badge-score">{job.score || 0}/100</span>
                              {job.source && (
                                <span style={{ fontSize: '10px', padding: '2px 6px', borderRadius: '4px', background: '#f1f5f9', color: '#475569', fontWeight: 600, textTransform: 'uppercase' }}>
                                  {job.source.startsWith('workday-') ? 'Workday' : job.source}
                                </span>
                              )}
                            </div>
                            
                            <select 
                              value={app.status}
                              onChange={(e) => onStatusChange(app.id, e.target.value)}
                              style={{ 
                                padding: '6px', fontSize: '12px', borderRadius: '6px', 
                                border: `1px solid ${colors.border}`, background: colors.bg, color: colors.text, fontWeight: 500 
                              }}
                            >
                              {columns.map(c => (
                                <option key={c.id} value={c.id}>{c.label}</option>
                              ))}
                            </select>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        );
      })}
    </div>
  );
}
