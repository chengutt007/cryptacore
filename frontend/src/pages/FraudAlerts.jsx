import React, { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { alertsAPI } from '../api/client'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(dt) {
  if (!dt) return '—'
  return new Date(dt).toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

const TYPE_META = {
  RETURN_FRAUD:        { label: '↩ Return Fraud',         color: '#f59e0b', bg: 'rgba(245,158,11,0.12)' },
  SUSPICIOUS_BEHAVIOR: { label: '👁 Suspicious Behavior',  color: '#06b6d4', bg: 'rgba(6,182,212,0.10)' },
  HIGH_RISK:           { label: '🚨 High Risk',            color: '#ef4444', bg: 'rgba(239,68,68,0.12)'  },
  PAYMENT_FRAUD:       { label: '💳 Payment Fraud',        color: '#a855f7', bg: 'rgba(168,85,247,0.12)' },
  PRICING_ANOMALY:     { label: '📊 Pricing Anomaly',      color: '#ec4899', bg: 'rgba(236,72,153,0.12)' },
  INVENTORY_MISMATCH:  { label: '📦 Inventory Mismatch',   color: '#84cc16', bg: 'rgba(132,204,22,0.10)'  },
  FAKE_REVIEW:         { label: '✍ Fake Review',           color: '#8b5cf6', bg: 'rgba(139,92,246,0.12)' },
}

function TypeBadge({ type }) {
  const m = TYPE_META[type] || { label: type, color: '#64748b', bg: 'rgba(100,116,139,0.1)' }
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', padding: '4px 10px',
      borderRadius: 20, fontSize: 11, fontWeight: 700,
      color: m.color, background: m.bg,
      border: `1px solid ${m.color}40`, whiteSpace: 'nowrap',
    }}>
      {m.label}
    </span>
  )
}

function ScorePill({ score }) {
  const color = score >= 80 ? '#ef4444' : score >= 60 ? '#f59e0b' : '#06b6d4'
  return (
    <span style={{
      fontWeight: 800, fontSize: 14,
      color, fontFamily: 'Space Grotesk',
    }}>
      {score?.toFixed(1)}
    </span>
  )
}

function SummaryCard({ label, value, color = 'var(--text-primary)', icon }) {
  return (
    <div className="card" style={{ padding: '16px 20px', display: 'flex', alignItems: 'center', gap: 14 }}>
      <div style={{ fontSize: 28 }}>{icon}</div>
      <div>
        <div style={{ fontSize: 22, fontWeight: 800, color, fontFamily: 'Space Grotesk' }}>{value}</div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</div>
      </div>
    </div>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────

const FILTER_TYPES = [
  { key: '', label: 'All Types' },
  { key: 'HIGH_RISK', label: '🚨 High Risk' },
  { key: 'RETURN_FRAUD', label: '↩ Return Fraud' },
  { key: 'SUSPICIOUS_BEHAVIOR', label: '👁 Suspicious Behavior' },
  { key: 'PAYMENT_FRAUD', label: '💳 Payment Fraud' },
  { key: 'PRICING_ANOMALY', label: '📊 Pricing Anomaly' },
]

const POLL_INTERVAL = 5000  // 5 seconds
const PAGE_SIZE = 50

export default function FraudAlerts() {
  const navigate = useNavigate()

  const [alerts, setAlerts] = useState([])
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filterType, setFilterType] = useState('')
  const [filterScore, setFilterScore] = useState(0)
  const [resolving, setResolving] = useState(null)
  const [page, setPage] = useState(0)
  const [liveCount, setLiveCount] = useState(0)  // tracks new alerts added by polling

  // Tracks IDs already rendered — used to append-only without duplicating
  const seenIdsRef = useRef(new Set())

  // ── Initial full load (shows spinner) ─────────────────────────────────────
  const initialLoad = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = {
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
        ...(filterType ? { alert_type: filterType } : {}),
        ...(filterScore > 0 ? { min_score: filterScore } : {}),
      }
      const [alertsRes, summaryRes] = await Promise.all([
        alertsAPI.get(params),
        alertsAPI.summary(),
      ])
      const incoming = alertsRes.data
      // Reset seen IDs and rebuild from fresh load
      seenIdsRef.current = new Set(incoming.map(a => a.id))
      setAlerts(incoming)
      setSummary(summaryRes.data)
    } catch (err) {
      setError('Failed to load alerts. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }, [filterType, filterScore, page])

  // ── Silent background poll (no spinner, append-only) ──────────────────────
  const pollAlerts = useCallback(async () => {
    try {
      // Always fetch latest 500 alerts so we catch any new ones
      const params = {
        limit: 500,
        offset: 0,
        ...(filterType ? { alert_type: filterType } : {}),
        ...(filterScore > 0 ? { min_score: filterScore } : {}),
      }
      const [alertsRes, summaryRes] = await Promise.all([
        alertsAPI.get(params),
        alertsAPI.summary(),
      ])

      const incoming = alertsRes.data
      const newAlerts = incoming.filter(a => !seenIdsRef.current.has(a.id))

      if (newAlerts.length > 0) {
        // Prepend new alerts at the top (newest first)
        newAlerts.forEach(a => seenIdsRef.current.add(a.id))
        setAlerts(prev => [...newAlerts, ...prev])
        setLiveCount(c => c + newAlerts.length)
      }

      // Always update summary counts
      setSummary(summaryRes.data)
    } catch {
      // silent — do not disrupt existing display on poll failure
    }
  }, [filterType, filterScore])

  // Run initial load whenever filters/page change
  useEffect(() => { initialLoad() }, [initialLoad])

  // Set up live polling interval (independent of page changes)
  useEffect(() => {
    const interval = setInterval(pollAlerts, POLL_INTERVAL)
    return () => clearInterval(interval)
  }, [pollAlerts])

  const handleInvestigate = (userId) => {
    navigate(`/explorer?user=${userId}`)
  }

  const handleResolve = async (alertId) => {
    setResolving(alertId)
    try {
      await alertsAPI.resolve(alertId)
      setAlerts(prev => prev.map(a => a.id === alertId ? { ...a, is_resolved: true } : a))
    } catch {
      // silent fail
    } finally {
      setResolving(null)
    }
  }

  return (
    <div>
      {/* Header */}
      <div className="page-header" style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10 }}>
        <div>
          <h1 className="page-title">Fraud Alerts</h1>
          <p className="page-subtitle">Real-time fraud detection alerts — investigate and resolve cases</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, paddingTop: 4 }}>
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.3)',
            borderRadius: 20, padding: '5px 14px', fontSize: 12, fontWeight: 700,
            color: '#10b981',
          }}>
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#10b981', display: 'inline-block', animation: 'pulse 1.5s infinite' }} />
            LIVE
          </span>
          {liveCount > 0 && (
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              +{liveCount} new
            </span>
          )}
        </div>
      </div>

      {/* Summary cards */}
      {summary && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, marginBottom: 24 }}>
          <SummaryCard icon="🔔" label="Total Alerts" value={summary.total} />
          <SummaryCard icon="🚨" label="High Risk" value={summary.high_risk} color="#ef4444" />
          <SummaryCard icon="↩" label="Return Fraud" value={summary.return_fraud} color="#f59e0b" />
          <SummaryCard icon="👁" label="Suspicious Behavior" value={summary.suspicious_behavior} color="#06b6d4" />
        </div>
      )}

      {/* Filters */}
      <div className="card" style={{ padding: '14px 20px', marginBottom: 20, display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {FILTER_TYPES.map(f => (
            <button key={f.key} onClick={() => { setFilterType(f.key); setPage(0) }}
              className="btn"
              style={{
                fontSize: 11, padding: '5px 12px',
                background: filterType === f.key
                  ? 'linear-gradient(135deg, var(--accent-cyan), var(--accent-violet))'
                  : 'var(--bg-secondary)',
                border: `1px solid ${filterType === f.key ? 'transparent' : 'var(--border)'}`,
                color: filterType === f.key ? 'white' : 'var(--text-secondary)',
              }}>
              {f.label}
            </button>
          ))}
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center' }}>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Min score</span>
          {[0, 60, 75, 80].map(s => (
            <button key={s} onClick={() => { setFilterScore(s); setPage(0) }}
              className="btn"
              style={{
                fontSize: 11, padding: '5px 10px',
                background: filterScore === s
                  ? 'linear-gradient(135deg, #ef4444, #f59e0b)'
                  : 'var(--bg-secondary)',
                border: `1px solid ${filterScore === s ? 'transparent' : 'var(--border)'}`,
                color: filterScore === s ? 'white' : 'var(--text-secondary)',
              }}>
              {s === 0 ? 'Any' : `${s}+`}
            </button>
          ))}
          <button onClick={initialLoad} className="btn btn-outline" style={{ fontSize: 11, padding: '5px 12px' }}>
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div style={{ padding: '14px 18px', borderRadius: 10, background: 'rgba(239,68,68,0.08)', border: '1px solid #ef444430', color: '#fca5a5', fontSize: 13, marginBottom: 16 }}>
          ⚠ {error}
        </div>
      )}

      {/* Table */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        {loading ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 60, gap: 12, color: 'var(--text-muted)' }}>
            <div className="spinner" style={{ width: 20, height: 20, borderWidth: 2 }} />
            Loading alerts...
          </div>
        ) : alerts.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '50px 20px', color: 'var(--text-muted)' }}>
            <div style={{ fontSize: 36, marginBottom: 12 }}>✅</div>
            <div style={{ fontSize: 14 }}>No alerts match the current filters</div>
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ background: 'var(--bg-secondary)' }}>
                {['Alert Type', 'User ID', 'Risk Score', 'Message', 'Created At', 'Status', 'Actions'].map(h => (
                  <th key={h} style={{
                    textAlign: 'left', padding: '12px 16px',
                    color: 'var(--text-muted)', fontWeight: 600,
                    borderBottom: '1px solid var(--border)',
                    textTransform: 'uppercase', letterSpacing: '0.05em', fontSize: 10,
                    whiteSpace: 'nowrap',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {alerts.map((alert, i) => (
                <tr key={alert.id}
                  style={{
                    background: alert.is_resolved
                      ? 'rgba(16,185,129,0.03)'
                      : i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)',
                    opacity: alert.is_resolved ? 0.6 : 1,
                    transition: 'background 0.15s',
                  }}
                >
                  {/* Alert Type */}
                  <td style={{ padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <TypeBadge type={alert.alert_type} />
                  </td>

                  {/* User ID */}
                  <td style={{ padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <button
                      onClick={() => handleInvestigate(alert.user_id)}
                      style={{
                        background: 'none', border: 'none', cursor: 'pointer',
                        color: 'var(--accent-cyan)', fontWeight: 700, fontFamily: 'Space Grotesk',
                        fontSize: 12, padding: 0,
                        textDecoration: 'underline', textDecorationStyle: 'dotted',
                      }}
                    >
                      {alert.user_id}
                    </button>
                  </td>

                  {/* Risk Score */}
                  <td style={{ padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <ScorePill score={alert.risk_score} />
                  </td>

                  {/* Message */}
                  <td style={{ padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.04)', color: 'var(--text-secondary)', maxWidth: 340 }}>
                    <span title={alert.message} style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                      {alert.message}
                    </span>
                  </td>

                  {/* Created At */}
                  <td style={{ padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.04)', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                    {formatDate(alert.created_at)}
                  </td>

                  {/* Status */}
                  <td style={{ padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    {alert.is_resolved
                      ? <span style={{ color: '#10b981', fontWeight: 600, fontSize: 11 }}>✓ Resolved</span>
                      : <span style={{ color: '#f59e0b', fontWeight: 600, fontSize: 11 }}>● Open</span>
                    }
                  </td>

                  {/* Actions */}
                  <td style={{ padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <button
                        onClick={() => handleInvestigate(alert.user_id)}
                        className="btn btn-primary"
                        style={{ fontSize: 10, padding: '5px 12px', whiteSpace: 'nowrap' }}
                      >
                        🔍 Investigate
                      </button>
                      {!alert.is_resolved && (
                        <button
                          onClick={() => handleResolve(alert.id)}
                          className="btn btn-outline"
                          disabled={resolving === alert.id}
                          style={{ fontSize: 10, padding: '5px 10px' }}
                        >
                          {resolving === alert.id ? '...' : '✓'}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* Pagination */}
        {!loading && alerts.length > 0 && (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', borderTop: '1px solid var(--border)' }}>
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              Showing {page * PAGE_SIZE + 1}–{page * PAGE_SIZE + alerts.length} alerts
            </span>
            <div style={{ display: 'flex', gap: 6 }}>
              <button className="btn btn-outline" onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0} style={{ fontSize: 11 }}>
                ← Prev
              </button>
              <button className="btn btn-outline" onClick={() => setPage(p => p + 1)} disabled={alerts.length < PAGE_SIZE} style={{ fontSize: 11 }}>
                Next →
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
