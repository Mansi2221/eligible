"use client";

import { useState } from "react";
import {
  auditVerify,
  diabeticPatients,
  getToken,
  review,
  runMatch,
  type Decision,
  type Role,
  type TrialResult,
} from "@/lib/api";
import styles from "./page.module.css";

const DECISION_LABEL: Record<Decision, string> = {
  eligible: "Eligible",
  ineligible: "Ineligible",
  needs_review: "Needs review",
};

export default function Home() {
  const [username, setUsername] = useState("dr.smith");
  const [role, setRole] = useState<Role>("physician");
  const [token, setToken] = useState<string | null>(null);

  const [patients, setPatients] = useState<number[]>([]);
  const [patient, setPatient] = useState<number | null>(null);
  const [results, setResults] = useState<TrialResult[]>([]);
  const [reviewed, setReviewed] = useState<Record<string, boolean>>({});
  const [audit, setAudit] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function signIn() {
    setError("");
    try {
      const t = await getToken(username, role);
      setToken(t);
      setPatients(await diabeticPatients(t));
    } catch (e) {
      setError(String(e));
    }
  }

  async function match() {
    if (!token || patient == null) return;
    setBusy(true);
    setError("");
    setResults([]);
    setReviewed({});
    try {
      setResults(await runMatch(token, patient));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function decide(nctId: string, approved: boolean) {
    if (!token || patient == null) return;
    try {
      await review(token, patient, nctId, approved);
      setReviewed((r) => ({ ...r, [nctId]: approved }));
    } catch (e) {
      setError(String(e));
    }
  }

  async function checkAudit() {
    if (!token) return;
    try {
      const a = await auditVerify(token);
      setAudit(`chain ${a.intact ? "intact ✓" : "BROKEN ✗"}, ${a.length} entries`);
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <main className={styles.main}>
      <header className={styles.header}>
        <h1>Eligible</h1>
        <span className={styles.tagline}>Patient-to-trial matching on harmonized clinical data</span>
      </header>

      {!token ? (
        <section className={styles.card}>
          <h2>Sign in</h2>
          <div className={styles.row}>
            <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="username" />
            <select value={role} onChange={(e) => setRole(e.target.value as Role)}>
              <option value="data_analyst">data_analyst</option>
              <option value="coordinator">coordinator</option>
              <option value="physician">physician</option>
            </select>
            <button onClick={signIn}>Sign in</button>
          </div>
        </section>
      ) : (
        <section className={styles.card}>
          <div className={styles.row}>
            <span className={styles.badge}>{role}</span>
            <select
              value={patient ?? ""}
              onChange={(e) => setPatient(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">select patient…</option>
              {patients.map((p) => (
                <option key={p} value={p}>
                  Patient {p}
                </option>
              ))}
            </select>
            <button onClick={match} disabled={busy || patient == null}>
              {busy ? "Matching…" : "Run match"}
            </button>
            <button onClick={checkAudit} className={styles.secondary}>
              Verify audit chain
            </button>
          </div>
          {audit && <p className={styles.audit}>{audit}</p>}
        </section>
      )}

      {error && <p className={styles.error}>{error}</p>}

      {results.map((t) => (
        <section key={t.nctId} className={styles.card}>
          <div className={styles.trialHead}>
            <a href={`https://clinicaltrials.gov/study/${t.nctId}`} target="_blank" rel="noreferrer">
              {t.nctId}
            </a>
            <span className={`${styles.decision} ${styles[t.decision]}`}>
              {DECISION_LABEL[t.decision]}
            </span>
            {role === "physician" && (
              <span className={styles.actions}>
                {reviewed[t.nctId] === undefined ? (
                  <>
                    <button onClick={() => decide(t.nctId, true)}>Approve</button>
                    <button onClick={() => decide(t.nctId, false)} className={styles.secondary}>
                      Reject
                    </button>
                  </>
                ) : (
                  <span className={styles.reviewed}>
                    {reviewed[t.nctId] ? "approved ✓" : "rejected ✗"}, logged to audit
                  </span>
                )}
              </span>
            )}
          </div>
          <ul className={styles.criteria}>
            {t.criteria.map((c, i) => (
              <li key={i}>
                <span className={`${styles.status} ${styles["s_" + c.status]}`}>{c.status}</span>
                <span className={styles.kind}>{c.kind}</span>
                <span className={styles.text}>{c.criterion}</span>
                {c.evidence && <span className={styles.evidence}>- {c.evidence}</span>}
              </li>
            ))}
          </ul>
        </section>
      ))}
    </main>
  );
}
