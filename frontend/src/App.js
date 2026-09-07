// Copyright (c) 2026 chandankumardv22
import React, { Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';
import { Activity, AlertTriangle, ArrowUpRight, Award, BrainCircuit, BriefcaseBusiness, Check, ChevronRight, Cpu, Crosshair, Download, FileSearch, Gauge, Loader2, Moon, Radar, ShieldCheck, Sparkles, Sun, Target, TrendingUp, Upload, Zap } from 'lucide-react';
import './App.css';

const LazyLiveJobOpenings = React.lazy(() => import('./LiveJobOpenings'));

const api = (process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const errorMessage = (error) => error.response?.data?.error || error.response?.data?.detail || error.message || 'Analysis could not be completed.';

async function downloadCareerReport(data) {
  const [{ jsPDF }, autoTableModule] = await Promise.all([
    import('jspdf'),
    import('jspdf-autotable'),
  ]);
  const autoTable = autoTableModule.default ?? autoTableModule;
  const doc = new jsPDF({ unit: 'pt', format: 'a4' });
  const scorecard = data.scorecard || { overall: data.ats_score || 0, sections: {}, evidence: [] };
  const intelligence = data.career_intelligence || {};
  const margin = 42; const width = doc.internal.pageSize.getWidth() - margin * 2;
  let y = 52;
  const addHeader = () => { doc.setFillColor(16, 20, 29); doc.rect(0, 0, doc.internal.pageSize.getWidth(), 28, 'F'); doc.setTextColor(255, 255, 255); doc.setFont('helvetica', 'bold'); doc.setFontSize(9); doc.text('RESUMENAVIGATOR  /  CAREER INTELLIGENCE REPORT', margin, 18); doc.setTextColor(16, 20, 29); };
  const addTitle = (title, subtitle = '') => { if (y > 700) { doc.addPage(); addHeader(); y = 54; } doc.setFont('helvetica', 'bold'); doc.setFontSize(16); doc.setTextColor(16, 20, 29); doc.text(title, margin, y); y += 17; if (subtitle) { doc.setFont('helvetica', 'normal'); doc.setFontSize(9); doc.setTextColor(92, 99, 112); const lines = doc.splitTextToSize(subtitle, width); doc.text(lines, margin, y); y += lines.length * 12 + 9; } };
  const table = (head, body, columnStyles = {}) => { autoTable(doc, { startY: y, margin: { left: margin, right: margin }, head: [head], body, styles: { font: 'helvetica', fontSize: 8, cellPadding: 6, textColor: [40, 44, 54], overflow: 'linebreak' }, headStyles: { fillColor: [108, 91, 218], textColor: 255, fontStyle: 'bold' }, alternateRowStyles: { fillColor: [247, 246, 252] }, columnStyles, didDrawCell: (hook) => { if (hook.section === 'body' && hook.column.index === 4) { const url = String(hook.cell.raw || ''); if (url.startsWith('http')) doc.link(hook.cell.x, hook.cell.y, hook.cell.width, hook.cell.height, { url }); } }, didDrawPage: () => addHeader() }); y = doc.lastAutoTable.finalY + 22; };
  const jobs = Object.entries(data.jobs_by_role || {}).flatMap(([role, list]) => (list || []).map(job => [role, job.job_title || job.title || 'Open role', job.company_name || job.employer_name || 'Hiring company', job.location || 'India', job.redirect_url || job.job_apply_link || '']));
  addHeader();
  doc.setFont('helvetica', 'bold'); doc.setFontSize(27); doc.text('Career Intelligence', margin, y); y += 30; doc.setTextColor(108, 91, 218); doc.text('REPORT', margin, y); y += 28; doc.setTextColor(16, 20, 29); doc.setFontSize(11); doc.setFont('helvetica', 'normal'); doc.text(`${data.candidate_name || 'Candidate'}  |  ${data.detected_domain || 'Career profile'}  |  ${new Date().toLocaleDateString()}`, margin, y); y += 35;
  table(['Overall ATS readiness', 'Target role', 'Recommended roles'], [[`${scorecard.overall}/100`, data.predicted_role || 'Not identified', (data.recommended_roles || []).join(', ') || 'Not identified']]);
  addTitle('Profile and analysis summary', data.career_suggestions || data.custom_suggestion || 'No narrative summary was generated.');
  table(['Candidate', 'Email', 'College'], [[data.candidate_name || 'Not found', data.candidate_email || 'Not found', data.candidate_college || 'Not found']]);
  addTitle('Explainability', 'Each score below is produced from evidence detected in the uploaded resume.');
  table(['Score dimension', 'Score'], Object.entries(scorecard.sections || {}).map(([name, value]) => [name, `${value}/100`]));
  table(['Evidence'], (scorecard.evidence || []).map(item => [item]));
  if (scorecard.recruiter_readiness != null) { addTitle('Recruiter readiness signals', 'Derived from the weighted ATS rubric. These are readiness indicators, not hiring guarantees.'); table(['Signal', 'Value'], [['Confidence', `${scorecard.confidence?.value ?? scorecard.confidence ?? '—'}%`], ['Recruiter readiness', `${scorecard.recruiter_readiness}%`], ['Interview probability', `${scorecard.interview_probability}%`], ['Hiring confidence', `${scorecard.hiring_confidence}%`]]); }
  if ((scorecard.weak_areas || []).length) { addTitle('Weak areas & prioritized fixes', 'Ordered by impact on your ATS score.'); table(['Area', 'Score', 'Problem', 'Recommendation', 'Est. gain'], scorecard.weak_areas.map(w => [w.area, `${w.score}/100`, w.problem, w.recommendation, w.expected_ats_gain || '']), { 2: { cellWidth: 120 }, 3: { cellWidth: 130 } }); }
  addTitle('Capability map', 'Strengths are extracted from your resume. Growth edges are role-profile gaps identified from the same analysis.');
  table(['Confirmed strengths', 'Priority growth edges'], [[(data.matched_skills || []).join(', ') || 'None reliably extracted', (data.missing_skills || []).join(', ') || 'No major gaps identified']]);
  addTitle('Growth simulator', 'A practical, resume-aligned 90-day progression.');
  table(['Step', 'Focus', 'Project or proof point'], (data.learning_roadmap || []).map(step => [step.title || `Step ${step.step}`, step.focus || '', step.project_idea || '']));
  if (intelligence.recruiter_simulation) { addTitle('Recruiter simulation', intelligence.recruiter_simulation.summary || ''); table(['Resume section', 'Attention', 'Reason'], (intelligence.recruiter_simulation.attention_map || []).map(item => [item.section, item.attention, item.reason])); }
  if (intelligence.career_dna) { addTitle('Career evidence signals', intelligence.career_dna.note || ''); table(['Signal', 'Evidence score'], [['Leadership', `${intelligence.career_dna.leadership_signal}/100`], ['Innovation', `${intelligence.career_dna.innovation_signal}/100`], ['Communication', `${intelligence.career_dna.communication_signal}/100`], ['Learning', `${intelligence.career_dna.learning_signal}/100`]]); }
  if ((intelligence.interview_predictor || []).length) { addTitle('Interview preparation', 'Questions are generated from detected skills and resume evidence.'); table(['Type', 'Question', 'Why it matters'], intelligence.interview_predictor.map(item => [item.type, item.question, item.why])); }
  if ((intelligence.resume_timeline || []).length) { addTitle('Resume timeline'); table(['Year', 'Extracted event'], intelligence.resume_timeline.map(item => [item.year, item.event])); }
  addTitle('Job opportunities and application links', 'Listings are queried with the role and skills detected in this resume. Select any URL below to apply.');
  if (jobs.length) { table(['Role', 'Job title', 'Company', 'Location', 'Apply URL'], jobs, { 4: { cellWidth: 130, textColor: [79, 70, 229] } }); } else { table(['Status'], [['No verified provider listings were available at report time. Use the skill-specific LinkedIn, Naukri, and Indeed searches in the dashboard.']]); }
  const pageCount = doc.internal.getNumberOfPages();
  for (let page = 1; page <= pageCount; page += 1) { doc.setPage(page); doc.setFont('helvetica', 'normal'); doc.setFontSize(8); doc.setTextColor(110, 114, 126); doc.text(`ResumeNavigator - confidential career intelligence report - page ${page} of ${pageCount}`, margin, doc.internal.pageSize.getHeight() - 24); }
  doc.save('ResumeNavigator-Career-Intelligence-Report.pdf');
}

function ScoreRing({ score }) {
  const radius = 62; const length = 2 * Math.PI * radius;
  return <div className="score-ring"><svg viewBox="0 0 144 144"><circle className="ring-track" cx="72" cy="72" r={radius}/><circle className="ring-value" cx="72" cy="72" r={radius} style={{ strokeDasharray: length, strokeDashoffset: length * (1 - score / 100) }}/></svg><div><strong>{score}</strong><span>/100</span><p>ATS readiness</p></div></div>;
}

function UploadPanel({ file, setFile, loading, analyze, jobDescription, setJobDescription }) {
  const onDrop = useCallback((accepted) => accepted[0] && setFile(accepted[0]), [setFile]);
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    },
    maxFiles: 1,
    disabled: loading,
  });
  return (
    <section className="upload-panel upload-panel--smart" id="analyze">
      <div {...getRootProps()} className={`dropzone ${isDragActive ? 'active' : ''} ${file ? 'ready' : ''}`}>
        <input {...getInputProps()} />
        <div className="drop-icon"><Upload size={24} /></div>
        <div>
          <strong>{file ? file.name : 'Drop your resume here'}</strong>
          <p>{file ? `${Math.ceil(file.size / 1024)} KB · ready to scan` : 'PDF or Word (.docx) · NLP parsing + ML pipeline'}</p>
        </div>
        <ChevronRight className="drop-arrow" />
      </div>
      <textarea
        className="jd-input"
        placeholder="Optional: paste a job description for Sentence-Transformer cosine matching…"
        value={jobDescription}
        onChange={(e) => setJobDescription(e.target.value)}
        rows={3}
        disabled={loading}
      />
      <button className="primary-button" disabled={!file || loading} onClick={analyze}>
        {loading ? <><Loader2 className="spin" size={18} /> Running full pipeline</> : <><Sparkles size={18} /> Analyze my resume</>}
      </button>
    </section>
  );
}

function CareerAnalysisAnimation() {
  const stages = [
    ['Resume scan', FileSearch],
    ['Skill signals', Sparkles],
    ['Role alignment', Target],
    ['Opportunity map', BriefcaseBusiness],
  ];
  // Adjusted animation delay for faster feedback
const animationDelay = 0.1; // seconds per stage
  return <section className="career-loading" role="status" aria-live="polite">
    <div className="career-loading__intro">
      <span className="eyebrow"><BrainCircuit size={14}/> Career intelligence at work</span>
      <h2>Mapping your next move</h2>
      <p>We’re reading your resume for concrete evidence—not generating a generic report.</p>
    </div>
    <div className="career-orbit">
      <div className="career-orbit__ring ring-one"/>
      <div className="career-orbit__ring ring-two"/>
      <div className="career-orbit__core"><FileSearch size={28}/><span>Resume</span></div>
      {stages.map(([label, Icon], index) => (
        <div className={`career-orbit__node node-${index + 1}`} key={label} style={{ animationDelay: `${index * animationDelay}s` }}>
          <Icon size={17}/><span>{label}</span>
        </div>
      ))}
    </div>
    <div className="career-loading__steps">
      {stages.map(([label, Icon], index) => (
        <div key={label} style={{ animationDelay: `${index * animationDelay}s` }}>
          <span><Icon size={14}/>{label}</span>
        </div>
      ))}
    </div>
    {/* Add a spinner for quick visual feedback */}
    <div className="loading-spinner"><Loader2 className="spin" size={32}/></div>
  </section>;
}

function RoleExplorer({ resumeText }) {
  const [role, setRole] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const analyze = async () => {
    if (!role.trim() || !resumeText) return;
    setLoading(true); setError(''); setResult(null);
    try {
      const resp = await axios.post(`${api}/api/role-analysis`, { resume_text: resumeText, target_role: role.trim() }, { timeout: 90000 });
      if (resp.data.error) throw new Error(resp.data.error);
      setResult(resp.data);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e) => { if (e.key === 'Enter') analyze(); };
  const pct = result?.role_match_percentage ?? 0;
  const radius = 52; const circumference = 2 * Math.PI * radius;

  return <section className="panel role-explorer" id="role-explorer">
    <div className="section-title"><div><span className="label">Role explorer</span><h3>Analyze for your dream role</h3></div><Crosshair size={20}/></div>
    <p className="role-explorer__subtitle">Enter any job role below and we'll show exactly which skills you already have, what's missing, and a tailored plan to get there.</p>
    <div className="role-input-group">
      <input type="text" value={role} onChange={e => setRole(e.target.value)} onKeyDown={handleKey} placeholder="e.g., Data Scientist, DevOps Engineer, Financial Analyst..." className="role-input" disabled={loading}/>
      <button className="role-analyze-btn" disabled={!role.trim() || loading} onClick={analyze}>{loading ? <><Loader2 className="spin" size={16}/> Analyzing</> : <><Target size={16}/> Analyze for this role</>}</button>
    </div>
    {error && <div className="role-error">{error}</div>}
    {result && !result.error && <div className="role-results">
      <div className="role-results__header">
        <div className="role-match-ring">
          <svg viewBox="0 0 120 120"><circle className="ring-track" cx="60" cy="60" r={radius}/><circle className="ring-value" cx="60" cy="60" r={radius} style={{ strokeDasharray: circumference, strokeDashoffset: circumference * (1 - pct / 100) }}/></svg>
          <div><strong>{pct}%</strong><span>match</span></div>
        </div>
        <div className="role-match-info">
          <span className="label">Matched role profile</span>
          <h4>{result.matched_role}</h4>
          <p className="role-match-domain">{result.domain}</p>
          <p className="role-match-core">{result.core_skills_matched}/{result.core_skills_total} core skills matched</p>
        </div>
      </div>
      <div className="role-skills-grid">
        <div className="role-skill-col">
          <p><Check size={15}/> Skills you have</p>
          <div className="chips">{result.skills_you_have.length ? result.skills_you_have.map(s => <span className="good" key={s}>{s}</span>) : <em>None matched</em>}</div>
        </div>
        <div className="role-skill-col">
          <p><Target size={15}/> Skills you need</p>
          <div className="chips">{result.skills_you_need.length ? result.skills_you_need.map(s => <span className="gap" key={s}>{s}</span>) : <em>You're fully covered!</em>}</div>
        </div>
      </div>
      <div className="role-recommendation"><BrainCircuit size={18}/><p>{result.recommendation}</p></div>
      <div className="role-roadmap">
        <h4><Zap size={16}/> Your path to {result.matched_role}</h4>
        <div className="roadmap-grid">{(result.learning_roadmap || []).map(step => <article key={step.step}><span>{String(step.step).padStart(2, '0')}</span><h4>{step.title}</h4><p>{step.focus}</p><small>{step.project_idea}</small></article>)}</div>
      </div>
      {(result.jobs_by_role || result.jobs_count > 0 || result.portal_searches) && (
        <Suspense fallback={<div className="panel live-jobs-panel"><p>Loading job opportunities…</p></div>}>
          <LazyLiveJobOpenings
            recommendedRoles={[result.matched_role]}
            matchedSkills={result.skills_you_have || result.job_search_skills || []}
            jobsByRole={result.jobs_by_role}
            jobsMessage={result.jobs_message || `Direct-apply openings for ${result.matched_role} in your resume city.`}
            jobsCount={result.jobs_count}
            candidateLocation={result.candidate_location}
            portalSearches={result.portal_searches}
            allowRefresh
          />
        </Suspense>
      )}
    </div>}
    {result?.error && <div className="role-error">{result.error}</div>}
  </section>;
}

const RADAR_LABELS = { 'Resume Structure': 'Structure', 'Skill Match': 'Skills', Experience: 'Experience', Projects: 'Projects', Education: 'Education', Formatting: 'Format', Achievements: 'Impact', Grammar: 'Grammar' };

function SkillRadar({ sections }) {
  const entries = Object.entries(sections || {});
  if (!entries.length) return null;
  const size = 260; const c = size / 2; const rMax = c - 44; const n = entries.length;
  const angle = (i) => (Math.PI * 2 * i) / n - Math.PI / 2;
  const point = (val, i, r = rMax) => [c + Math.cos(angle(i)) * r * (val / 100), c + Math.sin(angle(i)) * r * (val / 100)];
  const rings = [25, 50, 75, 100];
  const poly = entries.map(([, v], i) => point(v, i).join(',')).join(' ');
  return (
    <div className="radar-wrap">
      <svg viewBox={`0 0 ${size} ${size}`} className="radar-svg">
        {rings.map(r => <polygon key={r} className="radar-ring" points={entries.map((_, i) => point(r, i).join(',')).join(' ')} />)}
        {entries.map((_e, i) => { const [x, y] = point(100, i); return <line key={i} className="radar-axis" x1={c} y1={c} x2={x} y2={y} />; })}
        <polygon className="radar-area" points={poly} />
        {entries.map(([, v], i) => { const [x, y] = point(v, i); return <circle key={i} className="radar-dot" cx={x} cy={y} r={3} />; })}
        {entries.map(([name], i) => { const [x, y] = point(118, i); return <text key={name} className="radar-label" x={x} y={y} textAnchor="middle" dominantBaseline="middle">{RADAR_LABELS[name] || name}</text>; })}
      </svg>
    </div>
  );
}

function SignalStrip({ scorecard }) {
  const conf = scorecard.confidence?.value ?? scorecard.confidence ?? null;
  const stats = [
    { label: 'Confidence', value: conf, suffix: '%', icon: ShieldCheck, hint: scorecard.confidence?.basis || 'Model certainty in this analysis.' },
    { label: 'Recruiter readiness', value: scorecard.recruiter_readiness, suffix: '%', icon: Gauge, hint: 'How screen-ready the resume looks to a recruiter.' },
    { label: 'Interview probability', value: scorecard.interview_probability, suffix: '%', icon: TrendingUp, hint: 'Estimated shortlist likelihood from resume signals.' },
    { label: 'Hiring confidence', value: scorecard.hiring_confidence, suffix: '%', icon: Award, hint: 'Blended strength indicator — not a guarantee.' },
  ].filter(s => s.value != null);
  if (!stats.length) return null;
  return <div className="signal-strip">{stats.map(({ label, value, suffix, icon: Icon, hint }) => (
    <article className="signal-card panel" key={label} title={hint}>
      <div className="signal-card__top"><Icon size={16} /><span>{label}</span></div>
      <b>{value}<small>{suffix}</small></b>
      <div className="mini-bar"><i style={{ width: `${Math.min(100, value)}%` }} /></div>
    </article>
  ))}</div>;
}

function WeakAreasPanel({ weakAreas }) {
  if (!weakAreas?.length) return null;
  return (
    <article className="panel weak-card">
      <div className="section-title"><div><span className="label">Growth edges</span><h3>Weak areas & fixes</h3></div><AlertTriangle size={20} /></div>
      <div className="weak-list">{weakAreas.map((w) => (
        <div className={`weak-item ${w.priority}`} key={w.area}>
          <div className="weak-item__head"><strong>{w.area}</strong><span className="weak-score">{w.score}/100</span><span className={`prio prio--${w.priority}`}>{w.priority}</span></div>
          <p className="weak-problem">{w.problem}</p>
          <p className="weak-rec"><Check size={13} /> {w.recommendation}</p>
          {w.expected_ats_gain && <span className="weak-gain">{w.expected_ats_gain}</span>}
        </div>
      ))}</div>
    </article>
  );
}

const ALGORITHM_CATALOG = [
  {
    id: 'nlp',
    name: 'Natural Language Processing (NLP)',
    phase: 'Parsing',
    summary: 'Extracts text from PDF/DOCX, cleans it, and pulls skills, degrees, and years of experience with rules and regex.',
  },
  {
    id: 'tfidf',
    name: 'TF-IDF',
    phase: 'Feature extraction',
    summary: 'Turns resume skills and phrases into numerical vectors so the classifier can score career fit.',
  },
  {
    id: 'logistic_regression',
    name: 'Logistic Regression',
    phase: 'Role classification',
    summary: 'Predicts target roles such as Machine Learning Engineer, Data Analyst, Full Stack Developer, or DevOps Engineer.',
  },
  {
    id: 'sentence_transformers_cosine',
    name: 'Sentence Transformers & Cosine Similarity',
    phase: 'Semantic matching',
    summary: 'Embeds resume and job text, then uses cosine similarity for match scores and skill-gap analysis.',
  },
  {
    id: 'gemini_llm',
    name: 'Generative AI (Gemini LLM)',
    phase: 'Intelligence',
    summary: 'Validates uploads with gemini-2.5-flash, checks role realism, and builds personalized roadmap JSON.',
  },
];

function AlgorithmsPanel({ algorithmsUsed, liveStatus }) {
  // Always present the full academic stack. "Active" = used in last analysis or known available.
  const statusById = {
    nlp: algorithmsUsed?.nlp_parsing?.used ?? liveStatus?.nlp_parsing ?? true,
    tfidf: algorithmsUsed?.tfidf?.used ?? liveStatus?.tfidf ?? true,
    logistic_regression: algorithmsUsed?.logistic_regression?.used ?? liveStatus?.logistic_regression ?? true,
    sentence_transformers_cosine: algorithmsUsed?.sentence_transformers_cosine?.used ?? liveStatus?.sentence_transformers_cosine ?? false,
    gemini_llm: algorithmsUsed?.gemini_llm?.used ?? liveStatus?.gemini_llm ?? false,
  };

  return (
    <section className="panel algorithms-panel" id="algorithms">
      <div className="section-title">
        <div>
          <span className="label">Algorithm stack</span>
          <h3>Five engines powering every analysis</h3>
        </div>
        <Cpu size={20} />
      </div>
      <p className="algorithms-panel__intro">
        Every analysis runs <strong>NLP parsing</strong>, <strong>TF-IDF</strong>, <strong>Logistic Regression</strong>,
        <strong> Sentence Transformers + Cosine Similarity</strong>, and <strong>Gemini 2.5 Flash</strong> —
        not mock scores. Upload a resume to see live Active status on each card.
      </p>
      <div className="algorithms-grid">
        {ALGORITHM_CATALOG.map((algo, index) => {
          const active = statusById[algo.id];
          return (
            <article key={algo.id} className={`algorithm-card ${active ? 'is-active' : ''}`}>
              <header>
                <span className="algorithm-card__index">{String(index + 1).padStart(2, '0')}</span>
                <span className={`algorithm-card__status ${active ? 'on' : 'off'}`}>{active ? 'In pipeline' : 'Optional / setup'}</span>
              </header>
              <h4>{algo.name}</h4>
              <p className="algorithm-card__phase">{algo.phase}</p>
              <p>{algo.summary}</p>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function InsightDashboard({ data }) {
  const scorecard = data.scorecard || { overall: data.ats_score || 0, sections: {}, evidence: [] };
  const breakdown = data.ats_analysis?.score_breakdown || scorecard.pipeline_breakdown || {};
  const sections = Object.entries(scorecard.sections || {});
  const strengths = (data.strengths?.length ? data.strengths : data.matched_skills || []).slice(0, 10);
  const gaps = (data.missing_skills || []).slice(0, 8);
  const engine = scorecard.engine || data.nlp_engine || {};
  const semanticOn = Boolean(data.semantic_analysis?.available || engine.embeddings);
  const algorithms = data.algorithms_used || {};
  const resume = data.resume || {};
  const rolePred = data.role_prediction || data.ml_role_prediction || {};
  const semanticScore = data.semantic_match_score ?? data.semantic_analysis?.semantic_match_score;
  const ats = data.ats_score ?? scorecard.overall ?? 0;
  const verdict = ats >= 75 ? 'Strong screening foundation' : ats >= 55 ? 'Promising, with targeted gaps' : 'Needs sharper positioning';

  return (
    <section className="dashboard" id="dashboard">
      <div className="dash-heading">
        <div>
          <p className="eyebrow">Smart Resume Analyzer</p>
          <h2>{data.candidate_name || resume.name || 'Your'}’s opportunity map</h2>
          <p>
            {data.detected_domain}
            {data.years_of_experience != null ? <> · <b>{data.years_of_experience}y</b> experience</> : null}
            {(data.academic_degrees || []).length ? <> · {(data.academic_degrees || []).slice(0, 2).join(', ')}</> : null}
          </p>
        </div>
        <div className="dash-actions">
          <span className="engine-badge"><Cpu size={13} /> {semanticOn ? 'ST + Cosine on' : 'ST standby'}</span>
          <button className="report-button" onClick={() => downloadCareerReport(data)}><Download size={15} /> Download full report</button>
          <span className="status-pill"><Activity size={14} /> Analysis complete</span>
        </div>
      </div>

      <AlgorithmsPanel algorithmsUsed={algorithms} />

      <div className="smart-kpi-grid">
        <article className="panel smart-kpi"><span className="label">ATS score</span><b>{ats}<small>/100</small></b></article>
        <article className="panel smart-kpi"><span className="label">Predicted role (TF-IDF + LR)</span><b>{data.predicted_role || '—'}</b><small>{rolePred.confidence != null ? `${rolePred.confidence <= 1 ? Math.round(rolePred.confidence * 100) : rolePred.confidence}% conf.` : ''}</small></article>
        <article className="panel smart-kpi"><span className="label">Realistic target (Gemini)</span><b>{data.realistic_role || data.predicted_role || '—'}</b></article>
        <article className="panel smart-kpi"><span className="label">Semantic job match</span><b>{semanticScore != null ? `${semanticScore}%` : '—'}</b><small>Cosine similarity</small></article>
      </div>

      <div className="hero-grid">
        <article className="score-card panel">
          <ScoreRing score={ats} />
          <div className="score-copy">
            <span className="label">Recruiter signal</span>
            <h3>{verdict}</h3>
            <p>{data.career_suggestions || data.custom_suggestion}</p>
            <a href="#evidence">See score evidence <ArrowUpRight size={15} /></a>
          </div>
        </article>
        <article className="summary-card panel">
          <div className="card-top"><span className="icon-wrap purple"><BrainCircuit size={20} /></span><span className="label">Resume preview (NLP)</span></div>
          <p><b>{resume.name || data.candidate_name}</b> · {resume.email || data.candidate_email}</p>
          <p className="ml-role-note">{resume.phone || data.candidate_phone} · {data.years_of_experience || 0} years experience</p>
          <div className="chips">{(resume.skills || data.matched_skills || []).slice(0, 8).map((x) => <span className="good" key={x}>{x}</span>)}</div>
          {(rolePred.alternative_roles || rolePred.top_roles || []).length > 0 && (
            <p className="ml-role-note">Alternatives: {(rolePred.alternative_roles || rolePred.top_roles).map((a) => a.role || a).join(', ')}</p>
          )}
        </article>
      </div>

      {Object.keys(breakdown).length > 0 && (
        <section className="panel roadmap" id="ats-breakdown">
          <div className="section-title"><div><span className="label">ATS breakdown</span><h3>Deterministic score components</h3></div><Gauge size={20} /></div>
          <div className="metrics-grid">{Object.entries(breakdown).map(([name, value], i) => (
            <article className="metric panel" key={name}>
              <div><span>{name.replace(/_/g, ' ')}</span><b>{value}<small>/100</small></b></div>
              <div className="bar"><i style={{ width: `${value}%`, transitionDelay: `${i * 60}ms` }} /></div>
            </article>
          ))}</div>
        </section>
      )}

      <SignalStrip scorecard={scorecard} />
      {sections.length > 0 && (
        <div className="metrics-grid">{sections.map(([name, value], i) => (
          <article className="metric panel" key={name}>
            <div><span>{name}</span><b>{value}<small>/100</small></b></div>
            <div className="bar"><i style={{ width: `${value}%`, transitionDelay: `${i * 80}ms` }} /></div>
          </article>
        ))}</div>
      )}

      <div className="intel-grid">
        <article className="panel skills-card">
          <div className="section-title"><div><span className="label">Skill gap analysis</span><h3>Matched vs missing</h3></div><Target size={20} /></div>
          <div className="skill-group"><p><Check size={15} /> Matched skills</p><div className="chips">{strengths.length ? strengths.map((x) => <span className="good" key={x}>{x}</span>) : <em>None yet</em>}</div></div>
          <div className="skill-group"><p><Target size={15} /> Missing skills</p><div className="chips">{gaps.length ? gaps.map((x) => <span className="gap" key={x}>{x}</span>) : <em>No major gaps</em>}</div></div>
          {(data.weaknesses || []).length > 0 && <div className="skill-group"><p>Weaknesses</p><ul>{data.weaknesses.slice(0, 5).map((w) => <li key={w}>{w}</li>)}</ul></div>}
        </article>
        <article className="panel evidence-card" id="evidence">
          <div className="section-title"><div><span className="label">Improvements</span><h3>Resume suggestions</h3></div><Gauge size={20} /></div>
          <ol>{(data.resume_improvements || scorecard.evidence || []).slice(0, 8).map((item, i) => (
            <li key={item}><b>{String(i + 1).padStart(2, '0')}</b><span>{item}</span></li>
          ))}</ol>
        </article>
      </div>

      <section className="panel roadmap">
        <div className="section-title"><div><span className="label">Learning roadmap</span><h3>Gemini personalized plan</h3></div><Zap size={20} /></div>
        <div className="roadmap-grid">{(data.learning_roadmap || []).map((step) => (
          <article key={step.step || step.phase}>
            <span>{String(step.step || step.phase || '').toString().padStart(2, '0')}</span>
            <h4>{step.title}</h4>
            <p>{step.focus || (step.skills || []).join(', ')}</p>
            <small>{step.project_idea || (step.projects || []).join('; ') || step.duration}</small>
          </article>
        ))}</div>
      </section>

      {(data.career_milestones || []).length > 0 && (
        <section className="panel roadmap">
          <div className="section-title"><div><span className="label">Career milestones</span><h3>Next targets</h3></div><Award size={20} /></div>
          <div className="roadmap-grid">{data.career_milestones.map((m) => (
            <article key={m.milestone}>
              <span>{m.target}</span>
              <h4>{m.milestone}</h4>
              <p>{(m.skills_required || []).join(', ')}</p>
            </article>
          ))}</div>
        </section>
      )}

      <div className="radar-grid">
        <article className="panel radar-card">
          <div className="section-title"><div><span className="label">Dimension radar</span><h3>Balanced profile view</h3></div><Radar size={20} /></div>
          <SkillRadar sections={scorecard.sections} />
        </article>
        <WeakAreasPanel weakAreas={scorecard.weak_areas} />
      </div>

      <Suspense fallback={<div className="panel live-jobs-panel"><p>Loading job opportunities…</p></div>}>
        <LazyLiveJobOpenings
          recommendedRoles={data.recommended_roles}
          matchedSkills={data.job_search_skills || data.matched_skills}
          jobsByRole={data.jobs_by_role}
          jobsMessage={data.jobs_message}
          jobsCount={data.jobs_count}
          candidateName={data.candidate_name}
          candidateEmail={data.candidate_email}
          candidateLocation={data.candidate_location}
          portalSearches={data.portal_searches}
        />
      </Suspense>
      {data.resume_text && <RoleExplorer resumeText={data.resume_text} />}
    </section>
  );
}

export default function App() {
  const [file, setFile] = useState(null);
  const [jobDescription, setJobDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [theme, setTheme] = useState(() => (typeof window !== 'undefined' && localStorage.getItem('rn-theme')) || 'light');
  const [algoStatus, setAlgoStatus] = useState(null);
  useEffect(() => { document.documentElement.setAttribute('data-theme', theme); try { localStorage.setItem('rn-theme', theme); } catch { /* ignore */ } }, [theme]);
  useEffect(() => {
    axios.get(`${api}/api/algorithms`, { timeout: 8000 }).then((resp) => {
      const map = {};
      (resp.data.algorithms || []).forEach((item) => { map[item.id] = item.used; });
      setAlgoStatus({
        nlp_parsing: map.nlp,
        tfidf: map.tfidf,
        logistic_regression: map.logistic_regression,
        sentence_transformers_cosine: map.sentence_transformers_cosine,
        gemini_llm: map.gemini_llm,
      });
    }).catch(() => {});
  }, []);
  const toggleTheme = () => setTheme((t) => (t === 'light' ? 'dark' : 'light'));
  const analyze = async () => {
    if (!file) return;
    setLoading(true); setError(''); setResult(null);
    try {
      const form = new FormData();
      form.append('file', file);
      if (jobDescription.trim()) form.append('job_description', jobDescription.trim());
      const response = await axios.post(`${api}/api/analyze-resume`, form, { timeout: 180000 });
      if (response.data.error) throw new Error(response.data.error);
      setResult(response.data);
      setTimeout(() => document.querySelector('#dashboard')?.scrollIntoView({ behavior: 'smooth' }), 80);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setLoading(false);
    }
  };
  const jobCount = useMemo(() => result?.jobs_count || 0, [result]);
  return (
    <div className="app-shell">
      <div className="ambient ambient-one" /><div className="ambient ambient-two" />
      <header>
        <a className="brand" href="#top"><span>◈</span> ResumeNavigator</a>
        <nav>
          <a href="#analyze">Analyzer</a>
          <a href="#algorithms">Algorithms</a>
          <a href="#dashboard">Intelligence</a>
          <a href="#live-jobs">Opportunities</a>
        </nav>
        <div className="header-actions">
          <button className="theme-toggle" onClick={toggleTheme} aria-label="Toggle dark mode">{theme === 'light' ? <Moon size={16} /> : <Sun size={16} />}</button>
          <button className="quiet-button" onClick={() => document.querySelector('#analyze')?.scrollIntoView({ behavior: 'smooth' })}>Start analysis <ArrowUpRight size={15} /></button>
        </div>
      </header>
      <main id="top">
        <section className="hero">
          <div className="hero-copy">
            <p className="eyebrow"><Sparkles size={14} /> Smart Resume Analyzer & Job Recommendation</p>
            <h1>Make your next<br /><em>choice</em> undeniable.</h1>
            <p className="hero-text">NLP parsing → TF-IDF + Logistic Regression → Sentence Transformers + Cosine Similarity → Gemini 2.5 Flash. Real models, real scores, local job apply links.</p>
            <div className="trust-row"><span><b>5</b> algorithms</span><i /><span><b>Explainable</b> ATS</span><i /><span><b>{jobCount || 'Live'}</b> openings</span></div>
          </div>
          <div className="orbital">
            <div className="orbital-card card-a"><span>ATS signal</span><b>{result?.ats_score ?? '—'}</b><small>/100</small></div>
            <div className="orbital-card card-b"><BrainCircuit size={22} /><span>Semantic match</span><small>{result?.semantic_match_score != null ? `${result.semantic_match_score}%` : 'Cosine'}</small></div>
            <div className="core-orb"><Sparkles size={32} /></div>
          </div>
        </section>
        <UploadPanel file={file} setFile={setFile} loading={loading} analyze={analyze} jobDescription={jobDescription} setJobDescription={setJobDescription} />
        {error && <div className="error-box">{error}</div>}
        {loading && <CareerAnalysisAnimation />}
        {!result && <div className="pre-algo-wrap"><AlgorithmsPanel liveStatus={algoStatus} /></div>}
        {result && <InsightDashboard data={result} />}
      </main>
      <footer><span>ResumeNavigator Smart Analyzer</span><span>NLP · TF-IDF · Logistic Regression · Cosine · Gemini</span></footer>
    </div>
  );
}
