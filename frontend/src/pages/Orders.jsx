import React, { useState, useEffect } from 'react'
import { dashboardAPI } from '../api/client'

const DEMO_ORDERS = [
  { order_id: 'ORD-7f3a2901', user_id: 'usr_7f3a29', amount: 1499.99, fraud_risk_score: 87, payment_fraud_score: 91, is_returned: true, is_suspicious: true, created_at: new Date().toISOString() },
  { order_id: 'ORD-2b8c4422', user_id: 'usr_2b8c44', amount: 899.00, fraud_risk_score: 78, payment_fraud_score: 82, is_returned: false, is_suspicious: true, created_at: new Date(Date.now() - 3600000).toISOString() },
  { order_id: 'ORD-9d1e7133', user_id: 'usr_9d1e71', amount: 2340.50, fraud_risk_score: 74, payment_fraud_score: 68, is_returned: true, is_suspicious: true, created_at: new Date(Date.now() - 7200000).toISOString() },
  { order_id: 'ORD-5c3f8844', user_id: 'usr_5c3f88', amount: 450.00, fraud_risk_score: 63, payment_fraud_score: 55, is_returned: false, is_suspicious: true, created_at: new Date(Date.now() - 10800000).toISOString() },
  { order_id: 'ORD-3a7b1255', user_id: 'usr_3a7b12', amount: 187.99, fraud_risk_score: 61, payment_fraud_score: 60, is_returned: true, is_suspicious: true, created_at: new Date(Date.now() - 14400000).toISOString() },
  { order_id: 'ORD-8e2d5566', user_id: 'usr_8e2d55', amount: 3100.00, fraud_risk_score: 58, payment_fraud_score: 72, is_returned: false, is_suspicious: true, created_at: new Date(Date.now() - 18000000).toISOString() },
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

export default function Orders() {
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [sortBy, setSortBy] = useState('fraud_risk_score')

  useEffect(() => {
    dashboardAPI.suspiciousOrders(100)
      .then(r => setOrders(r.data))
      .catch(() => setOrders(DEMO_ORDERS))
      .finally(() => setLoading(false))
  }, [])

  const sorted = [...orders].sort((a, b) => b[sortBy] - a[sortBy])

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
        <h1 className="page-title">Suspicious Orders</h1>
        <p className="page-subtitle">Orders flagged by payment and return fraud models</p>
      </div>

      {/* Sort controls */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <span style={{ color: 'var(--text-muted)', fontSize: 12, alignSelf: 'center' }}>Sort by:</span>
        {[
          { key: 'fraud_risk_score', label: 'Overall Risk' },
          { key: 'payment_fraud_score', label: 'Payment Risk' },
          { key: 'amount', label: 'Amount' },
        ].map(({ key, label }) => (
          <button key={key} onClick={() => setSortBy(key)}
            className="btn" style={{
              background: sortBy === key ? 'var(--accent-cyan-dim)' : 'var(--bg-card)',
              border: `1px solid ${sortBy === key ? 'var(--accent-cyan)' : 'var(--border)'}`,
              color: sortBy === key ? 'var(--accent-cyan)' : 'var(--text-secondary)',
            }}>
            {label}
          </button>
        ))}
        <div style={{ flex: 1 }} />
        <span style={{ color: 'var(--text-muted)', fontSize: 12, alignSelf: 'center' }}>
          {orders.length} suspicious orders found
        </span>
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
                <th>Order ID</th>
                <th>User</th>
                <th>Amount</th>
                <th>Overall Risk</th>
                <th>Payment Risk</th>
                <th>Returned</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {sorted.length === 0 ? (
                <tr><td colSpan={7} style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
                  No suspicious orders detected
                </td></tr>
              ) : sorted.map(o => {
                const riskLevel = o.fraud_risk_score >= 75 ? 'CRITICAL' : o.fraud_risk_score >= 55 ? 'HIGH' : 'MEDIUM'
                return (
                  <tr key={o.order_id}>
                    <td>
                      <span style={{ fontFamily: 'monospace', color: 'var(--text-primary)', fontSize: 12 }}>
                        {o.order_id}
                      </span>
                    </td>
                    <td>
                      <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{o.user_id}</span>
                    </td>
                    <td>
                      <span style={{ color: 'var(--text-primary)', fontWeight: 600, fontFamily: 'Space Grotesk' }}>
                        ${o.amount?.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </span>
                    </td>
                    <td style={{ minWidth: 160 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <ScoreBar score={o.fraud_risk_score} />
                        <span className={`risk-badge ${riskLevel}`}>{riskLevel}</span>
                      </div>
                    </td>
                    <td style={{ minWidth: 140 }}><ScoreBar score={o.payment_fraud_score} /></td>
                    <td>
                      {o.is_returned
                        ? <span style={{ color: '#f59e0b', fontWeight: 600, fontSize: 12 }}>⤴ Returned</span>
                        : <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>—</span>}
                    </td>
                    <td style={{ color: 'var(--text-muted)' }}>{timeAgo(o.created_at)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
