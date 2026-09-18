import Link from "next/link";
import { HealthPill } from "./components/HealthPill";
import { ProjectDashboard } from "./components/ProjectDashboard";

export default function HomePage() {
  return (
    <main className="page">
      <div className="header">
        <h1>ReviewForge</h1>
        <div className="header-actions">
          <Link href="/settings" className="nav-link">
            Storage &amp; Data
          </Link>
          <HealthPill />
        </div>
      </div>
      <ProjectDashboard />
    </main>
  );
}
