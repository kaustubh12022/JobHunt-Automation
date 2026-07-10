import React, { useState, useEffect } from 'react';
import { supabase } from '../lib/supabase';
import KanbanBoard from '../components/tracker/KanbanBoard';
import FilterBar from '../components/tracker/FilterBar';

export default function Tracker() {
  const [applications, setApplications] = useState([]);
  const [runs, setRuns] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState('all');
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [dateFilter, setDateFilter] = useState('');
  const [platformFilter, setPlatformFilter] = useState('');
  const [jobTypeFilter, setJobTypeFilter] = useState('');

  useEffect(() => {
    fetchRuns();
  }, []);

  useEffect(() => {
    fetchApplications();
    
    // Real-Time Tracker Refresh
    const channel = supabase.channel('custom-all-channel')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'applications' }, (payload) => {
        console.log('Change received!', payload);
        fetchApplications();
      })
      .subscribe();
      
    return () => {
      supabase.removeChannel(channel);
    };
  }, [selectedRunId]);

  const fetchRuns = async () => {
    const { data, error } = await supabase
      .from('pipeline_runs')
      .select('*')
      .order('started_at', { ascending: false });
    
    if (!error && data) {
      setRuns(data);
      if (selectedRunId === 'all' && data.length > 0) {
        // By default, find the most recent 'prod' run
        const latestProdRun = data.find(r => r.mode === 'prod');
        if (latestProdRun) {
          setSelectedRunId(latestProdRun.id);
        }
      }
    }
  };

  const fetchApplications = async () => {
    setLoading(true);
    let query = supabase
      .from('applications')
      .select(`
        id,
        status,
        notes,
        tracked_jobs!inner (
          id,
          title,
          company,
          score,
          source,
          job_type,
          url,
          missing_skills,
          pdf_filename,
          run_id,
          created_at
        )
      `)
      .order('created_at', { ascending: false });
      
    if (selectedRunId !== 'all') {
      query = query.eq('tracked_jobs.run_id', selectedRunId);
    }
    
    const { data, error } = await query;
    if (error) {
      console.error('Error fetching applications:', error);
    } else {
      setApplications(data);
    }
    setLoading(false);
  };

  const handleDeleteRun = async () => {
    if (selectedRunId === 'all') return;
    if (!window.confirm("Are you sure you want to permanently delete this pipeline run and all its local files?")) return;
    
    try {
      const res = await fetch(`/api/runs/${selectedRunId}`, { method: 'DELETE' });
      if (res.ok) {
        alert("Run deleted successfully.");
        setSelectedRunId('all');
        fetchRuns();
      } else {
        const err = await res.json();
        alert("Failed to delete run: " + err.error);
      }
    } catch (e) {
      console.error("Delete failed", e);
    }
  };

  const handleDeleteApp = async (appId) => {
    if (!window.confirm("Are you sure you want to permanently delete this application?")) return;
    
    try {
      const res = await fetch(`/api/applications/${appId}`, { method: 'DELETE' });
      if (res.ok) {
        fetchApplications();
      } else {
        const err = await res.json();
        alert("Failed to delete application: " + err.error);
      }
    } catch (e) {
      console.error("Delete failed", e);
    }
  };

  const handleStatusChange = async (appId, newStatus) => {
    // Optimistic update
    setApplications(prev => prev.map(app => 
      app.id === appId ? { ...app, status: newStatus } : app
    ));

    const { error } = await supabase
      .from('applications')
      .update({ status: newStatus })
      .eq('id', appId);
      
    if (error) {
      console.error('Error updating status', error);
      fetchApplications(); // revert
    } else {
      // Record history
      await supabase.from('status_history').insert({
        application_id: appId,
        new_status: newStatus
      });
    }
  };

  const getJob = (app) => {
    const tj = app.tracked_jobs;
    return Array.isArray(tj) ? tj[0] : tj;
  };

  const filteredApps = applications.filter(app => {
    const job = getJob(app);
    if (!job) return false;
    
    // Text search (name/company)
    if (search) {
      const s = search.toLowerCase();
      const title = job.title?.toLowerCase() || '';
      const company = job.company?.toLowerCase() || '';
      if (!title.includes(s) && !company.includes(s)) return false;
    }
    
    // Date filter
    if (dateFilter) {
      const createdDate = job.created_at?.split('T')[0] || app.created_at?.split('T')[0];
      if (createdDate !== dateFilter) return false;
    }
    
    // Platform filter
    if (platformFilter) {
      const src = job.source?.toLowerCase() || '';
      if (platformFilter === 'workday' && !src.startsWith('workday')) return false;
      if (platformFilter !== 'workday' && src !== platformFilter) return false;
    }
    
    // Job Type filter
    if (jobTypeFilter) {
      const jt = job.job_type || 'fulltime';
      if (jt !== jobTypeFilter) return false;
    }
    
    return true;
  });

  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto', position: 'relative' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px', flexWrap: 'wrap', gap: '16px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: 700, margin: 0 }}>Application Tracker</h1>
        
        <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-start', flexDirection: 'column' }}>
          <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
            <select 
              value={selectedRunId} 
              onChange={e => setSelectedRunId(e.target.value)}
              style={{ padding: '8px 12px', borderRadius: '8px', border: '1px solid var(--border-color)', background: 'var(--bg-panel)' }}
            >
              <option value="all">All Pipeline Runs</option>
              {runs.map(r => (
                <option key={r.id} value={r.id}>
                  {new Date(r.started_at).toLocaleString()} ({r.mode.toUpperCase()}) - {r.jobs_shortlisted} Resumes
                </option>
              ))}
            </select>
            
            {selectedRunId !== 'all' && (
              <button className="btn-danger" onClick={handleDeleteRun}>
                Delete Run
              </button>
            )}
          </div>
          
          <FilterBar 
            search={search} onSearchChange={setSearch} 
            dateFilter={dateFilter} onDateChange={setDateFilter} 
            platformFilter={platformFilter} onPlatformChange={setPlatformFilter}
            jobTypeFilter={jobTypeFilter} onJobTypeChange={setJobTypeFilter}
          />
        </div>
      </div>
      
      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
          Loading your applications...
        </div>
      ) : (
        <KanbanBoard applications={filteredApps} onStatusChange={handleStatusChange} onDeleteApp={handleDeleteApp} />
      )}
    </div>
  );
}
