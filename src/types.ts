export type Area = "ui" | "middleware" | "backend" | "database" | "sync";
export type Priority = 1 | 2 | 3;
export type Severity = "showstopper" | "serious" | "enhancement" | "nice_to_have";
export type Status = "open" | "closed";
export type Resolution = "none" | "fixed" | "no_repro" | "duplicate" | "wont_fix";
export type ActorType = "human" | "agent";

export interface BugSummary {
  id: string;
  product: string;
  title: string;
  area: Area | null;
  priority: Priority | null;
  severity: Severity | null;
  status: Status;
  resolution: Resolution;
  created_at: string;
  updated_at: string;
}

export interface Annotation {
  id: number;
  bug_id: string;
  author: string;
  author_type: ActorType;
  body: string;
  created_at: string;
}

export interface ArtifactSummary {
  id: number;
  bug_id: string;
  filename: string;
  mime_type: string | null;
  uploaded_at: string;
  url: string;
}

export interface Bug extends BugSummary {
  description: string | null;
  annotations: Annotation[];
  artifacts: ArtifactSummary[];
  related_bugs: string[];
}

export interface Product {
  name: string;
  description: string | null;
  archived: boolean;
  bug_count: number;
}

export interface Agent {
  key: string;
  name: string;
  description: string | null;
  created_at: string;
  active: boolean;
}

export interface BugListResponse {
  total: number;
  bugs: BugSummary[];
}

export interface BugFilters {
  q?: string;
  product?: string[];
  area?: Area[];
  priority?: Priority[];
  severity?: Severity[];
  status?: Status | "all";
  resolution?: Resolution[];
  related_to?: string;
  has_artifacts?: boolean;
  created_after?: string;
  created_before?: string;
}
