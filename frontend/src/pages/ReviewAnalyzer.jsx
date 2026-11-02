import React, { useState, useEffect, useCallback, useRef } from 'react'
import { reviewsAPI } from '../api/client'

// ─── Type metadata (mirrors FraudAlerts TYPE_META) ────────────────────────────

const TYPE_META = {
  BOT:          { label: '🤖 Bot Reviewer',    color: '#06b6d4', bg: 'rgba(6,182,212,0.12)',   desc: 'Automated bot posting identical reviews at scale' },
  COMPANY_FAKE: { label: '🏢 Company Fake',    color: '#f59e0b', bg: 'rgba(245,158,11,0.12)',  desc: 'Brand-planted review to inflate ratings or bash rivals' },
  SPAM:         { label: '📨 Spam Campaign',   color: '#ef4444', bg: 'rgba(239,68,68,0.12)',   desc: 'Contains external links, promo codes or solicitations' },
  FAKE:         { label: '✍ Paid/Fake',        color: '#a855f7', bg: 'rgba(168,85,247,0.12)',  desc: 'Incentivised or manufactured fake sentiment' },
  NORMAL:       { label: '✅ Genuine',          color: '#10b981', bg: 'rgba(16,185,129,0.10)',  desc: 'Authentic customer review' },
}

function TypeBadge({ status }) {
  const m = TYPE_META[status] || { label: status, color: '#64748b', bg: 'rgba(100,116,139,0.1)' }
  return (
    <span title={m.desc} style={{
      display: 'inline-flex', alignItems: 'center', padding: '4px 10px',
      borderRadius: 20, fontSize: 11, fontWeight: 700,
      color: m.color, background: m.bg,
      border: `1px solid ${m.color}40`, whiteSpace: 'nowrap', cursor: 'help',
    }}>
      {m.label}
    </span>
  )
}

function ScorePill({ score }) {
  const color = score >= 80 ? '#ef4444' : score >= 60 ? '#f59e0b' : score >= 40 ? '#a855f7' : '#10b981'
  return (
    <span style={{ fontWeight: 800, fontSize: 14, color, fontFamily: 'Space Grotesk' }}>
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

function formatDate(dt) {
  if (!dt) return '—'
  return new Date(dt).toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

// ─── Filter config ─────────────────────────────────────────────────────────────

const FILTER_TYPES = [
  { key: '', label: 'All Types' },
  { key: 'BOT', label: '🤖 Bot Reviewer' },
  { key: 'COMPANY_FAKE', label: '🏢 Company Fake' },
  { key: 'SPAM', label: '📨 Spam' },
  { key: 'FAKE', label: '✍ Paid/Fake' },
]

const POLL_INTERVAL = 3000   // 3 s — matches scanner interval
const PAGE_SIZE     = 50

// ─── Main component ───────────────────────────────────────────────────────────

export default function ReviewAnalyzer() {
  const [alerts,      setAlerts]      = useState([])
  const [summary,     setSummary]     = useState(null)
  const [loading,     setLoading]     = useState(true)
  const [error,       setError]       = useState(null)
  const [filterType,  setFilterType]  = useState('')
  const [filterScore, setFilterScore] = useState(0)
  const [page,        setPage]        = useState(0)
  const [liveCount,   setLiveCount]   = useState(0)
  const [scanning,    setScanning]    = useState(null)   // alert id being scanned
  const [resolving,   setResolving]   = useState(null)

  const seenIdsRef = useRef(new Set())

  // ── Initial load ──────────────────────────────────────────────────────────
  const initialLoad = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = {
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
        ...(filterType  ? { status: filterType }      : {}),
        ...(filterScore > 0 ? { min_score: filterScore } : {}),
      }
      const [alertsRes, summaryRes] = await Promise.all([
        reviewsAPI.liveAlerts(params),
        reviewsAPI.liveSummary(),
      ])
      const incoming = alertsRes.data
      seenIdsRef.current = new Set(incoming.map(a => a.id))
      setAlerts(incoming)
      setSummary(summaryRes.data)
    } catch {
      setError('Failed to load review alerts. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }, [filterType, filterScore, page])

  // ── Silent background poll ────────────────────────────────────────────────
  const pollAlerts = useCallback(async () => {
    try {
      const params = {
        limit: 500,
        offset: 0,
        ...(filterType  ? { status: filterType }      : {}),
        ...(filterScore > 0 ? { min_score: filterScore } : {}),
      }
      const [alertsRes, summaryRes] = await Promise.all([
        reviewsAPI.liveAlerts(params),
        reviewsAPI.liveSummary(),
      ])
      const incoming = alertsRes.data
      const newAlerts = incoming.filter(a => !seenIdsRef.current.has(a.id))
      if (newAlerts.length > 0) {
        newAlerts.forEach(a => seenIdsRef.current.add(a.id))
        setAlerts(prev => [...newAlerts, ...prev])
        setLiveCount(c => c + newAlerts.length)
      }
      setSummary(summaryRes.data)
    } catch {
      // silent on poll failure
    }
  }, [filterType, filterScore])

  useEffect(() => { initialLoad() }, [initialLoad])
  useEffect(() => {
    const interval = setInterval(pollAlerts, POLL_INTERVAL)
    return () => clearInterval(interval)
  }, [pollAlerts])

  // ── Resolve handler ───────────────────────────────────────────────────────
  const handleResolve = async (alertId) => {
    setResolving(alertId)
    try {
      await reviewsAPI.resolveAlert(alertId)
      setAlerts(prev => prev.map(a => a.id === alertId ? { ...a, is_resolved: true } : a))
    } catch {
      // silent
    } finally {
      setResolving(null)
    }
  }

  // ── Individual scan handler ───────────────────────────────────────────────
  const handleScanOne = async (reviewId, alertId) => {
    setScanning(alertId)
    try {
      const res = await reviewsAPI.scanOne(reviewId)
      const updated = res.data
      // Update this row in-place with fresh result
      setAlerts(prev => prev.map(a =>
        a.id === alertId
          ? { ...a, status: updated.status, risk_score: updated.risk_score, reason: updated.reason, detail: updated.detail }
          : a
      ))
    } catch {
      // silent
    } finally {
      setScanning(null)
    }
  }

  return (
    <div>
      {/* Header */}
      <div className="page-header" style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10 }}>
        <div>
          <h1 className="page-title">Review Analyzer</h1>
          <p className="page-subtitle">AI-powered fake review detection — BOT, Company Fake, Spam &amp; Paid reviews</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, paddingTop: 4 }}>
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.3)',
            borderRadius: 20, padding: '5px 14px', fontSize: 12, fontWeight: 700, color: '#10b981',
          }}>
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#10b981', display: 'inline-block', animation: 'pulse 1.5s infinite' }} />
            LIVE
          </span>
          {liveCount > 0 && (
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>+{liveCount} new</span>
          )}
        </div>
      </div>

      {/* Legend */}
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 18 }}>
        {Object.entries(TYPE_META).filter(([k]) => k !== 'NORMAL').map(([key, m]) => (
          <div key={key} style={{
            display: 'flex', alignItems: 'center', gap: 6,
            background: m.bg, border: `1px solid ${m.color}40`,
            borderRadius: 8, padding: '6px 12px', fontSize: 11,
          }}>
            <span style={{ fontWeight: 700, color: m.color }}>{m.label}</span>
            <span style={{ color: 'var(--text-muted)' }}>—</span>
            <span style={{ color: 'var(--text-secondary)' }}>{m.desc}</span>
          </div>
        ))}
      </div>

      {/* Summary cards */}
      {summary && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 14, marginBottom: 24 }}>
          <SummaryCard icon="📝" label="Total Detected"  value={summary.total}        />
          <SummaryCard icon="🤖" label="Bot Reviewers"   value={summary.bot}          color="#06b6d4" />
          <SummaryCard icon="🏢" label="Company Fake"    value={summary.company_fake} color="#f59e0b" />
          <SummaryCard icon="📨" label="Spam Campaigns"  value={summary.spam}         color="#ef4444" />
          <SummaryCard icon="✍" label="Paid / Fake"      value={summary.fake}         color="#a855f7" />
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
          {[0, 60, 75, 85].map(s => (
            <button key={s} onClick={() => { setFilterScore(s); setPage(0) }}
              className="btn"
              style={{
                fontSize: 11, padding: '5px 10px',
                background: filterScore === s ? 'linear-gradient(135deg, #ef4444, #f59e0b)' : 'var(--bg-secondary)',
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
            Loading review alerts...
          </div>
        ) : alerts.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '50px 20px', color: 'var(--text-muted)' }}>
            <div style={{ fontSize: 36, marginBottom: 12 }}>✅</div>
            <div style={{ fontSize: 14 }}>No suspicious reviews match the current filters</div>
            <div style={{ fontSize: 12, marginTop: 6 }}>The AI scanner detects 3–5 reviews every 3 seconds automatically</div>
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ background: 'var(--bg-secondary)' }}>
                {['Fraud Type', 'User ID', 'Product', 'Risk Score', 'AI Reason', 'Review Preview', 'Detected At', 'Status', 'Actions'].map(h => (
                  <th key={h} style={{
                    textAlign: 'left', padding: '12px 14px',
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
                  {/* Fraud Type */}
                  <td style={{ padding: '12px 14px', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <TypeBadge status={alert.status} />
                  </td>

                  {/* User ID */}
                  <td style={{ padding: '12px 14px', borderBottom: '1px solid rgba(255,255,255,0.04)', color: 'var(--accent-cyan)', fontWeight: 700, fontFamily: 'Space Grotesk', fontSize: 11 }}>
                    {alert.user_id}
                  </td>

                  {/* Product */}
                  <td style={{ padding: '12px 14px', borderBottom: '1px solid rgba(255,255,255,0.04)', color: 'var(--accent-violet)', fontFamily: 'Space Grotesk', fontSize: 11 }}>
                    {alert.product_id}
                  </td>

                  {/* Risk Score */}
                  <td style={{ padding: '12px 14px', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <ScorePill score={alert.risk_score} />
                  </td>

                  {/* AI Reason */}
                  <td style={{ padding: '12px 14px', borderBottom: '1px solid rgba(255,255,255,0.04)', color: 'var(--text-secondary)', maxWidth: 200 }}>
                    <span title={alert.detail} style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden', cursor: 'help' }}>
                      {alert.reason || '—'}
                    </span>
                  </td>

                  {/* Review Preview */}
                  <td style={{ padding: '12px 14px', borderBottom: '1px solid rgba(255,255,255,0.04)', color: 'var(--text-muted)', maxWidth: 220, fontStyle: 'italic', fontSize: 11 }}>
                    <span style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                      "{alert.review_text}"
                    </span>
                  </td>

                  {/* Detected At */}
                  <td style={{ padding: '12px 14px', borderBottom: '1px solid rgba(255,255,255,0.04)', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                    {formatDate(alert.created_at)}
                  </td>

                  {/* Status */}
                  <td style={{ padding: '12px 14px', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    {alert.is_resolved
                      ? <span style={{ color: '#10b981', fontWeight: 600, fontSize: 11 }}>✓ Resolved</span>
                      : <span style={{ color: '#f59e0b', fontWeight: 600, fontSize: 11 }}>● Open</span>
                    }
                  </td>

                  {/* Actions */}
                  <td style={{ padding: '12px 14px', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <div style={{ display: 'flex', gap: 5, flexWrap: 'nowrap' }}>
                      {/* Individual scan */}
                      <button
                        onClick={() => handleScanOne(alert.review_id, alert.id)}
                        className="btn btn-primary"
                        disabled={scanning === alert.id}
                        title="Re-scan this review with AI"
                        style={{ fontSize: 10, padding: '5px 10px', whiteSpace: 'nowrap' }}
                      >
                        {scanning === alert.id
                          ? <><div className="spinner" style={{ width: 10, height: 10, borderWidth: 1.5, display: 'inline-block', marginRight: 4 }} />Scanning</>
                          : '🔍 Scan'
                        }
                      </button>
                      {/* Resolve */}
                      {!alert.is_resolved && (
                        <button
                          onClick={() => handleResolve(alert.id)}
                          className="btn btn-outline"
                          disabled={resolving === alert.id}
                          title="Mark as resolved"
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
              <button className="btn btn-outline" onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0} style={{ fontSize: 11 }}>← Prev</button>
              <button className="btn btn-outline" onClick={() => setPage(p => p + 1)} disabled={alerts.length < PAGE_SIZE} style={{ fontSize: 11 }}>Next →</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
