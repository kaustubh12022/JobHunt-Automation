import React from 'react';
import { useNavigate } from 'react-router-dom';

export default function ApplicationCard({ app, onStatusChange, columns }) {
  const navigate = useNavigate();
  // Safe extraction for tracked_jobs
  const job = Array.isArray(app.tracked_jobs) ? app.tracked_jobs[0] : (app.tracked_jobs || {});

  const handleDragStart = (e) => {
    e.dataTransfer.setData('applicationId', app.id);
  };

  return (
    <div 
      className="kanban-card"
      draggable
      onDragStart={handleDragStart}
      onClick={() => navigate('/tracker/job/' + job.id)}
    >
      <div style={{ fontWeight: 600, marginBottom: '4px', fontSize: '14px', lineHeight: 1.4 }}>
        {job.title || 'Unknown Title'}
      </div>
      <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '12px' }}>
        {job.company || 'Unknown Company'}
      </div>
      
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span className="badge badge-score">{job.score || 0}/100</span>
        
        {/* Status select dropdown for mobile touch accessibility */}
        <select 
          style={{ fontSize: '12px', padding: '4px', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'rgba(255,255,255,0.5)', outline: 'none', cursor: 'pointer' }}
          value={app.status === 'offer_received' ? 'offer' : app.status}
          onChange={(e) => {
            e.stopPropagation();
            onStatusChange(e.target.value);
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {columns.map(col => (
            <option key={col.id} value={col.id}>{col.label}</option>
          ))}
        </select>
      </div>
    </div>
  );
}
