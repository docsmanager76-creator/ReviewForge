"use client";

import { useEffect, useState } from "react";
import { listProjects, ProjectSummary } from "../../lib/api";
import { CreateProjectForm } from "./CreateProjectForm";
import { VoiceAnalysisControls } from "./VoiceAnalysisControls";

export function ProjectDashboard() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);

  function refresh() {
    listProjects()
      .then(setProjects)
      .catch(() => setProjects([]));
  }

  useEffect(refresh, []);

  return (
    <>
      <CreateProjectForm onCreated={refresh} />

      <section className="panel">
        <h2>Projects</h2>
        {projects.length === 0 ? (
          <p style={{ color: "var(--text-dim)", fontSize: 14 }}>No projects yet.</p>
        ) : (
          <ul className="project-list">
            {projects.map((p) => (
              <li key={p.id} className="project-item">
                <div className="project-item-header">
                  <span>
                    {p.name} <span className="id">— {p.productName}</span>
                  </span>
                  <span className="id">{p.id}</span>
                </div>
                <VoiceAnalysisControls projectId={p.id} />
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
