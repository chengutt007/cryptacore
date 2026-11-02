import React, { useState, useEffect } from 'react'
import { dashboardAPI } from '../api/client'
import {
  RadialBarChart, RadialBar, ResponsiveContainer,
  PieChart, Pie, Cell, Tooltip, Legend,
  AreaChart, Area, XAxis, YAxis, CartesianGrid
} from 'recharts'

const FRAUD_COLORS = {
  FAKE_REVIEW: '#06b6d4',
  RETURN_FRAUD: '#7c3aed',
  SUSPICIOUS_BEHAVIOR: '#f59e0b',
  PAYMENT_FRAUD: '#ef4444',
}

const FRAUD_LABELS = {
  FAKE_REVIEW: 'Fake Reviews',
  RETURN_FRAUD: 'Return Fraud',
  SUSPICIOUS_BEHAVIOR: 'Suspicious Behavior',
  PAYMENT_FRAUD: 'Payment Fraud',
}

// Generate mock time series for visual chart
function mockTimeSeries() {
  const now = Date.now()
  return Array.from({ length: 14 }, (_, i) => ({
    date: new Date(now - (13 - i) * 86400000).toLocaleDateString('en', { month: 'short', day: 'numeric' }),
    alerts: Math.floor(Math.random() * 30 + 5),
    flagged: Math.floor(Math.random() * 8 + 1),
  }))
}

const timeSeries = mockTimeSeries()

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([dashboardAPI.stats(), dashboardAPI.recentAlerts(10)])
      .then(([s, a]) => {
        setStats(s.data)
        setAlerts(a.data)
      })
      .catch(() => {
        // Demo data when backend is offline
        setStats({
          total_users_analyzed: 1284,
          flagged_users: 47,
          total_reviews_analyzed: 3561,
          fake_reviews_detected: 412,
          total_orders_analyzed: 8934,
          suspicious_orders: 129,
          avg_crypta_risk_score: 31.4,
          alerts_today: 18,
          fraud_breakdown: {
            FAKE_REVIEW: 412,
            RETURN_FRAUD: 178,
            SUSPICIOUS_BEHAVIOR: 74,
            PAYMENT_FRAUD: 93,
          }
        })
        setAlerts([
          { id: 1, user_id: 'usr_7f3a29', fraud_type: 'PAYMENT_FRAUD', risk_score: 87, risk_level: 'CRITICAL', explanation: ['VPN detected', 'Geo mismatch'], created_at: new Date().toISOString() },
          { id: 2, user_id: 'usr_1a8c44', fraud_type: 'RETURN_FRAUD', risk_score: 74, risk_level: 'HIGH', explanation: ['85% return rate'], created_at: new Date(Date.now() - 300000).toISOString() },
          { id: 3, user_id: 'usr_9d2e71', fraud_type: 'FAKE_REVIEW', risk_score: 63, risk_level: 'HIGH', explanation: ['Spam keywords detected'], created_at: new Date(Date.now() - 900000).toISOString() },
          { id: 4, user_id: 'usr_3b5f88', fraud_type: 'SUSPICIOUS_BEHAVIOR', risk_score: 58, risk_level: 'MEDIUM', explanation: ['High login frequency'], created_at: new Date(Date.now() - 1800000).toISOString() },
        ])
      })
      .finally(() => setLoading(false))
  }, [])

  const pieData = stats ? Object.entries(stats.fraud_breakdown).map(([k, v]) => ({
    name: FRAUD_LABELS[k] || k, value: v, color: FRAUD_COLORS[k] || '#94a3b8'
  })) : []

  const scoreColor = (s) => s >= 75 ? '#ef4444' : s >= 55 ? '#f59e0b' : s >= 35 ? '#06b6d4' : '#10b981'

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300, gap: 12 }}>
      <div className="spinner" /> <span style={{ color: 'var(--text-secondary)' }}>Loading dashboard...</span>
    </div>
  )

  const STAT_CARDS = [
    { label: 'Users Analyzed', value: stats?.total_users_analyzed?.toLocaleString(), icon: '👤', color: '#06b6d4' },
    { label: 'Flagged Users', value: stats?.flagged_users, icon: '⚑', color: '#ef4444' },
    { label: 'Reviews Analyzed', value: stats?.total_reviews_analyzed?.toLocaleString(), icon: '✍', color: '#7c3aed' },
    { label: 'Fake Reviews', value: stats?.fake_reviews_detected, icon: '🚫', color: '#f59e0b' },
    { label: 'Orders Analyzed', value: stats?.total_orders_analyzed?.toLocaleString(), icon: '📦', color: '#06b6d4' },
    { label: 'Suspicious Orders', value: stats?.suspicious_orders, icon: '⚠', color: '#ef4444' },
    { label: 'Avg Risk Score', value: `${stats?.avg_crypta_risk_score?.toFixed(1)}`, icon: '📊', color: '#10b981' },
    { label: "Today's Alerts", value: stats?.alerts_today, icon: '🔔', color: '#f59e0b' },
  ]

  const alertTypeIcon = (t) =>
    t === 'PAYMENT_FRAUD' ? '💳' : t === 'RETURN_FRAUD' ? '📦' : t === 'FAKE_REVIEW' ? '✍' : '👤'

  const timeAgo = (iso) => {
    const diff = Date.now() - new Date(iso).getTime()
    if (diff < 60000) return 'just now'
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
    return `${Math.floor(diff / 86400000)}d ago`
  }

  return (
    <div className="dashboard-container">
      {/* ── Modern Header ── */}
      <div className="dashboard-hero">
        <div className="hero-titles">
          <h1 className="hero-title">Platform Intelligence</h1>
          <p className="hero-subtitle">Real-time fraud analytics and system health</p>
        </div>
        
        {/* Top-level Critical Metrics */}
        <div className="hero-metrics">
          <div className="metric-pill metric-primary">
            <div className="metric-icon">📊</div>
            <div>
              <div className="metric-value">{stats?.avg_crypta_risk_score?.toFixed(1) || '0.0'}</div>
              <div className="metric-label">Avg Risk Score</div>
            </div>
          </div>
          <div className="metric-pill metric-danger">
            <div className="metric-icon">⚠</div>
            <div>
              <div className="metric-value">{stats?.flagged_users || 0}</div>
              <div className="metric-label">Active Threats</div>
            </div>
          </div>
          <div className="metric-pill metric-accent">
            <div className="metric-icon">🚨</div>
            <div>
              <div className="metric-value">{stats?.alerts_today || 0}</div>
              <div className="metric-label">Alerts Today</div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Split Layout ── */}
      <div className="dashboard-grid">
        
        {/* LEFT COLUMN: Data & Charts (Consumes 2/3 width) */}
        <div className="dashboard-main">
          
          {/* Quick Stats Strip */}
          <div className="quick-stats-strip">
            <div className="q-stat">
              <span className="q-val">{stats?.total_users_analyzed?.toLocaleString() || 0}</span>
              <span className="q-lab">Users Analyzed</span>
            </div>
            <div className="q-divider" />
            <div className="q-stat">
              <span className="q-val">{stats?.total_orders_analyzed?.toLocaleString() || 0}</span>
              <span className="q-lab">Orders Scanned</span>
            </div>
            <div className="q-divider" />
            <div className="q-stat">
              <span className="q-val text-red">{stats?.suspicious_orders || 0}</span>
              <span className="q-lab">Suspicious Orders</span>
            </div>
            <div className="q-divider" />
            <div className="q-stat">
              <span className="q-val">{stats?.total_reviews_analyzed?.toLocaleString() || 0}</span>
              <span className="q-lab">Reviews Analyzed</span>
            </div>
            <div className="q-divider" />
            <div className="q-stat">
              <span className="q-val text-orange">{stats?.fake_reviews_detected || 0}</span>
              <span className="q-lab">Fake Reviews</span>
            </div>
          </div>

          {/* 14-Day Trend Chart */}
          <div className="saas-card chart-span">
            <div className="saas-card-header">
              <h3 className="saas-card-title">Detection Volume (14 Days)</h3>
              <div className="saas-card-actions">
                <span className="status-dot-pulse"></span> Live Sync
              </div>
            </div>
            <div className="saas-card-body">
              <ResponsiveContainer width="100%" height={260}>
                <AreaChart data={timeSeries} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="gradAlerts" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                    </linearGradient>
                    <linearGradient id="gradFlagged" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#7c3aed" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#7c3aed" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                  <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 11, fontFamily: 'Space Grotesk' }} axisLine={false} tickLine={false} dy={10} />
                  <YAxis tick={{ fill: '#64748b', fontSize: 11, fontFamily: 'Space Grotesk' }} axisLine={false} tickLine={false} dx={-10} />
                  <Tooltip 
                    contentStyle={{ background: 'rgba(15, 23, 42, 0.9)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, fontSize: 13, boxShadow: '0 8px 32px rgba(0,0,0,0.4)', backdropFilter: 'blur(8px)' }}
                    itemStyle={{ color: '#f8fafc', fontWeight: 600 }}
                  />
                  <Area type="monotone" dataKey="alerts" stroke="#06b6d4" fill="url(#gradAlerts)" strokeWidth={3} name="Total Alerts" activeDot={{ r: 6, strokeWidth: 0, fill: '#06b6d4' }} />
                  <Area type="monotone" dataKey="flagged" stroke="#7c3aed" fill="url(#gradFlagged)" strokeWidth={3} name="Critical Flags" activeDot={{ r: 6, strokeWidth: 0, fill: '#7c3aed' }} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Fraud Distribution */}
          <div className="saas-card">
            <div className="saas-card-header">
              <h3 className="saas-card-title">Threat Distribution</h3>
            </div>
            <div className="saas-card-body pie-container">
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" innerRadius={70} outerRadius={100} paddingAngle={4} dataKey="value" stroke="none">
                    {pieData.map((entry, i) => (
                      <Cell key={i} fill={entry.color} style={{ filter: 'drop-shadow(0px 4px 12px rgba(0,0,0,0.3))' }} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ background: 'rgba(15, 23, 42, 0.9)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, fontSize: 13, backdropFilter: 'blur(8px)' }}
                    itemStyle={{ color: '#f8fafc', fontWeight: 600 }}
                  />
                  <Legend 
                    verticalAlign="middle" align="right" layout="vertical"
                    formatter={(v) => <span style={{ color: '#cbd5e1', fontSize: 12, fontWeight: 500, paddingLeft: 6 }}>{v}</span>}
                    iconType="circle" iconSize={10} wrapperStyle={{ right: 0 }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

        </div>

        {/* RIGHT COLUMN: Live Threat Feed (Consumes 1/3 width) */}
        <div className="dashboard-sidebar">
          <div className="saas-card feed-card">
            <div className="saas-card-header sticky-header">
              <h3 className="saas-card-title flex items-center gap-2">
                <span className="live-indicator"></span> Live Threat Feed
              </h3>
              <span className="feed-count">{alerts.length} events</span>
            </div>
            
            <div className="feed-list">
              {alerts.length === 0 ? (
                <div className="empty-feed">No active threats detected</div>
              ) : alerts.map((a, idx) => (
                <div key={a.id} className="feed-item" style={{ animationDelay: `${idx * 0.05}s` }}>
                  <div className="feed-icon" style={{ 
                    color: a.risk_level === 'CRITICAL' ? '#ef4444' : a.risk_level === 'HIGH' ? '#f59e0b' : '#06b6d4',
                    background: a.risk_level === 'CRITICAL' ? 'rgba(239,68,68,0.1)' : a.risk_level === 'HIGH' ? 'rgba(245,158,11,0.1)' : 'rgba(6,182,212,0.1)'
                  }}>
                    {alertTypeIcon(a.fraud_type)}
                  </div>
                  <div className="feed-content">
                    <div className="feed-top">
                      <span className="feed-type">{FRAUD_LABELS[a.fraud_type] || a.fraud_type}</span>
                      <span className="feed-time">{timeAgo(a.created_at)}</span>
                    </div>
                    <div className="feed-desc">
                      User <strong className="feed-user">{a.user_id}</strong> · {a.explanation?.[0] || 'Anomaly detected'}
                    </div>
                    <div className="feed-score">
                      Risk Score <span style={{ color: scoreColor(a.risk_score) }}>{a.risk_score}</span>
                      <div className="mini-score-bar">
                        <div className="mini-score-fill" style={{ width: `${a.risk_score}%`, background: scoreColor(a.risk_score) }} />
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
        
      </div>
    </div>
  )
}
