import { HealthPill } from "./components/HealthPill";
import { ProjectDashboard } from "./components/ProjectDashboard";

export default function HomePage() {
  return (
    <main className="page">
      <div className="header">
        <h1>ReviewForge</h1>
        <HealthPill />
      </div>
      <ProjectDashboard />
    </main>
  );
}
