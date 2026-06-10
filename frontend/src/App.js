import React, { useState, useCallback, useMemo } from 'react';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';
import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';
import {
  Upload,
  FileSearch,
  FileText,
  Target,
  Briefcase,
  CheckCircle2,
  Loader2,
  ClipboardList,
} from 'lucide-react';
import LiveJobOpenings from './LiveJobOpenings';
import './App.css';

function getApiOrigin() {
  const raw = process.env.REACT_APP_API_URL;
  if (raw != null && String(raw).trim() !== '') {
    return String(raw).trim().replace(/\/$/, '');
  }
  return 'http://127.0.0.1:8000';
}

function getAnalyzeUrl() {
  return `${getApiOrigin()}/analyze`;
}

function formatApiError(err) {
  const data = err.response?.data;
  if (data?.error) return data.error;
  if (data?.detail?.error) return data.detail.error;
  if (typeof data?.detail === 'string') return data.detail;
  if (Array.isArray(data?.detail)) {
    const joined = data.detail
      .map((x) => (typeof x === 'string' ? x : x?.msg))
      .filter(Boolean)
      .join('; ');
    if (joined) return joined;
  }
  if (data?.message) return data.message;
  if (err.response?.status) return `Request failed with status code ${err.response.status}`;
  return err.message || 'Analysis failed. Please try again.';
}

function Header() {
  return (
    <header className="pf-header glass-panel">
      <div className="pf-header__inner">
        <span className="pf-gradient-text pf-header__brand">PathFinder</span>
        <nav className="pf-header__nav">
          <a href="#upload">Upload</a>
          <a href="#timeline">Process</a>
          <a href="#dashboard">Results</a>
        </nav>
      </div>
    </header>
  );
}

function ValueProps() {
  const items = [
    {
      icon: Target,
      title: 'ATS Scoring',
      text: 'Domain-aware scoring calibrated to your actual resume content.',
    },
    {
      icon: ClipboardList,
      title: 'Skill Precision',
      text: 'Professional competencies extracted without contact metadata noise.',
    },
    {
      icon: Briefcase,
      title: 'Live Job Matches',
      text: 'Curated India openings mapped to your recommended career roles.',
    },
  ];
  return (
    <div className="pf-value-grid">
      {items.map((item) => {
        const Icon = item.icon;
        return (
          <article key={item.title} className="pf-value-card glass-panel">
            <div className="pf-value-card__icon">
              <Icon size={22} strokeWidth={2} />
            </div>
            <h3>{item.title}</h3>
            <p>{item.text}</p>
          </article>
        );
      })}
    </div>
  );
}

function ProcessTimeline({ step }) {
  const steps = [
    { id: 1, label: 'Upload Resume', icon: Upload },
    { id: 2, label: 'Resume Scan', icon: FileSearch },
    { id: 3, label: 'Results & Report', icon: FileText },
  ];
  return (
    <section className="pf-timeline glass-panel" id="timeline">
      <h2 className="pf-timeline__title">Your PathFinder Journey</h2>
      <div className="pf-timeline__track">
        {steps.map((s, index) => {
          const Icon = s.icon;
          const status = step > s.id ? 'done' : step === s.id ? 'active' : 'pending';
          return (
            <div key={s.id} className={`pf-timeline__step pf-timeline__step--${status}`}>
              <div className="pf-timeline__node">
                {status === 'done' ? <CheckCircle2 size={22} /> : <Icon size={22} />}
              </div>
              <span className="pf-timeline__label">{s.label}</span>
              {index < steps.length - 1 && <div className="pf-timeline__connector" />}
            </div>
          );
        })}
      </div>
    </section>
  );
}

function HeroUpload({ file, setFile, loading, error, onAnalyze }) {
  const onDrop = useCallback((accepted) => {
    if (accepted?.[0]) setFile(accepted[0]);
  }, [setFile]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    multiple: false,
    disabled: loading,
  });

  return (
    <div className="pf-upload glass-panel" id="upload">
      <div
        {...getRootProps()}
        className={`pf-dropzone ${isDragActive ? 'pf-dropzone--active' : ''} ${file ? 'pf-dropzone--ready' : ''} ${loading ? 'pf-dropzone--disabled' : ''}`}
      >
        <input {...getInputProps()} />
        <div className="pf-dropzone__icon-wrap">
          <Upload size={32} strokeWidth={1.75} />
        </div>
        {file ? (
          <>
            <p className="pf-dropzone__title">{file.name}</p>
            <p className="pf-dropzone__meta">{(file.size / 1024).toFixed(1)} KB ready for analysis</p>
          </>
        ) : (
          <>
            <p className="pf-dropzone__title">
              {isDragActive ? 'Release to upload your PDF' : 'Drag & drop your resume'}
            </p>
            <p className="pf-dropzone__meta">PDF only · click to browse files</p>
          </>
        )}
      </div>

      <button
        type="button"
        className="pf-btn pf-btn--primary"
        onClick={onAnalyze}
        disabled={loading || !file}
      >
        {loading ? (
          <>
            <Loader2 className="pf-btn__spin" size={18} />
            Analyzing Resume
          </>
        ) : (
          'Analyze Resume'
        )}
      </button>

      {error && (
        <div className="pf-alert" role="alert">
          {error}
        </div>
      )}
    </div>
  );
}

function AtsScoreRing({ score }) {
  const radius = 54;
  const circ = 2 * Math.PI * radius;
  const offset = circ - (score / 100) * circ;
  const color = score >= 75 ? '#10b981' : score >= 50 ? '#f59e0b' : '#ef4444';

  return (
    <div className="pf-score">
      <svg viewBox="0 0 128 128" className="pf-score__svg">
        <circle cx="64" cy="64" r={radius} className="pf-score__track" />
        <circle
          cx="64"
          cy="64"
          r={radius}
          className="pf-score__fill"
          style={{ strokeDasharray: circ, strokeDashoffset: offset, stroke: color }}
        />
      </svg>
      <div className="pf-score__label">
        <span className="pf-score__value" style={{ color }}>{score}</span>
        <span className="pf-score__caption">ATS Score</span>
      </div>
    </div>
  );
}

function App() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  const timelineStep = useMemo(() => {
    if (results) return 3;
    if (loading) return 2;
    if (file) return 2;
    return 1;
  }, [file, loading, results]);

  const handleAnalyze = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const formData = new FormData();
      formData.append('file', file, file.name);
      const response = await axios.post(getAnalyzeUrl(), formData, { timeout: 120000 });

      if (response.data?.error) {
        setError(response.data.error);
        return;
      }

      setResults(response.data);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const matched = results?.matched_skills ?? [];
  const missing = results?.missing_skills ?? [];
  const role = results?.predicted_role;
  const roadmap = results?.learning_roadmap ?? [];
  const careerSuggestions = results?.career_suggestions ?? results?.custom_suggestion ?? '';
  const meta = results?.candidate_metadata ?? {};
  const candidateName = meta.candidate_name || results?.candidate_name || 'Not found';
  const candidateEmail = meta.candidate_email || results?.candidate_email || 'Not found';
  const candidatePhone = meta.candidate_phone || results?.candidate_phone || 'Not found';
  const candidateCollege = meta.candidate_college || results?.candidate_college || 'Not found';
  const detectedDomain = results?.detected_domain || 'Not specified';
  const recommendedRoles = results?.recommended_roles ?? [];
  const jobsByRole = results?.jobs_by_role ?? {};
  const jobsMessage = results?.jobs_message ?? null;
  const jobsCount = results?.jobs_count ?? 0;

  const generatePDFReport = () => {
    if (!results) return;
    const doc = new jsPDF();
    let y = 16;

    doc.setFontSize(18);
    doc.text('PathFinder Career Report', 14, y);
    y += 10;

    doc.setFontSize(11);
    const lines = [
      `Candidate Name: ${candidateName}`,
      `Email: ${candidateEmail}`,
      `Phone: ${candidatePhone}`,
      `College: ${candidateCollege}`,
      `Detected Domain: ${detectedDomain}`,
      `Predicted Role: ${role || 'N/A'}`,
      `Recommended Roles: ${(recommendedRoles || []).join(', ') || 'N/A'}`,
      `ATS Score: ${results.ats_score ?? 0}/100`,
    ];
    lines.forEach((line) => {
      doc.text(line, 14, y, { maxWidth: 180 });
      y += 6;
    });
    y += 4;

    doc.setFontSize(13);
    doc.text('Matched Skills', 14, y);
    y += 6;
    doc.setFontSize(11);
    doc.text(matched.length ? matched.join(', ') : 'None detected.', 14, y, { maxWidth: 180 });
    y += 10;

    doc.setFontSize(13);
    doc.text('Skill Gaps', 14, y);
    y += 6;
    doc.setFontSize(11);
    doc.text(missing.length ? missing.join(', ') : 'No major gaps listed.', 14, y, { maxWidth: 180 });
    y += 12;

    doc.setFontSize(13);
    doc.text('Career Suggestions', 14, y);
    y += 6;
    doc.setFontSize(10);
    const suggestionLines = doc.splitTextToSize(
      careerSuggestions || 'No career suggestions available.',
      180,
    );
    doc.text(suggestionLines, 14, y);
    y += suggestionLines.length * 5 + 8;

    doc.setFontSize(13);
    doc.text('Learning Roadmap', 14, y);
    y += 4;
    autoTable(doc, {
      startY: y,
      head: [['Step', 'Title', 'Focus', 'Project Idea']],
      body: (roadmap.length ? roadmap : [{ step: 1, title: 'Unavailable', focus: '-', project_idea: '-' }]).map((step) => [
        String(step.step ?? ''),
        String(step.title ?? ''),
        String(step.focus ?? ''),
        String(step.project_idea ?? ''),
      ]),
      styles: { fontSize: 9, cellPadding: 2 },
      headStyles: { fillColor: [30, 41, 59] },
    });

    y = doc.lastAutoTable ? doc.lastAutoTable.finalY + 10 : y + 20;
    doc.setFontSize(13);
    doc.text('Live Job Openings (India)', 14, y);
    y += 4;

    const rows = [];
    Object.entries(jobsByRole).forEach(([roleKey, roleJobs]) => {
      (roleJobs || []).forEach((job) => {
        rows.push([
          roleKey,
          String(job.company_name || job.employer_name || ''),
          String(job.job_title || ''),
          String(job.redirect_url || job.job_apply_link || ''),
        ]);
      });
    });

    autoTable(doc, {
      startY: y,
      head: [['Role', 'Company', 'Job Title', 'Apply Link']],
      body: rows.length ? rows : [['-', '-', '-', '-']],
      styles: { fontSize: 8, cellPadding: 2 },
      headStyles: { fillColor: [79, 70, 229] },
    });

    doc.save('PathFinder-Career-Report.pdf');
  };

  return (
    <div className="pf-app">
      <div className="pf-mesh" aria-hidden="true" />
      <Header />

      <main className="pf-main">
        <section className="pf-hero">
          <p className="pf-hero__eyebrow">Career path discovery</p>
          <h1 className="pf-hero__title pf-gradient-text">PathFinder</h1>
          <p className="pf-hero__subtitle">
            Upload your PDF resume for ATS scoring, precise skill extraction, and live India job matches.
            Personalized career roadmaps are delivered exclusively in your downloadable report.
          </p>
          <ValueProps />
          <HeroUpload
            file={file}
            setFile={setFile}
            loading={loading}
            error={error}
            onAnalyze={handleAnalyze}
          />
        </section>

        <ProcessTimeline step={timelineStep} />

        {loading && (
          <div className="pf-loading glass-panel" role="status" aria-live="polite">
            <Loader2 className="pf-loading__icon" size={36} />
            <p>Processing your resume…</p>
          </div>
        )}

        {results && (
          <section className="pf-dashboard glass-panel" id="dashboard">
            <div className="pf-dashboard__header">
              <h2>Analysis Results</h2>
              <p>Your dashboard reflects the unique content extracted from your resume.</p>
            </div>

            <div className="pf-dashboard__meta glass-panel pf-dashboard__meta--inner">
              <p><strong>Name:</strong> {candidateName}</p>
              <p><strong>Email:</strong> {candidateEmail}</p>
              <p><strong>Phone:</strong> {candidatePhone}</p>
              <p><strong>College:</strong> {candidateCollege}</p>
              <p><strong>Domain:</strong> {detectedDomain}</p>
              <p><strong>Predicted role:</strong> {role || 'N/A'}</p>
              <p>
                <strong>Recommended roles:</strong>{' '}
                {recommendedRoles.length ? recommendedRoles.join(', ') : 'N/A'}
              </p>
            </div>

            <div className="pf-dashboard__grid">
              <div className="pf-card glass-panel pf-card--center">
                <AtsScoreRing score={results.ats_score ?? 0} />
                <p className="pf-card__hint">
                  {results.ats_score >= 75
                    ? 'Strong alignment for your target role.'
                    : results.ats_score >= 50
                    ? 'Solid foundation with room to close skill gaps.'
                    : 'Prioritize missing keywords and clearer resume structure.'}
                </p>
              </div>

              <div className="pf-card glass-panel">
                <h3>Matched Skills</h3>
                <ul className="pf-list">
                  {matched.length > 0 ? matched.map((s, i) => <li key={i}>{s}</li>) : (
                    <li className="pf-list__empty">No professional skills detected.</li>
                  )}
                </ul>

                <h3 className="pf-card__subtitle">Skill Gaps</h3>
                <div className="pf-chips">
                  {missing.length > 0 ? missing.map((s, i) => (
                    <span className="pf-chip" key={i}>{s}</span>
                  )) : (
                    <span className="pf-list__empty">No major gaps detected.</span>
                  )}
                </div>
              </div>
            </div>

            <div className="pf-dashboard__actions">
              <button type="button" className="pf-btn pf-btn--primary" onClick={generatePDFReport}>
                Download Career Report (PDF)
              </button>
              <p className="pf-dashboard__note">
                Career suggestions and milestone roadmaps are included in the PDF report only.
              </p>
            </div>

            <LiveJobOpenings
              recommendedRoles={recommendedRoles}
              jobsByRole={jobsByRole}
              jobsMessage={jobsMessage}
              jobsCount={jobsCount}
              loading={false}
            />
          </section>
        )}
      </main>

      <footer className="pf-footer glass-panel">
        <span className="pf-gradient-text pf-footer__brand">PathFinder</span>
        <span>© {new Date().getFullYear()}</span>
      </footer>
    </div>
  );
}

export default App;
