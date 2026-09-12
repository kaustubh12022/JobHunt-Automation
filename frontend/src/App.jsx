import React from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Tracker from './pages/Tracker';
import JobDetailPage from './pages/JobDetailPage';
import ManualTailor from './pages/ManualTailor';
import PendingTailors from './pages/PendingTailors';
import { LayoutDashboard, Activity, LayoutGrid, FileEdit, Clock } from 'lucide-react';

function Layout({ children }) {
  const location = useLocation();
  const isDashboard = location.pathname === '/';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', width: '100vw' }}>
      {/* Desktop Top Nav */}
      <nav className="desktop-only" style={{ padding: '16px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(255,255,255,0.1)', background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(12px)', zIndex: 10 }}>
        <div style={{ fontSize: '20px', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '8px', background: 'linear-gradient(135deg, var(--cyan), #3b82f6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
          AutoApply
        </div>
        <div style={{ display: 'flex', gap: '24px' }}>
          <Link to="/" style={{ color: isDashboard ? 'var(--cyan)' : 'white', textDecoration: 'none', fontWeight: isDashboard ? '600' : '400' }}>Dashboard</Link>
          <Link to="/pending" style={{ color: location.pathname === '/pending' ? 'var(--cyan)' : 'white', textDecoration: 'none', fontWeight: location.pathname === '/pending' ? '600' : '400' }}>Pending Tailors</Link>
          <Link to="/tracker" style={{ color: location.pathname === '/tracker' || location.pathname.startsWith('/tracker/job/') ? 'var(--cyan)' : 'white', textDecoration: 'none', fontWeight: location.pathname === '/tracker' || location.pathname.startsWith('/tracker/job/') ? '600' : '400' }}>Tracker</Link>
          <Link to="/tailor" style={{ color: location.pathname === '/tailor' ? 'var(--cyan)' : 'white', textDecoration: 'none', fontWeight: location.pathname === '/tailor' ? '600' : '400' }}>Manual Tailor</Link>
        </div>
      </nav>

      <main style={{ flex: 1, position: 'relative', overflowY: 'auto' }}>
        {children}
      </main>

      {/* Mobile Bottom Nav */}
      <nav className="mobile-bottom-nav">
        <Link to="/" className={`mobile-nav-item ${isDashboard ? 'active' : ''}`}>
          <LayoutDashboard size={24} />
          <span>Dashboard</span>
        </Link>
        <Link to="/pending" className={`mobile-nav-item ${location.pathname === '/pending' ? 'active' : ''}`}>
          <Clock size={24} />
          <span>Pending</span>
        </Link>
        <Link to="/tracker" className={`mobile-nav-item ${location.pathname === '/tracker' || location.pathname.startsWith('/tracker/job/') ? 'active' : ''}`}>
          <LayoutGrid size={24} />
          <span>Tracker</span>
        </Link>
        <Link to="/tailor" className={`mobile-nav-item ${location.pathname === '/tailor' ? 'active' : ''}`}>
          <FileEdit size={24} />
          <span>Tailor</span>
        </Link>
      </nav>
    </div>
  );
}

import LivePipeline from './pages/LivePipeline';

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/live" element={<LivePipeline />} />
          <Route path="/pending" element={<PendingTailors />} />
          <Route path="/tracker" element={<Tracker />} />
          <Route path="/tracker/job/:jobId" element={<JobDetailPage />} />
          <Route path="/tailor" element={<ManualTailor />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
