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
  const [newRunData, setNewRunData] = useState(null);

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
      if (data.length > 0) {
        const latestRun = data[0];
        
        // Notification logic
        const lastSeen = localStorage.getItem('last_seen_run');
        if (lastSeen !== latestRun.id) {
          const { data: jobs } = await supabase.from('tracked_jobs').select('title, company, score').eq('run_id', latestRun.id);
          setNewRunData({ ...latestRun, jobs: jobs || [] });
        }

        if (selectedRunId === 'all') {
          // By default, select the most recent run for today if we just loaded
          const today = new Date().toISOString().split('T')[0];
          if (latestRun.started_at.startsWith(today)) {
            setSelectedRunId(latestRun.id);
          }
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
    
    return true;
  });

  const dismissNotification = () => {
    if (newRunData) {
      localStorage.setItem('last_seen_run', newRunData.id);
      setNewRunData(null);
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto', position: 'relative' }}>
      {/* NEW RUN NOTIFICATION MODAL */}
      {newRunData && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', zIndex: 9999, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <div style={{ background: '#fff', borderRadius: '16px', padding: '32px', maxWidth: '500px', width: '90%', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)' }}>
            <h2 style={{ margin: '0 0 16px', color: '#16a34a', display: 'flex', alignItems: 'center', gap: '8px' }}>
              🎉 Pipeline Completed!
            </h2>
            <p style={{ margin: '0 0 24px', color: '#64748b' }}>Here are the results from your most recent run:</p>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '24px' }}>
              <div style={{ background: '#f8fafc', padding: '16px', borderRadius: '8px', textAlign: 'center' }}>
                <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#334155' }}>{newRunData.jobs_scraped}</div>
                <div style={{ fontSize: '12px', color: '#64748b', textTransform: 'uppercase' }}>Jobs Scraped</div>
              </div>
              <div style={{ background: '#f8fafc', padding: '16px', borderRadius: '8px', textAlign: 'center' }}>
                <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#334155' }}>{newRunData.jobs_scored}</div>
                <div style={{ fontSize: '12px', color: '#64748b', textTransform: 'uppercase' }}>AI Scored</div>
              </div>
              <div style={{ background: '#f8fafc', padding: '16px', borderRadius: '8px', textAlign: 'center' }}>
                <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#16a34a' }}>{newRunData.jobs_shortlisted}</div>
                <div style={{ fontSize: '12px', color: '#64748b', textTransform: 'uppercase' }}>Shortlisted</div>
              </div>
              <div style={{ background: '#f8fafc', padding: '16px', borderRadius: '8px', textAlign: 'center' }}>
                <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#2563eb' }}>{newRunData.resumes_generated}</div>
                <div style={{ fontSize: '12px', color: '#64748b', textTransform: 'uppercase' }}>Resumes Gen</div>
              </div>
            </div>

            {newRunData.jobs && newRunData.jobs.length > 0 && (
              <div style={{ marginBottom: '24px' }}>
                <h4 style={{ margin: '0 0 8px', color: '#334155' }}>Shortlisted Matches:</h4>
                <ul style={{ margin: 0, paddingLeft: '20px', color: '#475569', fontSize: '14px' }}>
                  {newRunData.jobs.filter(j => j.score >= 50).map((j, i) => (
                    <li key={i} style={{ marginBottom: '4px' }}>
                      <strong>{j.company}</strong> ({j.title}) <span style={{ color: '#16a34a', fontWeight: 'bold' }}>{j.score}%</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <button onClick={dismissNotification} style={{ width: '100%', padding: '12px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer' }}>
              Awesome, let's view them!
            </button>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: '16px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: 700, margin: 0 }}>Application Tracker</h1>
        
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

          <FilterBar search={search} onSearchChange={setSearch} dateFilter={dateFilter} onDateChange={setDateFilter} />
        </div>
      </div>
      
      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
          Loading your applications...
        </div>
      ) : (
        <KanbanBoard applications={filteredApps} onStatusChange={handleStatusChange} />
      )}
    </div>
  );
}
