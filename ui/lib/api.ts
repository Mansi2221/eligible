// Typed client for the Eligible FastAPI backend.

const BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export type Role = "data_analyst" | "coordinator" | "physician";
export type Decision = "eligible" | "ineligible" | "needs_review";

export interface CriterionEval {
  kind: string;
  status: string;
  criterion: string;
  evidence: string;
}

export interface TrialResult {
  nctId: string;
  decision: Decision;
  criteria: CriterionEval[];
}

const STATUS_TO_DECISION: Record<string, Decision> = {
  eligible: "eligible",
  ineligible: "ineligible",
  candidate: "needs_review",
};

async function post(path: string, body: unknown, token?: string) {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${path} → ${res.status} ${(await res.text()).slice(0, 200)}`);
  return res.json();
}

async function get(path: string, token: string) {
  const res = await fetch(`${BASE}${path}`, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new Error(`${path} → ${res.status} ${(await res.text()).slice(0, 200)}`);
  return res.json();
}

export async function getToken(username: string, role: Role): Promise<string> {
  return (await post("/token", { username, role })).access_token;
}

export async function diabeticPatients(token: string): Promise<number[]> {
  return (await get("/patients/diabetic", token)).person_ids;
}

export async function runMatch(token: string, personId: number): Promise<TrialResult[]> {
  const bundle = await post("/match", { person_id: personId }, token);
  return (bundle.entry ?? []).map((e: { resource: FhirResearchSubject }) =>
    parseResearchSubject(e.resource)
  );
}

export async function review(
  token: string,
  personId: number,
  nctId: string,
  approved: boolean,
  note?: string
) {
  return post("/review", { person_id: personId, nct_id: nctId, approved, note }, token);
}

export async function auditVerify(token: string): Promise<{ intact: boolean; length: number }> {
  return get("/audit/verify", token);
}

// --- FHIR parsing ---
interface FhirExtension {
  url: string;
  valueCode?: string;
  valueString?: string;
  extension?: FhirExtension[];
}
interface FhirResearchSubject {
  status: string;
  study: { identifier: { value: string } };
  extension?: FhirExtension[];
}

function parseResearchSubject(rs: FhirResearchSubject): TrialResult {
  const criteria = (rs.extension ?? []).map((ext) => {
    const by = (u: string) => ext.extension?.find((e) => e.url === u);
    return {
      kind: by("kind")?.valueCode ?? "",
      status: by("status")?.valueCode ?? "",
      criterion: by("criterion")?.valueString ?? "",
      evidence: by("evidence")?.valueString ?? "",
    };
  });
  return {
    nctId: rs.study.identifier.value,
    decision: STATUS_TO_DECISION[rs.status] ?? "needs_review",
    criteria,
  };
}
