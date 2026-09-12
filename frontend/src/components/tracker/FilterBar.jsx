import React from 'react';

export default function FilterBar({ 
  search, onSearchChange, 
  dateFilter, onDateChange,
  platformFilter, onPlatformChange,
  jobTypeFilter, onJobTypeChange
}) {
  const selectStyle = {
    padding: '9px 16px',
    borderRadius: '8px',
    border: '1px solid rgba(255, 255, 255, 0.25)',
    background: 'rgba(255, 255, 255, 0.1)',
    color: '#ffffff',
    outline: 'none',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
    boxShadow: 'var(--shadow-sm)',
    colorScheme: 'light'
  };

  const optionStyle = {
    color: '#111827',
    background: '#ffffff',
    fontWeight: 600
  };

  return (
    <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
      <input 
        type="text" 
        placeholder="Search jobs or companies..." 
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
        style={{ ...selectStyle, minWidth: '250px', cursor: 'text' }}
      />
      <input 
        type="date" 
        value={dateFilter}
        onChange={(e) => onDateChange(e.target.value)}
        style={{ ...selectStyle, colorScheme: 'dark' }}
      />
      <select 
        value={platformFilter || ''} 
        onChange={(e) => onPlatformChange(e.target.value)}
        style={selectStyle}
      >
        <option value="" style={optionStyle}>All Platforms</option>
        <option value="linkedin" style={optionStyle}>LinkedIn</option>
        <option value="indeed" style={optionStyle}>Indeed</option>
        <option value="glassdoor" style={optionStyle}>Glassdoor</option>
        <option value="zip_recruiter" style={optionStyle}>ZipRecruiter</option>
        <option value="google" style={optionStyle}>Google</option>
        <option value="workday" style={optionStyle}>Workday</option>
        <option value="jsonld" style={optionStyle}>JSON-LD</option>
        <option value="manual" style={optionStyle}>Manual</option>
      </select>
      <select 
        value={jobTypeFilter || ''} 
        onChange={(e) => onJobTypeChange(e.target.value)}
        style={selectStyle}
      >
        <option value="" style={optionStyle}>All Job Types</option>
        <option value="fulltime" style={optionStyle}>Full-Time</option>
        <option value="internship" style={optionStyle}>Internship</option>
      </select>
    </div>
  );
}
