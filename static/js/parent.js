/* =========================================================
   HORIZONS PARENT DASHBOARD — parent.js
   Bootstrap 5 only — no custom layout CSS classes
========================================================= */

"use strict";

const HorizonsDash = (() => {

    let activeTab        = "overview";
    let activeSubjectTab = "subject-overview";
    let chartInstances   = {};

    function cfg() {
        return (window.dashboardData || {}).config || {};
    }

    function gradeLabel(pct) {
        const bands = cfg().grade_bands || [];
        for (const band of bands) {
            if (pct >= band.min) return { label: band.label, color: band.color };
        }
        return { label: "—", color: "secondary" };
    }

    function passFailBadge(pct) {
        const threshold = cfg().pass_threshold ?? 35;
        return pct >= threshold
            ? `<span class="badge bg-success-subtle text-success fw-semibold">Pass</span>`
            : `<span class="badge bg-danger-subtle text-danger fw-semibold">Fail</span>`;
    }

    function progressBar(pct, color) {
        return `
            <div class="progress" style="height:7px;">
                <div class="progress-bar bg-${color}" role="progressbar"
                     style="width:${pct}%" aria-valuenow="${pct}"
                     aria-valuemin="0" aria-valuemax="100">
                </div>
            </div>`;
    }

    function scoreColor(pct) {
        if (pct >= 70) return "success";
        if (pct >= 50) return "warning";
        return "danger";
    }

    function destroyChart(key) {
        if (chartInstances[key]) {
            chartInstances[key].destroy();
            delete chartInstances[key];
        }
    }

    /* ─────────────────────────────────────────
       TAB SWITCHER
    ───────────────────────────────────────── */

    function showTab(tabName, clickedEl) {
        if (tabName === activeTab) return;
        activeTab = tabName;

        document.querySelectorAll(".dashboard-tab").forEach(function(tab) {
            tab.classList.remove("active");
        });

        if (clickedEl) {
            clickedEl.classList.add("active");
        } else {
            var match = document.querySelector('.dashboard-tab[data-tab="' + tabName + '"]');
            if (match) match.classList.add("active");
        }

        const content = getEl("tab-content");
        if (!content) return;
        content.classList.remove("tab-fade-in");
        void content.offsetWidth;
        content.classList.add("tab-fade-in");

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

    /* ─────────────────────────────────────────
       HELPERS
    ───────────────────────────────────────── */

    function getEl(id) { return document.getElementById(id); }

    function _topWeak(d) {
        const as  = d.academic_summary || {};
        const sgj = d.subject_growth_journey || {};
        const top = as.top_subject
            || (sgj.top_performer ? { name: sgj.top_performer.subject, percentage: sgj.top_performer.current_score } : null);
        const weak = as.weak_subject
            || (sgj.weak_subject ? { name: sgj.weak_subject.subject, percentage: sgj.weak_subject.current_score } : null);
        return { top, weak };
    }

    function _trendCounts(subjects) {
        const counts = { improving: 0, stable: 0, declining: 0 };
        (subjects || []).forEach(s => { if (counts[s.trend] !== undefined) counts[s.trend]++; });
        return counts;
    }

    function _findRiskSubject(subjects, threshold) {
        const candidates = (subjects || [])
            .filter(s => s.current_score < threshold && s.trend !== "Strong Growth" && s.trend !== "Improving");
        if (!candidates.length) return null;
        return candidates.sort((a, b) => a.current_score - b.current_score)[0];
    }

    function _participationAreas(achievements, projects) {
        const areas = new Set();
        (achievements || []).forEach(a => { if (a.category) areas.add(a.category); });
        (projects || []).forEach(p => { if (p.type) areas.add(p.type); });
        return Array.from(areas);
    }

    function _row(label, value) {
        return `
            <div class="d-flex justify-content-between align-items-start mb-2 gap-2">
                <span class="text-muted small">${label}</span>
                <span class="small fw-semibold text-end">${value}</span>
            </div>`;
    }

    /* ─────────────────────────────────────────
       OVERVIEW
    ───────────────────────────────────────── */

    function renderOverview() {

        const d           = window.dashboardData || {};
        const library     = d.library_data  || {};
        const remedial    = d.remedial_data  || {};
        const projects    = d.project_data   || {};
        const achieves    = d.achievements   || [];
        const child       = d.child          || {};
        const sgj         = d.subject_growth_journey || {};
        const sgjSubjects = sgj.subjects || [];

        const { top, weak }  = _topWeak(d);
        const improving       = sgj.top_improving_subject  || null;
        const declining       = sgj.top_declining_subject  || null;
        const helpThreshold   = cfg().extra_help_threshold ?? 60;
        const riskSubject     = _findRiskSubject(sgjSubjects, helpThreshold);
        const projectList     = projects.projects || [];
        const participation   = _participationAreas(achieves, projectList);
        const latestAch       = achieves[0]    || null;
        const latestProj      = projectList[0] || null;

        function divider() {
            return `<div class="vr opacity-25 mx-1 d-none d-sm-block"></div>`;
        }

        function insightChip(icon, label, detail, colorClass) {
            return `
                <div class="d-flex align-items-start gap-2 p-2 rounded-3 mb-2" style="background:rgba(var(--bs-${colorClass}-rgb),.07);">
                    <span style="font-size:15px;line-height:1.4;">${icon}</span>
                    <div>
                        <div class="fw-semibold" style="font-size:12px;">${label}</div>
                        <div class="text-muted" style="font-size:11px;">${detail}</div>
                    </div>
                </div>`;
        }

        /* CARD 1 */
        const scoreVal  = d.overall_score || 0;
        const scoreClr  = scoreColor(scoreVal);
        const topVal    = top  ? `${top.name} · ${top.percentage}%`   : "Awaiting exam data";
        const weakVal   = weak ? `${weak.name} · ${weak.percentage}%` : "No weak area identified";
        const improvVal = improving ? `${improving.subject} · ${improving.first_score}% → ${improving.current_score}%` : "No major improvement yet";
        const declineVal = declining ? `${declining.subject} · ${declining.first_score}% → ${declining.current_score}%` : "No notable decline";

        const card1 = `
            <div class="card border-0 shadow-sm h-100">
                <div class="card-body p-3">
                    <p class="text-uppercase fw-bold text-muted mb-3" style="font-size:10px;letter-spacing:.9px;">📊 Student Horizon</p>
                    <div class="d-flex align-items-center gap-3 mb-3 p-2 rounded-3" style="background:rgba(var(--bs-${scoreClr}-rgb),.08);">
                        <div class="rounded-circle d-flex align-items-center justify-content-center fw-bold text-${scoreClr}"
                            style="width:48px;height:48px;border:2px solid rgba(var(--bs-${scoreClr}-rgb),.3);font-size:13px;flex-shrink:0;">
                            ${scoreVal}%
                        </div>
                        <div>
                            <div class="fw-semibold" style="font-size:13px;">Overall Score</div>
                            <div class="progress mt-1" style="height:5px;width:120px;">
                                <div class="progress-bar bg-${scoreClr}" style="width:${scoreVal}%;"></div>
                            </div>
                        </div>
                    </div>
                    <div class="d-flex flex-column gap-2">
                        ${insightChip("🥇", "Top Subject", topVal, "success")}
                        ${insightChip("⚠️", "Weak Subject", weakVal, "warning")}
                        ${insightChip("📈", "Most Improved", improvVal, "primary")}
                        ${insightChip("📉", "Least Growth / Declining", declineVal, "danger")}
                    </div>
                </div>
            </div>`;

        /* CARD 2 */
        let card2Body;
        if (library.is_reader) {
            const recentBooks = (library.recent_books && library.recent_books.length) ? library.recent_books : [];
            card2Body = `
                <div class="d-flex justify-content-around text-center border rounded-3 py-2 mb-3" style="background:rgba(13,110,253,.04);">
                    <div>
                        <div class="fw-bold fs-5 text-primary">${library.total_books || 0}</div>
                        <div class="text-muted" style="font-size:10px;text-transform:uppercase;letter-spacing:.5px;">Read</div>
                    </div>
                    ${divider()}
                    <div>
                        <div class="fw-bold fs-5 text-warning">${library.active_books || 0}</div>
                        <div class="text-muted" style="font-size:10px;text-transform:uppercase;letter-spacing:.5px;">Active</div>
                    </div>
                    ${divider()}
                    <div>
                        <div class="fw-bold fs-5 text-success">${library.favorite_type || "—"}</div>
                        <div class="text-muted" style="font-size:10px;text-transform:uppercase;letter-spacing:.5px;">Fav Genre</div>
                    </div>
                </div>
                ${recentBooks.length ? `
                <p class="text-muted mb-2" style="font-size:11px;text-transform:uppercase;letter-spacing:.6px;">Recent Books</p>
                <div class="d-flex flex-column gap-1">
                    ${recentBooks.map((b, i) => `
                        <div class="d-flex align-items-center gap-2 p-2 rounded-2" style="background:#f8f9fa;">
                            <span class="badge bg-primary-subtle text-primary rounded-pill" style="font-size:10px;">${i + 1}</span>
                            <span class="small fw-semibold">${b}</span>
                        </div>`).join("")}
                </div>` : ""}`;
        } else {
            card2Body = `
                <div class="d-flex align-items-center gap-2 p-2 rounded-3 mb-3" style="background:rgba(255,193,7,.1);">
                    <span style="font-size:20px;">📚</span>
                    <div>
                        <div class="fw-semibold" style="font-size:12px;">No Library Activity Yet</div>
                        <div class="text-muted" style="font-size:11px;">${library.suggestion || "Encourage issuing books from the school library."}</div>
                    </div>
                </div>
                <div class="d-flex flex-column gap-2">
                    ${insightChip("💡", "Why it matters", "Regular reading improves vocabulary, comprehension and academic scores across all subjects.", "primary")}
                    ${insightChip("🎯", "Getting started", "Try 1 book per month — fiction or non-fiction in an area the student already enjoys.", "success")}
                    ${insightChip("🏛️", "How to issue", "Visit the school library with the student diary. Books can be issued for 2 weeks.", "secondary")}
                </div>`;
        }
        const card2 = `
            <div class="card border-0 shadow-sm h-100">
                <div class="card-body p-3">
                    <p class="text-uppercase fw-bold text-muted mb-3" style="font-size:10px;letter-spacing:.9px;">📖 Learning Rhythm</p>
                    ${card2Body}
                </div>
            </div>`;

        /* CARD 3 */
        const hasExtra = achieves.length > 0 || (projects.project_count || 0) > 0;
        let card3Body;
        if (hasExtra) {
            card3Body = `
                <div class="d-flex justify-content-around text-center border rounded-3 py-2 mb-3" style="background:rgba(25,135,84,.04);">
                    <div>
                        <div class="fw-bold fs-5 text-success">${achieves.length}</div>
                        <div class="text-muted" style="font-size:10px;text-transform:uppercase;letter-spacing:.5px;">Achievements</div>
                    </div>
                    ${divider()}
                    <div>
                        <div class="fw-bold fs-5 text-primary">${projects.project_count || 0}</div>
                        <div class="text-muted" style="font-size:10px;text-transform:uppercase;letter-spacing:.5px;">Projects</div>
                    </div>
                    ${divider()}
                    <div>
                        <div class="fw-bold fs-5 text-warning">${participation.length || "—"}</div>
                        <div class="text-muted" style="font-size:10px;text-transform:uppercase;letter-spacing:.5px;">Areas</div>
                    </div>
                </div>
                ${participation.length ? `
                <div class="d-flex flex-wrap gap-1 mb-3">
                    ${participation.map(p => `<span class="badge bg-secondary-subtle text-secondary rounded-pill px-2" style="font-size:11px;">${p}</span>`).join("")}
                </div>` : ""}
                ${latestAch ? insightChip("🏆", `Latest Achievement · ${latestAch.date || ""}`, latestAch.title + (latestAch.awarded_by ? ` — ${latestAch.awarded_by}` : ""), "warning") : ""}
                ${latestProj ? insightChip("🔬", `Latest Project · ${latestProj.date || ""}`, latestProj.title, "primary") : ""}`;
        } else {
            card3Body = `
                <div class="text-center py-3">
                    <div style="font-size:36px;opacity:.35;">🏆</div>
                    <div class="fw-semibold small mt-2">No extracurriculars recorded yet</div>
                    <div class="text-muted mt-1" style="font-size:12px;line-height:1.6;">
                        Participating in sports, arts, competitions or community projects builds a
                        well-rounded profile alongside academics.
                    </div>
                </div>`;
        }
        const card3 = `
            <div class="card border-0 shadow-sm h-100">
                <div class="card-body p-3">
                    <p class="text-uppercase fw-bold text-muted mb-3" style="font-size:10px;letter-spacing:.9px;">🏆 Beyond Curriculum</p>
                    ${card3Body}
                </div>
            </div>`;

        /* SCHOLASTIC JOURNEY */
        const decliningSubjects = sgjSubjects.filter(s => s.five_year_growth < -5).sort((a,b) => a.five_year_growth - b.five_year_growth);
        const topDeclining = decliningSubjects[0] || null;

        function _trendCountsNew(subjects) {
            let improving = 0, stable = 0, declining = 0;
            (subjects || []).forEach(s => {
                const t = s.trend || "";
                if (t === "Strong Growth" || t === "Improving") improving++;
                else if (t === "Declining") declining++;
                else stable++;
            });
            return { improving, stable, declining };
        }
        const trendCountsNew = _trendCountsNew(sgjSubjects);

        const highGrowthVal = improving ? `${improving.subject} +${improving.five_year_growth}%` : "—";
        const highGrowthSub = improving ? `${improving.first_score}% → ${improving.current_score}%` : "No growth data yet";
        const bigDeclineVal = topDeclining ? `${topDeclining.subject} ${topDeclining.five_year_growth}%` : "—";
        const bigDeclineSub = topDeclining ? `${topDeclining.first_score}% → ${topDeclining.current_score}%` : "No decline detected";
        const improvedCount = trendCountsNew.improving;
        const totalSubjects = sgjSubjects.length;
        const improvedSub   = totalSubjects ? `out of ${totalSubjects} tracked` : "No subjects tracked yet";
        const remedialSessions = remedial.is_remedial ? (remedial.primary_remedial_sessions || remedial.session_count || 0) : 0;
        const remedialSub = remedial.is_remedial ? `${remedial.primary_remedial_subject || "select subjects"}` : "No remedial support required";

        const subjectInsights = [];
        if (improving) {
            const yrs = improving.years_present ? `over ${improving.years_present} year${improving.years_present === 1 ? "" : "s"}` : "";
            subjectInsights.push(insightChip("📈", `${improving.subject} improved ${improving.first_score}% → ${improving.current_score}% ${yrs}`, `Five-year growth of +${improving.five_year_growth}% — highest improvement across all subjects.`, "success"));
        }
        if (topDeclining) {
            const yrs = topDeclining.years_present ? `over ${topDeclining.years_present} year${topDeclining.years_present === 1 ? "" : "s"}` : "";
            subjectInsights.push(insightChip("📉", `${topDeclining.subject} dropped ${topDeclining.first_score}% → ${topDeclining.current_score}% ${yrs}`, `Decline of ${topDeclining.five_year_growth}% — needs focused revision and teacher consultation.`, "danger"));
        }
        if (weak)  subjectInsights.push(insightChip("⚠️", `${weak.name} · Current score ${weak.percentage}%, needs attention`, `Consistently the weakest performing subject — consider extra practice or tutoring.`, "warning"));
        if (top)   subjectInsights.push(insightChip("🌟", `${top.name} · Current score ${top.percentage}%, strongest subject`, `Maintain momentum — this area can anchor overall academic confidence.`, "primary"));
        if (riskSubject && riskSubject.subject !== (weak && weak.name)) subjectInsights.push(insightChip("🔴", `${riskSubject.subject} · ${riskSubject.current_score}%, at-risk and not improving`, `Below the ${helpThreshold}% benchmark with no upward trend.`, "danger"));

        const journeyRows = sgjSubjects.slice(0,6).map(s => {
            const isGrowing   = s.trend === "Strong Growth" || s.trend === "Improving";
            const isDeclining = s.trend === "Declining";
            const trendIcon   = isGrowing ? "↑" : isDeclining ? "↓" : "→";
            const trendColor  = isGrowing ? "success" : isDeclining ? "danger" : "secondary";
            const barWidth    = Math.min(s.current_score || 0, 100);
            const journeyText = (s.first_score !== undefined && s.first_score !== s.current_score) ? `${s.first_score}% → ${s.current_score}%` : `Current: ${s.current_score || 0}%`;
            return `
                <div class="d-flex align-items-center gap-2 py-2 border-bottom" style="min-width:0;">
                    <div style="width:90px;flex-shrink:0;font-size:12px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" title="${s.subject}">${s.subject}</div>
                    <div class="flex-grow-1"><div class="progress" style="height:5px;"><div class="progress-bar bg-${trendColor}" style="width:${barWidth}%;"></div></div></div>
                    <div style="width:32px;text-align:right;font-size:12px;font-weight:600;flex-shrink:0;">${s.current_score || 0}%</div>
                    <div class="text-${trendColor} fw-bold" style="width:14px;flex-shrink:0;font-size:13px;">${trendIcon}</div>
                    <div class="text-muted" style="font-size:10px;width:110px;flex-shrink:0;">${journeyText}</div>
                </div>`;
        }).join("");

        const scholasticCard = `
            <div class="card border-0 shadow-sm">
                <div class="card-body p-3">
                    <p class="text-uppercase fw-bold text-muted mb-3" style="font-size:10px;letter-spacing:.9px;">🎓 Scholastic Journey</p>
                    <div class="row g-2 mb-4">
                        <div class="col-6 col-md-3"><div class="rounded-3 p-3 h-100" style="background:rgba(25,135,84,.08);"><div class="text-muted mb-1" style="font-size:10px;text-transform:uppercase;letter-spacing:.6px;">Highest Growth</div><div class="fw-bold text-success" style="font-size:1rem;">${highGrowthVal}</div><div class="text-muted" style="font-size:11px;">${highGrowthSub}</div></div></div>
                        <div class="col-6 col-md-3"><div class="rounded-3 p-3 h-100" style="background:rgba(220,53,69,.08);"><div class="text-muted mb-1" style="font-size:10px;text-transform:uppercase;letter-spacing:.6px;">Biggest Decline</div><div class="fw-bold text-danger" style="font-size:1rem;">${bigDeclineVal}</div><div class="text-muted" style="font-size:11px;">${bigDeclineSub}</div></div></div>
                        <div class="col-6 col-md-3"><div class="rounded-3 p-3 h-100" style="background:rgba(13,110,253,.08);"><div class="text-muted mb-1" style="font-size:10px;text-transform:uppercase;letter-spacing:.6px;">Improved Subjects</div><div class="fw-bold text-primary" style="font-size:1.5rem;">${improvedCount}</div><div class="text-muted" style="font-size:11px;">${improvedSub}</div></div></div>
                        <div class="col-6 col-md-3"><div class="rounded-3 p-3 h-100" style="background:rgba(255,193,7,.1);"><div class="text-muted mb-1" style="font-size:10px;text-transform:uppercase;letter-spacing:.6px;">Remedial Sessions</div><div class="fw-bold text-warning" style="font-size:1.5rem;">${remedialSessions}</div><div class="text-muted" style="font-size:11px;">${remedialSub}</div></div></div>
                    </div>
                    <div class="row g-3">
                        ${subjectInsights.length ? `<div class="col-12 col-md-6"><p class="text-muted mb-2" style="font-size:11px;text-transform:uppercase;letter-spacing:.6px;">Key Insights</p>${subjectInsights.join("")}</div>` : ""}
                        ${journeyRows ? `<div class="col-12 ${subjectInsights.length ? "col-md-6" : ""}"><p class="text-muted mb-2" style="font-size:11px;text-transform:uppercase;letter-spacing:.6px;">Subject Score Journey</p>${journeyRows}</div>` : ""}
                    </div>
                </div>
            </div>`;

        const aiCard = `
            <div class="card border-primary border-opacity-25 shadow-sm">
                <div class="card-body">
                    <div class="d-flex align-items-center gap-2 mb-2">
                        <span class="badge bg-primary rounded-pill" style="width:10px;height:10px;padding:0;animation:pulse 1.8s infinite;"></span>
                        <span class="text-uppercase fw-bold text-muted small" style="font-size:11px;letter-spacing:.8px;">AI Summary</span>
                    </div>
                    <p class="small text-muted mb-2">Based on ${child.first_name || "this student"}'s performance this year, here are the key insights.</p>
                    <div id="ai-summary-body"><span class="text-muted small">Generating insights…</span></div>
                </div>
            </div>`;

        getEl("tab-content").innerHTML = `
            <div class="row g-3 mb-3">
                <div class="col-12 col-lg-4">${card1}</div>
                <div class="col-12 col-lg-4">${card2}</div>
                <div class="col-12 col-lg-4">${card3}</div>
            </div>
            <div class="row g-3 mb-3"><div class="col-12">${scholasticCard}</div></div>
            <div class="row g-3"><div class="col-12">${aiCard}</div></div>
        `;

        _generateAISummary(d);
    }

    /* ─────────────────────────────────────────
       AI SUMMARY
    ───────────────────────────────────────── */

    function _generateAISummary(d) {

        const el = getEl("ai-summary-body");
        if (!el) return;

        const child    = d.child    || {};
        const acad     = d.academic_summary || {};
        const sgj      = d.subject_growth_journey || {};
        const library  = d.library_data  || {};
        const remedial = d.remedial_data || {};
        const projects = d.project_data  || {};
        const achieves = d.achievements  || [];
        const rhythm   = d.learning_rhythm || {};

        const name         = (child.first_name || "").trim() || "The student";
        const overallScore = parseFloat(d.overall_score) || 0;
        const attendance   = parseFloat(d.days_present)  || 0;
        const sgjSubjects  = Array.isArray(sgj.subjects) ? sgj.subjects : [];

        function safe(val) {
            if (val === null || val === undefined) return null;
            if (typeof val === "number" && isNaN(val)) return null;
            if (typeof val === "string" && val.trim() === "") return null;
            return val;
        }
        function safeNum(val) {
            const n = parseFloat(val);
            return isNaN(n) ? null : n;
        }

        /* normalise top/weak from either sgj or academic_summary */
        function sn(s) { return s ? safe(s.subject || s.name) : null; }
        function ss(s) { return s ? safeNum(s.current_score !== undefined ? s.current_score : s.percentage) : null; }

        const topPerformer   = sgj.top_performer           || acad.top_subject  || null;
        const topImproving   = sgj.top_improving_subject   || null;
        const topDeclining   = sgj.top_declining_subject   || null;
        const mostConsistent = sgj.most_consistent_subject || null;
        const weakSubject    = sgj.weak_subject            || acad.weak_subject || null;

        const topName  = sn(topPerformer);   const topScore  = ss(topPerformer);
        const weakName = sn(weakSubject);     const weakScore = ss(weakSubject);
        const impName  = safe(topImproving  && topImproving.subject);
        const impG     = safeNum(topImproving  && topImproving.five_year_growth);
        const impF     = safeNum(topImproving  && topImproving.first_score);
        const impC     = safeNum(topImproving  && topImproving.current_score);
        const decName  = safe(topDeclining  && topDeclining.subject);
        const decG     = safeNum(topDeclining  && topDeclining.five_year_growth);
        const decF     = safeNum(topDeclining  && topDeclining.first_score);
        const decC     = safeNum(topDeclining  && topDeclining.current_score);
        const conName  = safe(mostConsistent && mostConsistent.subject);
        const conScore = safeNum(mostConsistent && mostConsistent.current_score);

        const hasRealGrowth = impG !== null && impG > 0 && impName !== topName;

        const readingProfile  = rhythm.reading_profile  || {};
        const rhythmStrengths = Array.isArray(rhythm.strengths) ? rhythm.strengths : [];
        const rhythmConcerns  = Array.isArray(rhythm.concerns)  ? rhythm.concerns  : [];

        const parts = [];

        /* 1. Academic Snapshot */
        if (overallScore > 0) {
            const desc = overallScore >= 80 ? "strong" : overallScore >= 60 ? "steady" : "developing";
            parts.push(`${name} is showing <strong>${desc} academic performance</strong> this year with an overall average of <strong>${overallScore}%</strong>.`);
        } else {
            parts.push(`Academic data for ${name} is still being recorded for this period.`);
        }

        /* 2. Strongest Subject */
        if (topName && topScore !== null) {
            const band = topScore >= 85 ? "excellent" : topScore >= 70 ? "strong" : "solid";
            parts.push(`<strong>Strongest subject:</strong> ${topName} at ${topScore}% — ${band} performance maintained this year.`);
        }

        /* 3. Weakest Subject */
        if (weakName && weakScore !== null && weakName !== topName) {
            const action = weakScore < 50
                ? "urgent attention and structured support are recommended."
                : weakScore < 65
                ? "additional practice sessions would make a noticeable difference."
                : "some extra revision before exams could push this higher.";
            parts.push(`<strong>Area needing focus:</strong> ${weakName} at ${weakScore}% — ${action}`);
        }

        /* 4. Growth Journey */
        if (hasRealGrowth && impName && impF !== null && impC !== null) {
            parts.push(`<strong>Growth journey:</strong> ${impName} has shown the strongest improvement, rising from ${impF}% to ${impC}% — a gain of +${impG}% that reflects sustained effort over multiple years.`);
        } else if (conName && conScore !== null) {
            const desc = conScore >= 75 ? "comfortably" : conScore >= 55 ? "steadily" : "consistently";
            parts.push(`<strong>Most consistent subject:</strong> ${conName} has ${desc} held around ${conScore}% across recent years — a reliable anchor in the academic profile.`);
        }

        if (decName && decG !== null && decF !== null && decC !== null) {
            parts.push(`<strong>Watch closely:</strong> ${decName} has slipped from ${decF}% to ${decC}% over recent years. A conversation with the subject teacher now could prevent further decline.`);
        }

        const improvedCount  = safeNum(sgj.improved_subject_count);
        const decliningCount = safeNum(sgj.declining_subject_count);
        const stableCount    = safeNum(sgj.stable_subject_count);
        const totalTracked   = sgjSubjects.length;
        if (totalTracked > 0 && improvedCount !== null) {
            const line = improvedCount > 0
                ? `${improvedCount} of ${totalTracked} subjects are on an upward trend`
                : `${stableCount || 0} subjects are stable`;
            parts.push(`<strong>Overall growth picture:</strong> ${line}${decliningCount > 0 ? `, while ${decliningCount} need attention` : ""}.`);
        }

        /* 5. Reading Behaviour */
        if (readingProfile.is_reader && safeNum(readingProfile.books_read) > 0) {
            const books  = safeNum(readingProfile.books_read);
            const genre  = safe(readingProfile.favorite_type);
            const active = safeNum(readingProfile.active_books);
            parts.push(
                `<strong>Reading behaviour:</strong> ${name} has issued ${books} book${books === 1 ? "" : "s"} from the library` +
                `${genre ? `, showing a preference for ${genre} titles` : ""}` +
                `${active && active > 0 ? ` with ${active} currently on loan` : ""}.`
            );
        } else {
            parts.push(`<strong>Reading behaviour:</strong> No library activity has been recorded yet — encouraging regular reading, even one book a month, can significantly support comprehension and vocabulary across all subjects.`);
        }

        /* 6. Remedial Support */
        if (remedial.is_remedial) {
            const sessions = safeNum(remedial.primary_remedial_sessions || remedial.session_count);
            const subj     = safe(remedial.primary_remedial_subject);
            if (subj && sessions !== null && sessions > 0) {
                parts.push(`<strong>Remedial support:</strong> ${name} is currently receiving targeted help in ${subj} (${sessions} session${sessions === 1 ? "" : "s"} completed). This additional support is a positive step and should be continued alongside regular class work.`);
            } else if (subj) {
                parts.push(`<strong>Remedial support:</strong> ${name} is enrolled in remedial sessions for ${subj}. Regular attendance will help close identified gaps.`);
            }
        } else {
            parts.push(`<strong>Remedial support:</strong> No remedial sessions are currently required — ${name} is managing the curriculum independently.`);
        }

        /* 7. Projects & Achievements */
        const projCount = safeNum(projects.project_count);
        const achCount  = achieves.length;
        const latestAch = achieves[0] || null;
        if (projCount !== null && projCount > 0 && achCount > 0) {
            const t = safe(latestAch && latestAch.title);
            parts.push(`<strong>Projects &amp; achievements:</strong> ${name} has completed ${projCount} project${projCount === 1 ? "" : "s"} and earned ${achCount} achievement${achCount === 1 ? "" : "s"}${t ? `, most recently "${t}"` : ""} — excellent engagement beyond the classroom.`);
        } else if (projCount !== null && projCount > 0) {
            parts.push(`<strong>Projects:</strong> ${name} has completed ${projCount} project${projCount === 1 ? "" : "s"} — great initiative in applying knowledge outside regular lessons.`);
        } else if (achCount > 0) {
            const t = safe(latestAch && latestAch.title);
            parts.push(`<strong>Achievements:</strong> ${achCount} achievement${achCount === 1 ? "" : "s"} recorded${t ? `, including "${t}"` : ""} — a sign of drive and engagement beyond academics.`);
        }

        /* 8. Learning Rhythm Insights */
        const rhythmLines = [];
        rhythmStrengths.forEach(s => {
            if (s.type === "academic_growth" && safe(s.subject) && safeNum(s.growth) > 0) rhythmLines.push(`upward academic momentum in ${s.subject} (+${s.growth}%)`);
            if (s.type === "projects" && safeNum(s.count) > 0) rhythmLines.push(`active project engagement (${s.count} project${s.count === 1 ? "" : "s"})`);
        });
        rhythmConcerns.forEach(c => {
            if (c.type === "declining_subject" && safe(c.subject) && safeNum(c.decline) > 0) rhythmLines.push(`a ${c.decline}% decline in ${c.subject} that warrants a closer look`);
        });
        if (rhythmLines.length) {
            parts.push(`<strong>Learning rhythm insights:</strong> The overall profile highlights ${rhythmLines.join("; ")}.`);
        }

        /* 9. Final Parent Recommendation */
        const rec = [];
        if (weakScore !== null && weakScore < 60 && weakName)   rec.push(`schedule a meeting with the ${weakName} teacher to discuss targeted improvement strategies`);
        if (!readingProfile.is_reader)                          rec.push(`encourage regular library visits to build reading habits early`);
        if (remedial.is_remedial)                               rec.push(`ensure consistent attendance at remedial sessions for maximum benefit`);
        if (attendance > 0 && attendance < 75)                  rec.push(`improve attendance — even a few more days per month can lift scores meaningfully`);
        if (decName)                                            rec.push(`monitor ${decName} closely over the coming term`);

        if (rec.length) {
            const recText = rec.length === 1 ? rec[0] : rec.slice(0,-1).join(", ") + ", and " + rec.at(-1);
            parts.push(`<strong>Recommendation for parents:</strong> To support ${name} most effectively, consider: ${recText}.`);
        } else if (overallScore >= 75) {
            parts.push(`<strong>Recommendation:</strong> ${name} is doing well — keep reinforcing the study habits that are working, and celebrate the progress made this year.`);
        }

        if (!parts.length) {
            el.innerHTML = `<p class="small text-muted mb-0" style="line-height:1.8;">No data available yet for this period.</p>`;
            return;
        }
        el.innerHTML = `<div style="line-height:1.85;">${parts.map(p => `<p class="small text-muted mb-2">${p}</p>`).join("")}</div>`;
    }

    /* ─────────────────────────────────────────
       SUBJECTS
    ───────────────────────────────────────── */

    function renderSubjects() {
        const subTabs = [
            { key: "subject-overview", label: "Overview"          },
            { key: "exam-wise",        label: "Exam Wise"         },
            { key: "full-year",        label: "Full Year"         },
            { key: "strengths",        label: "Strength Areas"    },
            { key: "improvements",     label: "Improvement Areas" },
        ];
        const navHTML = subTabs.map(t => `
            <button class="btn btn-sm ${t.key === activeSubjectTab ? "btn-primary" : "btn-outline-secondary"} me-1 mb-1"
                    data-sub="${t.key}" onclick="HorizonsDash.showSubjectTab('${t.key}', this)">
                ${t.label}
            </button>`).join("");
        getEl("tab-content").innerHTML = `<div class="mb-3">${navHTML}</div><div id="subject-tab-content"></div>`;
        renderSubjectContent(activeSubjectTab);
    }

    function showSubjectTab(key, clickedEl) {
        activeSubjectTab = key;
        document.querySelectorAll("[data-sub]").forEach(function(btn) {
            btn.className = btn.className.replace(/btn-primary/g, "btn-outline-secondary").replace(/btn-outline-secondary btn-outline-secondary/g, "btn-outline-secondary");
        });
        if (clickedEl) clickedEl.className = clickedEl.className.replace("btn-outline-secondary", "btn-primary");
        const ct = getEl("subject-tab-content");
        if (ct) { ct.classList.remove("tab-fade-in"); void ct.offsetWidth; ct.classList.add("tab-fade-in"); }
        renderSubjectContent(key);
    }

    function renderSubjectContent(key) {
        const map = {
            "subject-overview": renderSubjectOverview,
            "exam-wise":        renderExamWise,
            "full-year":        renderFullYear,
            "strengths":        renderStrengthAreas,
            "improvements":     renderImprovementAreas,
        };
        (map[key] || renderSubjectOverview)();
    }

    function renderSubjectOverview() {
        const subjects = (window.dashboardData || {}).subject_wise_marks || [];
        const html = subjects.length ? subjects.map(s => {
            const g = gradeLabel(s.percentage); const c = scoreColor(s.percentage);
            return `
                <div class="card border-0 shadow-sm mb-2">
                    <div class="card-body py-2 px-3">
                        <div class="d-flex align-items-center gap-3">
                            <div style="min-width:140px;">
                                <div class="fw-semibold small">${s.subject_name}</div>
                                <div class="text-muted" style="font-size:12px;">${s.total_obtained} / ${s.total_marks}</div>
                            </div>
                            <div class="flex-grow-1">${progressBar(s.percentage, c)}</div>
                            <div class="d-flex align-items-center gap-1 flex-shrink-0">
                                <span class="badge bg-${g.color}-subtle text-${g.color} fw-bold">${g.label}</span>
                                ${passFailBadge(s.percentage)}
                                <span class="small fw-semibold">${s.percentage}%</span>
                            </div>
                        </div>
                    </div>
                </div>`;
        }).join("") : `<p class="text-muted">No subject data available.</p>`;
        getEl("subject-tab-content").innerHTML = html;
    }

    function renderExamWise() {
        const subjects = (window.dashboardData || {}).subject_wise_marks || [];
        const opts = subjects.map((s, i) => `<option value="${i}">${s.subject_name}</option>`).join("");
        getEl("subject-tab-content").innerHTML = `
            <div class="card border-0 shadow-sm mb-3">
                <div class="card-body">
                    <label class="form-label fw-semibold small">Select Subject</label>
                    <select class="form-select form-select-sm" id="exam-subject-select" onchange="HorizonsDash.renderExamSelector(this.value)">${opts}</select>
                </div>
            </div>
            <div id="exam-detail-area"></div>`;
        renderExamSelector(0);
    }

    function renderExamSelector(idx) {
        const subjects = (window.dashboardData || {}).subject_wise_marks || [];
        const subject  = subjects[idx];
        const area     = getEl("exam-detail-area");
        if (!area || !subject) return;
        const html = (subject.exams || []).map(exam => `
            <div class="card border-0 shadow-sm mb-3">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <strong>${exam.exam_name}</strong>
                        ${passFailBadge(exam.exam_percentage)}
                        <span class="badge bg-secondary-subtle text-secondary fw-semibold">${exam.exam_percentage}%</span>
                    </div>
                    <div class="table-responsive">
                        <table class="table table-sm table-hover mb-0">
                            <thead class="table-light"><tr><th>Type</th><th>Obtained</th><th>Total</th><th>%</th><th>Grade</th></tr></thead>
                            <tbody>
                                ${(exam.exam_types || []).map(et => {
                                    const g = gradeLabel(et.percentage);
                                    return `<tr><td>${et.exam_type}</td><td>${et.obtained}</td><td>${et.total}</td><td>${et.percentage}%</td><td><span class="badge bg-${g.color}-subtle text-${g.color} fw-bold">${g.label}</span></td></tr>`;
                                }).join("")}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>`).join("") || `<p class="text-muted">No exam data available.</p>`;
        area.innerHTML = html;
    }

    function renderFullYear() {
        const subjects = (window.dashboardData || {}).subject_wise_marks || [];
        getEl("subject-tab-content").innerHTML = `
            <div class="card border-0 shadow-sm">
                <div class="card-body">
                    <p class="text-uppercase fw-bold text-muted mb-3" style="font-size:11px;letter-spacing:.8px;">Full Year Performance</p>
                    <div class="table-responsive">
                        <table class="table table-hover table-sm align-middle mb-0">
                            <thead class="table-light"><tr><th>Subject</th><th>Obtained</th><th>Total</th><th>%</th><th>Grade</th><th>Status</th></tr></thead>
                            <tbody>
                                ${subjects.map(s => {
                                    const g = gradeLabel(s.percentage);
                                    return `<tr><td class="fw-semibold">${s.subject_name}</td><td>${s.total_obtained}</td><td>${s.total_marks}</td><td>${s.percentage}%</td><td><span class="badge bg-${g.color}-subtle text-${g.color} fw-bold">${g.label}</span></td><td>${passFailBadge(s.percentage)}</td></tr>`;
                                }).join("")}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>`;
    }

    function renderStrengthAreas() {
        const subjects = (window.dashboardData || {}).subject_wise_marks || [];
        const strong   = subjects.filter(s => s.percentage >= 70).sort((a,b) => b.percentage - a.percentage);
        const html = strong.length ? strong.map(s => `
            <div class="card border-0 shadow-sm mb-2">
                <div class="card-body py-2 px-3 d-flex align-items-center gap-3">
                    <span class="badge bg-success rounded-circle p-2 fs-6">✓</span>
                    <div class="flex-grow-1"><div class="fw-semibold small">${s.subject_name}</div>${progressBar(s.percentage, "success")}</div>
                    <span class="fw-bold text-success small">${s.percentage}%</span>
                </div>
            </div>`).join("") : `<p class="text-muted">No subjects above 70% yet — keep going!</p>`;
        getEl("subject-tab-content").innerHTML = html;
    }

    function renderImprovementAreas() {
        const subjects = (window.dashboardData || {}).subject_wise_marks || [];
        const weak     = subjects.filter(s => s.percentage < 70).sort((a,b) => a.percentage - b.percentage);
        const tips = cfg().improvement_tips || [];
        const tipsHTML = tips.length
            ? `<ul class="list-unstyled mt-2 mb-0">${tips.map(t => `<li class="text-muted d-flex align-items-start gap-1 mb-1" style="font-size:12px;"><span class="text-primary fw-bold flex-shrink-0">→</span>${t}</li>`).join("")}</ul>`
            : "";
        const html = weak.length ? weak.map(s => `
            <div class="card border-0 shadow-sm mb-3">
                <div class="card-body">
                    <div class="d-flex align-items-center gap-2 mb-2">
                        <span class="badge bg-warning text-dark rounded-circle p-2">!</span>
                        <div><div class="fw-semibold small">${s.subject_name}</div><div class="text-muted" style="font-size:12px;">${s.percentage}% · ${s.total_obtained}/${s.total_marks}</div></div>
                        ${passFailBadge(s.percentage)}
                    </div>
                    ${progressBar(s.percentage, "warning")}
                    ${tipsHTML}
                </div>
            </div>`).join("") : `<div class="alert alert-success border-0">🎉 No weak subjects detected — excellent work!</div>`;
        getEl("subject-tab-content").innerHTML = html;
    }

    /* ─────────────────────────────────────────
       GRAPHS
    ───────────────────────────────────────── */

    const BLUE1  = "rgba(91,141,238,0.85)";
    const BLUE2  = "rgba(91,141,238,0.18)";
    const GREEN1 = "rgba(45,168,122,0.85)";
    const AMBER1 = "rgba(247,95,8,0.95)";
    const RED1   = "rgba(220,53,69,0.85)";
    const GRAY1  = "rgba(108,117,125,0.7)";

    function _noData(canvas, msg) {
        const ctx = canvas.getContext("2d");
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = "#9ca3af"; ctx.font = "13px system-ui,sans-serif";
        ctx.textAlign = "center"; ctx.textBaseline = "middle";
        ctx.fillText(msg, canvas.width/2, canvas.height/2);
    }

    function _chartCard(title, canvasId, icon) {
        return `
            <div class="col-12 col-lg-6">
                <div class="card border-0 shadow-sm h-100">
                    <div class="card-body d-flex flex-column" style="min-height:320px;">
                        <p class="text-uppercase fw-bold text-muted mb-3 flex-shrink-0" style="font-size:11px;letter-spacing:.8px;">${icon}&nbsp;${title}</p>
                        <div class="flex-grow-1 position-relative" style="min-height:240px;"><canvas id="${canvasId}"></canvas></div>
                    </div>
                </div>
            </div>`;
    }

    function _heatmapCard() {
        return `
            <div class="col-12">
                <div class="card border-0 shadow-sm">
                    <div class="card-body">
                        <p class="text-uppercase fw-bold text-muted mb-3" style="font-size:11px;letter-spacing:.8px;">🗓️&nbsp;Subject Performance Heatmap</p>
                        <div id="heatmap-container" class="table-responsive"></div>
                    </div>
                </div>
            </div>`;
    }

    function renderGraphs() {
        getEl("tab-content").innerHTML = `
            <div class="row g-3 mb-3">
                ${_chartCard("Subject Performance",       "chart-subject", "📊")}
                ${_chartCard("Five-Year Growth Journey",  "chart-growth",  "📈")}
               
            </div>
            <div class="row g-3">${_heatmapCard()}</div>`;
        requestAnimationFrame(renderCharts);
    }

    function renderCharts() {

        const d = window.dashboardData || {};
        const subjectAnalytics = d.subject_performance_analytics || {};
        const sgj              = d.subject_growth_journey        || {};
        const sgjSubjects      = sgj.subjects                    || [];
        const heatmap          = d.subject_heatmap               || {};

        /* ── CHART 1: Subject Performance ── */
        destroyChart("subject");
        const ctxSubject = getEl("chart-subject");
        if (ctxSubject) {
            const labels = subjectAnalytics.labels || [];
            const scores = subjectAnalytics.scores || [];
            if (!labels.length) {
                _noData(ctxSubject, "No subject data available.");
            } else {
                chartInstances.subject = new Chart(ctxSubject, {
                    type: "bar",
                    data: {
                        labels,
                        datasets: [{ label: "Score", data: scores,
                            backgroundColor: scores.map(s => s >= 75 ? GREEN1 : s >= 60 ? BLUE1 : AMBER1),
                            borderRadius: 6, barThickness: 18 }]
                    },
                    options: {
                        indexAxis: "y", responsive: true, maintainAspectRatio: false,
                        layout: { padding: { right: 12 } },
                        plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => `${ctx.raw}%` } } },
                        scales: {
                            x: { min: 0, max: 100, grid: { color: "rgba(0,0,0,0.05)" }, ticks: { font: { size: 11 }, callback: v => v + "%" } },
                            y: { grid: { display: false }, ticks: { font: { size: 11 } } }
                        }
                    }
                });
            }
        }

        /* ── CHART 2: Five-Year Growth Journey ── */
        destroyChart("growth");
        const ctxGrowth = getEl("chart-growth");
        if (ctxGrowth) {
            if (!sgjSubjects.length) {
                _noData(ctxGrowth, "No growth journey data available.");
            } else {
                const sorted  = [...sgjSubjects].sort((a,b) => b.five_year_growth - a.five_year_growth);
                const labels  = sorted.map(s => s.subject);
                const growths = sorted.map(s => s.five_year_growth);
                chartInstances.growth = new Chart(ctxGrowth, {
                    type: "bar",
                    data: {
                        labels,
                        datasets: [{ label: "5-Year Growth (%)", data: growths,
                            backgroundColor: growths.map(g => g >= 5 ? GREEN1 : g > 0 ? BLUE1 : g >= -5 ? GRAY1 : RED1),
                            borderRadius: 4, barThickness: 16 }]
                    },
                    options: {
                        indexAxis: "y", responsive: true, maintainAspectRatio: false,
                        layout: { padding: { right: 16 } },
                        plugins: {
                            legend: { display: false },
                            tooltip: { callbacks: { label: ctx => {
                                const s = sorted[ctx.dataIndex];
                                return [`Growth: ${ctx.raw > 0 ? "+" : ""}${ctx.raw}%`, `Start: ${s.first_score}%  →  Now: ${s.current_score}%`, `Trend: ${s.trend}`];
                            }}}
                        },
                        scales: {
                            x: { grid: { color: "rgba(0,0,0,0.05)" }, ticks: { font: { size: 11 }, callback: v => (v > 0 ? "+" : "") + v + "%" } },
                            y: { grid: { display: false }, ticks: { font: { size: 11 } } }
                        }
                    }
                });
            }
        }

        /* ── CHART 3: Growth Distribution (doughnut) ── */
        destroyChart("dist");
        const ctxDist = getEl("chart-dist");
        if (ctxDist) {
            const improved  = sgj.improved_subject_count  || 0;
            const stable    = sgj.stable_subject_count    || 0;
            const declining = sgj.declining_subject_count || 0;
            const total     = improved + stable + declining;
            if (!total) {
                _noData(ctxDist, "No distribution data available.");
            } else {
                chartInstances.dist = new Chart(ctxDist, {
                    type: "doughnut",
                    data: {
                        labels: ["Improving", "Stable", "Declining"],
                        datasets: [{ data: [improved, stable, declining],
                            backgroundColor: [GREEN1, GRAY1, RED1], borderWidth: 2, borderColor: "#fff", hoverOffset: 6 }]
                    },
                    options: {
                        responsive: true, maintainAspectRatio: false, cutout: "62%",
                        plugins: {
                            legend: { position: "bottom", labels: { boxWidth: 12, font: { size: 11 }, padding: 12 } },
                            tooltip: { callbacks: { label: ctx => {
                                const pct = total ? Math.round((ctx.raw / total) * 100) : 0;
                                return ` ${ctx.label}: ${ctx.raw} subject${ctx.raw === 1 ? "" : "s"} (${pct}%)`;
                            }}}
                        }
                    },
                    plugins: [{
                        id: "centre-label",
                        afterDraw(chart) {
                            const { ctx: c, chartArea: { left, top, right, bottom } } = chart;
                            const cx = (left + right) / 2, cy = (top + bottom) / 2;
                            c.save();
                            c.textAlign = "center"; c.textBaseline = "middle";
                            c.fillStyle = "#374151"; c.font = "bold 22px system-ui,sans-serif"; c.fillText(total, cx, cy - 8);
                            c.fillStyle = "#9ca3af"; c.font = "11px system-ui,sans-serif"; c.fillText("subjects", cx, cy + 12);
                            c.restore();
                        }
                    }]
                });
            }
        }

        /* ── HEATMAP ── */
        _renderHeatmap(heatmap);
    }

    function _renderHeatmap(heatmap) {
        const container = getEl("heatmap-container");
        if (!container) return;

        const years    = heatmap.years    || [];
        const subjects = heatmap.subjects || [];
        const values   = heatmap.values   || [];

        if (!years.length || !subjects.length) {
            container.innerHTML = `<p class="text-muted small">No heatmap data available yet.</p>`;
            return;
        }

        const lookup = {};
        values.forEach(v => { lookup[`${v.y}||${v.x}`] = v.v; });

        function cellBg(v) {
            if (v === null || v === undefined) return "#f3f4f6";
            if (v >= 85) return "rgba(45,168,122,0.22)";
            if (v >= 70) return "rgba(91,141,238,0.18)";
            if (v >= 60) return "rgba(59,130,246,0.12)";
            if (v >= 50) return "rgba(247,193,7,0.22)";
            return "rgba(220,53,69,0.14)";
        }
        function cellColor(v) {
            if (v === null || v === undefined) return "#9ca3af";
            if (v >= 70) return "#166534";
            if (v >= 50) return "#854d0e";
            return "#991b1b";
        }

        const headerCells = years.map(y =>
            `<th class="text-center text-muted fw-semibold" style="font-size:11px;white-space:nowrap;min-width:72px;">${y}</th>`
        ).join("");

        const bodyRows = subjects.map(subj => {
            const cells = years.map(yr => {
                const val = lookup[`${subj}||${yr}`];
                const display = (val !== undefined && val !== null) ? val.toFixed(1) + "%" : "—";
                return `<td class="text-center fw-semibold" style="font-size:12px;background:${cellBg(val)};color:${cellColor(val)};padding:6px 8px;">${display}</td>`;
            }).join("");
            return `<tr><td class="fw-semibold text-muted" style="font-size:12px;white-space:nowrap;padding:6px 8px;">${subj}</td>${cells}</tr>`;
        }).join("");

        container.innerHTML = `
            <table class="table table-sm table-bordered align-middle mb-0" style="border-color:#e5e7eb;">
                <thead class="table-light">
                    <tr><th style="font-size:11px;min-width:110px;">Subject</th>${headerCells}</tr>
                </thead>
                <tbody>${bodyRows}</tbody>
            </table>
            <div class="d-flex flex-wrap gap-3 mt-2 align-items-center">
                <span style="font-size:10px;color:#6b7280;">Legend:</span>
                ${[
                    ["rgba(45,168,122,0.22)","#166534","≥ 85%"],
                    ["rgba(91,141,238,0.18)","#166534","70–84%"],
                    ["rgba(247,193,7,0.22)", "#854d0e","50–69%"],
                    ["rgba(220,53,69,0.14)", "#991b1b","< 50%"],
                    ["#f3f4f6",              "#9ca3af","No data"]
                ].map(([bg,fg,label]) =>
                    `<span class="d-flex align-items-center gap-1"><span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:${bg};border:1px solid #e5e7eb;"></span><span style="font-size:10px;color:${fg};">${label}</span></span>`
                ).join("")}
            </div>`;
    }

    /* ─────────────────────────────────────────
       ACHIEVEMENTS
    ───────────────────────────────────────── */

    function renderAchievements() {
        const achievements = (window.dashboardData || {}).achievements || [];
        const categories   = cfg().achievement_categories || [];
        const filterButtons = [
            `<button class="btn btn-primary btn-sm" onclick="HorizonsDash.filterAchievements('all', this)">All</button>`,
            ...categories.map(c => `<button class="btn btn-outline-secondary btn-sm" onclick="HorizonsDash.filterAchievements('${c.key}', this)">${c.label}</button>`)
        ].join("\n");
        const filterBar = `<div class="d-flex flex-wrap gap-2 align-items-center mb-3">${filterButtons}<button class="btn btn-outline-primary btn-sm ms-auto" onclick="HorizonsDash.openAddAchievementModal()">+ Add Achievement</button></div>`;
        const cardsHTML = achievements.length
            ? `<div class="row g-3" id="achievement-grid">${_achievementCards(achievements, categories)}</div>`
            : `<div id="achievement-grid"><p class="text-muted">No achievements recorded yet.</p></div>`;
        getEl("tab-content").innerHTML = filterBar + cardsHTML + _addAchievementModal(categories);
    }

    function _achievementCards(list, categories) {
        const iconMap = {}; (categories || []).forEach(c => { iconMap[c.key] = c.icon || "🏅"; });
        return list.map((a, i) => `
            <div class="col-12 col-md-6">
                <div class="card border-0 shadow-sm h-100" data-category="${a.category || ""}">
                    <div class="card-body d-flex align-items-start gap-3">
                        <div class="rounded-3 bg-primary bg-opacity-10 d-flex align-items-center justify-content-center flex-shrink-0" style="width:44px;height:44px;font-size:22px;">${iconMap[a.category] || "🏅"}</div>
                        <div class="flex-grow-1 min-w-0">
                            <div class="fw-semibold small">${a.title || "Achievement"}</div>
                            <div class="text-muted" style="font-size:12px;">${a.date || ""} · ${a.awarded_by || ""}</div>
                            ${a.description ? `<p class="small text-muted mt-1 mb-0">${a.description}</p>` : ""}
                        </div>
                        <div class="d-flex flex-column gap-1 flex-shrink-0">
                            <button class="btn btn-sm btn-outline-secondary px-2 py-1" onclick="HorizonsDash.previewCertificate(${i})" title="Preview">👁</button>
                            <button class="btn btn-sm btn-outline-secondary px-2 py-1" onclick="HorizonsDash.editAchievement(${i})" title="Edit">✏️</button>
                            <button class="btn btn-sm btn-outline-danger px-2 py-1" onclick="HorizonsDash.deleteAchievement(${i})" title="Delete">🗑</button>
                        </div>
                    </div>
                </div>
            </div>`).join("");
    }

    function filterAchievements(category, btn) {
        document.querySelectorAll("#tab-content .d-flex.flex-wrap button").forEach(function(b) {
            b.className = b.className.replace("btn-primary","btn-outline-secondary").replace("btn-outline-secondary btn-outline-secondary","btn-outline-secondary");
        });
        if (btn) btn.className = btn.className.replace("btn-outline-secondary","btn-primary");
        const grid = getEl("achievement-grid");
        if (!grid) return;
        grid.querySelectorAll("[data-category]").forEach(function(card) {
            card.closest(".col-12") && (card.closest(".col-12").style.display = category === "all" || card.dataset.category === category ? "" : "none");
        });
    }

    function openAddAchievementModal() { var modal = new bootstrap.Modal(getEl("add-achievement-modal")); modal.show(); }

    function _addAchievementModal(categories) {
        const options = (categories || []).map(c => `<option value="${c.key}">${c.label}</option>`).join("");
        return `
        <div class="modal fade" id="add-achievement-modal" tabindex="-1">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content border-0 shadow">
                    <div class="modal-header border-0 pb-0"><h6 class="modal-title fw-semibold">Add Achievement</h6><button type="button" class="btn-close" data-bs-dismiss="modal"></button></div>
                    <div class="modal-body">
                        <div class="mb-3"><label class="form-label fw-semibold small">Title</label><input type="text" class="form-control" id="ach-title" placeholder="Science Olympiad Winner"></div>
                        <div class="mb-3"><label class="form-label fw-semibold small">Category</label><select class="form-select" id="ach-category">${options}</select></div>
                        <div class="mb-3"><label class="form-label fw-semibold small">Date</label><input type="date" class="form-control" id="ach-date"></div>
                        <div class="mb-3"><label class="form-label fw-semibold small">Awarded By</label><input type="text" class="form-control" id="ach-awarded-by" placeholder="School / Organisation"></div>
                        <div class="mb-3"><label class="form-label fw-semibold small">Description</label><textarea class="form-control" id="ach-desc" rows="3" placeholder="Brief description…"></textarea></div>
                    </div>
                    <div class="modal-footer border-0 pt-0">
                        <button class="btn btn-sm btn-outline-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button class="btn btn-sm btn-primary px-4" onclick="HorizonsDash.saveAchievement()">Save</button>
                    </div>
                </div>
            </div>
        </div>`;
    }

    function saveAchievement() {
        const payload = { title: getEl("ach-title").value, category: getEl("ach-category").value, date: getEl("ach-date").value, awarded_by: getEl("ach-awarded-by").value, description: getEl("ach-desc").value };
        console.log("Save achievement:", payload);
        bootstrap.Modal.getInstance(getEl("add-achievement-modal")).hide();
        alert("Achievement saved! (wire up AJAX POST to your endpoint)");
    }

    function previewCertificate(idx) {
        const a = ((window.dashboardData || {}).achievements || [])[idx];
        if (!a) return;
        alert(`Certificate Preview:\n\n${a.title}\nAwarded to: ${(window.dashboardData.child || {}).first_name}\nDate: ${a.date}`);
    }

    function editAchievement(idx)   { alert(`Edit achievement #${idx} — implement form with AJAX PUT.`); }
    function deleteAchievement(idx) { if (!confirm("Delete this achievement?")) return; alert(`Delete achievement #${idx} — implement AJAX DELETE.`); }

    /* ─────────────────────────────────────────
       EXTRA HELP
    ───────────────────────────────────────── */

    function renderExtraHelp() {
        const subjects      = (window.dashboardData || {}).subject_wise_marks || [];
        const helpThreshold = cfg().extra_help_threshold ?? 60;
        const priorityBands = cfg().priority_bands       || [];
        const parentTips    = cfg().parent_action_tips   || [];
        const subjectTips   = cfg().subject_action_tips  || [];

        const weak = subjects.filter(s => s.percentage < helpThreshold).sort((a,b) => a.percentage - b.percentage);

        function priorityBadge(pct) {
            for (const band of priorityBands) { if (pct < band.max) return `<span class="badge ${band.badge_class}">${band.label}</span>`; }
            return `<span class="badge bg-secondary">Low</span>`;
        }

        const weakHTML = weak.length ? weak.map(s => `
            <div class="card border-0 shadow-sm mb-3">
                <div class="card-body">
                    <div class="d-flex align-items-start gap-3">
                        <div class="flex-shrink-0 mt-1">${priorityBadge(s.percentage)}</div>
                        <div class="flex-grow-1">
                            <div class="fw-semibold small mb-1">${s.subject_name}</div>
                            ${progressBar(s.percentage, "danger")}
                            <div class="text-muted mt-1 mb-2" style="font-size:12px;">${s.percentage}% — ${s.total_obtained}/${s.total_marks} marks</div>
                            ${subjectTips.length ? `<p class="small fw-semibold mb-1">Suggested Actions</p><ul class="list-unstyled mb-0">${subjectTips.map(t => `<li class="text-muted d-flex gap-1 mb-1" style="font-size:12px;"><span class="text-primary fw-bold">→</span>${t}</li>`).join("")}</ul>` : ""}
                        </div>
                    </div>
                </div>
            </div>`).join("") : `<div class="alert alert-success border-0">🎉 No critical areas — student is performing well!</div>`;

        const actionsHTML   = parentTips.map(a => `<div class="d-flex align-items-start gap-2 py-2 border-bottom"><span class="flex-shrink-0">${a.icon}</span><span class="small">${a.action}</span></div>`).join("");
        const statCounters  = priorityBands.map(band => {
            const count = subjects.filter(s => s.percentage < band.max && (priorityBands.indexOf(band) === 0 || s.percentage >= priorityBands[priorityBands.indexOf(band)-1].max)).length;
            return `<div class="col-${Math.floor(12/(priorityBands.length||3))}"><div class="card border-0 ${band.bg_class||"bg-secondary"} bg-opacity-10 py-2"><div class="fs-4 fw-bold ${band.text_class||"text-secondary"} text-center">${count}</div><div class="text-muted text-center" style="font-size:10px;">${band.label}</div></div></div>`;
        }).join("");
        const onTrack = subjects.filter(s => s.percentage >= helpThreshold).length;

        getEl("tab-content").innerHTML = `
            <div class="row g-3 align-items-start">
                <div class="col-12 col-lg-8">
                    <p class="text-uppercase fw-bold text-muted mb-3" style="font-size:11px;letter-spacing:.8px;">Subjects Needing Attention</p>
                    ${weakHTML}
                </div>
                <div class="col-12 col-lg-4">
                    ${parentTips.length ? `<div class="card border-0 shadow-sm mb-3"><div class="card-body"><p class="text-uppercase fw-bold text-muted mb-3" style="font-size:11px;letter-spacing:.8px;">Parent Action Plan</p>${actionsHTML}</div></div>` : ""}
                    <div class="card border-0 shadow-sm">
                        <div class="card-body">
                            <p class="text-uppercase fw-bold text-muted mb-3" style="font-size:11px;letter-spacing:.8px;">Quick Stats</p>
                            <div class="row g-2 text-center">
                                ${statCounters}
                                <div class="col-${Math.floor(12/((priorityBands.length||2)+1))}">
                                    <div class="card border-0 bg-success bg-opacity-10 py-2">
                                        <div class="fs-4 fw-bold text-success text-center">${onTrack}</div>
                                        <div class="text-muted text-center" style="font-size:10px;">On Track</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>`;
    }

    /* ─────────────────────────────────────────
       INIT
    ───────────────────────────────────────── */

    function init() {
        document.querySelectorAll(".dashboard-tab").forEach(function(tab) { tab.classList.remove("active"); });
        var overviewTab = document.querySelector('.dashboard-tab[data-tab="overview"]');
        if (overviewTab) overviewTab.classList.add("active");
        renderOverview();
    }

    return { showTab, showSubjectTab, renderExamSelector, filterAchievements, openAddAchievementModal, saveAchievement, previewCertificate, editAchievement, deleteAchievement, init };

})();

document.addEventListener("DOMContentLoaded", HorizonsDash.init);