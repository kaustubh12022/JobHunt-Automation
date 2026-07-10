import React, { useState } from 'react';
import ApplicationCard from './ApplicationCard';

// Using lower-case statuses as per DB defaults, but displaying Title Case
const COLUMNS = [
  { id: 'generated', label: 'Generated' },
  { id: 'applied', label: 'Applied' },
  { id: 'shortlisted', label: 'Shortlisted' },
  { id: 'interview', label: 'Interview' },
  { id: 'offer_received', label: 'Offer' },
  { id: 'accepted', label: 'Accepted' },
  { id: 'rejected', label: 'Rejected' }
];

export default function KanbanBoard({ applications, onStatusChange, onDeleteApp }) {
  const [dragOverCol, setDragOverCol] = useState(null);
  const getAppsForColumn = (statusId) => applications.filter(app => app.status === statusId);

  const handleDragOver = (e, colId) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (dragOverCol !== colId) setDragOverCol(colId);
  };

  const handleDragLeave = (e, colId) => {
    // Only clear if we actually left the column (not entering a child)
    if (!e.currentTarget.contains(e.relatedTarget)) {
      setDragOverCol(null);
    }
  };

  const handleDrop = (e, statusId) => {
    e.preventDefault();
    setDragOverCol(null);
    const appId = e.dataTransfer.getData('applicationId');
    if (appId) {
      onStatusChange(appId, statusId);
    }
  };

  return (
    <div className="kanban-board">
      {COLUMNS.map(col => {
        const apps = getAppsForColumn(col.id);
        return (
          <div 
            key={col.id} 
            className={`kanban-column ${dragOverCol === col.id ? 'drag-over' : ''}`}
            onDragOver={e => handleDragOver(e, col.id)}
            onDragLeave={e => handleDragLeave(e, col.id)}
            onDrop={e => handleDrop(e, col.id)}
          >
            <div className="kanban-column-header">
              <span>{col.label}</span>
              <span className="kanban-count">{apps.length}</span>
            </div>
            {apps.map(app => (
              <ApplicationCard 
                key={app.id} 
                app={app} 
                onStatusChange={(newStatus) => onStatusChange(app.id, newStatus)}
                onDeleteApp={() => onDeleteApp(app.id)}
                columns={COLUMNS}
              />
            ))}
          </div>
        );
      })}
    </div>
  );
}
