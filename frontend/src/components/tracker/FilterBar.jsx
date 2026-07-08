import React from 'react';

export default function FilterBar({ search, onSearchChange, dateFilter, onDateChange }) {
  return (
    <div style={{ display: 'flex', gap: '12px' }}>
      <input 
        type="text" 
        placeholder="Search jobs or companies..." 
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
        style={{
          padding: '8px 16px',
          borderRadius: '8px',
          border: '1px solid var(--border-color)',
          background: 'var(--bg-panel)',
          color: 'var(--text-main)',
          outline: 'none',
          fontSize: '14px',
          minWidth: '250px',
          boxShadow: 'var(--shadow-sm)'
        }}
      />
      <input 
        type="date" 
        value={dateFilter}
        onChange={(e) => onDateChange(e.target.value)}
        style={{
          padding: '8px 16px',
          borderRadius: '8px',
          border: '1px solid var(--border-color)',
          background: 'var(--bg-panel)',
          color: 'var(--text-main)',
          outline: 'none',
          fontSize: '14px',
          boxShadow: 'var(--shadow-sm)'
        }}
      />
    </div>
  );
}
