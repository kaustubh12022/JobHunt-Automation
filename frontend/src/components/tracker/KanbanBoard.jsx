import React from 'react';
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

export default function KanbanBoard({ applications, onStatusChange }) {
  const getAppsForColumn = (statusId) => applications.filter(app => app.status === statusId);

  const handleDrop = (e, statusId) => {
    e.preventDefault();
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
            className="kanban-column"
            onDragOver={e => e.preventDefault()}
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
                columns={COLUMNS}
              />
            ))}
          </div>
        );
      })}
    </div>
  );
}
