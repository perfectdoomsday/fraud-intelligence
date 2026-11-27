import { useEffect, useState } from 'react'
import type { ElementType, FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Activity, AlertOctagon, ArrowDownRight, ArrowUpRight, Bell, BrainCircuit, Check, ChevronDown,
  CircleDollarSign, Clock3, CreditCard, Database, FileSearch, Fingerprint, Gauge, LayoutDashboard,
  LogOut, RefreshCw, Search, Shield, ShieldAlert, ShieldCheck, Signal, SlidersHorizontal, Users,
  XCircle,
} from 'lucide-react'
import {
  Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { api, getToken, login, websocketUrl } from './services/api'
import type { Alert, Overview, Transaction } from './types'

type Page = 'overview' | 'transactions' | 'alerts' | 'models' | 'monitoring'

function formatMoney(value: number, currency = 'INR') {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency, maximumFractionDigits: 0 }).format(value)
}
function formatNumber(value: number) { return new Intl.NumberFormat('en-IN').format(value || 0) }
function prettyDate(value?: string) { return value ? new Date(value).toLocaleString() : '—' }

function LoginScreen({ onLogin }: { onLogin: (token: string, role: string) => void }) {
  const [email, setEmail] = useState('admin@local.test')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('')
    try { const result = await login(email, password); onLogin(result.access_token, result.role) }
    catch (err) { setError(err instanceof Error ? err.message : 'Unable to sign in') }
    finally { setBusy(false) }
  }
  return <div className="login-shell"><div className="login-card">
    <div className="brand-mark large"><ShieldAlert size={23} /></div>
    <div className="eyebrow">FINANCIAL CRIME INTELLIGENCE</div><h1>Sentinel Console</h1>
    <p className="muted">Sign in to investigate transaction risk and monitor fraud signals.</p>
    <form onSubmit={submit} className="login-form"><label>Email address<input value={email} onChange={e => setEmail(e.target.value)} type="email" required /></label>
      <label>Password<input value={password} onChange={e => setPassword(e.target.value)} type="password" required /></label>
      {error && <div className="form-error">{error}</div>}<button className="primary-button full" disabled={busy}>{busy ? 'Signing in…' : 'Sign in securely'}</button>
    </form><div className="login-foot"><ShieldCheck size={14} /> Protected with role-based access control</div>
  </div></div>
}

function RiskPill({ risk }: { risk?: string | null }) {
  const cls = (risk || 'pending').toLowerCase()
  return <span className={`risk-pill ${cls}`}>{risk || 'PENDING'}</span>
}
function MetricCard({ label, value, detail, icon: Icon, tone = 'blue', trend }: {
  label: string; value: string; detail: string; icon: ElementType; tone?: string; trend?: string
}) {
  return <div className="metric-card"><div className={`metric-icon ${tone}`}><Icon size={18} /></div>
    <div className="metric-label">{label}</div><div className="metric-value">{value}</div>
    <div className="metric-detail">{trend && <span className="trend"><ArrowUpRight size={13} />{trend}</span>}{detail}</div>
  </div>
}
function EmptyState({ icon: Icon, title, detail }: { icon: ElementType; title: string; detail: string }) {
  return <div className="empty-state"><div className="empty-icon"><Icon size={22} /></div><strong>{title}</strong><span>{detail}</span></div>
}

export default function App() {
  const [token, setToken] = useState(getToken())
  const [role, setRole] = useState(localStorage.getItem('fraud_role') || '')
  const [page, setPage] = useState<Page>('overview')
  const [search, setSearch] = useState('')
  const [liveItems, setLiveItems] = useState<Record<string, unknown>[]>([])
  const [connection, setConnection] = useState<'connecting' | 'live' | 'offline'>('connecting')
  const queryClient = useQueryClient()

  useEffect(() => {
    if (!token) return
    const socket = new WebSocket(websocketUrl())
    socket.onopen = () => setConnection('live')
    socket.onclose = () => setConnection('offline')
    socket.onerror = () => setConnection('offline')
    socket.onmessage = event => {
      try {
        const item = JSON.parse(event.data)
        setLiveItems(old => [item, ...old.filter(x => x.transaction_id !== item.transaction_id)].slice(0, 8))
        queryClient.invalidateQueries({ queryKey: ['overview'] })
        queryClient.invalidateQueries({ queryKey: ['transactions'] })
        queryClient.invalidateQueries({ queryKey: ['alerts'] })
      } catch { /* ignore malformed socket events */ }
    }
    return () => socket.close()
  }, [token, queryClient])

  const overview = useQuery({ queryKey: ['overview'], queryFn: () => api<Overview>('/analytics/overview'), enabled: !!token, refetchInterval: 10000 })
  const transactions = useQuery({ queryKey: ['transactions', search], queryFn: () => api<{ items: Transaction[]; total: number }>(`/transactions?page=1&page_size=100${search ? `&search=${encodeURIComponent(search)}` : ''}`), enabled: !!token, refetchInterval: 10000 })
  const alerts = useQuery({ queryKey: ['alerts'], queryFn: () => api<Alert[]>('/alerts'), enabled: !!token, refetchInterval: 10000 })
  const risk = useQuery({ queryKey: ['risk-distribution'], queryFn: () => api<{ category: string; count: number }[]>('/analytics/risk-distribution'), enabled: !!token })
  const trends = useQuery({ queryKey: ['trends'], queryFn: () => api<{ date: string; transactions: number; flagged: number }[]>('/analytics/trends?days=14'), enabled: !!token })
  const model = useQuery({ queryKey: ['active-model'], queryFn: () => api<Record<string, unknown>>('/models/active'), enabled: !!token })
  const modelList = useQuery({ queryKey: ['models'], queryFn: () => api<Record<string, unknown>[]>('/models'), enabled: !!token })
  const drift = useQuery({ queryKey: ['drift'], queryFn: () => api<Record<string, unknown>[]>('/monitoring/drift'), enabled: !!token })

  const updateAlert = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => api(`/alerts/${id}/status`, { method: 'PATCH', body: JSON.stringify({ status }) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['alerts'] }),
  })
  const createCase = useMutation({
    mutationFn: (alert: Alert) => api('/cases', { method: 'POST', body: JSON.stringify({ alert_id: alert.alert_id, title: `Investigation — ${alert.transaction_id}` }) }),
  })

  function signIn(accessToken: string, userRole: string) {
    localStorage.setItem('fraud_access_token', accessToken); localStorage.setItem('fraud_role', userRole)
    setRole(userRole); setToken(accessToken)
  }
  function signOut() {
    localStorage.removeItem('fraud_access_token'); localStorage.removeItem('fraud_role'); setToken(null); setRole(''); setLiveItems([])
  }
  const data = overview.data
  const canInvestigate = ['administrator', 'fraud_analyst', 'investigator'].includes(role)

  if (!token) return <LoginScreen onLogin={signIn} />

  const navItems: { key: Page; label: string; icon: ElementType; count?: number }[] = [
    { key: 'overview', label: 'Executive overview', icon: LayoutDashboard },
    { key: 'transactions', label: 'Live transactions', icon: CreditCard },
    { key: 'alerts', label: 'Investigation center', icon: ShieldAlert, count: alerts.data?.filter(a => !['CLOSED', 'FALSE_POSITIVE'].includes(a.status)).length },
    { key: 'models', label: 'Model intelligence', icon: BrainCircuit },
    { key: 'monitoring', label: 'System monitoring', icon: Activity },
  ]

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><ShieldAlert size={20} /></div><div><strong>SENTINEL</strong><span>RISK INTELLIGENCE</span></div></div>
      <div className="workspace-label">WORKSPACE</div>
      <nav>{navItems.map(item => <button key={item.key} className={`nav-item ${page === item.key ? 'active' : ''}`} onClick={() => setPage(item.key)}>
        <item.icon size={17} /><span>{item.label}</span>{item.count ? <b>{item.count}</b> : null}
      </button>)}</nav>
      <div className="sidebar-bottom"><div className="secure-status"><span className="status-dot" />All core services operational</div>
        <div className="user-card"><div className="avatar">{role.slice(0, 1).toUpperCase() || 'A'}</div><div className="user-meta"><strong>{role.replaceAll('_', ' ') || 'Analyst'}</strong><span>Authenticated session</span></div><button className="icon-button" title="Sign out" onClick={signOut}><LogOut size={16} /></button></div>
      </div>
    </aside>
    <main className="main-content">
      <header className="topbar"><div><div className="breadcrumbs">RISK OPERATIONS <span>/</span> {navItems.find(x => x.key === page)?.label.toUpperCase()}</div><h1>{navItems.find(x => x.key === page)?.label}</h1></div>
        <div className="top-actions"><div className={`connection ${connection}`}><span className="status-dot" />{connection === 'live' ? 'LIVE STREAM' : connection === 'connecting' ? 'CONNECTING' : 'STREAM OFFLINE'}</div>
          <button className="icon-button notification-button" title="Refresh data" onClick={() => queryClient.invalidateQueries()}><RefreshCw size={16} /></button><div className="date-chip"><Clock3 size={14} /> {new Date().toLocaleDateString()}</div></div>
      </header>
      {overview.isError && <div className="error-banner"><XCircle size={16} /> API unavailable: {(overview.error as Error).message}. Check that backend and Kafka are running.</div>}
      {page === 'overview' && <section className="page-stack">
        <div className="section-heading"><div><div className="eyebrow">REAL-TIME RISK PULSE</div><h2>Operational snapshot</h2><p>Transaction intelligence across the active processing window.</p></div><span className="refresh-note"><RefreshCw size={13} /> Refreshes every 10 seconds</span></div>
        <div className="metrics-grid">
          <MetricCard label="Transactions processed" value={formatNumber(data?.processed_transactions || 0)} detail={`${formatNumber(data?.total_transactions || 0)} received`} icon={CreditCard} />
          <MetricCard label="Flagged transactions" value={formatNumber(data?.flagged_transactions || 0)} detail="High and critical risk" icon={ShieldAlert} tone="amber" />
          <MetricCard label="Active alerts" value={formatNumber(data?.active_alerts || 0)} detail={`${formatNumber(data?.critical_alerts || 0)} critical`} icon={Bell} tone="red" />
          <MetricCard label="Confirmed fraud cases" value={formatNumber(data?.confirmed_fraud_cases || 0)} detail="Investigation disposition" icon={Fingerprint} tone="purple" />
        </div>
        <div className="metrics-grid secondary-metrics">
          <MetricCard label="Suspected fraud amount" value={formatMoney(data?.suspected_fraud_amount || 0)} detail="Value associated with high-risk transactions" icon={CircleDollarSign} tone="amber" />
          <MetricCard label="Average risk score" value={`${(data?.average_risk_score || 0).toFixed(1)} / 100`} detail="Processed transactions" icon={Gauge} />
          <MetricCard label="Estimated loss prevented" value="Not available" detail="Requires validated counterfactual analysis" icon={ShieldCheck} tone="green" />
          <MetricCard label="Model mode" value={String(model.data?.mode || 'Loading')} detail={String(model.data?.version || '')} icon={BrainCircuit} tone="purple" />
        </div>
        <div className="charts-grid">
          <div className="panel trend-panel"><div className="panel-heading"><div><h3>Transaction activity</h3><p>Daily volume and high-risk events</p></div><span className="legend"><i className="legend-blue" /> Processed <i className="legend-amber" /> Flagged</span></div>
            <div className="chart-area">{(trends.data?.length || 0) ? <ResponsiveContainer width="100%" height="100%"><AreaChart data={trends.data}><defs><linearGradient id="txFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#3b82f6" stopOpacity={0.3} /><stop offset="100%" stopColor="#3b82f6" stopOpacity={0} /></linearGradient></defs><CartesianGrid stroke="#1e2a3d" vertical={false} /><XAxis dataKey="date" tick={{ fill: '#718096', fontSize: 11 }} axisLine={false} tickLine={false} /><YAxis tick={{ fill: '#718096', fontSize: 11 }} axisLine={false} tickLine={false} /><Tooltip contentStyle={{ background: '#101a2b', border: '1px solid #29364b', borderRadius: 8 }} /><Area type="monotone" dataKey="transactions" stroke="#4d9bff" strokeWidth={2} fill="url(#txFill)" /><Area type="monotone" dataKey="flagged" stroke="#e6a94d" strokeWidth={2} fill="transparent" /></AreaChart></ResponsiveContainer> : <EmptyState icon={Activity} title="Waiting for transaction activity" detail="Publish synthetic events to populate this timeline." />}</div>
          </div>
          <div className="panel distribution-panel"><div className="panel-heading"><div><h3>Risk distribution</h3><p>Processed transaction classification</p></div></div>
            <div className="donut-wrap">{(risk.data?.length || 0) ? <><ResponsiveContainer width="100%" height={190}><PieChart><Pie data={risk.data} dataKey="count" nameKey="category" innerRadius={58} outerRadius={82} paddingAngle={3}>{risk.data?.map((entry, index) => <Cell key={entry.category} fill={({ LOW: '#237a68', MEDIUM: '#4d8bd8', HIGH: '#e3a34b', CRITICAL: '#e15f63' } as Record<string, string>)[entry.category] || ['#237a68', '#4d8bd8', '#e3a34b', '#e15f63'][index % 4]} />)}</Pie><Tooltip contentStyle={{ background: '#101a2b', border: '1px solid #29364b', borderRadius: 8 }} /></PieChart></ResponsiveContainer><div className="risk-legend">{risk.data?.map(x => <div key={x.category}><span className={`legend-dot ${x.category.toLowerCase()}`} />{x.category}<b>{formatNumber(x.count)}</b></div>)}</div></> : <EmptyState icon={Gauge} title="No risk scores yet" detail="Risk categories appear after the stream is processed." />}</div>
          </div>
        </div>
        <div className="panel"><div className="panel-heading"><div><h3>Latest transaction signals</h3><p>Most recent events arriving through the live stream</p></div><button className="text-button" onClick={() => setPage('transactions')}>View all transactions</button></div>
          <TransactionTable rows={liveItems.length ? liveItems as unknown as Transaction[] : (transactions.data?.items || []).slice(0, 6)} compact /></div>
      </section>}
      {page === 'transactions' && <section className="page-stack"><div className="section-heading"><div><div className="eyebrow">EVENT STREAM</div><h2>Transaction monitor</h2><p>Inspect transaction events, model outputs, and business decisions.</p></div><div className="live-tag"><span className="status-dot" /> Listening for events</div></div>
        <div className="panel"><div className="table-toolbar"><div className="search-box"><Search size={16} /><input placeholder="Search transaction, customer or merchant" value={search} onChange={e => setSearch(e.target.value)} /></div><div className="toolbar-right"><span>{formatNumber(transactions.data?.total || 0)} records</span><button className="icon-button" onClick={() => transactions.refetch()} title="Refresh"><RefreshCw size={16} /></button></div></div>
          <TransactionTable rows={transactions.data?.items || []} /></div>
      </section>}
      {page === 'alerts' && <section className="page-stack"><div className="section-heading"><div><div className="eyebrow">CASE OPERATIONS</div><h2>Fraud investigation center</h2><p>Prioritize risk, assign alerts, and track investigation outcomes.</p></div></div>
        <div className="alert-summary"><div><span>OPEN ALERTS</span><strong>{alerts.data?.filter(a => !['CLOSED', 'FALSE_POSITIVE'].includes(a.status)).length || 0}</strong></div><div><span>CRITICAL</span><strong className="text-danger">{alerts.data?.filter(a => a.severity === 'CRITICAL').length || 0}</strong></div><div><span>ACKNOWLEDGED</span><strong>{alerts.data?.filter(a => a.status === 'ACKNOWLEDGED').length || 0}</strong></div></div>
        <div className="panel"><div className="panel-heading"><div><h3>Alert queue</h3><p>Every alert is linked to a persisted transaction prediction.</p></div><span className="subtle-count">{alerts.data?.length || 0} total</span></div>
          <div className="table-wrap"><table><thead><tr><th>Alert / Transaction</th><th>Severity</th><th>Risk score</th><th>Detected</th><th>Assigned to</th><th>Status</th><th>Actions</th></tr></thead><tbody>
            {alerts.data?.map(alert => <tr key={alert.alert_id}><td><strong>{alert.alert_id}</strong><small>{alert.transaction_id} · {alert.customer_id}</small></td><td><RiskPill risk={alert.severity} /></td><td><strong>{alert.risk_score}</strong><div className="mini-bar"><i style={{ width: `${alert.risk_score}%` }} /></div></td><td>{prettyDate(alert.created_at)}</td><td>{alert.assigned_to || <span className="muted">Unassigned</span>}</td><td><span className="status-text">{alert.status.replaceAll('_', ' ')}</span></td><td><div className="action-group">
              {canInvestigate && alert.status === 'NEW' && <button className="small-button" disabled={updateAlert.isPending} onClick={() => updateAlert.mutate({ id: alert.alert_id, status: 'ACKNOWLEDGED' })}>Acknowledge</button>}
              {canInvestigate && <button className="small-button secondary" disabled={createCase.isPending} onClick={() => createCase.mutate(alert)}>Create case</button>}
              {canInvestigate && alert.status === 'ACKNOWLEDGED' && <button className="small-button secondary" onClick={() => updateAlert.mutate({ id: alert.alert_id, status: 'INVESTIGATING' })}>Investigate</button>}
            </div></td></tr>)}
          </tbody></table>{!alerts.data?.length && <EmptyState icon={ShieldCheck} title="No active alerts" detail="High and critical risk events will appear in this queue." />}</div>
        </div>
      </section>}
      {page === 'models' && <section className="page-stack"><div className="section-heading"><div><div className="eyebrow">MODEL GOVERNANCE</div><h2>Model intelligence</h2><p>Review model provenance and monitoring state before promotion.</p></div></div>
        <div className="model-hero"><div className="model-symbol"><BrainCircuit size={26} /></div><div><span className="eyebrow">ACTIVE INFERENCE MODE</span><h2>{String(model.data?.version || 'Loading model')}</h2><p>{String(model.data?.mode || '')} · artifact {model.data?.artifact_available ? 'available' : 'not found'}</p></div><RiskPill risk={model.data?.artifact_available ? 'LOW' : 'MEDIUM'} /></div>
        <div className="info-banner"><ShieldCheck size={17} /><div><strong>Promotion is a gated operation.</strong><span>Drift alone never promotes a candidate. The API restricts promotion to authorized ML engineers or administrators and requires an approval decision with a reason.</span></div></div>
        <div className="panel"><div className="panel-heading"><div><h3>Registered model versions</h3><p>Experiment and promotion history recorded in the model registry table.</p></div></div>
          <div className="table-wrap"><table><thead><tr><th>Version</th><th>Status</th><th>Artifact URI</th><th>Created</th></tr></thead><tbody>{modelList.data?.map((m, i) => <tr key={i}><td><strong>{String(m.version)}</strong></td><td><span className="status-text">{String(m.status)}</span></td><td className="code-cell">{String(m.artifact_uri)}</td><td>{prettyDate(String(m.created_at || ''))}</td></tr>)}</tbody></table>{!modelList.data?.length && <EmptyState icon={BrainCircuit} title="No registered model versions" detail="Run the offline training pipeline and register a candidate to populate this table." />}</div>
        </div>
      </section>}
      {page === 'monitoring' && <section className="page-stack"><div className="section-heading"><div><div className="eyebrow">PLATFORM HEALTH</div><h2>Data & system monitoring</h2><p>Review drift reports and service observability signals.</p></div></div>
        <div className="metrics-grid"><MetricCard label="API service" value="Healthy" detail="Health endpoint responding" icon={Activity} tone="green" /><MetricCard label="Kafka stream" value={connection === 'live' ? 'Connected' : 'Unknown'} detail="Dashboard websocket transport" icon={Signal} /><MetricCard label="Model artifact" value={model.data?.artifact_available ? 'Loaded' : 'Fallback'} detail={String(model.data?.version || '')} icon={BrainCircuit} tone="purple" /><MetricCard label="Drift reports" value={formatNumber(drift.data?.length || 0)} detail="Stored analysis runs" icon={SlidersHorizontal} tone="amber" /></div>
        <div className="panel"><div className="panel-heading"><div><h3>Data drift reports</h3><p>PSI-based feature distribution checks; review methodology before retraining.</p></div></div>
          <div className="table-wrap"><table><thead><tr><th>Report</th><th>Drift detected</th><th>Drift share</th><th>Affected features</th><th>Created</th></tr></thead><tbody>{drift.data?.map((r, i) => <tr key={i}><td><strong>{String(r.report_id)}</strong></td><td><RiskPill risk={r.drift_detected ? 'HIGH' : 'LOW'} /></td><td>{Number(r.drift_share || 0).toFixed(2)}</td><td>{Array.isArray(r.affected_features) ? r.affected_features.join(', ') : '—'}</td><td>{prettyDate(String(r.created_at || ''))}</td></tr>)}</tbody></table>{!drift.data?.length && <EmptyState icon={Activity} title="No drift reports yet" detail="Run the monitoring job after reference and current feature windows are available." />}</div>
        </div>
        <div className="panel infra-panel"><div className="panel-heading"><div><h3>Observability endpoints</h3><p>Connect external Prometheus and Grafana instances using these local endpoints.</p></div></div><div className="endpoint-grid"><div><span>API health</span><code>GET /health</code></div><div><span>Prometheus metrics</span><code>GET /api/v1/metrics</code></div><div><span>Live transactions</span><code>WS /api/v1/ws/transactions</code></div></div></div>
      </section>}
      <footer className="footer"><span>Sentinel Fraud Intelligence</span><span>Local synthetic-data demonstration · Not for production decisions</span></footer>
    </main>
  </div>
}

function TransactionTable({ rows, compact = false }: { rows: Transaction[]; compact?: boolean }) {
  return <div className="table-wrap"><table><thead><tr><th>Transaction</th><th>Customer</th><th>Amount</th><th>Risk score</th><th>Fraud probability</th><th>Decision</th><th>Status</th></tr></thead><tbody>
    {rows.map(row => <tr key={row.transaction_id}><td><strong>{row.transaction_id}</strong><small>{prettyDate(row.timestamp)}</small></td><td>{row.customer_id}</td><td>{formatMoney(row.amount, row.currency)}</td><td><div className="score-cell"><strong>{row.risk_score ?? '—'}</strong><RiskPill risk={row.risk_category} /></div></td><td>{row.fraud_probability == null ? '—' : `${(row.fraud_probability * 100).toFixed(1)}%`}</td><td><span className="decision-text">{row.decision || 'PENDING'}</span></td><td><span className={`status-dot ${row.processing_status === 'PROCESSED' ? 'green-dot' : ''}`} /> {row.processing_status}</td></tr>)}
  </tbody></table>{!rows.length && <EmptyState icon={Database} title="No transactions available" detail="Generate data and stream it to Kafka to see scored transactions here." />}</div>
}
