import React, { useCallback, useMemo, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';
import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';
import { Activity, ArrowUpRight, BrainCircuit, BriefcaseBusiness, Check, ChevronRight, Download, FileSearch, Gauge, Loader2, Radar, Sparkles, Target, Upload, Zap } from 'lucide-react';
import LiveJobOpenings from './LiveJobOpenings';
import './App.css';

const api = (process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const errorMessage = (error) => error.response?.data?.error || error.response?.data?.detail || error.message || 'Analysis could not be completed.';

function downloadCareerReport(data) {
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

function UploadPanel({ file, setFile, loading, analyze }) {
  const onDrop = useCallback((accepted) => accepted[0] && setFile(accepted[0]), [setFile]);
  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop, accept: { 'application/pdf': ['.pdf'] }, maxFiles: 1, disabled: loading });
  return <section className="upload-panel" id="analyze"><div {...getRootProps()} className={`dropzone ${isDragActive ? 'active' : ''} ${file ? 'ready' : ''}`}><input {...getInputProps()}/><div className="drop-icon"><Upload size={24}/></div><div><strong>{file ? file.name : 'Drop your resume here'}</strong><p>{file ? `${Math.ceil(file.size / 1024)} KB · ready to scan` : 'PDF files only · your document stays private'}</p></div><ChevronRight className="drop-arrow"/></div><button className="primary-button" disabled={!file || loading} onClick={analyze}>{loading ? <><Loader2 className="spin" size={18}/> Building intelligence brief</> : <><Sparkles size={18}/> Analyze my resume</>}</button></section>;
}

function CareerAnalysisAnimation() {
  const stages = [
    ['Resume scan', FileSearch],
    ['Skill signals', Sparkles],
    ['Role alignment', Target],
    ['Opportunity map', BriefcaseBusiness],
  ];
  return <section className="career-loading" role="status" aria-live="polite"><div className="career-loading__intro"><span className="eyebrow"><BrainCircuit size={14}/> Career intelligence at work</span><h2>Mapping your next move</h2><p>We’re reading your resume for concrete evidence—not generating a generic report.</p></div><div className="career-orbit"><div className="career-orbit__ring ring-one"/><div className="career-orbit__ring ring-two"/><div className="career-orbit__core"><FileSearch size={28}/><span>Resume</span></div>{stages.map(([label, Icon], index) => <div className={`career-orbit__node node-${index + 1}`} key={label}><Icon size={17}/><span>{label}</span></div>)}</div><div className="career-loading__steps">{stages.map(([label, Icon], index) => <div key={label} style={{ animationDelay: `${index * .65}s` }}><span><Icon size={14}/></span>{label}</div>)}</div></section>;
}

function InsightDashboard({ data }) {
  const scorecard = data.scorecard || { overall: data.ats_score || 0, sections: {}, evidence: [] };
  const sections = Object.entries(scorecard.sections || {});
  const strengths = (data.matched_skills || []).slice(0, 8);
  const gaps = (data.missing_skills || []).slice(0, 6);
  const verdict = scorecard.overall >= 75 ? 'Strong screening foundation' : scorecard.overall >= 55 ? 'Promising, with targeted gaps' : 'Needs sharper positioning';
  return <section className="dashboard" id="dashboard"><div className="dash-heading"><div><p className="eyebrow">Career intelligence brief</p><h2>{data.candidate_name || 'Your'}’s opportunity map</h2><p>{data.detected_domain} · target: <b>{data.predicted_role}</b></p></div><div className="dash-actions"><button className="report-button" onClick={() => downloadCareerReport(data)}><Download size={15}/> Download full report</button><span className="status-pill"><Activity size={14}/> Analysis complete</span></div></div>
    <div className="hero-grid"><article className="score-card panel"><ScoreRing score={scorecard.overall}/><div className="score-copy"><span className="label">Recruiter signal</span><h3>{verdict}</h3><p>This score is derived from resume structure, skill coverage, evidence of impact, and readability—not a random estimate.</p><a href="#evidence">See score evidence <ArrowUpRight size={15}/></a></div></article><article className="summary-card panel"><div className="card-top"><span className="icon-wrap purple"><BrainCircuit size={20}/></span><span className="label">AI career read</span></div><p>{data.career_suggestions || data.custom_suggestion}</p><div className="role-chips">{(data.recommended_roles || []).slice(0, 4).map(role => <span key={role}>{role}</span>)}</div></article></div>
    <div className="metrics-grid">{sections.map(([name, value], i) => <article className="metric panel" key={name}><div><span>{name}</span><b>{value}<small>/100</small></b></div><div className="bar"><i style={{ width: `${value}%`, transitionDelay: `${i * 80}ms` }}/></div></article>)}</div>
    <div className="intel-grid"><article className="panel skills-card"><div className="section-title"><div><span className="label">Capability map</span><h3>Strengths & growth edges</h3></div><Radar size={20}/></div><div className="skill-group"><p><Check size={15}/> Confirmed strengths</p><div className="chips">{strengths.map(x => <span className="good" key={x}>{x}</span>) || <em>No skills reliably extracted</em>}</div></div><div className="skill-group"><p><Target size={15}/> Highest-value gaps</p><div className="chips">{gaps.map(x => <span className="gap" key={x}>{x}</span>) || <em>No major gaps identified</em>}</div></div></article><article className="panel evidence-card" id="evidence"><div className="section-title"><div><span className="label">Explainability</span><h3>Why this score</h3></div><Gauge size={20}/></div><ol>{(scorecard.evidence || []).map((item, i) => <li key={item}><b>0{i + 1}</b><span>{item}</span></li>)}</ol></article></div>
    <section className="panel roadmap"><div className="section-title"><div><span className="label">Growth simulator</span><h3>Your next 90 days</h3></div><Zap size={20}/></div><div className="roadmap-grid">{(data.learning_roadmap || []).map(step => <article key={step.step}><span>{String(step.step).padStart(2, '0')}</span><h4>{step.title}</h4><p>{step.focus}</p><small>{step.project_idea}</small></article>)}</div></section>
    <LiveJobOpenings recommendedRoles={data.recommended_roles} matchedSkills={data.job_search_skills || data.matched_skills} jobsByRole={data.jobs_by_role} jobsMessage={data.jobs_message} jobsCount={data.jobs_count}/>
  </section>;
}

export default function App() {
  const [file, setFile] = useState(null); const [loading, setLoading] = useState(false); const [result, setResult] = useState(null); const [error, setError] = useState('');
  const analyze = async () => { if (!file) return; setLoading(true); setError(''); setResult(null); try { const form = new FormData(); form.append('file', file); const response = await axios.post(`${api}/analyze`, form, { timeout: 120000 }); if (response.data.error) throw new Error(response.data.error); setResult(response.data); setTimeout(() => document.querySelector('#dashboard')?.scrollIntoView({ behavior: 'smooth' }), 80); } catch (e) { setError(errorMessage(e)); } finally { setLoading(false); } };
  const jobCount = useMemo(() => result?.jobs_count || 0, [result]);
  return <div className="app-shell"><div className="ambient ambient-one"/><div className="ambient ambient-two"/><header><a className="brand" href="#top"><span>◈</span> Resume<span className="muted">Navigator</span></a><nav><a href="#analyze">Analyzer</a><a href="#dashboard">Intelligence</a><a href="#live-jobs">Opportunities</a></nav><button className="quiet-button" onClick={() => document.querySelector('#analyze')?.scrollIntoView({ behavior: 'smooth' })}>Start analysis <ArrowUpRight size={15}/></button></header><main id="top"><section className="hero"><div className="hero-copy"><p className="eyebrow"><Sparkles size={14}/> AI-powered career intelligence</p><h1>Make your next<br/><em>move</em> unmistakable.</h1><p className="hero-text">ResumeNavigator reads your resume like a modern hiring team: structure, evidence, skills, and role alignment—then turns the signal into an actionable career brief.</p><div className="trust-row"><span><b>Explainable</b> scoring</span><i/><span><b>Private</b> document scan</span><i/><span><b>{jobCount || 'Live'}</b> role matches</span></div></div><div className="orbital"><div className="orbital-card card-a"><span>ATS signal</span><b>{result?.ats_score ?? '—'}</b><small>Evidence-based</small></div><div className="orbital-card card-b"><BrainCircuit size={22}/><span>Career DNA</span><small>Role alignment</small></div><div className="core-orb"><Sparkles size={32}/></div></div></section><UploadPanel file={file} setFile={setFile} loading={loading} analyze={analyze}/>{error && <div className="error-box">{error}</div>}{loading && <CareerAnalysisAnimation/>}{result && <InsightDashboard data={result}/>}</main><footer><span>ResumeNavigator Career Intelligence</span><span>Built for clear next moves.</span></footer></div>;
}
