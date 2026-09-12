import React, { useRef } from 'react';
import { useNavigate } from 'react-router-dom';

export default function ApplicationCard({ app, onStatusChange, onDeleteApp, columns }) {
  const navigate = useNavigate();
  const isDragging = useRef(false);

  // Safe extraction for tracked_jobs
  const job = Array.isArray(app.tracked_jobs) ? app.tracked_jobs[0] : (app.tracked_jobs || {});

  const handleDragStart = (e) => {
    isDragging.current = true;
    e.dataTransfer.setData('applicationId', app.id);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragEnd = () => {
    // Reset dragging flag after a short delay so the click event fires first
    setTimeout(() => { isDragging.current = false; }, 0);
  };

  const handleClick = (e) => {
    // If clicking on a button or select, don't navigate
    if (e.target.tagName === 'BUTTON' || e.target.tagName === 'SELECT') return;
    // If we just finished a drag, don't navigate
    if (isDragging.current) return;
    navigate('/tracker/job/' + job.id);
  };

  return (
    <div 
      className="kanban-card"
      draggable
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      onClick={handleClick}
      style={{ position: 'relative' }}
    >
      <button 
        onClick={(e) => {
          e.stopPropagation();
          onDeleteApp();
        }}
        title="Delete Application"
        style={{ position: 'absolute', top: '8px', right: '8px', background: 'transparent', border: 'none', color: '#ef4444', cursor: 'pointer', padding: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '4px' }}
        onMouseOver={e => e.currentTarget.style.background = 'rgba(239, 68, 68, 0.1)'}
        onMouseOut={e => e.currentTarget.style.background = 'transparent'}
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18"></path><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path></svg>
      </button>

      <div style={{ fontWeight: 600, marginBottom: '4px', fontSize: '14px', lineHeight: 1.4, paddingRight: '20px', color: '#111827' }}>
        {job.title || 'Unknown Title'}
      </div>
      <div style={{ fontSize: '13px', color: '#6b7280', marginBottom: '12px' }}>
        {job.company || 'Unknown Company'}
      </div>
      
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          <span className="badge badge-score">{job.score || 0}/100</span>
          {job.source && (
            <span style={{ 
              fontSize: '10px', 
              padding: '2px 6px', 
              borderRadius: '4px', 
              background: job.source.startsWith('workday') ? '#dcfce7' : job.source === 'linkedin' ? '#dbeafe' : job.source === 'glassdoor' ? '#fee2e2' : '#f3f4f6',
              color: job.source.startsWith('workday') ? '#166534' : job.source === 'linkedin' ? '#1e40af' : job.source === 'glassdoor' ? '#991b1b' : '#374151',
              fontWeight: 500,
              textTransform: 'uppercase'
            }}>
              {job.source.startsWith('workday-') ? 'Workday' : job.source}
            </span>
          )}
          {job.job_type === 'internship' && (
            <span style={{ 
              fontSize: '10px', 
              padding: '2px 6px', 
              borderRadius: '4px', 
              background: '#fef3c7',
              color: '#92400e',
              fontWeight: 500,
              textTransform: 'uppercase'
            }}>
              Intern
            </span>
          )}
        </div>
        
        {/* Status select dropdown for mobile touch accessibility */}
        <select 
          style={{ fontSize: '12px', padding: '4px 8px', borderRadius: '6px', border: '1px solid #cbd5e1', background: '#f8fafc', color: '#111827', outline: 'none', cursor: 'pointer', fontWeight: 600, colorScheme: 'light' }}
          value={app.status}
          onChange={(e) => {
            e.stopPropagation();
            onStatusChange(e.target.value);
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {columns.map(col => (
            <option key={col.id} value={col.id} style={{ color: '#111827', background: '#ffffff', fontWeight: 600 }}>
              {col.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
