"use client";

import { useEffect, useState } from "react";
import { getHealth } from "../../lib/api";

type Status = "checking" | "ok" | "error";

export function HealthPill() {
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    let cancelled = false;
    getHealth()
      .then(() => !cancelled && setStatus("ok"))
      .catch(() => !cancelled && setStatus("error"));
    return () => {
      cancelled = true;
    };
  }, []);

  const label =
    status === "checking" ? "checking API..." : status === "ok" ? "API connected" : "API offline";

  return <span className={`status-pill ${status === "ok" ? "ok" : status === "error" ? "error" : ""}`}>{label}</span>;
}
