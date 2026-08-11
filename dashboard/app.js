const { createApp, ref, computed, onMounted, onUnmounted, watch } = Vue

// ─────────────────────────────────────────────────────────────────────────────
// DATA STORE — reads from results/ folder via the API server
// ─────────────────────────────────────────────────────────────────────────────
const API = '/api'

// Global Auth State
const authKey = ref(localStorage.getItem('dashboard_auth_key') || '')
const isAuthenticated = ref(true) // Start assuming true, axios interceptors will set false on 401

// Axios Interceptors for Authentication
axios.interceptors.request.use(config => {
    if (authKey.value) {
        config.headers['Authorization'] = `Bearer ${authKey.value}`
    }
    config.withCredentials = true
    return config
}, error => {
    return Promise.reject(error)
})

axios.interceptors.response.use(response => {
    // If a request succeeds and we were marked unauthorized, restore authorization state
    isAuthenticated.value = true
    return response
}, error => {
    if (error.response && error.response.status === 401) {
        isAuthenticated.value = false
    }
    return Promise.reject(error)
})

async function fetchData(endpoint) {
    try {
        console.log(`Fetching ${endpoint}...`)
        const res = await axios.get(`${API}${endpoint}`, {
            params: { _t: new Date().getTime() }
        })
        console.log(`Fetched ${endpoint}:`, res.data?.length || 'Object')
        return res.data
    } catch (e) {
        console.error(`Failed to fetch ${endpoint}:`, e.message)
        return null
    }
}

async function postAction(endpoint, payload = {}) {
    try {
        const res = await axios.post(`${API}${endpoint}`, payload)
        return res.data
    } catch (e) {
        console.error(`Action failed ${endpoint}:`, e.message)
        return { success: false, error: e.message }
    }
}

function parseOptions(content) {
    if (!content) return null;
    
    const lines = content.split('\n');
    const options = {};
    let currentOption = null;
    
    const headerPat = /^\s*(?:Option\s*(\d+)\s*[:\-]|Variation\s*(\d+)\s*[:\-]|===\s*VARIATION\s*(\d+)\s*===|Option\s*(\d+)\s*$|Variation\s*(\d+)\s*$)/i;
    
    let hasHeaders = false;
    for (const line of lines) {
        const match = headerPat.exec(line);
        if (match) {
            hasHeaders = true;
            const optNum = parseInt(match[1] || match[2] || match[3] || match[4] || match[5]);
            currentOption = optNum;
            options[currentOption] = [];
        } else {
            if (currentOption !== null) {
                options[currentOption].push(line);
            }
        }
    }
    
    if (!hasHeaders) return null;
    
    const result = [];
    const names = {
        1: "Professional & Formal",
        2: "Warm & Conversational",
        3: "Short High-Conversion DM"
    };
    for (const opt in options) {
        const num = parseInt(opt);
        result.push({
            number: num,
            name: names[num] || `Option ${num}`,
            text: options[opt].join('\n').trim()
        });
    }
    return result;
}

function cleanMessageContent(content, defaultOption) {
    if (!content) return "";
    const parsed = parseOptions(content);
    if (!parsed) return content;
    
    const prefOrder = defaultOption === 3 ? [3, 2, 1] : (defaultOption === 1 ? [1, 2, 3] : [2, 1, 3]);
    for (const opt of prefOrder) {
        const found = parsed.find(o => o.number === opt);
        if (found && found.text) {
            return found.text;
        }
    }
    return content;
}

// ─────────────────────────────────────────────────────────────────────────────
// OVERVIEW PAGE
// ─────────────────────────────────────────────────────────────────────────────
const OverviewPage = {
    template: `
    <div>
        <!-- CEO Message -->
        <div class="ceo-message mb-3" v-if="audit">
            <div class="ceo-avatar">🤖</div>
            <div class="text-xs text-dim mb-1">AI CEO ASSESSMENT</div>
            <div class="ceo-message-text">{{ audit.ceo_message }}</div>
        </div>

        <!-- Alerts -->
        <div v-for="alert in alerts" :key="alert" class="alert-banner danger mb-2">
            🚨 {{ alert }}
        </div>

        <!-- Stats Grid -->
        <div class="stats-grid mb-3">
            <div class="stat-card purple">
                <div class="stat-icon">👥</div>
                <div class="stat-value">{{ state.leads?.total || 0 }}</div>
                <div class="stat-label">Total Leads</div>
                <div class="stat-change up">
                    ↑ {{ state.leads?.enriched || 0 }} enriched
                </div>
            </div>
            <div class="stat-card green">
                <div class="stat-icon">🔥</div>
                <div class="stat-value">{{ state.leads?.interested || 0 }}</div>
                <div class="stat-label">Interested Leads</div>
                <div class="stat-change up">Hot pipeline</div>
            </div>
            <div class="stat-card yellow">
                <div class="stat-icon">📤</div>
                <div class="stat-value">{{ state.performance?.total_messages_sent || 0 }}</div>
                <div class="stat-label">Messages Sent</div>
                <div class="stat-change">All channels</div>
            </div>
            <div class="stat-card red">
                <div class="stat-icon">💬</div>
                <div class="stat-value">{{ state.replies?.total || 0 }}</div>
                <div class="stat-label">Replies Received</div>
                <div class="stat-change up">
                    {{ state.performance?.reply_rate || 0 }}% reply rate
                </div>
            </div>
        </div>

        <div class="grid-2 mb-3">
            <!-- System Health -->
            <div class="card">
                <div class="card-title">System Health</div>
                <div class="health-gauge">
                    <div class="gauge-circle"
                         :style="{ background: gaugeGradient }">
                        <div class="gauge-score" :style="{ color: healthColor }">
                            {{ audit?.health_score || '--' }}
                        </div>
                        <div class="gauge-label">/ 100</div>
                    </div>
                    <div class="badge" :class="healthBadgeClass">
                        {{ audit?.overall_health?.toUpperCase() || 'UNKNOWN' }}
                    </div>
                </div>

                <div style="margin-top: 1rem;">
                    <div v-for="metric in keyMetrics" :key="metric.label"
                         style="margin-bottom: 0.75rem;">
                        <div class="flex justify-between text-sm mb-1">
                            <span class="text-muted">{{ metric.label }}</span>
                            <span class="font-bold" :style="{ color: metric.color }">
                                {{ metric.value }}
                            </span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill"
                                 :style="{ width: metric.pct + '%', background: metric.color }">
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Today's Tasks -->
            <div class="card">
                <div class="card-title">
                    Today's Schedule
                    <span class="badge badge-info">{{ schedule.length }} tasks</span>
                </div>
                <div class="task-list" v-if="schedule.length">
                    <div v-for="task in schedule" :key="task.priority"
                         class="task-item" :class="task.urgency"
                         @click="runTask(task)">
                        <div class="task-urgency-dot" :class="task.urgency"></div>
                        <div class="task-info">
                            <div class="task-label">{{ task.label }}</div>
                            <div class="task-reason">{{ task.reason }}</div>
                            <div class="task-command">{{ task.command }}</div>
                        </div>
                        <button class="btn btn-ghost text-xs"
                                aria-label="Run task"
                                style="padding: 0.3rem 0.6rem;">▶</button>
                    </div>
                </div>
                <div class="empty" v-else>
                    <div class="empty-icon">✅</div>
                    <div class="empty-text">All tasks complete for today</div>
                </div>
            </div>
            
            <!-- Autonomous Workflow Tracker -->
            <div class="card" style="grid-column: span 2;">
                <div class="card-title flex justify-between items-center">
                    <span>Autonomous Workflow Tracker</span>
                    <span class="badge badge-purple" v-if="state.workflow?.last_updated">
                        Last Run: {{ new Date(state.workflow.last_updated).toLocaleString() }}
                    </span>
                </div>
                <div class="roadmap-steps" style="flex-direction: row; justify-content: space-between; align-items: center; padding: 1rem;">
                    
                    <!-- Audit Step -->
                    <div class="text-center flex items-center gap-2" style="flex-direction: column;">
                        <div class="step-icon" :style="state.workflow?.current_step === 'audit' ? 'background: rgba(99, 102, 241, 0.2); border-color: var(--primary); box-shadow: 0 0 15px rgba(99, 102, 241, 0.3);' : ''">🔍</div>
                        <div class="text-sm font-bold">1. Audit</div>
                        <button class="btn btn-primary btn-sm" @click="$emit('run-command', 'python intelligence/general_auditor.py')">Run Audit</button>
                    </div>
                    
                    <div style="flex: 1; height: 2px; background: var(--border); margin: 0 1rem;"></div>
                    
                    <!-- Craft Step -->
                    <div class="text-center flex items-center gap-2" style="flex-direction: column;">
                        <div class="step-icon" :style="state.workflow?.current_step === 'craft' ? 'background: rgba(99, 102, 241, 0.2); border-color: var(--primary); box-shadow: 0 0 15px rgba(99, 102, 241, 0.3);' : ''">✍️</div>
                        <div class="text-sm font-bold">2. Craft</div>
                        <button class="btn btn-primary btn-sm" @click="$emit('run-command', 'python outreach/message_writer.py')">Run Craft</button>
                    </div>

                    <div style="flex: 1; height: 2px; background: var(--border); margin: 0 1rem;"></div>
                    
                    <!-- Outreach Step -->
                    <div class="text-center flex items-center gap-2" style="flex-direction: column;">
                        <div class="step-icon" :style="state.workflow?.current_step === 'outreach' ? 'background: rgba(99, 102, 241, 0.2); border-color: var(--primary); box-shadow: 0 0 15px rgba(99, 102, 241, 0.3);' : ''">📤</div>
                        <div class="text-sm font-bold">3. Outreach</div>
                        <button class="btn btn-primary btn-sm" @click="$emit('run-command', 'python outreach/email_sender.py')">Run Outreach</button>
                    </div>
                    
                </div>
                <div class="text-xs text-center text-muted mt-2">
                    <span v-if="state.workflow?.current_step">
                        Waiting for human to run <b>{{ state.workflow.current_step }}</b>. Will auto-run 12 hours after Last Run.
                    </span>
                    <span v-else>Workflow Idle.</span>
                </div>
            </div>

            <!-- Daily Lifestyle Daemon Card -->
            <div class="card" style="grid-column: span 2; margin-top: 1rem;">
                <div class="card-title flex justify-between items-center">
                    <span>Daily Lifestyle Loop (Autonomous Scheduler)</span>
                    <span class="badge" :class="lifestyleBadgeClass">
                        {{ lifestyleState.status?.toUpperCase() || 'IDLE' }}
                    </span>
                </div>
                
                <div class="responsive-grid-2-1" style="padding: 0.5rem 0;">
                    <div>
                        <div class="flex justify-between mb-2">
                            <span class="text-muted text-xs">Scheduler Status:</span>
                            <span class="font-bold text-xs" :style="{ color: lifestyleState.is_running ? '#10B981' : '#EF4444' }">
                                {{ lifestyleState.is_running ? '🟢 ACTIVE (RUNNING DAILY)' : '🔴 PAUSED' }}
                            </span>
                        </div>
                        <div class="flex justify-between mb-2">
                            <span class="text-muted text-xs">Current Sequence Task:</span>
                            <span class="font-bold text-xs" style="color: var(--primary-light)">
                                {{ lifestyleState.current_task || 'None (Idle)' }}
                            </span>
                        </div>
                        <div class="flex justify-between mb-2">
                            <span class="text-muted text-xs">Last Lifestyle Run:</span>
                            <span class="text-xs">{{ lifestyleState.last_run ? new Date(lifestyleState.last_run).toLocaleString() : 'Never' }}</span>
                        </div>
                        <div class="flex justify-between mb-2">
                            <span class="text-muted text-xs">Next Scheduled Run:</span>
                            <span class="font-bold text-xs" style="color: #F59E0B">{{ lifestyleState.next_scheduled_run ? new Date(lifestyleState.next_scheduled_run).toLocaleString() : 'Pending' }}</span>
                        </div>
                        <div class="flex gap-2 text-xs text-muted" style="margin-top: 0.5rem;">
                            <span>Completed: <b style="color: var(--text);">{{ lifestyleState.completed_runs }}</b></span>
                            <span>|</span>
                            <span>Failed: <b style="color: var(--danger);">{{ lifestyleState.failed_runs }}</b></span>
                        </div>
                    </div>
                    
                    <div style="display: flex; flex-direction: column; justify-content: center; gap: 0.5rem;">
                        <button class="btn btn-primary" @click="forceLifestyleRun" :disabled="lifestyleState.status === 'running'" style="font-size: 0.8rem;">
                            ⚡ Run Lifestyle Loop Now
                        </button>
                        <button class="btn" :class="lifestyleState.is_running ? 'btn-ghost' : 'btn-primary'" @click="toggleLifestyle" style="font-size: 0.8rem;">
                            {{ lifestyleState.is_running ? '⏸️ Pause Daily Scheduler' : '▶️ Resume Daily Scheduler' }}
                        </button>
                    </div>
                </div>
                
                <!-- Daemon logs -->
                <div v-if="lifestyleLogs.length" style="margin-top: 1rem; border-top: 1px solid var(--border); padding-top: 0.75rem;">
                    <div class="text-xs text-dim mb-1 font-bold">Latest Daemon Events:</div>
                    <div style="background: rgba(0,0,0,0.25); border-radius: 6px; padding: 0.5rem; max-height: 90px; overflow-y: auto; font-family: monospace; font-size: 0.72rem; line-height: 1.4;">
                        <div v-for="(log, i) in lifestyleLogs.slice().reverse().slice(0, 5)" :key="i" style="margin-bottom: 2px;">
                            <span class="text-dim">[{{ new Date(log.timestamp).toLocaleTimeString() }}]</span>
                            <span :style="{ color: log.type === 'ERROR' || log.type === 'SUBPROCESS_FAILED' ? 'var(--danger)' : 'var(--text)' }">
                                [{{ log.type }}] {{ log.message }}
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Channel Performance -->
        <div class="card mb-3">
            <div class="card-title">Channel Performance Today</div>
            <div class="channel-meters">
                <div v-for="ch in channels" :key="ch.name" class="channel-meter">
                    <div class="channel-meta">
                        <div class="channel-name">
                            <span>{{ ch.icon }}</span>
                            <span>{{ ch.name }}</span>
                        </div>
                        <div class="channel-count">
                            {{ ch.today }} / {{ ch.limit }} sent
                            <span class="text-dim ml-1">({{ ch.remaining }} remaining)</span>
                        </div>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill"
                             :style="{ width: ch.pct + '%', background: ch.color }">
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Operational Roadmap -->
        <div class="card mb-3">
            <div class="card-title">System Workflow Roadmap</div>
            <div class="roadmap-steps">
                <div v-for="step in roadmap" :key="step.id" 
                     class="roadmap-step" :class="{ active: step.active, complete: step.complete }">
                    <div class="step-line" v-if="step.id < 7"></div>
                    <div class="step-icon">{{ step.complete ? '✅' : step.icon }}</div>
                    <div class="step-content">
                        <div class="step-title">{{ step.title }}</div>
                        <div class="step-desc">{{ step.description }}</div>
                    </div>
                    <div class="step-status">
                        <span v-if="step.complete" class="text-success">Complete</span>
                        <span v-else-if="step.active" class="text-primary-light pulse-text">Next Step</span>
                        <span v-else class="text-dim">Pending</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Today's Priorities -->
        <div class="card" v-if="audit?.today_priorities?.length">
            <div class="card-title">CEO Priorities</div>
            <div style="display: flex; flex-direction: column; gap: 0.6rem;">
                <div v-for="(p, i) in audit.today_priorities" :key="i"
                     style="display: flex; gap: 0.75rem; align-items: flex-start;">
                    <div style="width: 24px; height: 24px; border-radius: 6px;
                                background: rgba(99,102,241,0.2); display: flex;
                                align-items: center; justify-content: center;
                                font-size: 0.75rem; font-weight: 700;
                                color: var(--primary-light); flex-shrink: 0;">
                        {{ i + 1 }}
                    </div>
                    <div class="text-sm" style="color: var(--text-muted); line-height: 1.5; padding-top: 0.2rem;">
                        {{ p }}
                    </div>
                </div>
            </div>
        </div>
    </div>
    `,

    props: ['state', 'audit', 'schedule', 'config'],
    emits: ['run-task', 'run-command'],

    setup(props, { emit }) {
        const alerts = computed(() => props.audit?.critical_issues || [])
        
        // Daily Lifestyle state
        const lifestyleState = ref({
            is_running: true,
            status: 'idle',
            current_task: null,
            last_run: null,
            next_scheduled_run: null,
            completed_runs: 0,
            failed_runs: 0
        })
        const lifestyleLogs = ref([])

        async function fetchLifestyle() {
            try {
                const stateRes = await fetchData('/lifestyle/state')
                if (stateRes) lifestyleState.value = stateRes
                
                const logsRes = await fetchData('/lifestyle/logs')
                if (logsRes) lifestyleLogs.value = logsRes
            } catch (e) {
                console.error("Failed to fetch lifestyle:", e)
            }
        }

        async function forceLifestyleRun() {
            try {
                await postAction('/lifestyle/run')
                await fetchLifestyle()
            } catch (e) {
                console.error(e)
            }
        }

        async function toggleLifestyle() {
            try {
                const target = !lifestyleState.value.is_running
                await postAction('/lifestyle/state', { is_running: target })
                await fetchLifestyle()
            } catch (e) {
                console.error(e)
            }
        }

        const lifestyleBadgeClass = computed(() => {
            const status = lifestyleState.value.status
            if (status === 'running') return 'badge-success'
            if (status === 'error') return 'badge-danger'
            return 'badge-info'
        })

        let lifestyleInterval
        onMounted(() => {
            fetchLifestyle()
            lifestyleInterval = setInterval(fetchLifestyle, 5000)
        })

        onUnmounted(() => {
            if (lifestyleInterval) clearInterval(lifestyleInterval)
        })

        const healthColor = computed(() => {
            const score = props.audit?.health_score || 0
            if (score >= 80) return '#10B981'
            if (score >= 60) return '#F59E0B'
            if (score >= 40) return '#EF4444'
            return '#6B7280'
        })

        const gaugeGradient = computed(() => {
            const c = healthColor.value
            return `conic-gradient(${c} 0%, ${c} ${props.audit?.health_score || 0}%, #1F2937 ${props.audit?.health_score || 0}%)`
        })

        const healthBadgeClass = computed(() => {
            const h = props.audit?.overall_health
            if (['excellent', 'good'].includes(h)) return 'badge-success'
            if (h === 'fair') return 'badge-warning'
            return 'badge-danger'
        })

        const keyMetrics = computed(() => [
            {
                label: 'Reply Rate',
                value: props.state?.performance?.reply_rate + '%',
                pct: Math.min(props.state?.performance?.reply_rate || 0, 100),
                color: '#6366F1'
            },
            {
                label: 'Interest Rate',
                value: props.state?.performance?.interest_rate + '%',
                pct: Math.min((props.state?.performance?.interest_rate || 0) * 5, 100),
                color: '#10B981'
            },
            {
                label: 'Conversion Rate',
                value: props.state?.performance?.conversion_rate + '%',
                pct: Math.min((props.state?.performance?.conversion_rate || 0) * 5, 100),
                color: '#F59E0B'
            }
        ])

        const cfg = computed(() => props.config?.outreach || {})
        const outreach = computed(() => props.state?.outreach || {})

        const channels = computed(() => [
            {
                name: 'WhatsApp',
                icon: '💬',
                today: outreach.value.whatsapp?.sent_today || 0,
                limit: cfg.value.daily_whatsapp_limit || 30,
                remaining: Math.max(0, (cfg.value.daily_whatsapp_limit || 30) - (outreach.value.whatsapp?.sent_today || 0)),
                pct: Math.min(((outreach.value.whatsapp?.sent_today || 0) / (cfg.value.daily_whatsapp_limit || 30)) * 100, 100),
                color: '#25D366'
            },
            {
                name: 'Email',
                icon: '📧',
                today: outreach.value.email?.sent_today || 0,
                limit: cfg.value.daily_email_limit || 50,
                remaining: Math.max(0, (cfg.value.daily_email_limit || 50) - (outreach.value.email?.sent_today || 0)),
                pct: Math.min(((outreach.value.email?.sent_today || 0) / (cfg.value.daily_email_limit || 50)) * 100, 100),
                color: '#6366F1'
            },
            {
                name: 'Instagram',
                icon: '📸',
                today: outreach.value.instagram?.sent_today || 0,
                limit: cfg.value.daily_instagram_limit || 20,
                remaining: Math.max(0, (cfg.value.daily_instagram_limit || 20) - (outreach.value.instagram?.sent_today || 0)),
                pct: Math.min(((outreach.value.instagram?.sent_today || 0) / (cfg.value.daily_instagram_limit || 20)) * 100, 100),
                color: '#E1306C'
            },
            {
                name: 'Facebook',
                icon: '📘',
                today: outreach.value.facebook?.sent_today || 0,
                limit: cfg.value.daily_facebook_limit || 20,
                remaining: Math.max(0, (cfg.value.daily_facebook_limit || 20) - (outreach.value.facebook?.sent_today || 0)),
                pct: Math.min(((outreach.value.facebook?.sent_today || 0) / (cfg.value.daily_facebook_limit || 20)) * 100, 100),
                color: '#1877F2'
            }
        ])

        function runTask(task) {
            emit('run-task', task)
        }

        const roadmap = computed(() => {
            const dp = props.state?.daily_progress || {}
            const leads = props.state?.leads?.total || 0
            const enriched = props.state?.leads?.enriched || 0
            const sent = props.state?.performance?.total_messages_sent || 0
            const replies = props.state?.replies?.total || 0
            const hasAudit = !!props.audit?.health_score
            
            // Heuristic for website audits
            const leadsWithSites = (props.leads || []).filter(l => l.website || l.has_website).length
            const auditsDone = (props.leads || []).filter(l => l.website_audit).length

            const steps = [
                { id: 1, title: 'Lead Discovery', description: 'Find potential businesses in target area', icon: '🔍', complete: !!dp.discovered_today },
                { id: 2, title: 'Deep Enrichment', description: 'Research business owners and pain points', icon: '💎', complete: !!dp.enriched_today },
                { id: 3, title: 'Website Auditing', description: 'Technical analysis of existing websites', icon: '🌐', complete: !!dp.audited_today },
                { id: 4, title: 'AI Message Crafting', description: 'Prepare hyper-personalized outreach scripts', icon: '✍️', complete: !!dp.crafted_today },
                { id: 5, title: 'Autonomous Outreach', description: 'Send messages via Email/WA/Social', icon: '📤', complete: !!dp.sent_today },
                { id: 6, title: 'Reply Management', description: 'Handle interested lead responses', icon: '💬', complete: !!dp.replies_checked_today },
                { id: 7, title: 'CEO Audit', description: 'Weekly performance review and optimization', icon: '🤖', complete: !!dp.audit_done_today }
            ]

            let foundActive = false
            return steps.map(s => {
                if (!s.complete && !foundActive) {
                    foundActive = true
                    return { ...s, active: true }
                }
                return { ...s, active: false }
            })
        })

        return {
            alerts, healthColor, gaugeGradient, healthBadgeClass,
            keyMetrics, channels, runTask, roadmap,
            lifestyleState, lifestyleLogs, forceLifestyleRun, toggleLifestyle, lifestyleBadgeClass
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// LEADS PAGE
// ─────────────────────────────────────────────────────────────────────────────
const LeadsPage = {
    template: `
    <div>
        <div class="flex justify-between items-center mb-3">
            <div>
                <h2 style="font-size: 1rem; font-weight: 700;">Lead Pipeline</h2>
                <p class="text-sm text-muted">{{ leads.length }} total leads</p>
            </div>
            <div class="flex gap-1">
                <button class="btn btn-primary" @click="$emit('enrich')" style="margin-right: 0.5rem;">
                    💎 Enrich All Leads
                </button>
                <select v-model="filterStatus"
                        style="background: var(--surface2); border: 1px solid var(--border);
                               color: var(--text); padding: 0.5rem 0.75rem; border-radius: 8px;
                               font-size: 0.82rem; outline: none;">
                    <option value="">All Status</option>
                    <option value="interested">Interested</option>
                    <option value="not_interested">Not Interested</option>
                    <option value="enriched">Enriched</option>
                </select>
                <select v-model="filterNiche"
                        style="background: var(--surface2); border: 1px solid var(--border);
                               color: var(--text); padding: 0.5rem 0.75rem; border-radius: 8px;
                               font-size: 0.82rem; outline: none;">
                    <option value="">All Niches</option>
                    <option v-for="n in niches" :key="n" :value="n">{{ n }}</option>
                </select>
            </div>
        </div>

        <!-- Stats row -->
        <div class="flex gap-2 mb-3" style="flex-wrap: wrap;">
            <div class="card" style="flex: 1; min-width: 100px; text-align: center;">
                <div style="font-size: 1.5rem; font-weight: 800; color: var(--primary-light);">
                    {{ totals.total }}
                </div>
                <div class="text-xs text-dim">Total</div>
            </div>
            <div class="card" style="flex: 1; min-width: 100px; text-align: center;">
                <div style="font-size: 1.5rem; font-weight: 800; color: var(--success);">
                    {{ totals.interested }}
                </div>
                <div class="text-xs text-dim">Interested 🔥</div>
            </div>
            <div class="card" style="flex: 1; min-width: 100px; text-align: center;">
                <div style="font-size: 1.5rem; font-weight: 800; color: var(--info);">
                    {{ totals.withEmail }}
                </div>
                <div class="text-xs text-dim">With Email</div>
            </div>
            <div class="card" style="flex: 1; min-width: 100px; text-align: center;">
                <div style="font-size: 1.5rem; font-weight: 800; color: #25D366;">
                    {{ totals.withWA }}
                </div>
                <div class="text-xs text-dim">With WhatsApp</div>
            </div>
            <div class="card" style="flex: 1; min-width: 100px; text-align: center;">
                <div style="font-size: 1.5rem; font-weight: 800; color: var(--warning);">
                    {{ totals.siteBuilt }}
                </div>
                <div class="text-xs text-dim">Site Built</div>
            </div>
        </div>

        <!-- Leads Table -->
        <div class="card">
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Business</th>
                            <th>Niche</th>
                            <th>City</th>
                            <th>Contacts</th>
                            <th>Score</th>
                            <th>Status</th>
                            <th>Pitch</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="lead in filteredLeads" :key="lead.name" 
                            @click="selectedLead = lead"
                            style="cursor: pointer;" class="hover-row">
                            <td>
                                <div class="font-bold" style="color: var(--text); font-size: 0.85rem;">
                                    {{ lead.name }}
                                </div>
                                <div class="text-xs text-dim">
                                    {{ lead.owner_name || 'Owner unknown' }}
                                </div>
                            </td>
                            <td>
                                <span class="badge badge-purple">{{ lead.niche || '—' }}</span>
                            </td>
                            <td class="text-sm">{{ lead.city || '—' }}</td>
                            <td>
                                <div class="flex gap-1" style="flex-wrap: wrap;">
                                    <span v-if="lead.contact_email" class="badge badge-info" title="Email">📧</span>
                                    <span v-if="lead.contact_whatsapp" class="badge badge-success" title="WhatsApp">💬</span>
                                    <span v-if="lead.instagram?.found" class="badge" style="background: rgba(225,48,108,0.15); color: #E1306C;" title="Instagram">📸</span>
                                    <span v-if="lead.facebook?.found" class="badge badge-info" title="Facebook">📘</span>
                                </div>
                            </td>
                            <td>
                                <div class="lead-score">
                                    <div class="score-dots">
                                        <div v-for="i in 10" :key="i"
                                             class="score-dot"
                                             :class="{ filled: i <= getScore(lead) }">
                                        </div>
                                    </div>
                                    <span class="text-xs text-muted">{{ lead.enrichment_score || '0/10' }}</span>
                                </div>
                            </td>
                            <td>
                                <span class="badge" :class="statusClass(lead.status)">
                                    {{ lead.status || 'active' }}
                                </span>
                            </td>
                            <td>
                                <div class="text-xs text-muted truncate" style="max-width: 200px;"
                                     :title="lead.pitch_angle">
                                    {{ lead.pitch_angle ? lead.pitch_angle.substring(0, 60) + '...' : '—' }}
                                </div>
                            </td>
                        </tr>
                    </tbody>
                </table>
                <div class="empty" v-if="!filteredLeads.length">
                    <div class="empty-icon">🔍</div>
                    <div class="empty-text">No leads match this filter</div>
                </div>
            </div>
        </div>

        <!-- Lead Detail Modal -->
        <div v-if="selectedLead" class="modal-overlay" @click.self="closeModal">
            <div class="modal-window wide">
                <div class="modal-header">
                    <div class="flex items-center gap-2">
                        <div class="logo-icon" style="width: 32px; height: 32px;">🏢</div>
                        <div>
                            <h2 v-if="!isEditing" style="font-size: 1.1rem; font-weight: 700;">{{ selectedLead.name }}</h2>
                            <input v-else v-model="editData.name" class="input-sm" placeholder="Business Name" />
                            <p class="text-xs text-muted">{{ selectedLead.niche }} in {{ selectedLead.city }}</p>
                        </div>
                    </div>
                    <div class="flex gap-2">
                        <button v-if="!isEditing" class="btn btn-ghost btn-sm" @click="startEditing">✏️ Edit</button>
                        <button v-else class="btn btn-success btn-sm" @click="saveLead">💾 Save</button>
                        <button class="btn btn-ghost" aria-label="Close" @click="closeModal">✕</button>
                    </div>
                </div>
                <div class="modal-body scrollable">
                    <div class="detail-grid">
                        <div class="detail-group">
                            <label>Owner / Decision Maker</label>
                            <div v-if="!isEditing" class="detail-value">{{ selectedLead.owner_name || 'Not identified yet' }}</div>
                            <input v-else v-model="editData.owner_name" class="input-sm" placeholder="Owner Name" />
                        </div>
                        <div class="detail-group">
                            <label>WhatsApp / Phone</label>
                            <div v-if="!isEditing" class="detail-value">{{ selectedLead.contact_whatsapp || selectedLead.phone || '—' }}</div>
                            <input v-else v-model="editData.contact_whatsapp" class="input-sm" placeholder="+234..." />
                        </div>
                        <div class="detail-group">
                            <label>Email</label>
                            <div v-if="!isEditing" class="detail-value">{{ selectedLead.contact_email || '—' }}</div>
                            <input v-else v-model="editData.contact_email" class="input-sm" placeholder="email@example.com" />
                        </div>
                        <div class="detail-group">
                            <label>Website</label>
                            <div v-if="!isEditing" class="detail-value">
                                <a v-if="selectedLead.website" :href="selectedLead.website" target="_blank" class="text-primary">{{ selectedLead.website }}</a>
                                <span v-else class="text-muted">No website found</span>
                            </div>
                            <input v-else v-model="editData.website" class="input-sm" placeholder="https://..." />
                        </div>
                    </div>

                    <!-- AI CEO Analysis -->
                    <div class="detail-section" v-if="selectedLead.personality">
                        <h3 class="detail-section-title">AI CEO Analysis</h3>
                        <div class="detail-section-grid">
                            <div class="info-card">
                                <div class="info-card-title">✨ Business Vibe</div>
                                <div class="text-sm">{{ selectedLead.personality.vibe }}</div>
                            </div>
                            <div class="info-card">
                                <div class="info-card-title">🏆 Key Pride</div>
                                <div class="text-sm">{{ selectedLead.personality.key_pride }}</div>
                            </div>
                            <div class="info-card">
                                <div class="info-card-title">💡 Biggest Opportunity</div>
                                <div class="text-sm">{{ selectedLead.personality.biggest_opportunity }}</div>
                            </div>
                        </div>
                    </div>

                    <!-- Pitch Angle -->
                    <div class="detail-section" v-if="selectedLead.pitch_angle">
                        <h3 class="detail-section-title">Suggested Pitch Angle</h3>
                        <div v-if="!isEditing" class="card" style="background: var(--bg); border-color: var(--border); font-style: italic; line-height: 1.6; font-size: 0.9rem;">
                            "{{ selectedLead.pitch_angle }}"
                        </div>
                        <textarea v-else v-model="editData.pitch_angle" class="input-sm" placeholder="Craft your pitch..."></textarea>
                    </div>

                    <!-- Enriched Data: Reviews & Sentiment -->
                    <div class="detail-section" v-if="selectedLead.reviews_analysis">
                        <h3 class="detail-section-title">Reviews & Sentiment</h3>
                        <div class="detail-section-grid">
                            <div class="info-card">
                                <div class="info-card-title">✅ Praises</div>
                                <ul class="text-xs" style="padding-left: 1.2rem; list-style: disc;">
                                    <li v-for="p in selectedLead.reviews_analysis.praises">{{ p }}</li>
                                </ul>
                                <div v-if="!selectedLead.reviews_analysis.praises?.length" class="text-xs text-muted italic">No specific praises found</div>
                            </div>
                            <div class="info-card">
                                <div class="info-card-title">❌ Complaints</div>
                                <ul class="text-xs" style="padding-left: 1.2rem; list-style: disc;">
                                    <li v-for="c in selectedLead.reviews_analysis.complaints">{{ c }}</li>
                                </ul>
                                <div v-if="!selectedLead.reviews_analysis.complaints?.length" class="text-xs text-muted italic">No specific complaints found</div>
                            </div>
                            <div class="info-card">
                                <div class="info-card-title">📊 Sentiment Summary</div>
                                <div class="text-xs">{{ selectedLead.reviews_analysis.sentiment_summary }}</div>
                            </div>
                        </div>
                    </div>

                    <!-- Enriched Data: Competitors & Timing -->
                    <div class="detail-section" v-if="selectedLead.competitors || selectedLead.contact_timing">
                        <div class="detail-section-grid">
                            <div v-if="selectedLead.competitors" class="info-card">
                                <div class="info-card-title">🤺 Competitors</div>
                                <div v-for="c in selectedLead.competitors" class="mb-2">
                                    <div class="text-xs font-bold">{{ c.name }}</div>
                                    <div class="text-xs text-muted">{{ c.notes }}</div>
                                </div>
                            </div>
                            <div v-if="selectedLead.contact_timing" class="info-card">
                                <div class="info-card-title">🕒 Best Send Time</div>
                                <div class="text-sm font-bold text-primary">{{ selectedLead.contact_timing.recommendation }}</div>
                                <div class="text-xs text-muted mt-1">Best Window: {{ selectedLead.contact_timing.best_send_time }}</div>
                            </div>
                        </div>
                    </div>

                    <!-- Website Audit Results -->
                    <div class="detail-section" v-if="selectedLead.website_audit">
                        <h3 class="detail-section-title">Website Audit Report</h3>
                        <div class="card mb-2" style="background: rgba(16, 185, 129, 0.05); border-color: rgba(16, 185, 129, 0.2);">
                            <div class="text-sm italic mb-2" style="color: var(--text);">
                                "{{ selectedLead.website_audit.ai_report }}"
                            </div>
                            <div class="grid-3" style="margin-top: 1rem;">
                                <div class="text-center">
                                    <div class="text-xs text-dim">Mobile</div>
                                    <div :class="selectedLead.website_audit.audit?.is_mobile_friendly ? 'text-success' : 'text-danger'">
                                        {{ selectedLead.website_audit.audit?.is_mobile_friendly ? '✅ Ready' : '❌ Bad' }}
                                    </div>
                                </div>
                                <div class="text-center">
                                    <div class="text-xs text-dim">Security</div>
                                    <div :class="selectedLead.website_audit.audit?.has_ssl ? 'text-success' : 'text-danger'">
                                        {{ selectedLead.website_audit.audit?.has_ssl ? '✅ SSL' : '❌ No SSL' }}
                                    </div>
                                </div>
                                <div class="text-center">
                                    <div class="text-xs text-dim">WhatsApp</div>
                                    <div :class="selectedLead.website_audit.audit?.has_whatsapp_button ? 'text-success' : 'text-danger'">
                                        {{ selectedLead.website_audit.audit?.has_whatsapp_button ? '✅ Found' : '❌ Missing' }}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- External Links -->
                    <div class="detail-section" v-if="selectedLead.maps_url || selectedLead.website_audit">
                        <h3 class="detail-section-title">External Links</h3>
                        <div class="flex gap-2">
                            <a v-if="selectedLead.maps_url" :href="selectedLead.maps_url" target="_blank" class="btn btn-ghost text-xs">📍 Google Maps</a>
                            <a v-if="selectedLead.website" :href="selectedLead.website" target="_blank" class="btn btn-ghost text-xs">🌐 Visit Site</a>
                            <a v-if="selectedLead.instagram?.url" :href="selectedLead.instagram.url" target="_blank" class="btn btn-ghost text-xs">📸 Instagram</a>
                            <a v-if="selectedLead.facebook?.url" :href="selectedLead.facebook.url" target="_blank" class="btn btn-ghost text-xs">📘 Facebook</a>
                        </div>
                    </div>
                </div>
                <div class="modal-footer" style="padding: 1rem 1.5rem; border-top: 1px solid var(--border); display: flex; justify-content: flex-end; gap: 0.75rem;">
                    <button class="btn btn-ghost" @click="closeModal">Close</button>
                    <button v-if="!selectedLead.enriched" class="btn btn-primary" @click="$emit('enrich'); closeModal();">💎 Enrich This Lead</button>
                </div>
            </div>
        </div>
    </div>
    `,

    props: ['leads'],
    emits: ['enrich'],

    setup(props) {
        const filterStatus = ref('')
        const filterNiche = ref('')
        const selectedLead = ref(null)

        const isEditing = ref(false)
        const editData = ref({})

        const niches = computed(() => {
            const n = new Set(props.leads.map(l => l.niche).filter(Boolean))
            return [...n].sort()
        })

        const filteredLeads = computed(() => {
            return props.leads.filter(l => {
                // Filter by Status
                if (filterStatus.value) {
                    if (filterStatus.value === 'enriched') {
                        if (!l.enriched) return false
                    } else if (l.status !== filterStatus.value) {
                        return false
                    }
                }
                
                // Filter by Niche
                if (filterNiche.value && l.niche !== filterNiche.value) return false
                
                return true
            })
        })

        const totals = computed(() => ({
            total: props.leads.length,
            interested: props.leads.filter(l => l.status === 'interested').length,
            withEmail: props.leads.filter(l => l.contact_email).length,
            withWA: props.leads.filter(l => l.contact_whatsapp).length,
            siteBuilt: props.leads.filter(l => l.site_built).length
        }))

        function getScore(lead) {
            try {
                return parseInt((lead.enrichment_score || '0/10').split('/')[0])
            } catch { return 0 }
        }

        function statusClass(status) {
            const map = {
                'interested': 'badge-success',
                'not_interested': 'badge-danger',
                'active': 'badge-info',
                'nurture': 'badge-warning',
                'replied': 'badge-purple',
                'closed': 'badge-gray'
            }
            return map[status] || 'badge-gray'
        }

        function startEditing() {
            isEditing.value = true
            editData.value = { 
                name: selectedLead.value.name,
                owner_name: selectedLead.value.owner_name,
                contact_email: selectedLead.value.contact_email,
                contact_whatsapp: selectedLead.value.contact_whatsapp,
                website: selectedLead.value.website,
                pitch_angle: selectedLead.value.pitch_angle
            }
        }

        async function saveLead() {
            const res = await axios.post('/api/update-lead', {
                name: selectedLead.value.name,
                updates: editData.value
            })
            if (res.data.success) {
                Object.assign(selectedLead.value, editData.value)
                isEditing.value = false
            } else {
                alert("Failed to save changes: " + (res.data.error || "Unknown error"))
            }
        }

        function closeModal() {
            selectedLead.value = null
            isEditing.value = false
        }

        return { 
            filterStatus, filterNiche, selectedLead, niches, 
            filteredLeads, totals, getScore, statusClass,
            isEditing, editData, startEditing, saveLead, closeModal
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// REPLIES PAGE
// ─────────────────────────────────────────────────────────────────────────────
const RepliesPage = {
    template: `
    <div>
        <div class="flex justify-between items-center mb-3">
            <div>
                <h2 style="font-size: 1rem; font-weight: 700;">Reply Manager</h2>
                <p class="text-sm text-muted">{{ replies.length }} total replies</p>
            </div>
            <div class="flex gap-1">
                <button class="btn btn-ghost" @click="fetchNewReplies"
                        :disabled="loading">
                    🔄 Fetch New Replies
                </button>
                <button class="btn btn-success" @click="approveAll('interested')"
                        :disabled="loading">
                    ✅ Approve All Interested
                </button>
                <button class="btn btn-primary" @click="sendQueued"
                        :disabled="loading">
                    📤 Send Queued
                </button>
            </div>
        </div>

        <!-- Tabs -->
        <div class="tabs">
            <div class="tab" :class="{ active: activeTab === 'all' }" @click="activeTab = 'all'">
                All ({{ replies.length }})
            </div>
            <div class="tab" :class="{ active: activeTab === 'interested' }" @click="activeTab = 'interested'">
                🔥 Interested ({{ byIntent('interested').length }})
            </div>
            <div class="tab" :class="{ active: activeTab === 'pending' }" @click="activeTab = 'pending'">
                ⏳ Pending ({{ byStatus('pending_review').length }})
            </div>
            <div class="tab" :class="{ active: activeTab === 'question' }" @click="activeTab = 'question'">
                ❓ Questions ({{ byIntent('question').length }})
            </div>
            <div class="tab" :class="{ active: activeTab === 'replied' }" @click="activeTab = 'replied'">
                ✅ Replied ({{ byStatus('replied').length }})
            </div>
        </div>

        <!-- Reply Cards -->
        <div class="reply-cards" v-if="filteredReplies.length">
            <div v-for="reply in filteredReplies" :key="reply.message_id"
                 class="reply-card" :class="reply.classification?.intent">

                <div class="reply-header">
                    <div>
                        <div class="reply-business">
                            <span v-if="reply.channel === 'whatsapp'" style="margin-right: 4px;" title="WhatsApp Reply">💬</span>
                            <span v-else style="margin-right: 4px;" title="Email Reply">📧</span>
                            {{ reply.business }}
                        </div>
                        <div class="reply-email">{{ reply.from_email }}</div>
                    </div>
                    <div class="flex gap-2 items-center">
                        <!-- Intent specific SVG Icons -->
                        <span style="display: flex; align-items: center;">
                            <svg v-if="reply.classification?.intent === 'interested'" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="filter: drop-shadow(0 0 4px rgba(16,185,129,0.4));">
                                <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>
                            </svg>
                            <svg v-else-if="reply.classification?.intent === 'question'" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#3B82F6" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="filter: drop-shadow(0 0 4px rgba(59,130,246,0.4));">
                                <circle cx="12" cy="12" r="10"/>
                                <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
                                <line x1="12" y1="17" x2="12.01" y2="17"/>
                            </svg>
                            <svg v-else-if="reply.classification?.intent === 'not_interested'" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#EF4444" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="filter: drop-shadow(0 0 4px rgba(239,68,68,0.3));">
                                <circle cx="12" cy="12" r="10"/>
                                <line x1="15" y1="9" x2="9" y2="15"/>
                                <line x1="9" y1="9" x2="15" y2="15"/>
                            </svg>
                            <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#9CA3AF" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                                <circle cx="12" cy="12" r="10"/>
                                <line x1="12" y1="8" x2="12" y2="12"/>
                                <line x1="12" y1="16" x2="12.01" y2="16"/>
                            </svg>
                        </span>
                        
                        <span class="badge" :class="intentClass(reply.classification?.intent)">
                            {{ reply.classification?.intent || 'unknown' }}
                        </span>
                        <span class="badge" :class="statusBadge(reply.status)">
                            {{ reply.status }}
                        </span>
                    </div>
                </div>

                <div class="reply-body">"{{ reply.body_preview }}"</div>

                <!-- Draft reply (Live-Editable Glassmorphic Textarea) -->
                <div class="reply-draft" v-if="reply.drafted_reply?.body">
                    <div class="reply-draft-label">
                        <span>🤖 AI DRAFT REPLY (Click to edit)</span>
                        <span class="badge badge-purple" style="font-size: 0.6rem; padding: 0.1rem 0.3rem;">Editable</span>
                    </div>
                    <textarea class="input-sm" 
                              v-model="reply.drafted_reply.body" 
                              style="background: rgba(0, 0, 0, 0.35); border: 1px solid rgba(99, 102, 241, 0.25); color: var(--text); font-family: inherit; font-size: 0.85rem; line-height: 1.5; width: 100%; min-height: 120px; resize: vertical; padding: 0.6rem 0.8rem; border-radius: 8px; margin-top: 0.25rem; outline: none; transition: all 0.2s;"
                              @focus="$event.target.style.borderColor = 'var(--primary)'; $event.target.style.boxShadow = '0 0 8px rgba(99,102,241,0.2)'"
                              @blur="$event.target.style.borderColor = 'rgba(99, 102, 241, 0.25)'; $event.target.style.boxShadow = 'none'"></textarea>
                </div>

                <!-- Actions -->
                <div class="reply-actions" v-if="reply.status === 'pending_review'">
                    <button class="btn btn-success"
                            @click="approveReply(reply.message_id)"
                            :disabled="loading">
                        ✅ Approve & Queue
                    </button>
                    <button class="btn btn-ghost"
                            @click="rejectReply(reply.message_id)"
                            :disabled="loading">
                        ❌ Reject
                    </button>
                </div>

                <div class="text-xs text-dim" style="margin-top: 0.5rem;">
                    Received: {{ formatDate(reply.date_received) }}
                </div>
            </div>
        </div>

        <div class="empty" v-else>
            <div class="empty-icon">📭</div>
            <div class="empty-text">No replies in this category</div>
        </div>

        <!-- Action result -->
        <div v-if="actionResult" class="alert-banner success mt-2"
             style="margin-top: 1rem;">
            {{ actionResult }}
        </div>
    </div>
    `,

    props: ['replies'],
    emits: ['refresh', 'run-command'],

    setup(props, { emit }) {
        const activeTab = ref('all')
        const loading = ref(false)
        const actionResult = ref('')

        const filteredReplies = computed(() => {
            if (activeTab.value === 'interested') return byIntent('interested')
            if (activeTab.value === 'pending') return byStatus('pending_review')
            if (activeTab.value === 'question') return byIntent('question')
            if (activeTab.value === 'replied') return byStatus('replied')
            return props.replies
        })

        function byIntent(intent) {
            return props.replies.filter(r => r.classification?.intent === intent)
        }

        function byStatus(status) {
            return props.replies.filter(r => r.status === status)
        }

        function intentClass(intent) {
            const map = {
                'interested': 'badge-success',
                'not_interested': 'badge-danger',
                'question': 'badge-info',
                'out_of_office': 'badge-gray',
                'other': 'badge-gray'
            }
            return map[intent] || 'badge-gray'
        }

        function statusBadge(status) {
            const map = {
                'pending_review': 'badge-warning',
                'ready_to_send': 'badge-info',
                'replied': 'badge-success',
                'rejected': 'badge-danger'
            }
            return map[status] || 'badge-gray'
        }

        function formatDate(dateStr) {
            if (!dateStr) return '—'
            try {
                return new Date(dateStr).toLocaleDateString('en-GB', {
                    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'
                })
            } catch { return dateStr }
        }

        async function approveReply(messageId) {
            loading.value = true
            const reply = props.replies.find(r => r.message_id === messageId)
            const editBody = reply?.drafted_reply?.body || ''

            const result = await postAction('/approve-reply', { 
                message_id: messageId,
                edit_body: editBody
            })
            if (result.success) {
                actionResult.value = `✅ Reply approved and queued`
                emit('refresh')
            }
            loading.value = false
            setTimeout(() => actionResult.value = '', 3000)
        }

        async function rejectReply(messageId) {
            loading.value = true
            await postAction('/reject-reply', { message_id: messageId })
            actionResult.value = '❌ Reply rejected'
            emit('refresh')
            loading.value = false
            setTimeout(() => actionResult.value = '', 3000)
        }

        async function approveAll(intent) {
            loading.value = true
            const result = await postAction('/approve-all', { intent })
            actionResult.value = `✅ Approved all ${intent} replies`
            emit('refresh')
            loading.value = false
            setTimeout(() => actionResult.value = '', 3000)
        }

        async function sendQueued() {
            loading.value = true
            const result = await postAction('/send-queued-replies')
            actionResult.value = result.message || '📤 Queued replies sent'
            emit('refresh')
            loading.value = false
            setTimeout(() => actionResult.value = '', 3000)
        }

        function fetchNewReplies() {
            emit('run-command', 'python response_management/reply_monitor.py')
        }

        return {
            activeTab, loading, actionResult, filteredReplies,
            byIntent, byStatus, intentClass, statusBadge, formatDate,
            approveReply, rejectReply, approveAll, sendQueued, fetchNewReplies
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// OUTREACH PAGE
// ─────────────────────────────────────────────────────────────────────────────
const OutreachPage = {
    template: `
    <div>
        <div class="flex justify-between items-center mb-3">
            <div>
                <h2 style="font-size: 1rem; font-weight: 700;">Outreach Control</h2>
                <p class="text-sm text-muted">Manage and trigger outreach channels</p>
            </div>
        </div>

        <!-- Channel Controls -->
        <div class="grid-2 mb-3">
            <div v-for="ch in channelControls" :key="ch.id" class="card">
                <div class="card-title">
                    {{ ch.icon }} {{ ch.name }}
                    <span class="badge" :class="ch.statusClass">{{ ch.status }}</span>
                </div>

                <div class="flex gap-2 mb-2" style="font-size: 0.82rem;">
                    <div>
                        <div class="text-dim text-xs">Total Sent</div>
                        <div class="font-bold" style="color: var(--text);">{{ ch.totalSent }}</div>
                    </div>
                    <div>
                        <div class="text-dim text-xs">Today</div>
                        <div class="font-bold" style="color: var(--text);">{{ ch.todaySent }}</div>
                    </div>
                    <div>
                        <div class="text-dim text-xs">Remaining</div>
                        <div class="font-bold" style="color: var(--success);">{{ ch.remaining }}</div>
                    </div>
                    <div>
                        <div class="text-dim text-xs">Failed</div>
                        <div class="font-bold" style="color: var(--danger);">{{ ch.failed }}</div>
                    </div>
                </div>

                <div class="progress-bar mb-2">
                    <div class="progress-fill"
                         :style="{ width: ch.pct + '%', background: ch.color }"></div>
                </div>

                <div class="flex gap-1">
                    <button class="btn btn-primary" style="flex: 1;"
                            @click="triggerChannel(ch.command)"
                            :disabled="loading || ch.remaining === 0">
                        {{ ch.remaining === 0 ? '✅ Limit Reached' : '▶ Send Now' }}
                    </button>
                    <button class="btn btn-ghost"
                            @click="triggerChannel(ch.command + ' --dry-run')"
                            :disabled="loading">
                        🔍
                    </button>
                </div>
            </div>
        </div>

        <!-- Crafted Outbound Queue Section -->
        <div class="card mb-3">
            <div class="card-title flex justify-between items-center" style="border-bottom: 1px solid var(--border); padding-bottom: 0.75rem; margin-bottom: 1rem;">
                <span style="font-size: 0.95rem; font-weight: 700; color: var(--primary-light);">✍️ Crafted Outbound Queue & Follow-Ups</span>
                <span class="badge badge-purple" v-if="sequences.length">{{ sequences.length }} Lead Campaigns</span>
            </div>
            
            <div v-if="!sequences.length" class="empty" style="padding: 3rem 0;">
                <div style="font-size: 2.5rem; margin-bottom: 0.75rem;">📋</div>
                <div class="empty-text font-bold" style="color: var(--text-dim);">No Crafted Message Sequences Found</div>
                <div class="text-xs text-muted mt-1" style="max-width: 400px; margin: 0.5rem auto 1rem;">
                    Run lead discovery, enrich, and execute <b>'Message Writer'</b> from Quick Actions to generate hyper-personalized outreach sequences.
                </div>
                <button class="btn btn-primary btn-sm" @click="triggerChannel('python outreach/message_writer.py')">
                    ✍️ Generate Sequences Now
                </button>
            </div>
            
            <div v-else class="outreach-grid" style="min-height: 420px;">
                <!-- Left panel: Lead List -->
                <div style="border-right: 1px solid var(--border); padding-right: 1rem; overflow-y: auto; max-height: 520px; display: flex; flex-direction: column; gap: 0.4rem;">
                    <div v-for="(seq, idx) in sequences" :key="seq.lead"
                         @click="selectedLeadIndex = idx"
                         style="padding: 0.75rem 1rem; border-radius: 8px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; transition: all 0.2s;"
                         :style="selectedLeadIndex === idx ? 'background: linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(167, 139, 250, 0.08)); border: 1px solid rgba(99, 102, 241, 0.3); color: var(--primary-light);' : 'border: 1px solid transparent; color: var(--text-muted);'">
                        <div style="font-size: 0.82rem; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 160px;">
                            {{ seq.lead }}
                        </div>
                        <span class="badge text-xs" :class="selectedLeadIndex === idx ? 'badge-primary' : 'badge-gray'" style="padding: 0.15rem 0.4rem;">
                            {{ seq.sequence?.length || 0 }} msg
                        </span>
                    </div>
                </div>
                
                <!-- Right panel: Lead Details & Timeline -->
                <div v-if="currentLead" style="overflow-y: auto; max-height: 520px; padding-right: 0.5rem;">
                    <div class="flex justify-between items-start mb-3" style="border-bottom: 1px solid var(--border); padding-bottom: 0.75rem;">
                        <div>
                            <h3 style="font-size: 1rem; font-weight: 700; color: var(--text); margin: 0;">{{ currentLead.lead }}</h3>
                            <div class="flex gap-2 mt-1.5" style="flex-wrap: wrap;">
                                <span v-if="currentLead.channels?.email" class="badge badge-purple text-xs">📧 {{ currentLead.channels.email }}</span>
                                <span v-if="currentLead.channels?.whatsapp" class="badge badge-success text-xs">💬 {{ currentLead.channels.whatsapp }}</span>
                                <span v-if="currentLead.channels?.instagram" class="badge badge-danger text-xs">📸 {{ currentLead.channels.instagram }}</span>
                                <span v-if="currentLead.channels?.facebook" class="badge badge-info text-xs">📘 {{ currentLead.channels.facebook }}</span>
                            </div>
                        </div>
                        <button class="btn btn-primary btn-sm" @click="approveAndQueueAll(currentLead)">
                            🚀 Approve Sequence
                        </button>
                    </div>
                    
                    <!-- Vertical Timeline -->
                    <div style="position: relative; padding-left: 1.5rem; margin-top: 1rem;">
                        <div style="position: absolute; left: 6px; top: 8px; bottom: 8px; width: 2px; background: var(--border);"></div>
                        
                        <div v-for="(msg, msgIdx) in currentLead.sequence" :key="msgIdx" 
                             style="position: relative; margin-bottom: 1.2rem;">
                            <!-- Timeline bullet -->
                            <div style="position: absolute; left: -22px; top: 4px; width: 14px; height: 14px; border-radius: 50%; border: 3px solid var(--surface);"
                                 :style="{ background: getChannelColor(msg.channel) }">
                            </div>
                            
                            <div class="card" style="margin: 0; padding: 0.85rem; border: 1px solid var(--border);">
                                <div class="flex justify-between items-center mb-2">
                                    <div class="flex gap-2 items-center">
                                        <span class="font-bold text-xs" style="color: var(--text-dim);">
                                            DAY {{ msg.day }}
                                        </span>
                                        <span class="badge" :style="{ background: getChannelColor(msg.channel) + '20', color: getChannelColor(msg.channel), border: '1px solid ' + getChannelColor(msg.channel) + '30' }" style="font-size: 0.65rem; padding: 0.1rem 0.35rem; font-weight: bold;">
                                            {{ msg.channel.toUpperCase() }}
                                        </span>
                                        <span class="text-xs text-muted" v-if="msg.to" style="opacity: 0.8;">
                                            → {{ msg.to }}
                                        </span>
                                    </div>
                                    <span class="badge text-xs" :class="msg.status === 'sent' ? 'badge-success' : msg.status === 'approved' ? 'badge-info' : 'badge-warning'" style="padding: 0.15rem 0.4rem;">
                                        {{ msg.status?.toUpperCase() || 'QUEUED' }}
                                    </span>
                                </div>
                                
                                <!-- Option Selector -->
                                <div v-if="hasOptions(msg)" class="flex gap-1 mb-2 mt-1" style="flex-wrap: wrap;">
                                    <button v-for="opt in getParsedOptions(msg)" :key="opt.number"
                                            class="btn text-xs btn-sm"
                                            :style="msg.selected_option === opt.number ? 
                                                    { 
                                                        background: getChannelColor(msg.channel) + '25', 
                                                        color: getChannelColor(msg.channel), 
                                                        border: '1px solid ' + getChannelColor(msg.channel) 
                                                    } : 
                                                    { 
                                                        background: 'rgba(255,255,255,0.03)', 
                                                        color: 'var(--text-muted)', 
                                                        border: '1px solid var(--border)' 
                                                    }"
                                            style="padding: 0.2rem 0.5rem; font-weight: 600; border-radius: 6px; font-size: 0.72rem;"
                                            @click="confirmSelectOption(msg, opt.number, opt.text)">
                                        {{ opt.number === 1 ? 'Option 1: Formal' : opt.number === 2 ? 'Option 2: Warm' : 'Option 3: Short DM' }}
                                    </button>
                                </div>

                                <!-- Content preview -->
                                <div style="background: rgba(0,0,0,0.2); border-radius: 6px; padding: 0.65rem; font-size: 0.8rem; line-height: 1.45;">
                                    <div v-if="msg.subject" style="font-weight: 700; border-bottom: 1px solid var(--border); padding-bottom: 0.3rem; margin-bottom: 0.3rem; color: var(--text);">
                                        Subject: {{ msg.subject }}
                                    </div>
                                    <div style="white-space: pre-wrap; color: var(--text-muted); font-size: 0.78rem;">{{ msg.content }}</div>
                                </div>
                                
                                <!-- Timeline action buttons -->
                                <div class="flex gap-1 mt-2 justify-end">
                                    <button class="btn btn-ghost text-xs" style="padding: 0.25rem 0.5rem; font-size: 0.75rem;" @click="openEditModal(msg, msgIdx)">
                                        ✍️ Edit Message
                                    </button>
                                    <button class="btn btn-primary text-xs" style="padding: 0.25rem 0.5rem; font-size: 0.75rem;" 
                                            @click="toggleMessageStatus(msg)" 
                                            :disabled="msg.status === 'sent'">
                                        {{ msg.status === 'approved' ? '⏸️ Hold' : '✅ Approve' }}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Edit Message Modal -->
        <div v-if="showEditModal" style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 1rem;" @click.self="showEditModal = false">
            <div class="card" style="width: 100%; max-width: 550px; padding: 1.5rem; margin: auto; border: 1px solid var(--border); box-shadow: 0 10px 25px rgba(0,0,0,0.5);">
                <div class="flex justify-between items-center mb-3" style="border-bottom: 1px solid var(--border); padding-bottom: 0.5rem;">
                    <span style="font-size: 0.95rem; font-weight: 700; color: var(--primary-light);">Edit Crafted Message — Day {{ editingMsg.day }} ({{ editingMsg.channel }})</span>
                    <button class="btn btn-ghost" aria-label="Close" style="padding: 0.2rem 0.5rem;" @click="showEditModal = false">✕</button>
                </div>
                
                <div class="mb-3" v-if="editingMsg.subject !== undefined">
                    <label class="text-xs text-dim mb-1 block" style="font-weight: 600;">Email Subject</label>
                    <input type="text" v-model="editSubject" 
                           style="width: 100%; background: var(--surface2); border: 1px solid var(--border); color: var(--text); padding: 0.5rem; border-radius: 6px; outline: none; font-size: 0.8rem;" />
                </div>
                
                <div class="mb-3">
                    <label class="text-xs text-dim mb-1 block" style="font-weight: 600;">Message Body</label>
                    <textarea rows="10" v-model="editContent" 
                              style="width: 100%; background: var(--surface2); border: 1px solid var(--border); color: var(--text); padding: 0.5rem; border-radius: 6px; outline: none; font-size: 0.8rem; font-family: inherit; line-height: 1.45; resize: vertical;"></textarea>
                </div>
                
                <div class="flex gap-1 justify-end" style="border-top: 1px solid var(--border); padding-top: 0.75rem;">
                    <button class="btn btn-ghost" @click="showEditModal = false">Cancel</button>
                    <button class="btn btn-primary" @click="saveEditedMessage">Save Changes</button>
                </div>
            </div>
        </div>

        <!-- Option Selection Confirmation Modal -->
        <div v-if="showConfirmModal" style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center; z-index: 1010; padding: 1rem;" @click.self="showConfirmModal = false">
            <div class="card" style="width: 100%; max-width: 400px; padding: 1.5rem; margin: auto; border: 1px solid var(--border); box-shadow: 0 10px 25px rgba(0,0,0,0.5); text-align: center;">
                <div style="font-size: 2.2rem; margin-bottom: 0.5rem;">✍️</div>
                <h3 style="font-size: 1rem; font-weight: 700; color: var(--text); margin-bottom: 0.5rem;">Switch Message Option?</h3>
                <p class="text-xs text-muted mb-4" style="line-height: 1.5;">
                    Are you sure you want to switch to <strong>Option {{ confirmOptNumber }}</strong> ({{ confirmOptNumber === 1 ? 'Formal' : confirmOptNumber === 2 ? 'Warm' : 'Short DM' }})? This will replace the current active message content.
                </p>
                <div class="flex gap-2 justify-center">
                    <button class="btn btn-ghost btn-sm" @click="showConfirmModal = false">Cancel</button>
                    <button class="btn btn-primary btn-sm" @click="applySelectOption">Confirm Switch</button>
                </div>
            </div>
        </div>

        <!-- Quick Actions -->
        <div class="card mb-3">
            <div class="card-title">Quick Actions</div>
            <div class="grid-actions">
                <button v-for="action in quickActions" :key="action.label"
                        class="btn" :class="action.btnClass"
                        @click="triggerChannel(action.command)"
                        :disabled="loading"
                        style="justify-content: flex-start; padding: 0.75rem 1rem;">
                    <span>{{ action.icon }}</span>
                    <div style="text-align: left;">
                        <div style="font-size: 0.82rem;">{{ action.label }}</div>
                        <div style="font-size: 0.7rem; opacity: 0.7;">{{ action.desc }}</div>
                    </div>
                </button>
            </div>
        </div>

        <!-- Action Log -->
        <div class="card">
            <div class="card-title">Recent Actions</div>
            <div class="timeline" v-if="actionLog.length">
                <div v-for="entry in actionLog" :key="entry.time" class="timeline-item">
                    <div class="timeline-dot"
                         :style="{ background: entry.success ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)' }">
                        {{ entry.success ? '✅' : '❌' }}
                    </div>
                    <div class="timeline-content">
                        <div class="timeline-title">{{ entry.command }}</div>
                        <div class="timeline-time">{{ entry.time }}</div>
                        <div class="timeline-detail" v-if="entry.output">
                            {{ entry.output.substring(0, 200) }}
                        </div>
                    </div>
                </div>
            </div>
            <div class="empty" v-else>
                <div class="empty-text text-dim">No actions run yet this session</div>
            </div>
        </div>

        <!-- Detailed Outreach Logs (Last 12 Days) -->
        <div class="card" style="margin-top: 1.5rem;">
            <div class="card-title flex justify-between items-center" style="border-bottom: 1px solid var(--border); padding-bottom: 0.75rem; margin-bottom: 1rem;">
                <span style="font-size: 0.95rem; font-weight: 700; color: var(--primary-light);">📊 Detailed Outreach Logs (Last 12 Days)</span>
                <button class="btn btn-ghost btn-sm" @click="fetchDetailedLogs" :disabled="logsLoading" style="font-size: 0.75rem; padding: 0.25rem 0.5rem;">
                    {{ logsLoading ? '🔄 Loading...' : '🔄 Refresh Logs' }}
                </button>
            </div>

            <!-- Filter Bar -->
            <div class="log-filter-bar">
                <span class="text-xs text-muted font-bold" style="text-transform: uppercase; letter-spacing: 0.5px;">Filters:</span>
                <select v-model="filterChannel" class="log-filter-select">
                    <option value="">All Channels</option>
                    <option value="email">📧 Email</option>
                    <option value="whatsapp">💬 WhatsApp</option>
                    <option value="facebook">📘 Facebook</option>
                    <option value="instagram">📸 Instagram</option>
                </select>

                <select v-model="filterStatus" class="log-filter-select">
                    <option value="">All Statuses</option>
                    <option value="success">✅ Success</option>
                    <option value="failed">❌ Failed</option>
                </select>
                
                <span class="text-xs text-dim" style="margin-left: auto;" v-if="filteredLogs.length">
                    Showing {{ filteredLogs.length }} message{{ filteredLogs.length !== 1 ? 's' : '' }}
                </span>
            </div>

            <!-- Logs List -->
            <div class="logs-container" v-if="filteredLogs.length">
                <div v-for="log in filteredLogs" :key="log.id" class="log-card" :class="['channel-' + log.channel, { 'is-expanded': log.expanded }]">
                    <!-- Header (clickable to expand) -->
                    <div class="log-header" @click="toggleLogExpansion(log)">
                        <div class="log-meta-left">
                            <span :class="['log-channel-badge', log.channel]">
                                <span v-if="log.channel === 'email'">📧 Email</span>
                                <span v-else-if="log.channel === 'whatsapp'">💬 WhatsApp</span>
                                <span v-else-if="log.channel === 'facebook'">📘 Facebook</span>
                                <span v-else-if="log.channel === 'instagram'">📸 Instagram</span>
                            </span>
                            
                            <span class="log-business-name" :title="log.business">
                                {{ log.business || 'Unknown Business' }}
                            </span>
                            
                            <span class="log-direction" style="opacity: 0.85;">
                                → {{ log.recipient || 'Unknown Recipient' }}
                            </span>
                        </div>
                        
                        <div class="log-meta-right">
                            <span class="badge" :class="log.success ? 'badge-success' : 'badge-danger'" style="font-size: 0.7rem; padding: 0.15rem 0.45rem;">
                                {{ log.success ? 'Success' : 'Failed' }}
                            </span>
                            <span class="log-time">
                                {{ formatLogDate(log.timestamp) }}
                            </span>
                            <span class="log-expand-icon">▼</span>
                        </div>
                    </div>

                    <!-- Expandable Body -->
                    <div class="log-body" v-if="log.expanded">
                        <!-- Error banner if failed -->
                        <div class="log-error-banner" v-if="!log.success">
                            <span>🚨</span>
                            <div>
                                <strong style="font-weight: 700;">Delivery Failure:</strong>
                                <span style="margin-left: 0.25rem;">{{ log.error || 'Unknown error occurred during sending.' }}</span>
                            </div>
                        </div>

                        <!-- Routing details (From / To) -->
                        <div class="log-routing-details">
                            <div class="log-route-item">
                                <span class="log-route-label">From (Sender)</span>
                                <span class="log-route-value" v-if="log.channel === 'email'">
                                    {{ config?.brevo?.from_name || 'Olie' }} &lt;{{ config?.brevo?.from_email || 'oliekings@gmail.com' }}&gt;
                                </span>
                                <span class="log-route-value" v-else-if="log.channel === 'whatsapp'">
                                    WhatsApp Account ({{ config?.owner?.whatsapp || '+2348128493744' }})
                                </span>
                                <span class="log-route-value" v-else-if="log.channel === 'facebook'">
                                    Facebook Page Messenger
                                </span>
                                <span class="log-route-value" v-else-if="log.channel === 'instagram'">
                                    Instagram Direct Messenger (@oliekings_outreach)
                                </span>
                            </div>
                            <div class="log-route-item">
                                <span class="log-route-label">To (Recipient)</span>
                                <span class="log-route-value">{{ log.recipient || '—' }}</span>
                            </div>
                            <div class="log-route-item" v-if="log.channel === 'email' && log.subject">
                                <span class="log-route-label">Subject</span>
                                <span class="log-route-value" style="font-family: inherit;">{{ log.subject }}</span>
                            </div>
                        </div>

                        <!-- Message Content Preview -->
                        <div class="log-message-preview">
                            <div class="log-message-subject" v-if="log.channel === 'email' && log.subject">
                                Subject: {{ log.subject }}
                            </div>
                            <div style="font-size: 0.8rem; font-family: inherit;">{{ log.message }}</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Loading State -->
            <div class="loading" v-else-if="logsLoading" style="padding: 3rem 0;">
                <div class="spinner"></div>
                <div class="text-muted text-sm" style="margin-top: 0.5rem;">Fetching outreach history logs...</div>
            </div>

            <!-- Empty State -->
            <div class="empty" v-else style="padding: 3rem 0;">
                <div style="font-size: 2.5rem; margin-bottom: 0.75rem;">📊</div>
                <div class="empty-text font-bold" style="color: var(--text-dim);">No Outreach Logs Found</div>
                <div class="text-xs text-muted mt-1" style="max-width: 400px; margin: 0.5rem auto;">
                    There are no logged outreach sends matching the current filters for the past 12 days.
                </div>
            </div>
        </div>
    </div>
    `,

    props: ['state', 'config'],

    setup(props) {
        const loading = ref(false)
        const actionLog = ref([])

        // Detailed Outreach Logs state
        const detailedLogs = ref([])
        const logsLoading = ref(false)
        const filterChannel = ref('')
        const filterStatus = ref('')

        async function fetchDetailedLogs() {
            logsLoading.value = true
            try {
                const res = await fetchData('/logs/detailed')
                if (res) {
                    detailedLogs.value = res.map((log, index) => ({
                        ...log,
                        id: `${log.timestamp}_${log.recipient}_${index}`,
                        expanded: false
                    }))
                }
            } catch (e) {
                console.error("Failed to load detailed logs:", e)
            } finally {
                logsLoading.value = false
            }
        }

        function toggleLogExpansion(log) {
            log.expanded = !log.expanded
        }

        const filteredLogs = computed(() => {
            return detailedLogs.value.filter(log => {
                const matchesChannel = !filterChannel.value || log.channel === filterChannel.value
                const matchesStatus = !filterStatus.value || 
                    (filterStatus.value === 'success' && log.success) || 
                    (filterStatus.value === 'failed' && !log.success)
                return matchesChannel && matchesStatus
            })
        })

        function formatLogDate(dateStr) {
            if (!dateStr) return '—'
            try {
                return new Date(dateStr).toLocaleString('en-GB', {
                    day: 'numeric',
                    month: 'short',
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit'
                })
            } catch {
                return dateStr
            }
        }

        // Outbound sequence states
        const sequences = ref([])
        const selectedLeadIndex = ref(0)
        
        // Message editing state
        const showEditModal = ref(false)
        const editingMsg = ref(null)
        const editingMsgIdx = ref(-1)
        const editSubject = ref("")
        const editContent = ref("")

        // Message option selection state
        const showConfirmModal = ref(false)
        const confirmMsg = ref(null)
        const confirmOptNumber = ref(-1)
        const confirmOptText = ref("")

        const currentLead = computed(() => {
            if (sequences.value.length && selectedLeadIndex.value < sequences.value.length) {
                return sequences.value[selectedLeadIndex.value]
            }
            return null
        })

        async function fetchSequences() {
            try {
                const res = await fetchData('/outreach/sequences')
                if (res) {
                    res.forEach(lead => {
                        if (lead.sequence) {
                            lead.sequence.forEach(msg => {
                                if (msg.content && msg.content.includes("Option 1:") && !msg.raw_content) {
                                    msg.raw_content = msg.content;
                                    if (!msg.selected_option) {
                                        msg.selected_option = msg.channel === 'email' ? 2 : 3;
                                    }
                                    msg.content = cleanMessageContent(msg.raw_content, msg.selected_option);
                                }
                            });
                        }
                    });
                    sequences.value = res
                }
            } catch (e) {
                console.error("Failed to load sequences:", e)
            }
        }

        function hasOptions(msg) {
            const content = msg.raw_content || msg.content;
            return content && content.includes("Option 1:");
        }

        function getParsedOptions(msg) {
            const content = msg.raw_content || msg.content;
            return parseOptions(content) || [];
        }

        function confirmSelectOption(msg, optNumber, optText) {
            if (msg.selected_option === optNumber) return;
            confirmMsg.value = msg;
            confirmOptNumber.value = optNumber;
            confirmOptText.value = optText;
            showConfirmModal.value = true;
        }

        function applySelectOption() {
            if (confirmMsg.value) {
                confirmMsg.value.selected_option = confirmOptNumber.value;
                confirmMsg.value.content = confirmOptText.value;
                showConfirmModal.value = false;
                saveSequences();
            }
        }

        function getChannelColor(channel) {
            const map = {
                whatsapp: '#25D366',
                email: '#6366F1',
                instagram: '#E1306C',
                facebook: '#1877F2'
            }
            return map[channel] || '#6B7280'
        }

        function toggleMessageStatus(msg) {
            if (msg.status === 'sent') return
            msg.status = msg.status === 'approved' ? 'queued' : 'approved'
            saveSequences()
        }

        function approveAndQueueAll(leadSeq) {
            leadSeq.sequence.forEach(msg => {
                if (msg.status !== 'sent') {
                    msg.status = 'approved'
                }
            })
            saveSequences()
        }

        function openEditModal(msg, idx) {
            editingMsg.value = msg
            editingMsgIdx.value = idx
            editSubject.value = msg.subject || ""
            editContent.value = msg.content || ""
            showEditModal.value = true
        }

        function saveEditedMessage() {
            if (editingMsg.value) {
                editingMsg.value.content = editContent.value
                if (editingMsg.value.subject !== undefined) {
                    editingMsg.value.subject = editSubject.value
                }
                showEditModal.value = false
                saveSequences()
            }
        }

        async function saveSequences() {
            try {
                await postAction('/outreach/sequences', sequences.value)
            } catch (e) {
                console.error("Failed to save sequences:", e)
            }
        }

        onMounted(() => {
            fetchSequences()
            fetchDetailedLogs()
        })

        const cfg = computed(() => props.config?.outreach || {})
        const outreach = computed(() => props.state?.outreach || {})

        const channelControls = computed(() => {
            const make = (id, name, icon, color, cmd, limit_key) => {
                const data = outreach.value[id] || {}
                const limit = cfg.value[limit_key] || 0
                const today = data.sent_today || 0
                const total = data.total_sent || 0
                const failed = data.failed || 0
                const remaining = Math.max(0, limit - today)
                return {
                    id, name, icon, color, command: cmd,
                    totalSent: total, todaySent: today, remaining, failed,
                    pct: Math.min((today / Math.max(limit, 1)) * 100, 100),
                    status: remaining > 0 ? 'active' : 'limit reached',
                    statusClass: remaining > 0 ? 'badge-success' : 'badge-warning'
                }
            }
            return [
                make('whatsapp', 'WhatsApp', '💬', '#25D366', 'python outreach/whatsapp_sender.py --ignore-timing', 'daily_whatsapp_limit'),
                make('email', 'Email', '📧', '#6366F1', 'python outreach/email_sender.py --ignore-timing', 'daily_email_limit'),
                make('instagram', 'Instagram', '📸', '#E1306C', 'python outreach/instagram_sender.py --ignore-timing', 'daily_instagram_limit'),
                make('facebook', 'Facebook', '📘', '#1877F2', 'python outreach/facebook_sender.py --ignore-timing', 'daily_facebook_limit')
            ]
        })

        const quickActions = [
            { label: 'Find New Leads', desc: 'Run lead finder', icon: '🔍', command: 'python intelligence/lead_finder.py', btnClass: 'btn-ghost' },
            { label: 'Enrich Leads', desc: 'Deep research', icon: '🔬', command: 'python intelligence/lead_enricher.py', btnClass: 'btn-ghost' },
            { label: 'Build Sites', desc: 'Sample websites', icon: '🌐', command: 'python intelligence/general_auditor.py', btnClass: 'btn-ghost' },
            { label: 'Check Inbox', desc: 'Monitor replies', icon: '📬', command: 'python response_management/reply_monitor.py', btnClass: 'btn-ghost' },
            { label: 'Run Audit', desc: 'Full system audit', icon: '📊', command: 'python ai_ceo.py audit', btnClass: 'btn-ghost' },
            { label: 'CEO Full Run', desc: 'Complete daily run', icon: '🤖', command: 'python ai_ceo.py full', btnClass: 'btn-primary' }
        ]

        async function triggerChannel(command) {
            loading.value = true
            const result = await postAction('/run-command', { command })
            actionLog.value.unshift({
                command,
                time: new Date().toLocaleTimeString(),
                success: result.success,
                output: result.output || result.error || ''
            })
            if (actionLog.value.length > 20) actionLog.value.pop()
            loading.value = false
            // Proactively refresh sequences in case message writer generated new ones!
            fetchSequences()
            // Proactively refresh detailed logs!
            fetchDetailedLogs()
        }

        return { 
            loading, actionLog, channelControls, quickActions, triggerChannel,
            sequences, selectedLeadIndex, currentLead, getChannelColor,
            toggleMessageStatus, approveAndQueueAll, openEditModal, showEditModal,
            editingMsg, editSubject, editContent, saveEditedMessage,
            showConfirmModal, confirmOptNumber, confirmSelectOption, applySelectOption,
            hasOptions, getParsedOptions,
            detailedLogs, logsLoading, filterChannel, filterStatus, fetchDetailedLogs, toggleLogExpansion, filteredLogs, formatLogDate
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// AUDIT PAGE
// ─────────────────────────────────────────────────────────────────────────────
const AuditPage = {
    template: `
    <div>
        <div class="flex justify-between items-center mb-3">
            <div>
                <h2 style="font-size: 1rem; font-weight: 700;">CEO Audit</h2>
                <p class="text-sm text-muted">Daily performance intelligence</p>
            </div>
            <button class="btn btn-primary" @click="runAudit" :disabled="loading">
                {{ loading ? '⏳ Running...' : '🔄 Run Audit Now' }}
            </button>
        </div>

        <div v-if="audit">
            <!-- Health + KPIs -->
            <div class="grid-3 mb-3">
                <div class="card" style="text-align: center;">
                    <div class="text-xs text-dim mb-2">OVERALL HEALTH</div>
                    <div style="font-size: 2.5rem; font-weight: 800;"
                         :style="{ color: healthColor }">
                        {{ audit.health_score }}
                    </div>
                    <div class="text-xs text-muted">/ 100</div>
                    <div class="badge mt-1" :class="healthClass">
                        {{ audit.overall_health?.toUpperCase() }}
                    </div>
                </div>

                <div class="card" style="text-align: center;">
                    <div class="text-xs text-dim mb-2">PIPELINE VALUE</div>
                    <div style="font-size: 1.5rem; font-weight: 800; color: var(--success);">
                        ₦{{ formatNumber(audit.kpis?.estimated_pipeline_value_ngn || 0) }}
                    </div>
                    <div class="text-xs text-muted">estimated</div>
                </div>

                <div class="card" style="text-align: center;">
                    <div class="text-xs text-dim mb-2">DAYS TO 1ST CLIENT</div>
                    <div style="font-size: 1.5rem; font-weight: 800; color: var(--warning);">
                        {{ audit.kpis?.days_to_first_client_estimate || '?' }}
                    </div>
                    <div class="text-xs text-muted">estimate</div>
                </div>
            </div>

            <!-- CEO Message -->
            <div class="ceo-message mb-3">
                <div class="ceo-avatar">🤖</div>
                <div class="text-xs text-dim mb-1">CEO ASSESSMENT</div>
                <div class="ceo-message-text">{{ audit.ceo_message }}</div>
            </div>

            <div class="grid-2 mb-3">
                <!-- Critical Issues -->
                <div class="card">
                    <div class="card-title">🔴 Critical Issues</div>
                    <div v-if="audit.critical_issues?.length">
                        <div v-for="issue in audit.critical_issues" :key="issue"
                             class="alert-banner danger mb-1"
                             style="margin-bottom: 0.5rem;">
                            {{ issue }}
                        </div>
                    </div>
                    <div class="empty" v-else style="padding: 1rem;">
                        <div class="text-sm text-muted">No critical issues 🎉</div>
                    </div>
                </div>

                <!-- Opportunities -->
                <div class="card">
                    <div class="card-title">✅ Opportunities</div>
                    <div v-if="audit.opportunities?.length"
                         style="display: flex; flex-direction: column; gap: 0.5rem;">
                        <div v-for="opp in audit.opportunities" :key="opp"
                             style="display: flex; gap: 0.5rem; align-items: flex-start;">
                            <span style="color: var(--success);">→</span>
                            <span class="text-sm text-muted">{{ opp }}</span>
                        </div>
                    </div>
                    <div class="empty" v-else style="padding: 1rem;">
                        <div class="text-sm text-muted">Keep working the system</div>
                    </div>
                </div>
            </div>

            <!-- Weekly Targets -->
            <div class="card mb-3" v-if="audit.weekly_targets?.length">
                <div class="card-title">📅 Weekly Targets</div>
                <div style="display: flex; flex-direction: column; gap: 0.6rem;">
                    <div v-for="(t, i) in audit.weekly_targets" :key="i"
                         style="display: flex; gap: 0.75rem; align-items: center;">
                        <div style="width: 28px; height: 28px; border-radius: 8px;
                                    background: rgba(16,185,129,0.15); display: flex;
                                    align-items: center; justify-content: center;
                                    font-size: 0.8rem; color: var(--success); flex-shrink: 0;">
                            {{ i + 1 }}
                        </div>
                        <div class="text-sm text-muted">{{ t }}</div>
                    </div>
                </div>
            </div>

            <!-- Hire Signal -->
            <div class="alert-banner warning" v-if="audit.hire_signal?.includes('yes')">
                👥 HIRING SIGNAL: {{ audit.hire_signal }}
            </div>
        </div>

        <div class="loading" v-else>
            <div class="spinner"></div>
            <div class="text-muted text-sm">Run an audit to see results</div>
        </div>
    </div>
    `,

    props: ['audit'],
    emits: ['refresh'],

    setup(props, { emit }) {
        const loading = ref(false)

        const healthColor = computed(() => {
            const score = props.audit?.health_score || 0
            if (score >= 80) return '#10B981'
            if (score >= 60) return '#F59E0B'
            return '#EF4444'
        })

        const healthClass = computed(() => {
            const h = props.audit?.overall_health
            if (['excellent', 'good'].includes(h)) return 'badge-success'
            if (h === 'fair') return 'badge-warning'
            return 'badge-danger'
        })

        function formatNumber(n) {
            if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M'
            if (n >= 1000) return (n / 1000).toFixed(0) + 'K'
            return n.toString()
        }

        async function runAudit() {
            loading.value = true
            await postAction('/run-command', { command: 'python ai_ceo.py audit' })
            emit('refresh')
            loading.value = false
        }

        return { loading, healthColor, healthClass, formatNumber, runAudit }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// SETTINGS PAGE
// ─────────────────────────────────────────────────────────────────────────────
const SettingsPage = {
    template: `
    <div>
        <div class="tabs">
            <div class="tab" :class="{ active: activeTab === 'ceo' }" @click="activeTab = 'ceo'">
                🤖 CEO Config
            </div>
            <div class="tab" :class="{ active: activeTab === 'env' }" @click="activeTab = 'env'">
                🔑 API Keys (.env)
            </div>
        </div>

        <div v-if="activeTab === 'ceo'">
            <div class="card mb-3">
                <div class="card-title">General Settings</div>
                <div class="grid-2">
                    <div class="form-group" v-if="localConfig.owner">
                        <label>CEO Name</label>
                        <input type="text" v-model="localConfig.owner.name" class="form-input">
                    </div>
                    <div class="form-group" v-if="localConfig.owner">
                        <label>Owner WhatsApp</label>
                        <input type="text" v-model="localConfig.owner.whatsapp" class="form-input">
                    </div>
                    <div class="form-group" v-if="localConfig.owner">
                        <label>Review Deadline (Hours)</label>
                        <input type="number" v-model="localConfig.owner.review_deadline_hours" class="form-input">
                    </div>
                </div>
            </div>

            <div class="card mb-3" v-if="localConfig.outreach">
                <div class="card-title">Outreach Limits</div>
                <div class="grid-2">
                    <div class="form-group">
                        <label>Daily Email Limit</label>
                        <input type="number" v-model="localConfig.outreach.daily_email_limit" class="form-input">
                    </div>
                    <div class="form-group">
                        <label>Daily WhatsApp Limit</label>
                        <input type="number" v-model="localConfig.outreach.daily_whatsapp_limit" class="form-input">
                    </div>
                    <div class="form-group">
                        <label>Daily Instagram Limit</label>
                        <input type="number" v-model="localConfig.outreach.daily_instagram_limit" class="form-input">
                    </div>
                    <div class="form-group">
                        <label>Daily Facebook Limit</label>
                        <input type="number" v-model="localConfig.outreach.daily_facebook_limit" class="form-input">
                    </div>
                </div>
            </div>

            <div class="card mb-3" v-if="localConfig.outreach">
                <div class="card-title">Lead Generation Batch Targets</div>
                <div class="grid-3">
                    <div class="form-group">
                        <label>Morning Target (9:00 AM)</label>
                        <input type="number" v-model="localConfig.outreach.morning_leads_limit" class="form-input">
                    </div>
                    <div class="form-group">
                        <label>Afternoon Target (1:00 PM)</label>
                        <input type="number" v-model="localConfig.outreach.afternoon_leads_limit" class="form-input">
                    </div>
                    <div class="form-group">
                        <label>Evening Target (5:00 PM)</label>
                        <input type="number" v-model="localConfig.outreach.evening_leads_limit" class="form-input">
                    </div>
                </div>
            </div>

            <div class="card mb-3" v-if="localConfig.outreach">
                <div class="card-title">Targeting</div>
                <div class="form-group">
                    <label>Country</label>
                    <input type="text" v-model="localConfig.outreach.country" class="form-input">
                </div>
                <div class="form-group">
                    <label>Cities (comma separated)</label>
                    <input type="text" :value="localConfig.outreach.cities.join(', ')" 
                           @input="localConfig.outreach.cities = $event.target.value.split(',').map(s => s.trim())"
                           class="form-input">
                </div>
                <div class="form-group">
                    <label>Niches (comma separated)</label>
                    <input type="text" :value="localConfig.outreach.niches.join(', ')" 
                           @input="localConfig.outreach.niches = $event.target.value.split(',').map(s => s.trim())"
                           class="form-input">
                </div>
            </div>

            <div class="flex justify-end">
                <button class="btn btn-primary" @click="saveConfig" :disabled="loading">
                    {{ loading ? 'Saving...' : 'Save CEO Config' }}
                </button>
            </div>
        </div>

        <div v-if="activeTab === 'env'">
            <div class="card mb-3">
                <div class="card-title">System API Keys & Credentials</div>
                <p class="text-xs text-dim mb-2">These are stored in your .env file. Clicking an input will reveal the key.</p>
                <div class="grid-env">
                    <div v-for="(val, key) in envVars" :key="key" class="form-group">
                        <label>{{ key }}</label>
                        <input type="password" v-model="envVars[key]" class="form-input" 
                               @focus="$event.target.type='text'" @blur="$event.target.type='password'">
                    </div>
                </div>
            </div>

            <div class="flex justify-end">
                <button class="btn btn-primary" @click="saveEnv" :disabled="loading">
                    {{ loading ? 'Saving...' : 'Save API Keys' }}
                </button>
            </div>
        </div>
    </div>
    `,
    props: ['config'],
    emits: ['refresh'],
    setup(props, { emit }) {
        const activeTab = ref('ceo')
        const loading = ref(false)
        const localConfig = ref(JSON.parse(JSON.stringify(props.config)))
        const envVars = ref({})

        // Initialize limits if not present
        const initLimits = (cfg) => {
            if (cfg && cfg.outreach) {
                if (cfg.outreach.morning_leads_limit === undefined) cfg.outreach.morning_leads_limit = 10;
                if (cfg.outreach.afternoon_leads_limit === undefined) cfg.outreach.afternoon_leads_limit = 10;
                if (cfg.outreach.evening_leads_limit === undefined) cfg.outreach.evening_leads_limit = 10;
            }
        };
        initLimits(localConfig.value);

        // Keep localConfig in sync if parent config changes
        watch(() => props.config, (newVal) => {
            if (newVal) {
                localConfig.value = JSON.parse(JSON.stringify(newVal));
                initLimits(localConfig.value);
            }
        }, { deep: true });

        onMounted(async () => {
            try {
                const res = await axios.get(`${API}/env`)
                envVars.value = res.data
            } catch (e) {}
        })

        async function saveConfig() {
            loading.value = true
            try {
                await axios.post(`${API}/config`, localConfig.value)
                emit('refresh')
            } catch (e) {
                alert('Failed to save config')
            }
            loading.value = false
        }

        async function saveEnv() {
            loading.value = true
            try {
                await axios.post(`${API}/env`, envVars.value)
                alert('API Keys saved! Restart the dashboard server to apply changes.')
            } catch (e) {
                alert('Failed to save API keys')
            }
            loading.value = false
        }

        return { activeTab, loading, localConfig, envVars, saveConfig, saveEnv }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// SCALE PAGE
// ─────────────────────────────────────────────────────────────────────────────
const ScalePage = {
    template: `
    <div>
        <div class="flex justify-between items-center mb-3">
            <div>
                <h2 style="font-size: 1rem; font-weight: 700;">Scale & Expansion</h2>
                <p class="text-sm text-muted">Grow your outreach into new markets</p>
            </div>
            <button class="btn btn-primary" @click="showNewCampaign = true">
                🚀 Launch New Campaign
            </button>
        </div>

        <!-- Revenue Dashboard -->
        <div class="grid-4 mb-3" v-if="analytics">
            <div class="card" style="text-align: center; border-left: 4px solid var(--success);">
                <div class="text-xs text-dim mb-1 uppercase tracking-wider">Est. Monthly Revenue</div>
                <div style="font-size: 1.25rem; font-weight: 800; color: var(--success);">
                    ₦{{ formatMoney(analytics.revenue?.expected_monthly_ngn || 0) }}
                </div>
            </div>
            <div class="card" style="text-align: center; border-left: 4px solid var(--success);">
                <div class="text-xs text-dim mb-1 uppercase tracking-wider">Est. Annual Revenue</div>
                <div style="font-size: 1.25rem; font-weight: 800; color: var(--success);">
                    ₦{{ formatMoney(analytics.revenue?.expected_annual_ngn || 0) }}
                </div>
            </div>
            <div class="card" style="text-align: center; border-left: 4px solid var(--info);">
                <div class="text-xs text-dim mb-1 uppercase tracking-wider">Avg. Deal Size</div>
                <div style="font-size: 1.25rem; font-weight: 800; color: var(--info);">
                    ₦{{ formatMoney(analytics.revenue?.avg_deal_ngn || 0) }}
                </div>
            </div>
            <div class="card" style="text-align: center; border-left: 4px solid var(--warning);">
                <div class="text-xs text-dim mb-1 uppercase tracking-wider">Pipeline Value</div>
                <div style="font-size: 1.25rem; font-weight: 800; color: var(--warning);">
                    ₦{{ formatMoney(analytics.revenue?.potential_pipeline_ngn || 0) }}
                </div>
            </div>
        </div>

        <div class="grid-2 mb-3">
            <!-- Active Campaigns -->
            <div class="card">
                <div class="card-title">Active Campaigns</div>
                <div v-if="campaigns && campaigns.length">
                    <div v-for="c in campaigns" :key="c.id" class="mb-3 p-3 border-rounded" 
                         style="background: var(--surface2); border: 1px solid var(--border);">
                        <div class="flex justify-between items-center mb-1">
                            <div class="font-bold text-sm">{{ c.name }}</div>
                            <span class="badge" :class="c.status === 'active' ? 'badge-success' : 'badge-gray'">{{ c.status }}</span>
                        </div>
                        <div class="text-xs text-dim mb-2">📍 {{ c.city }} • {{ c.niches?.join(', ') }}</div>
                        <div class="progress-bar mb-1" style="height: 6px;">
                            <div class="progress-fill" :style="{ width: (c.leads_found / (c.target_leads || 1) * 100) + '%' }"></div>
                        </div>
                        <div class="flex justify-between text-xs">
                            <span class="text-muted">{{ c.leads_found }} / {{ c.target_leads }} leads found</span>
                            <span class="font-bold">{{ Math.round(c.leads_found / (c.target_leads || 1) * 100) }}%</span>
                        </div>
                    </div>
                </div>
                <div class="empty" v-else style="padding: 2rem;">
                    <div class="text-muted text-sm">No active campaigns</div>
                    <button class="btn btn-ghost mt-2" @click="showNewCampaign = true">Create your first campaign</button>
                </div>
            </div>

            <!-- Expansion Roadmap -->
            <div class="card">
                <div class="card-title">🗺️ Expansion Roadmap</div>
                <p class="text-xs text-dim mb-3">AI recommended cities based on tier and spending power</p>
                <div v-if="expansion && expansion.length" style="display: flex; flex-direction: column; gap: 0.75rem;">
                    <div v-for="city in expansion" :key="city.city" 
                         class="flex gap-3 items-center p-2 border-rounded hover-surface"
                         style="transition: background 0.2s;">
                        <div style="width: 32px; height: 32px; border-radius: 8px; background: var(--accent-alpha); display: flex; align-items: center; justify-content: center; font-size: 1rem;">
                            📍
                        </div>
                        <div style="flex: 1;">
                            <div class="text-sm font-bold">{{ city.city }} <span class="text-xs text-dim">({{ city.state }})</span></div>
                            <div class="text-xs text-muted">{{ city.why }}</div>
                        </div>
                        <button class="btn btn-ghost p-2" aria-label="Launch in this city" @click="launchCity(city.city)" title="Launch in this city">🚀</button>
                    </div>
                </div>
                <div class="empty" v-else>
                    <div class="text-muted text-sm">Loading roadmap...</div>
                </div>
            </div>
        </div>

        <!-- New Campaign Modal -->
        <div v-if="showNewCampaign" class="modal-overlay" @click.self="showNewCampaign = false" style="z-index: 2000;">
             <div class="card" style="width: 450px; max-width: 95%; box-shadow: 0 20px 50px rgba(0,0,0,0.5);">
                 <div class="card-title" style="font-size: 1.1rem; border-bottom: 1px solid var(--border); padding-bottom: 1rem; margin-bottom: 1rem;">
                    Launch New Campaign
                 </div>
                 <div class="form-group mb-3">
                     <label class="text-xs font-bold uppercase tracking-wider text-dim">Campaign Name</label>
                     <input type="text" v-model="newCamp.name" class="form-input" placeholder="e.g. Lagos Restaurants Expansion">
                 </div>
                 <div class="grid-2 mb-3">
                     <div class="form-group">
                         <label class="text-xs font-bold uppercase tracking-wider text-dim">City</label>
                         <input type="text" v-model="newCamp.city" class="form-input">
                     </div>
                     <div class="form-group">
                         <label class="text-xs font-bold uppercase tracking-wider text-dim">Lead Target</label>
                         <input type="number" v-model="newCamp.daily_lead_target" class="form-input">
                     </div>
                 </div>
                 <div class="form-group mb-4">
                     <label class="text-xs font-bold uppercase tracking-wider text-dim">Niches (comma separated)</label>
                     <input type="text" v-model="newCamp.niches" class="form-input" placeholder="restaurants, salons, schools">
                 </div>
                 <div class="flex gap-2 justify-end">
                     <button class="btn btn-ghost" @click="showNewCampaign = false">Cancel</button>
                     <button class="btn btn-primary" @click="submitCampaign" :disabled="submitting">
                        {{ submitting ? 'Launching...' : '🚀 Start Campaign' }}
                     </button>
                 </div>
             </div>
        </div>
    </div>
    `,
    props: ['analytics', 'campaigns', 'expansion'],
    emits: ['refresh'],
    setup(props, { emit }) {
        const showNewCampaign = ref(false)
        const submitting = ref(false)
        const newCamp = ref({ 
            name: '', 
            city: 'Lagos', 
            niches: 'restaurants, salons',
            daily_lead_target: 20
        })

        function formatMoney(n) {
            if (!n) return '0'
            if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M'
            if (n >= 1000) return (n / 1000).toFixed(0) + 'K'
            return n.toLocaleString()
        }

        async function submitCampaign() {
            submitting.value = true
            try {
                const data = {
                    ...newCamp.value,
                    niches: newCamp.value.niches.split(',').map(s => s.trim()).filter(Boolean)
                }
                await axios.post(`${API}/scale/campaigns`, data)
                showNewCampaign.value = false
                emit('refresh')
                // Reset form
                newCamp.value = { name: '', city: 'Lagos', niches: 'restaurants, salons', daily_lead_target: 20 }
            } catch (e) {
                alert('Failed to launch campaign')
            }
            submitting.value = false
        }

        function launchCity(city) {
            newCamp.value.city = city
            newCamp.value.name = `${city} Market Entry`
            showNewCampaign.value = true
        }

        return { showNewCampaign, submitting, newCamp, formatMoney, submitCampaign, launchCity }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// EVOLUTION PAGE
// ─────────────────────────────────────────────────────────────────────────────
const EvolutionPage = {
    template: `
    <div>
        <div class="flex justify-between items-center mb-3">
            <div>
                <h2 style="font-size: 1rem; font-weight: 700;">System Brain & Self-Improvement</h2>
                <p class="text-sm text-muted">AI-driven learning and autonomous optimization</p>
            </div>
            <button class="btn btn-primary" @click="runEvolution" :disabled="running">
                {{ running ? '🧠 Learning...' : '🧠 Run Evolution Cycle' }}
            </button>
        </div>

        <div class="grid-3 mb-3">
            <div class="card" style="text-align: center; border-bottom: 3px solid var(--accent);">
                <div class="text-xs text-dim mb-1 uppercase tracking-wider">Lessons Learned</div>
                <div style="font-size: 1.5rem; font-weight: 800; color: var(--accent);">{{ lessons.length }}</div>
            </div>
            <div class="card" style="text-align: center; border-bottom: 3px solid var(--success);">
                <div class="text-xs text-dim mb-1 uppercase tracking-wider">Optimizations Made</div>
                <div style="font-size: 1.5rem; font-weight: 800; color: var(--success);">{{ optimizations.length }}</div>
            </div>
            <div class="card" style="text-align: center; border-bottom: 3px solid var(--info);">
                <div class="text-xs text-dim mb-1 uppercase tracking-wider">Confidence Score</div>
                <div style="font-size: 1.5rem; font-weight: 800; color: var(--info);">{{ avgConfidence }}%</div>
            </div>
        </div>

        <div class="grid-2">
            <!-- Lessons List -->
            <div class="card">
                <div class="card-title">📖 Knowledge Base</div>
                <div v-if="lessons.length" style="display: flex; flex-direction: column; gap: 0.75rem; max-height: 500px; overflow-y: auto; padding-right: 0.5rem;">
                    <div v-for="l in lessons.slice().reverse()" :key="l.id" 
                         class="p-2 border-rounded hover-surface" 
                         style="background: var(--surface2); border: 1px solid var(--border);">
                        <div class="flex justify-between items-start mb-1">
                            <span class="badge" :class="l.impact === 'negative' ? 'badge-warning' : 'badge-success'" style="font-size: 0.6rem; text-transform: uppercase;">
                                {{ l.category?.replace('_', ' ') || 'Insight' }}
                            </span>
                            <span class="text-xs text-dim">{{ formatDate(l.timestamp) }}</span>
                        </div>
                        <div class="text-sm font-bold mb-1">{{ l.insight }}</div>
                        <div class="text-xs text-muted" style="background: rgba(0,0,0,0.2); padding: 0.4rem; border-radius: 4px;">
                            💡 Takeaway: {{ l.actionable_takeaway }}
                        </div>
                    </div>
                </div>
                <div class="empty" v-else style="padding: 3rem;">
                    <div class="text-muted text-sm">No lessons learned yet. Run an evolution cycle to begin learning.</div>
                </div>
            </div>

            <!-- Optimizations Log -->
            <div class="card">
                <div class="card-title">🔧 Optimization Log</div>
                <div v-if="optimizations.length" style="display: flex; flex-direction: column; gap: 0.5rem; max-height: 500px; overflow-y: auto;">
                    <div v-for="(o, i) in optimizations.slice().reverse()" :key="i" 
                         class="text-xs p-3 border-rounded mb-2" 
                         style="background: var(--surface2); border-left: 3px solid var(--success);">
                        <div class="flex justify-between mb-1">
                            <span class="font-bold" :class="o.health === 'healthy' ? 'text-success' : 'text-warning'">
                                SYSTEM {{ o.health?.toUpperCase() }}
                            </span>
                            <span class="text-dim">{{ formatDate(o.timestamp) }}</span>
                        </div>
                        <div class="mb-2 font-medium">{{ o.summary }}</div>
                        <div class="flex gap-3 text-dim">
                            <span>🛠️ {{ o.optimizations_count }} Config fixes</span>
                            <span>📚 {{ o.lessons_count }} New insights</span>
                        </div>
                    </div>
                </div>
                <div class="empty" v-else style="padding: 3rem;">
                    <div class="text-muted text-sm">No optimizations logged yet.</div>
                </div>
            </div>
        </div>
    </div>
    `,
    props: ['lessons', 'optimizations', 'running'],
    emits: ['run-evolution'],
    setup(props, { emit }) {
        const avgConfidence = computed(() => {
            if (!props.lessons.length) return 0
            const total = props.lessons.reduce((acc, l) => acc + (l.confidence_score || 0.8), 0)
            return Math.round((total / props.lessons.length) * 100)
        })

        function formatDate(ts) {
            if (!ts) return ''
            const date = new Date(ts)
            return date.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ' ' + 
                   date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }

        function runEvolution() {
            emit('run-evolution')
        }

        return { avgConfidence, formatDate, runEvolution }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN APP
// ─────────────────────────────────────────────────────────────────────────────
const App = {
    components: { OverviewPage, LeadsPage, RepliesPage, OutreachPage, AuditPage, SettingsPage, ScalePage, EvolutionPage },

    template: `
    <div v-if="!isAuthenticated" class="login-wrapper">
        <div class="login-card">
            <div class="login-logo">🤖</div>
            <h2>AI CEO Command Center</h2>
            <p>Enter your authorization key to access the dashboard</p>
            <form @submit.prevent="handleLogin" class="login-form">
                <div class="form-group">
                    <input type="password" v-model="loginKey" placeholder="Authorization Key" class="form-input text-center" required>
                </div>
                <div v-if="loginError" class="login-error">{{ loginError }}</div>
                <button type="submit" class="btn btn-primary w-full" :disabled="loggingIn">
                    {{ loggingIn ? 'Authenticating...' : 'Enter Dashboard 🔓' }}
                </button>
            </form>
        </div>
    </div>
    <div v-else class="layout">
        <!-- Sidebar Backdrop Overlay -->
        <div v-if="mobileMenuOpen" class="sidebar-backdrop" @click="mobileMenuOpen = false"></div>

        <!-- Sidebar -->
        <aside class="sidebar" :class="{ 'mobile-open': mobileMenuOpen }">
            <div class="sidebar-logo">
                <div class="logo-mark">
                    <div class="logo-icon">🤖</div>
                    <div>
                        <div class="logo-text">AI CEO</div>
                        <div class="logo-sub">Outreach Engine</div>
                    </div>
                </div>
            </div>

            <nav class="sidebar-nav">
                <div class="nav-section">
                    <div class="nav-label">Command Center</div>
                    <div class="nav-item" :class="{ active: page === 'overview' }"
                         @click="page = 'overview'; mobileMenuOpen = false">
                        <span class="icon">📊</span> Overview
                    </div>
                    <div class="nav-item" :class="{ active: page === 'leads' }"
                         @click="page = 'leads'; mobileMenuOpen = false">
                        <span class="icon">👥</span> Leads
                        <span class="nav-badge green">{{ leadsCount }}</span>
                    </div>
                    <div class="nav-item" :class="{ active: page === 'replies' }"
                         @click="page = 'replies'; mobileMenuOpen = false">
                        <span class="icon">💬</span> Replies
                        <span class="nav-badge" v-if="pendingReplies > 0">{{ pendingReplies }}</span>
                    </div>
                    <div class="nav-item" :class="{ active: page === 'outreach' }"
                         @click="page = 'outreach'; mobileMenuOpen = false">
                        <span class="icon">📤</span> Outreach
                    </div>
                    <div class="nav-item" :class="{ active: page === 'audit' }"
                         @click="page = 'audit'; mobileMenuOpen = false">
                        <span class="icon">🔍</span> Audit
                    </div>
                    <div class="nav-item" :class="{ active: page === 'scale' }"
                         @click="page = 'scale'; mobileMenuOpen = false">
                        <span class="icon">🚀</span> Scale
                    </div>
                    <div class="nav-item" :class="{ active: page === 'evolution' }"
                         @click="page = 'evolution'; mobileMenuOpen = false">
                        <span class="icon">🧠</span> Brain
                    </div>
                    <div class="nav-item" :class="{ active: page === 'settings' }"
                         @click="page = 'settings'; mobileMenuOpen = false">
                        <span class="icon">⚙️</span> Settings
                    </div>
                </div>

                <div class="nav-section" style="margin-top: 1rem;">
                    <div class="nav-label">Quick Run</div>
                    <div class="nav-item" @click="runFullCeo(); mobileMenuOpen = false">
                        <span class="icon">⚡</span> Full CEO Run
                    </div>
                    <div class="nav-item" @click="findLeads(); mobileMenuOpen = false">
                        <span class="icon">🔍</span> Find Leads
                    </div>
                    <div class="nav-item" @click="enrichLeads(); mobileMenuOpen = false">
                        <span class="icon">💎</span> Enrich Leads
                    </div>
                    <div class="nav-item" @click="writeMessages(); mobileMenuOpen = false">
                        <span class="icon">✍️</span> Write Messages
                    </div>
                    <div class="nav-item" @click="checkInbox(); mobileMenuOpen = false">
                        <span class="icon">📬</span> Check Inbox
                    </div>
                </div>
            </nav>

            <div class="sidebar-footer">
                <div class="system-status">
                    <div class="status-dot"></div>
                    System {{ loading ? 'running...' : 'ready' }}
                </div>
                <div class="text-xs text-dim" style="margin-top: 0.4rem;">
                    Last refresh: {{ lastRefresh }}
                </div>
                <button v-if="authKey" @click="handleLogout" class="btn btn-ghost w-full" style="margin-top: 0.75rem; justify-content: center; padding: 0.4rem; font-size: 0.75rem; border: 1px dashed rgba(255,255,255,0.15);">
                    🔒 Log Out
                </button>
            </div>
        </aside>

        <!-- Main -->
        <main class="main">
            <div class="topbar">
                <div class="topbar-left" style="display: flex; align-items: center;">
                    <button class="hamburger-btn" @click="toggleMobileMenu" aria-label="Toggle menu">
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                            <line x1="3" y1="12" x2="21" y2="12"></line>
                            <line x1="3" y1="6" x2="21" y2="6"></line>
                            <line x1="3" y1="18" x2="21" y2="18"></line>
                        </svg>
                    </button>
                    <div>
                        <h1>{{ pageTitle }}</h1>
                        <p>{{ pageSubtitle }}</p>
                    </div>
                </div>
                <div class="topbar-right">
                    <div v-if="hotLeads > 0" class="alert-banner danger"
                         style="margin: 0; padding: 0.4rem 0.8rem; font-size: 0.78rem;">
                        🔥 {{ hotLeads }} hot lead{{ hotLeads > 1 ? 's' : '' }} waiting
                    </div>
                    <button class="btn btn-ghost" @click="refreshData" :disabled="loading">
                        {{ loading ? '⏳' : '🔄' }} Refresh
                    </button>
                    <button class="btn btn-primary" @click="runFullCeo" :disabled="loading">
                        🤖 Run CEO
                    </button>
                </div>
            </div>

            <div class="page">
                <!-- Loading overlay -->
                <div v-if="initialLoading" class="loading">
                    <div class="spinner"></div>
                    <div>Loading dashboard data...</div>
                </div>

                <template v-else>
                    <OverviewPage v-if="page === 'overview'"
                                  :state="state" :audit="latestAudit"
                                  :schedule="schedule" :config="config"
                                  @run-task="handleRunTask"
                                  @run-command="runStreamingCommand" />

                    <LeadsPage v-if="page === 'leads'"
                               :leads="leads"
                               @enrich="enrichLeads" />

                    <RepliesPage v-if="page === 'replies'"
                                 :replies="replies"
                                 @refresh="refreshData"
                                 @run-command="runStreamingCommand" />

                    <OutreachPage v-if="page === 'outreach'"
                                  :state="state" :config="config" />

                    <AuditPage v-if="page === 'audit'"
                               :audit="latestAudit"
                               @refresh="refreshData" />

                    <ScalePage v-if="page === 'scale'"
                               :analytics="scaleAnalytics"
                               :campaigns="campaigns"
                               :expansion="expansionRoadmap"
                               @refresh="refreshData" />

                    <EvolutionPage v-if="page === 'evolution'"
                                   :lessons="lessons"
                                   :optimizations="optimizations"
                                   :running="isRunningEvolution"
                                   @run-evolution="runEvolution" />

                    <SettingsPage v-if="page === 'settings'"
                                  :config="config"
                                  @refresh="refreshData" />
                </template>
            </div>
        </main>

        <!-- Terminal Modal -->
        <div v-if="showTerminal" class="modal-overlay" @click.self="closeTerminal">
            <div class="terminal-window">
                <div class="terminal-header">
                    <div class="terminal-title">
                        <span class="icon">💻</span>
                        <span>TERMINAL — {{ activeCommand }}</span>
                    </div>
                    <div class="terminal-controls">
                        <div class="control-dot dot-red" @click="closeTerminal" style="cursor: pointer;"></div>
                        <div class="control-dot dot-yellow"></div>
                        <div class="control-dot dot-green"></div>
                    </div>
                </div>
                <div class="terminal-body" ref="terminalBody">
                    <div v-for="(line, i) in terminalLines" :key="i" 
                         class="terminal-line" :class="line.type">
                        <span v-if="line.type === 'command'">$ </span>
                        {{ line.text }}
                    </div>
                    <div v-if="isRunning" class="terminal-line">
                        <span class="terminal-cursor"></span>
                    </div>
                </div>
                <div class="terminal-footer">
                    <button class="btn btn-ghost" @click="closeTerminal" :disabled="isRunning">
                        {{ isRunning ? 'Running...' : 'Close Terminal' }}
                    </button>
                </div>
            </div>
        </div>

        <!-- Command result toast -->
        <div v-if="toast" style="
            position: fixed; bottom: 1.5rem; right: 1.5rem;
            background: var(--surface2); border: 1px solid var(--border);
            border-radius: 10px; padding: 0.75rem 1rem;
            font-size: 0.82rem; color: var(--text);
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            z-index: 9999; max-width: 320px;
            animation: fadeInUp 0.3s ease;">
            {{ toast }}
        </div>
    </div>
    `,

    setup() {
        const loginKey = ref('')
        const loginError = ref('')
        const loggingIn = ref(false)

        async function handleLogin() {
            loggingIn.value = true
            loginError.value = ''
            try {
                const res = await axios.post(`${API}/login`, { key: loginKey.value })
                if (res.data && res.data.success) {
                    authKey.value = loginKey.value
                    localStorage.setItem('dashboard_auth_key', loginKey.value)
                    isAuthenticated.value = true
                    loginKey.value = ''
                    await refreshData()
                } else {
                    loginError.value = 'Invalid authorization key'
                }
            } catch (e) {
                loginError.value = e.response?.data?.error || 'Invalid authorization key'
            } finally {
                loggingIn.value = false
            }
        }

        async function handleLogout() {
            try {
                await axios.post(`${API}/logout`)
            } catch (e) {}
            authKey.value = ''
            localStorage.removeItem('dashboard_auth_key')
            isAuthenticated.value = false
            page.value = 'overview'
        }

        const page = ref('overview')
        const loading = ref(false)
        const initialLoading = ref(true)
        const toast = ref('')
        const mobileMenuOpen = ref(false)

        const toggleMobileMenu = () => {
            mobileMenuOpen.value = !mobileMenuOpen.value
        }

        // Data
        const state = ref({})
        const leads = ref([])
        const replies = ref([])
        const schedule = ref([])
        const latestAudit = ref(null)
        const scaleAnalytics = ref(null)
        const campaigns = ref([])
        const expansionRoadmap = ref([])
        const lessons = ref([])
        const optimizations = ref([])
        const config = ref({})
        const lastRefresh = ref('—')

        // Terminal State
        const showTerminal = ref(false)
        const terminalLines = ref([])
        const isRunning = ref(false)
        const activeCommand = ref('')
        const terminalBody = ref(null)

        const leadsCount = computed(() => leads.value.length)
        const pendingReplies = computed(() =>
            replies.value.filter(r => r.status === 'pending_review').length
        )
        const hotLeads = computed(() =>
            replies.value.filter(r =>
                r.classification?.intent === 'interested' && !r.action_taken
            ).length
        )

        const pageTitle = computed(() => {
            const titles = {
                overview: 'Command Center',
                leads: 'Lead Pipeline',
                replies: 'Reply Manager',
                outreach: 'Outreach Control',
                audit: 'CEO Audit',
                scale: 'Scale & Growth',
                evolution: 'System Brain',
                settings: 'System Settings'
            }
            return titles[page.value] || 'Dashboard'
        })

        const pageSubtitle = computed(() => {
            const subs = {
                overview: "Today's performance at a glance",
                leads: 'All your leads and their status',
                replies: 'Manage incoming replies and follow-ups',
                outreach: 'Control your outreach channels',
                audit: 'AI CEO performance analysis',
                scale: 'Campaign scaling and revenue tracking',
                evolution: 'Self-learning and optimization history',
                settings: 'Configure CEO behavior and API keys'
            }
            return subs[page.value] || ''
        })

        async function refreshData() {
            loading.value = true
            try {
                const [
                    stateData, leadsData, repliesData, scheduleData, auditData, configData,
                    analyticsData, campaignsData, expansionData, lessonsData, optimizationsData, workflowData
                ] = await Promise.all([
                        fetchData('/state'),
                        fetchData('/leads'),
                        fetchData('/replies'),
                        fetchData('/schedule'),
                        fetchData('/audit'),
                        fetchData('/config'),
                        fetchData('/scale/analytics'),
                        fetchData('/scale/campaigns'),
                        fetchData('/scale/expansion'),
                        fetchData('/evolution/lessons'),
                        fetchData('/evolution/optimizations'),
                        fetchData('/workflow/state')
                    ])

                if (stateData) state.value = stateData
                if (leadsData) {
                    leads.value = leadsData
                    console.log(`Leads updated: ${leads.value.length}`)
                }
                if (repliesData) replies.value = repliesData
                if (scheduleData) schedule.value = scheduleData?.tasks || []
                if (auditData) latestAudit.value = auditData
                if (configData) config.value = configData
                if (stateData) {
                    scaleAnalytics.value = stateData.revenue || null
                    expansionRoadmap.value = stateData.expansion || []
                    campaigns.value = stateData.campaigns || []
                }
                if (lessonsData) lessons.value = lessonsData
                if (optimizationsData) optimizations.value = optimizationsData
                if (stateData && workflowData) stateData.workflow = workflowData

                lastRefresh.value = new Date().toLocaleTimeString()
            } catch (e) {
                showToast('❌ Failed to load data — is the server running?')
            }
            loading.value = false
            initialLoading.value = false
        }

        async function runFullCeo() {
            runStreamingCommand('python ai_ceo.py full')
        }

        async function findLeads() {
            runStreamingCommand('python intelligence/lead_finder.py')
        }

        async function enrichLeads() {
            runStreamingCommand('python intelligence/lead_enricher.py')
        }

        async function writeMessages() {
            runStreamingCommand('python outreach/message_writer.py')
        }

        async function checkInbox() {
            runStreamingCommand('python response_management/reply_monitor.py')
        }

        async function handleRunTask(task) {
            runStreamingCommand(task.command)
        }

        const isRunningEvolution = ref(false)
        async function runEvolution() {
            isRunningEvolution.value = true
            runStreamingCommand('python intelligence/self_optimizer.py --apply')
            // Reset flag after a while or on completion
            setTimeout(() => isRunningEvolution.value = false, 5000)
        }

        function runStreamingCommand(command) {
            showTerminal.value = true
            terminalLines.value = []
            terminalLines.value.push({ type: 'command', text: command })
            isRunning.value = true
            activeCommand.value = command

            let url = `${API}/stream-command?command=${encodeURIComponent(command)}`
            if (authKey.value) {
                url += `&auth_key=${encodeURIComponent(authKey.value)}`
            }
            const eventSource = new EventSource(url)

            eventSource.onmessage = (event) => {
                const data = JSON.parse(event.data)
                
                if (data.type === 'output') {
                    terminalLines.value.push({ type: 'output', text: data.line })
                    scrollToBottom()
                } else if (data.type === 'end') {
                    isRunning.value = false
                    terminalLines.value.push({ 
                        type: data.success ? 'success' : 'error', 
                        text: data.success ? '✔ Command completed successfully' : `✘ Command failed with code ${data.code}` 
                    })
                    eventSource.close()
                    
                    // Advance Workflow on success
                    if (data.success) {
                        let nextStep = null;
                        if (command.includes('general_auditor.py')) nextStep = 'craft';
                        else if (command.includes('message_writer.py')) nextStep = 'outreach';
                        else if (command.includes('email_sender.py')) nextStep = 'audit';
                        
                        if (nextStep) {
                            postAction('/workflow/state', { current_step: nextStep, status: 'idle' }).then(() => refreshData());
                        } else {
                            refreshData();
                        }
                    } else {
                        refreshData();
                    }
                } else if (data.type === 'error') {
                    isRunning.value = false
                    terminalLines.value.push({ type: 'error', text: `ERROR: ${data.message}` })
                    eventSource.close()
                }
            }

            eventSource.onerror = (err) => {
                console.error("EventSource failed:", err)
                isRunning.value = false
                terminalLines.value.push({ type: 'error', text: 'Connection lost to server' })
                eventSource.close()
            }
        }

        function scrollToBottom() {
            setTimeout(() => {
                if (terminalBody.value) {
                    terminalBody.value.scrollTop = terminalBody.value.scrollHeight
                }
            }, 50)
        }

        function closeTerminal() {
            if (!isRunning.value) {
                showTerminal.value = false
            } else {
                showToast('⏳ Command is still running...')
            }
        }

        function showToast(message) {
            toast.value = message
            setTimeout(() => toast.value = '', 4000)
        }

        // Auto-refresh every 60 seconds
        let refreshInterval
        onMounted(async () => {
            await refreshData()
            refreshInterval = setInterval(refreshData, 60000)
        })

        onUnmounted(() => {
            if (refreshInterval) clearInterval(refreshInterval)
        })

        return {
            page, loading, initialLoading, toast,
            state, leads, replies, schedule, latestAudit, config,
            lastRefresh, leadsCount, pendingReplies, hotLeads,
            pageTitle, pageSubtitle,
            showTerminal, terminalLines, isRunning, activeCommand, terminalBody,
            scaleAnalytics, campaigns, expansionRoadmap,
            lessons, optimizations, isRunningEvolution,
            mobileMenuOpen, toggleMobileMenu,
            refreshData, runFullCeo, findLeads, enrichLeads, writeMessages, checkInbox, handleRunTask, runStreamingCommand, runEvolution, closeTerminal,
            authKey, isAuthenticated, loginKey, loginError, loggingIn, handleLogin, handleLogout
        }
    }
}

createApp(App).mount('#app')