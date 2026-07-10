import React from 'react';

export default function FilterBar({ 
  search, onSearchChange, 
  dateFilter, onDateChange,
  platformFilter, onPlatformChange,
  jobTypeFilter, onJobTypeChange
}) {
  const selectStyle = {
    padding: '8px 16px',
    borderRadius: '8px',
    border: '1px solid var(--border-color)',
    background: 'var(--bg-panel)',
    color: 'var(--text-main)',
    outline: 'none',
    fontSize: '14px',
    boxShadow: 'var(--shadow-sm)'
  };

  return (
    <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
      <input 
        type="text" 
        placeholder="Search jobs or companies..." 
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
        style={{ ...selectStyle, minWidth: '250px' }}
      />
      <input 
        type="date" 
        value={dateFilter}
        onChange={(e) => onDateChange(e.target.value)}
        style={selectStyle}
      />
      <select 
        value={platformFilter || ''} 
        onChange={(e) => onPlatformChange(e.target.value)}
        style={selectStyle}
      >
        <option value="">All Platforms</option>
        <option value="linkedin">LinkedIn</option>
        <option value="indeed">Indeed</option>
        <option value="glassdoor">Glassdoor</option>
        <option value="zip_recruiter">ZipRecruiter</option>
        <option value="google">Google</option>
        <option value="workday">Workday</option>
        <option value="jsonld">JSON-LD</option>
        <option value="manual">Manual</option>
      </select>
      <select 
        value={jobTypeFilter || ''} 
        onChange={(e) => onJobTypeChange(e.target.value)}
        style={selectStyle}
      >
        <option value="">All Job Types</option>
        <option value="fulltime">Full-Time</option>
        <option value="internship">Internship</option>
      </select>
    </div>
  );
}
