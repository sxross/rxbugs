import { bugs as bugsApi } from "../api";
import type { BugFilters, BugSummary, Priority, Severity, Area } from "../types";
import { formatAge, priorityBadge, severityBadge, el, navigate } from "../utils";

let _debounce: ReturnType<typeof setTimeout> | null = null;

const AREAS: Area[] = ["ui", "middleware", "backend", "database", "sync"];
const SEVERITIES: Severity[] = ["showstopper", "serious", "enhancement", "nice_to_have"];

export function render(container: HTMLElement): void {
  const filters: BugFilters = { status: "open" };
  let results: BugSummary[] = [];
  let total = 0;

  container.innerHTML = `
    <header>
      <h1>🐛 RxBugs</h1>
      <div class="header-actions">
        <button class="btn btn-ghost btn-icon" id="admin-btn" title="Admin" aria-label="Admin">⚙️</button>
      </div>
    </header>

    <div class="search-bar">
      <input type="search" class="search-input" id="q" placeholder="Search bugs…" autocomplete="off" />
    </div>

    <div class="filter-chips" id="filter-chips"></div>
    <div class="results-count" id="results-count"></div>
    <div class="bug-list" id="bug-list"></div>

    <button class="fab" id="new-bug-btn" aria-label="New bug">+</button>
  `;

  const qInput = container.querySelector<HTMLInputElement>("#q")!;
  const chipsEl = container.querySelector<HTMLElement>("#filter-chips")!;
  const countEl = container.querySelector<HTMLElement>("#results-count")!;
  const listEl = container.querySelector<HTMLElement>("#bug-list")!;

  // ---- filter chip state ----
  type ChipGroup = { label: string; key: keyof BugFilters; values: string[]; multi: boolean };
  const chipGroups: ChipGroup[] = [
    { label: "Closed", key: "status", values: ["closed"], multi: false },
    { label: "All", key: "status", values: ["all"], multi: false },
    { label: "P1", key: "priority", values: ["1"], multi: true },
    { label: "P2", key: "priority", values: ["2"], multi: true },
    { label: "P3", key: "priority", values: ["3"], multi: true },
    ...SEVERITIES.map(s => ({ label: s.replace("_", " "), key: "severity" as keyof BugFilters, values: [s], multi: true })),
    ...AREAS.map(a => ({ label: a, key: "area" as keyof BugFilters, values: [a], multi: true })),
  ];

  function buildChips(): void {
    chipsEl.innerHTML = "";
    chipGroups.forEach(group => {
      const chip = el("button", { className: "chip", type: "button" }, group.label);
      const isActive = isChipActive(group);
      if (isActive) chip.classList.add("active");
      chip.addEventListener("click", () => toggleChip(group));
      chipsEl.appendChild(chip);
    });
  }

  function isChipActive(group: ChipGroup): boolean {
    const val = (filters as Record<string, unknown>)[group.key];
    if (group.key === "status") return val === group.values[0];
    if (Array.isArray(val)) return group.values.every(v => (val as string[]).includes(v));
    return false;
  }

  function toggleChip(group: ChipGroup): void {
    if (group.key === "status") {
      if ((filters.status as string) === group.values[0]) {
        filters.status = "open";
      } else {
        (filters as Record<string, unknown>)[group.key] = group.values[0];
      }
    } else {
      const key = group.key as "priority" | "severity" | "area";
      const existing = (filters[key] ?? []) as string[];
      const v = group.values[0];
      if (existing.includes(v)) {
        const next = existing.filter(x => x !== v);
        if (next.length === 0) delete (filters as Record<string, unknown>)[key];
        else (filters as Record<string, unknown>)[key] = next;
      } else {
        (filters as Record<string, unknown>)[key] = [...existing, v];
      }
    }
    buildChips();
    loadBugs();
  }

  function loadBugs(): void {
    listEl.innerHTML = `<div class="loading-center"><div class="spinner"></div></div>`;
    bugsApi.list(filters).then(data => {
      results = data.bugs;
      total = data.total;
      renderList();
    }).catch(err => {
      listEl.innerHTML = `<div class="error-banner">${err.message}</div>`;
    });
  }

  function renderList(): void {
    const statusLabel = filters.status === "all" ? "bugs" :
      filters.status === "closed" ? "closed bugs" : "open bugs";
    const qText = filters.q ? ` for "${filters.q}"` : "";
    countEl.textContent = `${total} ${statusLabel}${qText}`;

    if (results.length === 0) {
      listEl.innerHTML = `<div class="empty-state">No bugs found.</div>`;
      return;
    }
    listEl.innerHTML = "";
    results.forEach(bug => {
      const row = el("a", { className: "bug-row", href: `#/bugs/${bug.id}` });
      row.innerHTML = `
        <span class="bug-row-id">${bug.id}</span>
        <span class="bug-row-title">${escHtml(bug.title)}</span>
        <span class="bug-row-meta">
          ${bug.priority ? `<span class="badge badge-p${bug.priority}">P${bug.priority}</span>` : ""}
          ${bug.severity ? `<span class="badge badge-${bug.severity}">${escHtml(bug.severity.replace("_", " "))}</span>` : ""}
          ${bug.area ? `<span class="badge" style="background:var(--surface2);color:var(--text-dim)">${escHtml(bug.area)}</span>` : ""}
          <span class="age">${formatAge(bug.updated_at)}</span>
        </span>
      `;
      listEl.appendChild(row);
    });
  }

  // ---- search debounce ----
  qInput.addEventListener("input", () => {
    if (_debounce) clearTimeout(_debounce);
    _debounce = setTimeout(() => {
      const q = qInput.value.trim();
      if (q) filters.q = q; else delete filters.q;
      loadBugs();
    }, 250);
  });

  container.querySelector("#new-bug-btn")!.addEventListener("click", () => navigate("/bugs/new"));
  container.querySelector("#admin-btn")!.addEventListener("click", () => navigate("/admin"));

  buildChips();
  loadBugs();
}

function escHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// re-export unused imports to satisfy TS
export { priorityBadge, severityBadge };
