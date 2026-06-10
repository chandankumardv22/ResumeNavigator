import React from 'react';

function normalizeJob(job) {
  return {
    role_category: job.role_category || '',
    company_name: job.company_name || job.employer_name || 'Company',
    job_title: job.job_title || job.title || 'Open Role',
    location: job.location || 'India',
    redirect_url: job.redirect_url || job.job_apply_link || job.link || '#',
    job_employment_type: job.job_employment_type || job.type || 'Full-time',
  };
}

function JobCard({ job, index }) {
  const j = normalizeJob(job);
  const canApply = j.redirect_url && j.redirect_url !== '#';

  return (
    <article className="job-card" style={{ animationDelay: `${index * 60}ms` }}>
      <div className="job-card__header">
        <div className="job-card__company-logo" aria-hidden="true">
          {j.company_name.charAt(0).toUpperCase()}
        </div>
        <div className="job-card__meta">
          <h4 className="job-card__title">{j.job_title}</h4>
          <p className="job-card__company">{j.company_name}</p>
        </div>
      </div>
      <div className="job-card__tags">
        <span className="job-card__tag">{j.location}</span>
        <span className="job-card__tag">{j.job_employment_type}</span>
      </div>
      <div className="job-card__footer job-card__footer--apply">
        {canApply ? (
          <a
            className="btn btn--sm btn--apply"
            href={j.redirect_url}
            target="_blank"
            rel="noopener noreferrer"
          >
            Apply Now
          </a>
        ) : (
          <span className="job-card__tag">Apply link unavailable</span>
        )}
      </div>
    </article>
  );
}

function RoleJobGroup({ roleName, jobs }) {
  return (
    <section className="live-jobs__role-group">
      <h3 className="live-jobs__role-heading">{roleName}</h3>
      <div className="jobs-grid--four">
        {(jobs || []).length > 0 ? (
          jobs.map((job, i) => (
            <JobCard key={`${roleName}-${job.job_title}-${i}`} job={job} index={i} />
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
  jobsByRole,
  jobsMessage,
  jobsCount,
  loading = false,
}) {
  const roleOrder = (recommendedRoles || []).length
    ? recommendedRoles
    : Object.keys(jobsByRole || {});

  const totalJobs = jobsCount ?? Object.values(jobsByRole || {}).reduce(
    (sum, list) => sum + (list?.length || 0),
    0,
  );

  return (
    <section className="live-jobs-panel" id="live-jobs">
      <div className="live-jobs-panel__header">
        <h3 className="live-jobs-panel__title">Live Job Openings (India)</h3>
        <p className="live-jobs-panel__sub">
          {totalJobs > 0
            ? `${totalJobs} active openings across your recommended roles`
            : 'Real-time India job search'}
        </p>
        {loading && (
          <p className="live-jobs-panel__notice live-jobs-panel__notice--loading" role="status">
            Fetching live India job openings for your roles…
          </p>
        )}
        {!loading && jobsMessage && (
          <p className="live-jobs-panel__notice" role="status">{jobsMessage}</p>
        )}
      </div>

      {roleOrder.map((roleName) => (
        <RoleJobGroup
          key={roleName}
          roleName={roleName}
          jobs={jobsByRole?.[roleName] || []}
        />
      ))}
    </section>
  );
}
