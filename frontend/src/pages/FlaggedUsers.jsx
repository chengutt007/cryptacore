import React, { useState, useEffect } from 'react'
import { usersAPI } from '../api/client'

const DEMO_USERS = [
  { user_id: 'usr_7f3a29', crypta_risk_score: 91, risk_level: 'CRITICAL', is_flagged: true, account_age_days: 12, total_orders: 45, total_returns: 38, last_analyzed: new Date().toISOString() },
  { user_id: 'usr_2b8c44', crypta_risk_score: 78, risk_level: 'HIGH', is_flagged: true, account_age_days: 30, total_orders: 22, total_returns: 17, last_analyzed: new Date(Date.now() - 3600000).toISOString() },
  { user_id: 'usr_9d1e71', crypta_risk_score: 74, risk_level: 'HIGH', is_flagged: true, account_age_days: 8, total_orders: 67, total_returns: 12, last_analyzed: new Date(Date.now() - 7200000).toISOString() },
  { user_id: 'usr_5c3f88', crypta_risk_score: 63, risk_level: 'MEDIUM', is_flagged: true, account_age_days: 55, total_orders: 18, total_returns: 6, last_analyzed: new Date(Date.now() - 10800000).toISOString() },
  { user_id: 'usr_3a7b12', crypta_risk_score: 61, risk_level: 'MEDIUM', is_flagged: true, account_age_days: 90, total_orders: 31, total_returns: 8, last_analyzed: new Date(Date.now() - 14400000).toISOString() },
  { user_id: 'usr_8e2d55', crypta_risk_score: 57, risk_level: 'MEDIUM', is_flagged: true, account_age_days: 120, total_orders: 9, total_returns: 2, last_analyzed: new Date(Date.now() - 18000000).toISOString() },
]

function ScoreBar({ score }) {
  const color = score >= 75 ? '#ef4444' : score >= 55 ? '#f59e0b' : '#06b6d4'
  return (
    <div className="score-bar-wrap">
      <div className="score-bar">
        <div className="score-bar-fill" style={{ width: `${score}%`, background: `linear-gradient(90deg, ${color}, ${color}99)` }} />
      </div>
      <span className="score-value" style={{ color }}>{score?.toFixed(1)}</span>
    </div>
  )
}

export default function FlaggedUsers() {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('ALL')
  const [expandedRow, setExpandedRow] = useState(null)

  useEffect(() => {
    usersAPI.flagged(100, 40)
      .then(r => setUsers(r.data))
      .catch(() => {
        // Mock V2 data for demo if backend fails
        setUsers(DEMO_USERS.map(u => ({
          ...u,
          top_risk_factor: u.crypta_risk_score > 80 ? 'Excessive Return Rate' : 'Suspicious Login Velocity',
          explanation: [
            'User has return rate > 75% on high value items.',
            'Login activity detected from 3 different countries in 24h.',
            'Potential refund abuse: 4 consecutive returns of undamaged goods.'
          ],
          fraud_subtypes: u.crypta_risk_score > 80 ? [{ label: 'Refund Abuse' }, { label: 'Policy Gaming' }] : []
        })))
      })
      .finally(() => setLoading(false))
  }, [])

  const filtered = filter === 'ALL' ? users : users.filter(u => u.risk_level === filter)

  const timeAgo = (iso) => {
    const diff = Date.now() - new Date(iso).getTime()
    if (diff < 60000) return 'just now'
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
    return `${Math.floor(diff / 86400000)}d ago`
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Flagged Users</h1>
        <p className="page-subtitle">High-risk users detected by the Crypta AI engine (V2)</p>
      </div>

      {/* Summary row */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
        {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM'].map(f => {
          const count = f === 'ALL' ? users.length : users.filter(u => u.risk_level === f).length
          const colors = { CRITICAL: '#ef4444', HIGH: '#f59e0b', MEDIUM: '#06b6d4', ALL: '#7c3aed' }
          return (
            <button key={f} onClick={() => setFilter(f)}
              className="btn" style={{
                background: filter === f ? `${colors[f]}20` : 'var(--bg-card)',
                border: `1px solid ${filter === f ? colors[f] : 'var(--border)'}`,
                color: filter === f ? colors[f] : 'var(--text-secondary)',
                gap: 8
              }}>
              {f} <span style={{
                background: filter === f ? colors[f] : 'var(--border)',
                color: filter === f ? 'white' : 'var(--text-muted)',
                borderRadius: 20, padding: '1px 7px', fontSize: 11, fontWeight: 700
              }}>{count}</span>
            </button>
          )
        })}
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
          <div className="spinner" style={{ width: 28, height: 28 }} />
        </div>
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: 40 }}></th>
                <th>User ID</th>
                <th>Risk Level</th>
                <th>Crypta Score</th>
                <th>Top Factor</th>
                <th>Orders</th>
                <th>Returns</th>
                <th>Last Analyzed</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr><td colSpan={8} style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
                  No users matching this filter
                </td></tr>
              ) : filtered.map(u => {
                const returnRate = u.total_orders > 0
                  ? ((u.total_returns / u.total_orders) * 100).toFixed(0) : '0'
                const isExpanded = expandedRow === u.user_id
                return (
                  <React.Fragment key={u.user_id}>
                    <tr onClick={() => setExpandedRow(isExpanded ? null : u.user_id)} 
                        style={{ cursor: 'pointer', background: isExpanded ? 'var(--bg-secondary)' : 'transparent' }}>
                      <td style={{ textAlign: 'center', color: 'var(--text-muted)' }}>{isExpanded ? '▾' : '▸'}</td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <div style={{
                            width: 24, height: 24, borderRadius: 6,
                            background: `hsl(${parseInt(u.user_id.slice(-3), 16) % 360}, 65%, 35%)`,
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontSize: 10, fontWeight: 700, color: 'white', flexShrink: 0
                          }}>
                            {u.user_id.slice(-2).toUpperCase()}
                          </div>
                          <span style={{ fontFamily: 'monospace', color: 'var(--text-primary)', fontSize: 13 }}>
                            {u.user_id}
                          </span>
                        </div>
                      </td>
                      <td><span className={`risk-badge ${u.risk_level}`}>{u.risk_level}</span></td>
                      <td style={{ minWidth: 140 }}><ScoreBar score={u.crypta_risk_score} /></td>
                      <td style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{u.top_risk_factor || 'Suspicious Activity'}</td>
                      <td style={{ color: 'var(--text-primary)' }}>{u.total_orders}</td>
                      <td style={{ color: 'var(--text-primary)' }}>{u.total_returns} <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>({returnRate}%)</span></td>
                      <td style={{ color: 'var(--text-muted)', fontSize: 12 }}>{timeAgo(u.last_analyzed)}</td>
                    </tr>
                    {isExpanded && (
                      <tr>
                        <td colSpan={8} style={{ padding: '0 0 20px 0', background: 'var(--bg-secondary)' }}>
                          <div style={{ padding: '16px 40px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
                            <div>
                              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 12 }}>AI Explanation</div>
                              <ul style={{ paddingLeft: 14, display: 'flex', flexDirection: 'column', gap: 6 }}>
                                {u.explanation?.map((ex, i) => (
                                  <li key={i} style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{ex}</li>
                                ))}
                              </ul>
                            </div>
                            <div>
                                <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 12 }}>Fraud Types</div>
                                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                                  {u.fraud_subtypes?.map((st, i) => (
                                    <span key={i} style={{ padding: '4px 10px', borderRadius: 4, background: '#ef444420', color: '#fca5a5', fontSize: 11, border: '1px solid #ef444440' }}>
                                      {st.label}
                                    </span>
                                  )) || <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>General Anomaly</span>}
                                </div>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
