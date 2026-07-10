import React from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Tracker from './pages/Tracker';
import JobDetailPage from './pages/JobDetailPage';
import ManualTailor from './pages/ManualTailor';
function Layout({ children }) {
  const location = useLocation();
  const isDashboard = location.pathname === '/';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', width: '100vw' }}>
      <nav style={{ padding: '16px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: 'var(--glass-border)', background: 'var(--bg-panel)' }}>
        <div style={{ fontSize: '20px', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ color: 'var(--cyan)' }}>⚡</span> AutoApply
        </div>
        <div style={{ display: 'flex', gap: '16px' }}>
          <Link to="/" style={{ color: isDashboard ? 'var(--cyan)' : 'white', textDecoration: 'none', fontWeight: isDashboard ? '600' : '400', textShadow: isDashboard ? 'var(--glow)' : 'none' }}>Dashboard</Link>
          <Link to="/tracker" style={{ color: location.pathname === '/tracker' || location.pathname.startsWith('/tracker/job/') ? 'var(--cyan)' : 'white', textDecoration: 'none', fontWeight: location.pathname === '/tracker' || location.pathname.startsWith('/tracker/job/') ? '600' : '400', textShadow: location.pathname === '/tracker' || location.pathname.startsWith('/tracker/job/') ? 'var(--glow)' : 'none' }}>Tracker</Link>
          <Link to="/tailor" style={{ color: location.pathname === '/tailor' ? 'var(--cyan)' : 'white', textDecoration: 'none', fontWeight: location.pathname === '/tailor' ? '600' : '400', textShadow: location.pathname === '/tailor' ? 'var(--glow)' : 'none' }}>Manual Tailor</Link>
        </div>
      </nav>
      <main style={{ flex: 1, position: 'relative' }}>
        {children}
      </main>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/tracker" element={<Tracker />} />
          <Route path="/tracker/job/:jobId" element={<JobDetailPage />} />
          <Route path="/tailor" element={<ManualTailor />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
