/* =========================================================
   HORIZONS PARENT DASHBOARD — parent.js
   Modular tab rendering system
   Depends on: Bootstrap 5, Chart.js (loaded in template)
========================================================= */

"use strict";

/* ─────────────────────────────────────────────────────────
   GLOBAL STATE
   dashboardData is injected by Django into the template as
   a JSON block:  <script>const dashboardData = {{ dashboard_json|safe }};</script>
───────────────────────────────────────────────────────── */

const HorizonsDash = (() => {

    /* ── active tab tracking ── */
    let activeTab        = "overview";
    let activeSubjectTab = "subject-overview";
    let chartInstances   = {};

    /* ─────────────────────────────────────────────
       UTILITY HELPERS
    ───────────────────────────────────────────── */

    function getEl(id) {
        return document.getElementById(id);
    }

    function gradeLabel(pct) {
        if (pct >= 90) return { label: "A+", cls: "grade-aplus" };
        if (pct >= 80) return { label: "A",  cls: "grade-a"    };
        if (pct >= 70) return { label: "B+", cls: "grade-bplus" };
        if (pct >= 60) return { label: "B",  cls: "grade-b"    };
        if (pct >= 50) return { label: "C",  cls: "grade-c"    };
        return              { label: "F",  cls: "grade-f"    };
    }

    function passFailBadge(pct) {
        return pct >= 35
            ? `<span class="status-badge status-pass">Pass</span>`
            : `<span class="status-badge status-fail">Fail</span>`;
    }

    function progressBar(pct, colorClass) {
        return `
            <div class="hz-progress">
                <div class="hz-progress-fill ${colorClass}" style="--pct:${pct}%"></div>
            </div>`;
    }

    function destroyChart(key) {
        if (chartInstances[key]) {
            chartInstances[key].destroy();
            delete chartInstances[key];
        }
    }

    /* ─────────────────────────────────────────────
       PRIMARY TAB SWITCHER
    ───────────────────────────────────────────── */

    function showTab(tabName) {
        if (tabName === activeTab) return;
        activeTab = tabName;

        /* update nav card states */
        document.querySelectorAll(".nav-tab-card").forEach(card => {
            card.classList.toggle("active", card.dataset.tab === tabName);
        });

        /* fade content area */
        const content = getEl("tab-content");
        content.classList.remove("tab-fade-in");
        void content.offsetWidth; /* reflow */
        content.classList.add("tab-fade-in");

        /* destroy any live charts before re-render */
        Object.keys(chartInstances).forEach(destroyChart);

        const renders = {
            overview:     renderOverview,
            subjects:     renderSubjects,
            graphs:       renderGraphs,
            achievements: renderAchievements,
            "extra-help": renderExtraHelp,
        };

        (renders[tabName] || renderOverview)();
    }

    /* ─────────────────────────────────────────────
       OVERVIEW RENDERER
    ───────────────────────────────────────────── */

    function renderOverview() {
        const d  = window.dashboardData || {};
        const child = d.child || {};
        const subjectMarks = d.subject_wise_marks || [];

        /* derive top subjects for strengths block */
        const sorted     = [...subjectMarks].sort((a, b) => b.percentage - a.percentage);
        const strengths  = sorted.slice(0, 3);
        const weaknesses = sorted.slice(-2).reverse();

        const strengthsHTML = strengths.map(s => `
            <div class="strength-chip">
                <span class="strength-dot dot-green"></span>
                ${s.subject_name}
                <span class="chip-pct">${s.percentage}%</span>
            </div>`).join("");

        const weakHTML = weaknesses.map(s => `
            <div class="strength-chip">
                <span class="strength-dot dot-amber"></span>
                ${s.subject_name}
                <span class="chip-pct">${s.percentage}%</span>
            </div>`).join("");

        getEl("tab-content").innerHTML = `

            <!-- STAT RIBBON -->
            <div class="stat-ribbon mb-3">

                <div class="stat-tile">
                    <div class="stat-icon stat-icon-blue">📊</div>
                    <div class="stat-body">
                        <div class="stat-value">${d.overall_score ?? "—"}%</div>
                        <div class="stat-label">Overall Score</div>
                    </div>
                </div>

                <div class="stat-tile">
                    <div class="stat-icon stat-icon-green">📅</div>
                    <div class="stat-body">
                        <div class="stat-value">${d.days_present ?? "—"}%</div>
                        <div class="stat-label">Attendance</div>
                    </div>
                </div>

                <div class="stat-tile">
                    <div class="stat-icon stat-icon-amber">🏅</div>
                    <div class="stat-body">
                        <div class="stat-value">${(d.achievements || []).length}</div>
                        <div class="stat-label">Awards</div>
                    </div>
                </div>

                <div class="stat-tile">
                    <div class="stat-icon stat-icon-purple">📚</div>
                    <div class="stat-body">
                        <div class="stat-value">${subjectMarks.length}</div>
                        <div class="stat-label">Subjects</div>
                    </div>
                </div>

            </div>

            <!-- TWO-COL GRID -->
            <div class="overview-grid">

                <!-- Academic Strengths -->
                <div class="glass-card p-3">
                    <div class="section-eyebrow">Academic Strengths</div>
                    <div class="chip-group mt-2">
                        ${strengthsHTML || '<p class="text-muted small mb-0">No data available.</p>'}
                    </div>
                </div>

                <!-- Needs Attention -->
                <div class="glass-card p-3">
                    <div class="section-eyebrow">Needs Attention</div>
                    <div class="chip-group mt-2">
                        ${weakHTML || '<p class="text-muted small mb-0">No data available.</p>'}
                    </div>
                </div>

            </div>

            <!-- AI SUMMARY -->
            <div class="glass-card p-3 mt-3 ai-summary-card">
                <div class="d-flex align-items-center gap-2 mb-2">
                    <span class="ai-pulse-dot"></span>
                    <span class="section-eyebrow mb-0">AI Summary</span>
                </div>
                <p class="small text-muted mb-2">
                    Based on ${child.first_name || "this student"}'s performance this year, here are the key insights.
                </p>
                <div class="ai-summary-body" id="ai-summary-body">
                    <span class="text-muted small">Generating personalized insights…</span>
                </div>
            </div>

        `;

        _generateAISummary(d);
    }

    function _generateAISummary(d) {
        const el = getEl("ai-summary-body");
        if (!el) return;
        const subjectMarks = d.subject_wise_marks || [];
        const sorted = [...subjectMarks].sort((a, b) => b.percentage - a.percentage);
        const best   = sorted[0]  || {};
        const worst  = sorted[sorted.length - 1] || {};

        /* lightweight client-side summary — replace with real AI call when ready */
        const summary = `
            <ul class="ai-insight-list">
                <li>
                    <span class="ai-tag ai-tag-green">Strength</span>
                    Performing exceptionally well in <strong>${best.subject_name || "—"}</strong>
                    with ${best.percentage || 0}%.
                </li>
                <li>
                    <span class="ai-tag ai-tag-amber">Focus Area</span>
                    <strong>${worst.subject_name || "—"}</strong> at ${worst.percentage || 0}%
                    needs consistent revision and practice.
                </li>
                <li>
                    <span class="ai-tag ai-tag-blue">Attendance</span>
                    ${d.days_present >= 85
                        ? "Excellent attendance record this year."
                        : "Attendance is below 85% — consider addressing absences with the class teacher."}
                </li>
            </ul>`;

        el.innerHTML = summary;
    }

    /* ─────────────────────────────────────────────
       SUBJECTS RENDERER (with sub-tabs)
    ───────────────────────────────────────────── */

    function renderSubjects() {
        getEl("tab-content").innerHTML = `

            <!-- SUBJECTS SUB-NAV -->
            <div class="sub-nav mb-3" id="subject-sub-nav">

                ${[
                    { key: "subject-overview",    label: "Overview"            },
                    { key: "exam-wise",           label: "Exam Wise Marks"     },
                    { key: "full-year",           label: "Full Year"           },
                    { key: "strengths",           label: "Strength Areas"      },
                    { key: "improvements",        label: "Improvement Areas"   },
                ].map(t => `
                    <button
                        class="sub-nav-btn ${t.key === activeSubjectTab ? "active" : ""}"
                        data-sub="${t.key}"
                        onclick="HorizonsDash.showSubjectTab('${t.key}')"
                    >
                        ${t.label}
                    </button>`).join("")}

            </div>

            <div id="subject-tab-content" class="tab-fade-in"></div>

        `;

        renderSubjectContent(activeSubjectTab);
    }

    function showSubjectTab(key) {
        activeSubjectTab = key;
        document.querySelectorAll(".sub-nav-btn").forEach(btn => {
            btn.classList.toggle("active", btn.dataset.sub === key);
        });
        const ct = getEl("subject-tab-content");
        ct.classList.remove("tab-fade-in");
        void ct.offsetWidth;
        ct.classList.add("tab-fade-in");
        renderSubjectContent(key);
    }

    function renderSubjectContent(key) {
        const renders = {
            "subject-overview": renderSubjectOverview,
            "exam-wise":        renderExamWise,
            "full-year":        renderFullYear,
            "strengths":        renderStrengthAreas,
            "improvements":     renderImprovementAreas,
        };
        (renders[key] || renderSubjectOverview)();
    }

    function renderSubjectOverview() {
        const subjects = (window.dashboardData || {}).subject_wise_marks || [];
        const html = subjects.length ? subjects.map(s => {
            const g = gradeLabel(s.percentage);
            return `
                <div class="subject-row glass-card p-3 mb-2">
                    <div class="subject-row-info">
                        <div class="subject-name">${s.subject_name}</div>
                        <div class="subject-score-line text-muted small">${s.total_obtained} / ${s.total_marks}</div>
                    </div>
                    <div class="subject-row-right">
                        ${progressBar(s.percentage, "fill-blue")}
                        <div class="d-flex align-items-center gap-2 mt-1">
                            <span class="grade-badge ${g.cls}">${g.label}</span>
                            ${passFailBadge(s.percentage)}
                            <span class="small fw-semibold">${s.percentage}%</span>
                        </div>
                    </div>
                </div>`;
        }).join("") : `<p class="text-muted">No subject data available.</p>`;

        getEl("subject-tab-content").innerHTML = html;
    }

    function renderExamWise() {
        const subjects = (window.dashboardData || {}).subject_wise_marks || [];
        const selectOptions = subjects.map((s, i) =>
            `<option value="${i}">${s.subject_name}</option>`
        ).join("");

        getEl("subject-tab-content").innerHTML = `
            <div class="glass-card p-3 mb-3">
                <label class="form-label mb-1">Select Subject</label>
                <select class="form-select form-select-sm" id="exam-subject-select" onchange="HorizonsDash.renderExamSelector(this.value)">
                    ${selectOptions}
                </select>
            </div>
            <div id="exam-detail-area"></div>
        `;

        renderExamSelector(0);
    }

    function renderExamSelector(idx) {
        const subjects = (window.dashboardData || {}).subject_wise_marks || [];
        const subject  = subjects[idx];
        const area     = getEl("exam-detail-area");
        if (!area || !subject) return;

        const examsHTML = (subject.exams || []).map(exam => `
            <div class="glass-card p-3 mb-3">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <strong>${exam.exam_name}</strong>
                    <span class="status-badge ${exam.exam_percentage >= 35 ? "status-pass" : "status-fail"}">
                        ${exam.exam_percentage}%
                    </span>
                </div>
                <table class="table table-sm hz-table">
                    <thead>
                        <tr>
                            <th>Type</th>
                            <th>Obtained</th>
                            <th>Total</th>
                            <th>%</th>
                            <th>Grade</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${(exam.exam_types || []).map(et => {
                            const g = gradeLabel(et.percentage);
                            return `
                                <tr>
                                    <td>${et.exam_type}</td>
                                    <td>${et.obtained}</td>
                                    <td>${et.total}</td>
                                    <td>${et.percentage}%</td>
                                    <td><span class="grade-badge ${g.cls}">${g.label}</span></td>
                                </tr>`;
                        }).join("")}
                    </tbody>
                </table>
            </div>`).join("") || `<p class="text-muted">No exam data available.</p>`;

        area.innerHTML = examsHTML;
    }

    function renderFullYear() {
        const subjects = (window.dashboardData || {}).subject_wise_marks || [];
        const html = `
            <div class="glass-card p-3">
                <div class="section-eyebrow mb-3">Full Year Performance</div>
                <table class="table hz-table">
                    <thead>
                        <tr>
                            <th>Subject</th>
                            <th>Obtained</th>
                            <th>Total</th>
                            <th>%</th>
                            <th>Grade</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${subjects.map(s => {
                            const g = gradeLabel(s.percentage);
                            return `
                                <tr>
                                    <td class="fw-semibold">${s.subject_name}</td>
                                    <td>${s.total_obtained}</td>
                                    <td>${s.total_marks}</td>
                                    <td>${s.percentage}%</td>
                                    <td><span class="grade-badge ${g.cls}">${g.label}</span></td>
                                    <td>${passFailBadge(s.percentage)}</td>
                                </tr>`;
                        }).join("")}
                    </tbody>
                </table>
            </div>`;
        getEl("subject-tab-content").innerHTML = html;
    }

    function renderStrengthAreas() {
        const subjects = (window.dashboardData || {}).subject_wise_marks || [];
        const strong   = subjects.filter(s => s.percentage >= 70)
                                 .sort((a, b) => b.percentage - a.percentage);
        const html = strong.length ? strong.map(s => `
            <div class="glass-card p-3 mb-2 d-flex align-items-center gap-3">
                <div class="area-icon area-icon-green">✓</div>
                <div class="flex-grow-1">
                    <div class="fw-semibold">${s.subject_name}</div>
                    ${progressBar(s.percentage, "fill-green")}
                </div>
                <div class="fw-bold text-success">${s.percentage}%</div>
            </div>`).join("")
            : `<p class="text-muted">No subjects above 70% yet — keep going!</p>`;
        getEl("subject-tab-content").innerHTML = html;
    }

    function renderImprovementAreas() {
        const subjects = (window.dashboardData || {}).subject_wise_marks || [];
        const weak     = subjects.filter(s => s.percentage < 70)
                                 .sort((a, b) => a.percentage - b.percentage);
        const tips = {
            default: [
                "Schedule 30-minute daily revision sessions.",
                "Use past exam papers for practice.",
                "Ask the subject teacher for extra guidance.",
            ]
        };
        const html = weak.length ? weak.map(s => `
            <div class="glass-card p-3 mb-3">
                <div class="d-flex align-items-center gap-3 mb-2">
                    <div class="area-icon area-icon-amber">!</div>
                    <div>
                        <div class="fw-semibold">${s.subject_name}</div>
                        <div class="small text-muted">${s.percentage}% · ${s.total_obtained}/${s.total_marks}</div>
                    </div>
                    ${passFailBadge(s.percentage)}
                </div>
                ${progressBar(s.percentage, "fill-amber")}
                <ul class="improvement-tips mt-2">
                    ${tips.default.map(t => `<li>${t}</li>`).join("")}
                </ul>
            </div>`).join("")
            : `<div class="success-box">🎉 No weak subjects detected — excellent work!</div>`;
        getEl("subject-tab-content").innerHTML = html;
    }

    /* ─────────────────────────────────────────────
       GRAPHS RENDERER
    ───────────────────────────────────────────── */

    function renderGraphs() {
        getEl("tab-content").innerHTML = `
            <div class="graphs-grid">

                <div class="glass-card p-3">
                    <div class="section-eyebrow mb-3">Subject Comparison</div>
                    <canvas id="chart-subject" height="220"></canvas>
                </div>

                <div class="glass-card p-3">
                    <div class="section-eyebrow mb-3">Attendance Trend</div>
                    <canvas id="chart-attendance" height="220"></canvas>
                </div>

                <div class="glass-card p-3">
                    <div class="section-eyebrow mb-3">Yearly Performance Trend</div>
                    <canvas id="chart-yearly" height="220"></canvas>
                </div>

                <div class="glass-card p-3">
                    <div class="section-eyebrow mb-3">Class Comparison</div>
                    <canvas id="chart-scatter" height="220"></canvas>
                </div>

            </div>
        `;

        /* defer to next frame so canvas is in DOM */
        requestAnimationFrame(renderCharts);
    }

    function renderCharts() {
        const d        = window.dashboardData || {};
        const subjects = d.subject_wise_marks || [];
        const labels   = subjects.map(s => s.subject_name);
        const pcts     = subjects.map(s => s.percentage);

        const blue1 = "rgba(91,141,238,0.85)";
        const blue2 = "rgba(91,141,238,0.18)";
        const green1 = "rgba(45,168,122,0.85)";
        const green2 = "rgba(45,168,122,0.18)";
        const amber1 = "rgba(212,134,90,0.85)";

        /* 1 – Subject Comparison (horizontal bar) */
        destroyChart("subject");
        const ctxS = getEl("chart-subject");
        if (ctxS) {
            chartInstances["subject"] = new Chart(ctxS, {
                type: "bar",
                data: {
                    labels,
                    datasets: [{
                        label: "Score %",
                        data:  pcts,
                        backgroundColor: pcts.map(p => p >= 70 ? green1 : p >= 50 ? blue1 : amber1),
                        borderRadius: 8,
                    }]
                },
                options: {
                    indexAxis: "y",
                    responsive: true,
                    scales: { x: { max: 100, grid: { color: "rgba(0,0,0,0.05)" } } },
                    plugins: { legend: { display: false } },
                }
            });
        }

        /* 2 – Attendance Trend (line) */
        destroyChart("attendance");
        const ctxA = getEl("chart-attendance");
        const attTrend = d.attendance_trend || [78, 82, 75, 90, 88, 85, 91, 87, 93, 88, 90, 95];
        const months   = ["Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec","Jan","Feb","Mar"];
        if (ctxA) {
            chartInstances["attendance"] = new Chart(ctxA, {
                type: "line",
                data: {
                    labels: months,
                    datasets: [{
                        label: "Attendance %",
                        data:  attTrend,
                        borderColor:     green1,
                        backgroundColor: green2,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                    }]
                },
                options: {
                    responsive: true,
                    scales: { y: { min: 0, max: 100, grid: { color: "rgba(0,0,0,0.05)" } } },
                    plugins: { legend: { display: false } },
                }
            });
        }

        /* 3 – Yearly Performance Trend (multi-line) */
        destroyChart("yearly");
        const ctxY = getEl("chart-yearly");
        const yearlyData = d.yearly_trend || [62, 67, 71, 74, 78, 75, 80, 79, 82, 85, 83, 88];
        if (ctxY) {
            chartInstances["yearly"] = new Chart(ctxY, {
                type: "line",
                data: {
                    labels: months,
                    datasets: [{
                        label: "Score %",
                        data:  yearlyData,
                        borderColor:     blue1,
                        backgroundColor: blue2,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                    }]
                },
                options: {
                    responsive: true,
                    scales: { y: { min: 0, max: 100, grid: { color: "rgba(0,0,0,0.05)" } } },
                    plugins: { legend: { display: false } },
                }
            });
        }

        /* 4 – Class Scatter */
        destroyChart("scatter");
        const ctxSc = getEl("chart-scatter");
        const classData = d.class_scatter || Array.from({ length: 28 }, () => ({
            x: Math.floor(Math.random() * 100),
            y: Math.floor(Math.random() * 100),
        }));
        const studentPoint = { x: d.overall_score || 75, y: d.days_present || 88 };

        if (ctxSc) {
            chartInstances["scatter"] = new Chart(ctxSc, {
                type: "scatter",
                data: {
                    datasets: [
                        {
                            label: "Classmates",
                            data:  classData,
                            backgroundColor: "rgba(91,141,238,0.30)",
                            pointRadius: 5,
                        },
                        {
                            label: "This Student",
                            data:  [studentPoint],
                            backgroundColor: amber1,
                            pointRadius: 10,
                            pointStyle: "star",
                        }
                    ]
                },
                options: {
                    responsive: true,
                    scales: {
                        x: { title: { display: true, text: "Score %" }, min: 0, max: 100 },
                        y: { title: { display: true, text: "Attendance %" }, min: 0, max: 100 },
                    },
                }
            });
        }
    }

    /* ─────────────────────────────────────────────
       ACHIEVEMENTS RENDERER
    ───────────────────────────────────────────── */

    function renderAchievements() {
        const achievements = (window.dashboardData || {}).achievements || [];

        const filterBar = `
            <div class="filter-bar mb-3">
                <button class="filter-chip active" onclick="HorizonsDash.filterAchievements('all', this)">All</button>
                <button class="filter-chip" onclick="HorizonsDash.filterAchievements('academic', this)">Academic</button>
                <button class="filter-chip" onclick="HorizonsDash.filterAchievements('sports', this)">Sports</button>
                <button class="filter-chip" onclick="HorizonsDash.filterAchievements('arts', this)">Arts</button>
                <button class="filter-chip ms-auto" onclick="HorizonsDash.openAddAchievementModal()">
                    + Add Achievement
                </button>
            </div>`;

        const cardsHTML = achievements.length
            ? `<div class="achievement-grid" id="achievement-grid">${_achievementCards(achievements)}</div>`
            : `<div id="achievement-grid"><p class="text-muted">No achievements recorded yet.</p></div>`;

        getEl("tab-content").innerHTML = filterBar + cardsHTML + _addAchievementModal();
    }

    function _achievementCards(list) {
        const icons = { academic: "🎓", sports: "⚽", arts: "🎨", default: "🏅" };
        return list.map((a, i) => `
            <div class="achievement-card glass-card p-3" data-category="${a.category || "academic"}">
                <div class="achievement-icon">${icons[a.category] || icons.default}</div>
                <div class="achievement-body">
                    <div class="fw-semibold">${a.title || "Achievement"}</div>
                    <div class="small text-muted">${a.date || ""} · ${a.awarded_by || ""}</div>
                    ${a.description ? `<p class="small mt-1 mb-0">${a.description}</p>` : ""}
                </div>
                <div class="achievement-actions">
                    <button class="icon-btn" title="Preview Certificate" onclick="HorizonsDash.previewCertificate(${i})">👁</button>
                    <button class="icon-btn" title="Edit" onclick="HorizonsDash.editAchievement(${i})">✏️</button>
                    <button class="icon-btn icon-btn-danger" title="Delete" onclick="HorizonsDash.deleteAchievement(${i})">🗑</button>
                </div>
            </div>`).join("");
    }

    function filterAchievements(category, btn) {
        document.querySelectorAll(".filter-chip").forEach(c => c.classList.remove("active"));
        btn.classList.add("active");
        const grid = getEl("achievement-grid");
        if (!grid) return;
        grid.querySelectorAll(".achievement-card").forEach(card => {
            card.style.display = (category === "all" || card.dataset.category === category) ? "" : "none";
        });
    }

    function openAddAchievementModal() {
        const modal = bootstrap.Modal.getOrCreateInstance(getEl("add-achievement-modal"));
        modal.show();
    }

    function previewCertificate(idx) {
        const a = ((window.dashboardData || {}).achievements || [])[idx];
        if (!a) return;
        alert(`Certificate Preview:\n\n${a.title}\nAwarded to: ${(window.dashboardData.child || {}).first_name}\nDate: ${a.date}`);
    }

    function editAchievement(idx) {
        /* placeholder — wire to real API endpoint */
        alert(`Edit achievement #${idx} — implement form with AJAX PUT.`);
    }

    function deleteAchievement(idx) {
        if (!confirm("Delete this achievement?")) return;
        /* placeholder — wire to real API endpoint */
        alert(`Delete achievement #${idx} — implement AJAX DELETE.`);
    }

    function _addAchievementModal() {
        return `
        <div class="modal fade" id="add-achievement-modal" tabindex="-1">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content hz-modal">
                    <div class="modal-header border-0 pb-0">
                        <h6 class="modal-title fw-semibold">Add Achievement</h6>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <label class="form-label">Title</label>
                            <input type="text" class="form-control" id="ach-title" placeholder="Science Olympiad Winner">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Category</label>
                            <select class="form-select" id="ach-category">
                                <option value="academic">Academic</option>
                                <option value="sports">Sports</option>
                                <option value="arts">Arts</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Date</label>
                            <input type="date" class="form-control" id="ach-date">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Awarded By</label>
                            <input type="text" class="form-control" id="ach-awarded-by" placeholder="School / Organisation">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Description</label>
                            <textarea class="form-control" id="ach-desc" rows="3" placeholder="Brief description…"></textarea>
                        </div>
                    </div>
                    <div class="modal-footer border-0 pt-0">
                        <button class="btn btn-sm btn-outline-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button class="btn btn-sm btn-primary-custom px-4" onclick="HorizonsDash.saveAchievement()">Save</button>
                    </div>
                </div>
            </div>
        </div>`;
    }

    function saveAchievement() {
        const payload = {
            title:      getEl("ach-title").value,
            category:   getEl("ach-category").value,
            date:       getEl("ach-date").value,
            awarded_by: getEl("ach-awarded-by").value,
            description:getEl("ach-desc").value,
        };
        /* TODO: AJAX POST to /api/achievements/ */
        console.log("Save achievement:", payload);
        bootstrap.Modal.getInstance(getEl("add-achievement-modal")).hide();
        alert("Achievement saved! (wire up AJAX POST to your endpoint)");
    }

    /* ─────────────────────────────────────────────
       EXTRA HELP RENDERER
    ───────────────────────────────────────────── */

    function renderExtraHelp() {
        const subjects = (window.dashboardData || {}).subject_wise_marks || [];
        const weak     = subjects.filter(s => s.percentage < 60)
                                 .sort((a, b) => a.percentage - b.percentage);

        const priorityColor = pct => pct < 40 ? "priority-red" : pct < 50 ? "priority-amber" : "priority-yellow";
        const priorityLabel = pct => pct < 40 ? "Critical" : pct < 50 ? "High" : "Medium";

        const parentActions = [
            { icon: "📞", action: "Schedule a meeting with the class teacher." },
            { icon: "📖", action: "Ensure 1 hour of dedicated study time daily." },
            { icon: "📝", action: "Review completed homework regularly." },
            { icon: "💬", action: "Encourage open communication about learning challenges." },
            { icon: "🧑‍💻", action: "Consider online resources or tutoring for weak subjects." },
        ];

        const weakHTML = weak.length ? weak.map(s => `
            <div class="glass-card p-3 mb-3 help-card">
                <div class="d-flex align-items-start gap-3">
                    <div class="priority-badge ${priorityColor(s.percentage)}">
                        ${priorityLabel(s.percentage)}
                    </div>
                    <div class="flex-grow-1">
                        <div class="fw-semibold mb-1">${s.subject_name}</div>
                        ${progressBar(s.percentage, "fill-red")}
                        <div class="small text-muted mt-1">${s.percentage}% — ${s.total_obtained}/${s.total_marks} marks</div>
                        <div class="improvement-tips mt-2">
                            <div class="small fw-semibold mb-1">Suggested Actions</div>
                            <ul>
                                <li>Identify specific chapters causing difficulty.</li>
                                <li>Practice past papers under timed conditions.</li>
                                <li>Request additional worksheets from subject teacher.</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>`).join("")
            : `<div class="success-box">🎉 No critical areas — student is performing well across all subjects!</div>`;

        const actionsHTML = parentActions.map(a => `
            <div class="parent-action-item">
                <span class="parent-action-icon">${a.icon}</span>
                <span class="small">${a.action}</span>
            </div>`).join("");

        getEl("tab-content").innerHTML = `

            <div class="extra-help-grid">

                <div>
                    <div class="section-eyebrow mb-3">Subjects Needing Attention</div>
                    ${weakHTML}
                </div>

                <div>
                    <div class="glass-card p-3 mb-3">
                        <div class="section-eyebrow mb-3">Parent Action Plan</div>
                        ${actionsHTML}
                    </div>
                    <div class="glass-card p-3">
                        <div class="section-eyebrow mb-2">Quick Stats</div>
                        <div class="d-flex gap-3 flex-wrap">
                            <div class="quick-stat">
                                <div class="quick-stat-val text-danger">${subjects.filter(s=>s.percentage<40).length}</div>
                                <div class="quick-stat-label">Critical</div>
                            </div>
                            <div class="quick-stat">
                                <div class="quick-stat-val" style="color:var(--amber)">${subjects.filter(s=>s.percentage>=40&&s.percentage<60).length}</div>
                                <div class="quick-stat-label">High Priority</div>
                            </div>
                            <div class="quick-stat">
                                <div class="quick-stat-val text-success">${subjects.filter(s=>s.percentage>=70).length}</div>
                                <div class="quick-stat-label">On Track</div>
                            </div>
                        </div>
                    </div>
                </div>

            </div>
        `;
    }

    /* ─────────────────────────────────────────────
       INIT
    ───────────────────────────────────────────── */

    function init() {
        renderOverview();
    }

    /* Public API */
    return {
        showTab,
        showSubjectTab,
        renderExamSelector,
        filterAchievements,
        openAddAchievementModal,
        saveAchievement,
        previewCertificate,
        editAchievement,
        deleteAchievement,
        init,
    };

})();

/* Bootstrap */
document.addEventListener("DOMContentLoaded", HorizonsDash.init);