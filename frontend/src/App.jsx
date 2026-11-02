import React, { useState } from 'react'
import { BrowserRouter, Routes, Route, NavLink, useLocation } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import ReviewAnalyzer from './pages/ReviewAnalyzer'
import FlaggedUsers from './pages/FlaggedUsers'
import Orders from './pages/Orders'
import RiskExplorer from './pages/RiskExplorer'
import FraudAlerts from './pages/FraudAlerts'

const NAV = [
  { path: '/', label: 'Dashboard', icon: '⊞', exact: true },
  { path: '/reviews', label: 'Review Analyzer', icon: '✍' },
  { path: '/users', label: 'Flagged Users', icon: '⚑' },
  { path: '/orders', label: 'Suspicious Orders', icon: '📦' },
  { path: '/fraud-alerts', label: 'Fraud Alerts', icon: '🚨' },
  { path: '/explorer', label: 'Risk Explorer', icon: '🔍' },
]

function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="logo-mark">
          <div className="logo-shield">🛡️</div>
          <div>
            <div className="logo-text">Crypta Core AI</div>
            <div className="logo-sub">Fraud Detection</div>
          </div>
        </div>
      </div>
      <nav className="sidebar-nav">
        <div className="nav-section-label">Navigation</div>
        {NAV.map(({ path, label, icon, exact }) => (
          <NavLink
            key={path}
            to={path}
            end={exact}
            className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
          >
            <span className="nav-icon">{icon}</span>
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-footer">
        <div className="status-pill">
          <div className="status-dot" />
          AI Engine Online
        </div>
      </div>
    </aside>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">
        <Sidebar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/reviews" element={<ReviewAnalyzer />} />
            <Route path="/users" element={<FlaggedUsers />} />
            <Route path="/orders" element={<Orders />} />
            <Route path="/fraud-alerts" element={<FraudAlerts />} />
            <Route path="/explorer" element={<RiskExplorer />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
