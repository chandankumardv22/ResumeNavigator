import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { BriefcaseBusiness, Check, ExternalLink, Loader2, RefreshCw } from 'lucide-react';

const api = (process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const APPLIED_KEY = 'rn-applied-jobs';

function loadApplied() {
  try {
    const raw = localStorage.getItem(APPLIED_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function saveApplied(map) {
  try {
    localStorage.setItem(APPLIED_KEY, JSON.stringify(map));
  } catch {
    /* ignore */
  }
}

function jobKey(job) {
  return `${job.redirect_url || ''}|${job.job_title || ''}|${job.company_name || ''}`;
}

function normalizeJob(job) {
  return {
    role_category: job.role_category || '',
    company_name: job.company_name || job.employer_name || 'Company',
    job_title: job.job_title || job.title || 'Open Role',
    location: job.location || 'India',
    redirect_url: job.redirect_url || job.job_apply_link || job.link || '#',
    job_employment_type: job.job_employment_type || job.type || 'Full-time',
    source: job.source || 'Verified provider',
    skill_match_pct: Number(job.skill_match_pct) || 0,
    matched_skills: Array.isArray(job.matched_skills) ? job.matched_skills : [],
    tags: Array.isArray(job.tags) ? job.tags : [],
  };
}

function matchTone(pct) {
  if (pct >= 70) return 'high';
  if (pct >= 40) return 'mid';
  return 'low';
}

function JobCard({ job, index, applied, onApply, applying }) {
  const j = normalizeJob(job);
  const canApply = j.redirect_url && j.redirect_url !== '#' && /^https?:\/\//i.test(j.redirect_url);
  const isSearch = j.job_employment_type === 'Search' || /search$/i.test(j.source);
  const pct = Number(j.skill_match_pct) || 0;
  const key = jobKey(j);
  const isApplied = Boolean(applied[key]);

  return (
    <article className={`job-card ${isApplied ? 'job-card--applied' : ''}`} style={{ animationDelay: `${index * 50}ms` }}>
      <div className="job-card__header">
        <div className="job-card__company-logo" aria-hidden="true">
          {j.company_name.charAt(0).toUpperCase()}
        </div>
        <div className="job-card__meta">
          <h4 className="job-card__title">{j.job_title}</h4>
          <p className="job-card__company">{j.company_name}</p>
        </div>
        {pct > 0 && (
          <span className={`job-card__match job-card__match--${matchTone(pct)}`} title="Overlap with your matched skills">
            {pct}% match
          </span>
        )}
      </div>
      <div className="job-card__tags">
        <span className="job-card__tag">{j.location}</span>
        {!isSearch && <span className="job-card__tag">{j.job_employment_type}</span>}
        <span className="job-card__tag">{j.source}</span>
      </div>
      {j.matched_skills.length > 0 && (
        <div className="job-card__skills">
          {j.matched_skills.slice(0, 4).map((skill) => (
            <span key={skill} className="job-card__skill">{skill}</span>
          ))}
        </div>
      )}
      <div className="job-card__footer job-card__footer--apply">
        {canApply ? (
          <button
            type="button"
            className={`btn btn--sm btn--apply ${isApplied ? 'btn--applied' : ''}`}
            disabled={applying === key}
            onClick={() => onApply(j)}
          >
            {applying === key ? (
              <><Loader2 className="spin" size={14} /> Opening…</>
            ) : isApplied ? (
              <><Check size={14} /> Applied · Open again</>
            ) : (
              <><ExternalLink size={14} /> Apply Now</>
            )}
          </button>
        ) : (
          <span className="job-card__tag">Apply link unavailable</span>
        )}
      </div>
    </article>
  );
}

function RoleJobGroup({ roleName, jobs, applied, onApply, applying }) {
  return (
    <section className="live-jobs__role-group">
      <h3 className="live-jobs__role-heading">
        <BriefcaseBusiness size={16} /> {roleName}
        <span className="live-jobs__role-count">{(jobs || []).length} openings</span>
      </h3>
      <div className="jobs-grid--four">
        {(jobs || []).length > 0 ? (
          jobs.map((job, i) => (
            <JobCard
              key={`${roleName}-${job.job_title}-${i}`}
              job={job}
              index={i}
              applied={applied}
              onApply={onApply}
              applying={applying}
            />
          ))
        ) : (
          <p className="live-jobs__empty-role">No active listings for this role right now.</p>
        )}
      </div>
    </section>
  );
}

export default function LiveJobOpenings({
  recommendedRoles,
  matchedSkills = [],
  jobsByRole: jobsByRoleProp,
  jobsMessage,
  jobsCount,
  loading: externalLoading = false,
  candidateName,
  candidateEmail,
  candidateLocation,
  portalSearches: portalSearchesProp = [],
  allowRefresh = true,
}) {
  const [jobsByRole, setJobsByRole] = useState(jobsByRoleProp || {});
  const [message, setMessage] = useState(jobsMessage || '');
  const [count, setCount] = useState(jobsCount);
  const [portalSearches, setPortalSearches] = useState(portalSearchesProp || []);
  const [locationLabel, setLocationLabel] = useState(candidateLocation || '');
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter] = useState('all');
  const [applied, setApplied] = useState(loadApplied);
  const [applying, setApplying] = useState('');
  const [applyNote, setApplyNote] = useState('');

  useEffect(() => {
    setJobsByRole(jobsByRoleProp || {});
    setMessage(jobsMessage || '');
    setCount(jobsCount);
    setPortalSearches(portalSearchesProp || []);
    setLocationLabel(candidateLocation || '');
  }, [jobsByRoleProp, jobsMessage, jobsCount, portalSearchesProp, candidateLocation]);

  const roleOrder = (recommendedRoles || []).length
    ? recommendedRoles
    : Object.keys(jobsByRole || {});

  const filteredByRole = useMemo(() => {
    const out = {};
    roleOrder.forEach((role) => {
      // Feed is already direct-apply + location-filtered from the API.
      let list = (jobsByRole?.[role] || []).filter((j) => {
        const n = normalizeJob(j);
        return n.redirect_url && n.redirect_url !== '#' && /^https?:\/\//i.test(n.redirect_url)
          && n.job_employment_type !== 'Search'
          && !/search$/i.test(n.source);
      });
      if (filter === 'best') {
        list = list.filter((j) => (j.skill_match_pct ?? 0) >= 40);
      } else if (filter === 'applied') {
        list = list.filter((j) => applied[jobKey(normalizeJob(j))]);
      }
      out[role] = list;
    });
    return out;
  }, [jobsByRole, roleOrder, filter, applied]);

  const totalJobs = count ?? Object.values(jobsByRole || {}).reduce(
    (sum, list) => sum + (list?.length || 0),
    0,
  );
  const visibleJobs = Object.values(filteredByRole).reduce((sum, list) => sum + (list?.length || 0), 0);
  const searchTerms = [...new Set((matchedSkills || []).filter(Boolean))].slice(0, 6).join(' ');
  const place = (locationLabel && locationLabel !== 'Not found') ? locationLabel : 'India';
  const platformLinks = portalSearches.length
    ? portalSearches.map((p) => [p.company_name || p.source, p.redirect_url])
    : [
      ['LinkedIn', `https://www.linkedin.com/jobs/search/?keywords=${encodeURIComponent(searchTerms)}&location=${encodeURIComponent(place)}`],
      ['Naukri', `https://www.naukri.com/${encodeURIComponent(searchTerms).replace(/%20/g, '-')}-jobs-in-${encodeURIComponent(place).toLowerCase().replace(/%20/g, '-')}`],
      ['Indeed', `https://in.indeed.com/jobs?q=${encodeURIComponent(searchTerms)}&l=${encodeURIComponent(place)}`],
    ];

  const refreshJobs = async () => {
    if (!roleOrder.length) return;
    setRefreshing(true);
    setApplyNote('');
    try {
      const resp = await axios.post(
        `${api}/api/fetch-jobs`,
        {
          recommended_roles: roleOrder.slice(0, 5),
          matched_skills: matchedSkills,
          jobs_per_role: 12,
          candidate_location: place !== 'India' ? place : candidateLocation || undefined,
        },
        { timeout: 90000 },
      );
      setJobsByRole(resp.data.jobs_by_role || {});
      setMessage(resp.data.jobs_message || '');
      setCount(resp.data.jobs_count);
      setPortalSearches(resp.data.portal_searches || []);
      if (resp.data.candidate_location) setLocationLabel(resp.data.candidate_location);
    } catch (e) {
      setMessage(e.response?.data?.detail || e.message || 'Could not refresh job openings.');
    } finally {
      setRefreshing(false);
    }
  };

  const onApply = async (job) => {
    const key = jobKey(job);
    setApplying(key);
    setApplyNote('');
    try {
      await axios.post(
        `${api}/api/apply`,
        {
          job_title: job.job_title,
          company_name: job.company_name,
          redirect_url: job.redirect_url,
          role_category: job.role_category,
          skill_match_pct: job.skill_match_pct,
          matched_skills: job.matched_skills,
          candidate_name: candidateName || undefined,
          candidate_email: candidateEmail || undefined,
        },
        { timeout: 15000 },
      );
    } catch {
      // Still open the apply link even if tracking fails.
    }
    const next = { ...applied, [key]: Date.now() };
    setApplied(next);
    saveApplied(next);
    setApplyNote(`Opening application for ${job.job_title} at ${job.company_name}…`);
    window.open(job.redirect_url, '_blank', 'noopener,noreferrer');
    setApplying('');
  };

  const loading = externalLoading || refreshing;

  return (
    <section className="live-jobs-panel" id="live-jobs">
      <div className="live-jobs-panel__header">
        <div className="live-jobs-panel__heading-row">
          <div>
            <h3 className="live-jobs-panel__title">Direct-apply jobs near you</h3>
            <p className="live-jobs-panel__sub">
              {totalJobs > 0
                ? `${totalJobs} openings in ${place} · ${visibleJobs} shown · apply directly`
                : `Direct-apply openings in ${place}`}
            </p>
          </div>
          {allowRefresh && roleOrder.length > 0 && (
            <button type="button" className="job-refresh-btn" onClick={refreshJobs} disabled={loading}>
              {refreshing ? <Loader2 className="spin" size={15} /> : <RefreshCw size={15} />}
              {refreshing ? 'Refreshing' : 'Refresh openings'}
            </button>
          )}
        </div>
        {searchTerms && (
          <p className="live-jobs-panel__sub">
            Filtered to your resume address (<strong>{place}</strong>) and skills: <strong>{searchTerms}</strong>
          </p>
        )}
        <div className="job-platform-links">
          <span className="job-platform-links__label">Browse in {place}:</span>
          {platformLinks.map(([name, href]) => (
            <a key={name} href={href} target="_blank" rel="noopener noreferrer">{name}</a>
          ))}
        </div>
        <div className="job-filter-row" role="tablist" aria-label="Filter openings">
          {[
            ['all', 'All local openings'],
            ['best', 'Best skill match'],
            ['applied', 'Applied'],
          ].map(([id, label]) => (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={filter === id}
              className={`job-filter-chip ${filter === id ? 'is-active' : ''}`}
              onClick={() => setFilter(id)}
            >
              {label}
            </button>
          ))}
        </div>
        {loading && (
          <p className="live-jobs-panel__notice live-jobs-panel__notice--loading" role="status">
            Fetching live openings matched to your skills…
          </p>
        )}
        {!loading && message && (
          <p className="live-jobs-panel__notice" role="status">{message}</p>
        )}
        {applyNote && <p className="live-jobs-panel__notice live-jobs-panel__notice--apply">{applyNote}</p>}
      </div>

      {roleOrder.map((roleName) => (
        <RoleJobGroup
          key={roleName}
          roleName={roleName}
          jobs={filteredByRole[roleName] || []}
          applied={applied}
          onApply={onApply}
          applying={applying}
        />
      ))}
    </section>
  );
}
