import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import EnhancedTabletDashboard from './pages/EnhancedTabletDashboard';
import Medications from './pages/Medications';
import Reminders from './pages/Reminders';
import Finance from './pages/Finance';
import Habits from './pages/Habits';
import Admin from './pages/Admin';
import './App.css';

function App() {
  return (
    <Router>
      <Routes>
        {/* Default route redirects to dashboard */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />

        {/* Main application routes */}
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/tablet" element={<EnhancedTabletDashboard />} />
        <Route path="/medications" element={<Medications />} />
        <Route path="/reminders" element={<Reminders />} />
        <Route path="/finance" element={<Finance />} />
        <Route path="/habits" element={<Habits />} />
        <Route path="/admin" element={<Admin />} />

        {/* Catch-all route for 404s - redirect to dashboard */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
