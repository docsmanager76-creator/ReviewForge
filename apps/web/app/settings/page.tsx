import Link from "next/link";
import { StorageSettings } from "../components/StorageSettings";

export default function SettingsPage() {
  return (
    <main className="page">
      <div className="header">
        <h1>Settings</h1>
        <Link href="/" className="nav-link">
          ← Back to Dashboard
        </Link>
      </div>
      <StorageSettings />
    </main>
  );
}
