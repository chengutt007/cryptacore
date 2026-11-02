import React, { useState, useCallback, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { usersAPI, paymentsAPI } from '../api/client'

// ──────────────────────────────────────────────
// Shared Sub-components
// ──────────────────────────────────────────────

function ScoreGauge({ score }) {
  const color = score >= 75 ? '#ef4444' : score >= 55 ? '#f59e0b' : score >= 35 ? '#06b6d4' : '#10b981'
  const level = score >= 75 ? 'CRITICAL' : score >= 55 ? 'HIGH' : score >= 35 ? 'MEDIUM' : 'LOW'
  const circumference = 2 * Math.PI * 52
  const offset = circumference - (score / 100) * circumference

  return (
    <div className="gauge-container">
      <svg width="140" height="140" viewBox="0 0 140 140">
        <circle cx="70" cy="70" r="52" fill="none" stroke="#1f2d40" strokeWidth="12" />
        <circle cx="70" cy="70" r="52" fill="none" stroke={color} strokeWidth="12"
          strokeDasharray={circumference} strokeDashoffset={offset}
          strokeLinecap="round"
          transform="rotate(-90 70 70)"
          style={{ transition: 'stroke-dashoffset 1.2s cubic-bezier(0.34, 1.56, 0.64, 1)', filter: `drop-shadow(0 0 8px ${color})` }}
        />
        <text x="70" y="65" textAnchor="middle" fill={color}
          style={{ fontFamily: 'Space Grotesk', fontWeight: 800, fontSize: 28 }}>{score?.toFixed(0)}</text>
        <text x="70" y="83" textAnchor="middle" fill="#94a3b8"
          style={{ fontFamily: 'Inter', fontSize: 11 }}>CRYPTA SCORE</text>
      </svg>
      <span className={`risk-badge ${level}`}>{level} RISK</span>
    </div>
  )
}

function ShapBar({ label, contribution, maxContrib }) {
  const pct = maxContrib > 0 ? (contribution / maxContrib) * 100 : 0
  const color = pct >= 60 ? '#ef4444' : pct >= 30 ? '#f59e0b' : '#06b6d4'
  return (
    <div className="shap-row">
      <div className="shap-label" title={label}>{label}</div>
      <div className="shap-bar-wrap">
        <div className="shap-bar-fill" style={{ width: `${pct}%`, background: `linear-gradient(90deg, ${color}, ${color}80)` }} />
      </div>
      <div className="shap-val" style={{ color }}>{contribution?.toFixed(1)}</div>
    </div>
  )
}

function StatPill({ label, value, highlight }) {
  return (
    <div style={{
      padding: '10px 14px', borderRadius: 10,
      background: highlight ? 'rgba(239,68,68,0.08)' : 'var(--bg-secondary)',
      border: `1px solid ${highlight ? '#ef444440' : 'var(--border)'}`,
      display: 'flex', flexDirection: 'column', gap: 2
    }}>
      <span style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</span>
      <span style={{ fontSize: 15, fontWeight: 700, color: highlight ? '#fca5a5' : 'var(--text-primary)' }}>{value}</span>
    </div>
  )
}

function DataTable({ columns, rows, emptyMsg = 'No data' }) {
  if (!rows || rows.length === 0) {
    return <div style={{ fontSize: 12, color: 'var(--text-muted)', padding: '12px 0' }}>{emptyMsg}</div>
  }
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
        <thead>
          <tr>
            {columns.map(c => (
              <th key={c.key} style={{
                textAlign: 'left', padding: '6px 10px',
                color: 'var(--text-muted)', fontWeight: 600,
                borderBottom: '1px solid var(--border)', whiteSpace: 'nowrap',
                textTransform: 'uppercase', letterSpacing: '0.05em', fontSize: 10
              }}>
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} style={{ background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)' }}>
              {columns.map(c => {
                const raw = row[c.key]
                const val = c.render ? c.render(raw, row) : (raw ?? '—')
                return (
                  <td key={c.key} style={{ padding: '7px 10px', color: 'var(--text-secondary)', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    {val}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function formatDate(dt) {
  if (!dt) return '—'
  return new Date(dt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function RiskFlag({ suspicious }) {
  return suspicious
    ? <span style={{ color: '#ef4444', fontWeight: 700, fontSize: 11 }}>⚠ Suspicious</span>
    : <span style={{ color: '#10b981', fontSize: 11 }}>✓ Normal</span>
}

// ──────────────────────────────────────────────
// Main Component
// ──────────────────────────────────────────────

export default function RiskExplorer() {
  const [searchParams] = useSearchParams()
  const [mode, setMode] = useState('user') // user | payment
  const [userId, setUserId] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('orders')

  // Payment form state (unchanged — still manual by design)
  const [payForm, setPayForm] = useState({
    user_id: '',
    order_id: '',
    amount: 299.99,
    amount_vs_user_avg_ratio: 1.2,
    failed_attempts_24h: 0,
    payment_method_changes_7d: 0,
    geo_mismatch: 0,
    time_since_last_payment_hours: 24,
    card_bin_risk: 0.1,
    is_new_payment_method: 0,
    vpn_detected: 0,
    transaction_hour: 14,
  })
  const [payResult, setPayResult] = useState(null)

  // ── User lookup ───────────────────────────────────────────────────────────
  const lookupUser = useCallback(async (id) => {
    const trimId = (id || userId).trim()
    if (!trimId) return
    setLoading(true)
    setError(null)
    setResult(null)
    setActiveTab('orders')
    try {
      const res = await usersAPI.full(trimId)
      setResult(res.data)
    } catch (err) {
      const detail = err?.response?.data?.detail
      setError(detail || 'User not found or backend error.')
    } finally {
      setLoading(false)
    }
  }, [userId])

  // ── Auto-load from URL ?user= param (for Investigate flow) ───────────────
  useEffect(() => {
    const userParam = searchParams.get('user')
    if (userParam) {
      setUserId(userParam)
      setMode('user')
      // Slight delay to let state settle
      const t = setTimeout(() => lookupUser(userParam), 100)
      return () => clearTimeout(t)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') lookupUser()
  }

  // ── Payment analysis ──────────────────────────────────────────────────────
  const analyzePayment = async () => {
    setLoading(true)
    try {
      const res = await paymentsAPI.analyze(payForm)
      setPayResult(res.data)
    } catch (err) {
      setPayResult({ error: 'Payment analysis failed.' })
    } finally {
      setLoading(false)
    }
  }

  const pf = (k) => (e) => setPayForm(f => ({ ...f, [k]: isNaN(Number(e.target.value)) ? e.target.value : Number(e.target.value) }))

  // ── Derived ───────────────────────────────────────────────────────────────
  const profile = result?.user_profile || {}
  const maxContrib = result?.top_contributors ? Math.max(...result.top_contributors.map(c => c.contribution)) : 1

  const tabs = [
    { key: 'orders', label: `Orders (${result?.orders?.length ?? 0})` },
    { key: 'returns', label: `Returns (${result?.returns?.length ?? 0})` },
    { key: 'logins', label: `Logins (${result?.login_history?.length ?? 0})` },
    { key: 'devices', label: `Devices (${result?.device_history?.length ?? 0})` },
  ]

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Risk Score Explorer</h1>
        <p className="page-subtitle">Real-time user analysis from live database data</p>
      </div>

      {/* Mode toggle */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        {[{ k: 'user', label: '👤 User Risk Analysis' }, { k: 'payment', label: '💳 Payment Fraud Score' }].map(({ k, label }) => (
          <button key={k} onClick={() => { setMode(k); setResult(null); setPayResult(null); setError(null) }}
            className="btn" style={{
              background: mode === k ? 'linear-gradient(135deg, var(--accent-cyan), var(--accent-violet))' : 'var(--bg-card)',
              border: `1px solid ${mode === k ? 'transparent' : 'var(--border)'}`,
              color: mode === k ? 'white' : 'var(--text-secondary)',
            }}>{label}</button>
        ))}
      </div>

      {/* ── USER MODE ────────────────────────────────────────────────────── */}
      {mode === 'user' && (
        <>
          {/* Search bar */}
          <div className="card" style={{ padding: '20px 24px', marginBottom: 20 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 12 }}>
              Enter a User ID to load real database profile and compute live risk score
            </div>
            <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
              <input
                className="input-field"
                style={{ flex: 1, fontSize: 15 }}
                placeholder="e.g. USR_000000"
                value={userId}
                onChange={e => { setUserId(e.target.value); setResult(null); setError(null) }}
                onKeyDown={handleKeyDown}
              />
              <button
                className="btn btn-primary"
                style={{ minWidth: 160, height: 42 }}
                onClick={() => lookupUser()}
                disabled={loading || !userId.trim()}
              >
                {loading
                  ? <><div className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} /> Analyzing...</>
                  : '🔍 Analyze User'}
              </button>
            </div>
            {error && (
              <div style={{ marginTop: 12, padding: '10px 14px', borderRadius: 8, background: 'rgba(239,68,68,0.08)', border: '1px solid #ef444430', color: '#fca5a5', fontSize: 13 }}>
                ⚠ {error}
              </div>
            )}
          </div>

          {/* Results */}
          {result && (
            <>
              {/* Top row: Score + Profile stats */}
              <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr', gap: 16, marginBottom: 16 }}>
                {/* Score gauge */}
                <div className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 24, gap: 12 }}>
                  <ScoreGauge score={result.risk_score} />
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)', textAlign: 'center', marginTop: 4 }}>
                    {result.recommended_action}
                  </div>
                  <div style={{ fontSize: 11, color: '#10b981', background: 'rgba(16,185,129,0.1)', padding: '4px 10px', borderRadius: 20, border: '1px solid rgba(16,185,129,0.2)' }}>
                    ✓ Real Database Data
                  </div>
                </div>

                {/* Profile stats */}
                <div className="card">
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', letterSpacing: '0.07em', textTransform: 'uppercase', marginBottom: 14 }}>
                    User Profile — {result.user_id}
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginBottom: 14 }}>
                    <StatPill label="Account Age" value={`${profile.account_age_days ?? result.account_age_days} days`} />
                    <StatPill label="Email" value={result.email || '—'} />
                    <StatPill label="Status" value={result.is_flagged ? '🚩 Flagged' : '✓ Clean'} highlight={result.is_flagged} />
                    <StatPill label="Total Orders" value={profile.total_orders ?? '—'} />
                    <StatPill label="Total Returns" value={profile.total_returns ?? '—'} highlight={(profile.total_returns ?? 0) > 5} />
                    <StatPill label="Return Rate" value={profile.return_rate != null ? `${(profile.return_rate * 100).toFixed(1)}%` : '—'} highlight={(profile.return_rate ?? 0) > 0.3} />
                    <StatPill label="Login / Day" value={profile.login_frequency_per_day?.toFixed(2) ?? '—'} highlight={(profile.login_frequency_per_day ?? 0) > 10} />
                    <StatPill label="IP Changes (30d)" value={profile.ip_changes_30d ?? '—'} highlight={(profile.ip_changes_30d ?? 0) > 5} />
                    <StatPill label="Device Changes (30d)" value={profile.device_changes_30d ?? '—'} highlight={(profile.device_changes_30d ?? 0) > 3} />
                  </div>
                </div>
              </div>

              {/* Second row: SHAP + Components */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
                {/* SHAP bar chart */}
                {result.top_contributors?.length > 0 && (
                  <div className="card">
                    <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', letterSpacing: '0.07em', textTransform: 'uppercase', marginBottom: 14 }}>
                      Top Risk Factors (SHAP)
                    </div>
                    <div className="shap-container">
                      {result.top_contributors.map((c, i) => (
                        <ShapBar key={i} label={c.factor} contribution={c.contribution} maxContrib={maxContrib} />
                      ))}
                    </div>
                  </div>
                )}

                {/* Component scores */}
                {result.component_scores && (
                  <div className="card">
                    <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', letterSpacing: '0.07em', textTransform: 'uppercase', marginBottom: 14 }}>
                      Component Breakdown
                    </div>
                    {Object.entries(result.component_scores).map(([k, v]) => {
                      const labels = { fake_review: 'Fake Review (5%)', return_fraud: 'Return Fraud (45%)', behavior: 'Behavior (40%)', payment_fraud: 'Payment (10%)' }
                      const color = v >= 75 ? '#ef4444' : v >= 55 ? '#f59e0b' : '#06b6d4'
                      return (
                        <div key={k} style={{ marginBottom: 10 }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, fontSize: 12, color: 'var(--text-secondary)' }}>
                            <span>{labels[k] || k}</span>
                            <span style={{ color, fontWeight: 600 }}>{v?.toFixed(1)}</span>
                          </div>
                          <div style={{ height: 6, background: 'var(--bg-secondary)', borderRadius: 3, overflow: 'hidden' }}>
                            <div style={{ height: '100%', width: `${v}%`, background: `linear-gradient(90deg, ${color}, ${color}88)`, borderRadius: 3, transition: 'width 0.8s ease' }} />
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>

              {/* Fraud reasons */}
              {result.fraud_reasons?.length > 0 && (
                <div className="card" style={{ marginBottom: 16, borderColor: 'var(--accent-red-dim)', background: 'rgba(239, 68, 68, 0.04)' }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#ef4444', letterSpacing: '0.07em', textTransform: 'uppercase', marginBottom: 12 }}>
                    ⚠ AI Fraud Reasons
                  </div>
                  <ul style={{ paddingLeft: 14, display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {result.fraud_reasons.map((r, i) => (
                      <li key={i} style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{r}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Data tabs */}
              <div className="card">
                {/* Tab headers */}
                <div style={{ display: 'flex', gap: 4, marginBottom: 16, borderBottom: '1px solid var(--border)', paddingBottom: 12 }}>
                  {tabs.map(t => (
                    <button key={t.key} onClick={() => setActiveTab(t.key)}
                      className="btn"
                      style={{
                        fontSize: 12, padding: '6px 14px',
                        background: activeTab === t.key ? 'linear-gradient(135deg, var(--accent-cyan), var(--accent-violet))' : 'var(--bg-secondary)',
                        border: `1px solid ${activeTab === t.key ? 'transparent' : 'var(--border)'}`,
                        color: activeTab === t.key ? 'white' : 'var(--text-secondary)',
                      }}>
                      {t.label}
                    </button>
                  ))}
                </div>

                {/* Tab content */}
                {activeTab === 'orders' && (
                  <DataTable
                    columns={[
                      { key: 'order_id', label: 'Order ID' },
                      { key: 'amount', label: 'Amount', render: v => `$${v?.toFixed(2)}` },
                      { key: 'fraud_risk_score', label: 'Fraud Score', render: v => {
                        const c = v >= 70 ? '#ef4444' : v >= 40 ? '#f59e0b' : '#10b981'
                        return <span style={{ color: c, fontWeight: 600 }}>{v?.toFixed(1)}</span>
                      }},
                      { key: 'is_returned', label: 'Returned', render: v => v ? <span style={{ color: '#f59e0b' }}>↩ Yes</span> : <span style={{ color: '#10b981' }}>No</span> },
                      { key: 'is_suspicious', label: 'Status', render: v => <RiskFlag suspicious={v} /> },
                      { key: 'created_at', label: 'Date', render: v => formatDate(v) },
                    ]}
                    rows={result.orders}
                    emptyMsg="No orders found for this user"
                  />
                )}

                {activeTab === 'returns' && (
                  <DataTable
                    columns={[
                      { key: 'return_id', label: 'Return ID' },
                      { key: 'order_id', label: 'Order ID' },
                      { key: 'return_reason', label: 'Reason' },
                      { key: 'item_condition', label: 'Condition', render: v => {
                        const c = v === 'DAMAGED' ? '#ef4444' : v === 'MISSING_PARTS' ? '#f59e0b' : '#10b981'
                        return <span style={{ color: c, fontWeight: 600 }}>{v}</span>
                      }},
                      { key: 'refund_amount', label: 'Refund', render: v => `$${v?.toFixed(2)}` },
                      { key: 'days_to_return', label: 'Days', render: v => v ?? '—' },
                      { key: 'created_at', label: 'Date', render: v => formatDate(v) },
                    ]}
                    rows={result.returns}
                    emptyMsg="No returns found for this user"
                  />
                )}

                {activeTab === 'logins' && (
                  <DataTable
                    columns={[
                      { key: 'login_time', label: 'Time', render: v => formatDate(v) },
                      { key: 'ip_address', label: 'IP Address' },
                      { key: 'device_id', label: 'Device ID' },
                      { key: 'location', label: 'Location', render: v => v || '—' },
                      { key: 'is_suspicious', label: 'Flag', render: v => <RiskFlag suspicious={v} /> },
                    ]}
                    rows={result.login_history}
                    emptyMsg="No login history found for this user"
                  />
                )}

                {activeTab === 'devices' && (
                  <DataTable
                    columns={[
                      { key: 'device_id', label: 'Device ID' },
                      { key: 'device_type', label: 'Type' },
                      { key: 'os', label: 'OS' },
                      { key: 'browser', label: 'Browser' },
                      { key: 'last_used', label: 'Last Used', render: v => formatDate(v) },
                      { key: 'is_new_device', label: 'New?', render: v => v
                        ? <span style={{ color: '#f59e0b', fontWeight: 600 }}>⚠ New</span>
                        : <span style={{ color: '#10b981' }}>Known</span>
                      },
                    ]}
                    rows={result.device_history}
                    emptyMsg="No device history found for this user"
                  />
                )}
              </div>
            </>
          )}

          {/* Empty state */}
          {!result && !error && !loading && (
            <div className="card" style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--text-muted)' }}>
              <div style={{ fontSize: 40, marginBottom: 16 }}>🔍</div>
              <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 8 }}>Enter a User ID to begin analysis</div>
              <div style={{ fontSize: 12 }}>
                Real data is loaded from the database — orders, returns, logins, devices, and risk score are computed live.
              </div>
            </div>
          )}
        </>
      )}

      {/* ── PAYMENT MODE ─────────────────────────────────────────────────── */}
      {mode === 'payment' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: 20, alignItems: 'start' }}>
          <div className="card">
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 16 }}>Payment Transaction Features</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
              {[
                ['user_id', 'User ID', 'text'],
                ['order_id', 'Order ID', 'text'],
                ['amount', 'Amount ($)', 'number'],
                ['amount_vs_user_avg_ratio', 'Amount / User Avg Ratio', 'number'],
                ['failed_attempts_24h', 'Failed Attempts (24h)', 'number'],
                ['payment_method_changes_7d', 'Payment Method Changes', 'number'],
                ['card_bin_risk', 'Card BIN Risk (0-1)', 'number'],
                ['time_since_last_payment_hours', 'Hours Since Last Payment', 'number'],
                ['transaction_hour', 'Transaction Hour (0-23)', 'number'],
              ].map(([key, label, type]) => (
                <div key={key} className="input-group">
                  <label className="input-label">{label}</label>
                  <input className="input-field" type={type} value={payForm[key]} onChange={pf(key)} />
                </div>
              ))}
              {[
                ['geo_mismatch', 'Geo Mismatch'],
                ['is_new_payment_method', 'New Payment Method'],
                ['vpn_detected', 'VPN Detected'],
              ].map(([key, label]) => (
                <div key={key} className="input-group">
                  <label className="input-label">{label}</label>
                  <select className="input-field" value={payForm[key]} onChange={pf(key)}>
                    <option value={0}>No (0)</option>
                    <option value={1}>Yes (1)</option>
                  </select>
                </div>
              ))}
            </div>
            <button className="btn btn-primary w-full" style={{ marginTop: 8 }} onClick={analyzePayment} disabled={loading}>
              {loading
                ? <><div className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} /> Computing...</>
                : '💳 Analyze Payment'}
            </button>
          </div>

          {/* Payment result */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: 28 }}>
              {payResult ? (
                <>
                  <ScoreGauge score={payResult.risk_score ?? 0} />
                  <div style={{ marginTop: 16, textAlign: 'center', fontSize: 13, color: 'var(--text-secondary)' }}>
                    Verdict: <strong style={{ color: 'var(--text-primary)' }}>{payResult.verdict}</strong>
                  </div>
                </>
              ) : (
                <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '20px 0' }}>
                  <div style={{ fontSize: 32, marginBottom: 12 }}>💳</div>
                  <div style={{ fontSize: 13 }}>Enter payment details and analyze</div>
                </div>
              )}
            </div>
            {payResult?.flags?.length > 0 && (
              <div className="card">
                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', letterSpacing: '0.07em', textTransform: 'uppercase', marginBottom: 12 }}>
                  Fraud Flags
                </div>
                <ul style={{ paddingLeft: 14, display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {payResult.flags.map((r, i) => (
                    <li key={i} style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{r}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
