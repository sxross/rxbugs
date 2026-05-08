import {
  agents as agentsApi,
  areas as areasApi,
  platforms as platformsApi,
  products as productsApi,
  severities as severitiesApi,
} from "../api";
import type { Agent, Area, Platform, Product, Severity } from "../types";
import { navigate, escHtml } from "../utils";

// ---------------------------------------------------------------------------
// Lookup-table entry shape (shared by Product, Area, Severity, Platform)
// ---------------------------------------------------------------------------

interface LookupEntry {
  name: string;
  description: string | null;
  archived: boolean;
  bug_count: number;
}

interface LookupApi<T extends LookupEntry> {
  list(includeArchived: boolean): Promise<T[]>;
  create(name: string): Promise<T>;
  rename(oldName: string, newName: string): Promise<T>;
  archive(name: string): Promise<T>;
}

// ---------------------------------------------------------------------------
// Generic lookup-table renderer
// ---------------------------------------------------------------------------

function renderLookupTable<T extends LookupEntry>(
  body: HTMLElement,
  list: T[],
  key: string,
  label: string,
  api: LookupApi<T>,
): void {
  const el = body.querySelector<HTMLElement>(`#${key}-list`)!;
  const errorEl = body.querySelector<HTMLElement>(`#${key}-error`)!;

  function refresh(items: T[]): void {
    el.innerHTML = items.length === 0
      ? `<div class="empty-state" style="padding:12px 0">No ${label.toLowerCase()} yet.</div>`
      : items.map(entry => `
          <div class="admin-row" data-${key}="${escHtml(entry.name)}">
            <div class="admin-row-info">
              <div class="admin-row-name">${escHtml(entry.name)}${entry.archived ? " (archived)" : ""}</div>
              <div class="admin-row-meta">${entry.bug_count} bug${entry.bug_count !== 1 ? "s" : ""}</div>
            </div>
            <div class="admin-row-actions">
              <button class="btn btn-secondary ${key}-rename-btn" data-name="${escHtml(entry.name)}"
                style="font-size:0.78rem;min-height:36px">Rename</button>
              ${!entry.archived ? `<button class="btn btn-danger ${key}-archive-btn" data-name="${escHtml(entry.name)}"
                style="font-size:0.78rem;min-height:36px">Archive</button>` : ""}
            </div>
          </div>
        `).join("");

    el.querySelectorAll<HTMLButtonElement>(`.${key}-rename-btn`).forEach(btn => {
      btn.addEventListener("click", () => {
        const old = btn.dataset["name"]!;
        const newName = prompt(`Rename ${label.toLowerCase()} "${old}" to:`, old);
        if (!newName || newName === old) return;
        api.rename(old, newName).then(() => api.list(true))
          .then(updated => refresh(updated))
          .catch(err => { errorEl.textContent = err.message; });
      });
    });

    el.querySelectorAll<HTMLButtonElement>(`.${key}-archive-btn`).forEach(btn => {
      btn.addEventListener("click", () => {
        const name = btn.dataset["name"]!;
        if (!confirm(`Archive "${name}"?`)) return;
        api.archive(name).then(() => api.list(true))
          .then(updated => refresh(updated))
          .catch(err => { errorEl.textContent = err.message; });
      });
    });
  }

  refresh(list);

  // Wire the "Add" button
  body.querySelector(`#add-${key}-btn`)!.addEventListener("click", () => {
    const input = body.querySelector<HTMLInputElement>(`#new-${key}-name`)!;
    const name = input.value.trim();
    if (!name) return;
    api.create(name).then(() => api.list(true))
      .then(updated => {
        refresh(updated);
        input.value = "";
        errorEl.textContent = "";
      })
      .catch(err => { errorEl.textContent = err.message; });
  });
}

// ---------------------------------------------------------------------------
// Section HTML template (shared by all 4 lookup tables)
// ---------------------------------------------------------------------------

function lookupSectionHtml(key: string, title: string, placeholder: string): string {
  return `
    <div class="admin-section">
      <h2>${title}</h2>
      <div id="${key}-list"></div>
      <div style="display:flex;gap:8px;margin-top:10px">
        <input class="form-control" id="new-${key}-name" type="text"
          placeholder="${placeholder}" style="max-width:200px" />
        <button class="btn btn-secondary" id="add-${key}-btn">Add</button>
      </div>
      <div class="form-error" id="${key}-error"></div>
    </div>`;
}

// ---------------------------------------------------------------------------
// Top-level render
// ---------------------------------------------------------------------------

export function render(container: HTMLElement): void {
  container.innerHTML = `
    <header>
      <button class="back-btn" id="back">← Bugs</button>
      <h1 style="font-size:1rem;color:var(--text)">Admin</h1>
      <div></div>
    </header>
    <div id="admin-body"><div class="loading-center"><div class="spinner"></div></div></div>
  `;
  container.querySelector("#back")!.addEventListener("click", () => navigate("/"));

  Promise.all([
    productsApi.list(true),
    areasApi.list(true),
    severitiesApi.list(true),
    platformsApi.list(true),
    agentsApi.list(),
  ]).then(([prods, ars, sevs, plats, agts]) => {
    renderAdmin(
      container.querySelector<HTMLElement>("#admin-body")!,
      prods, ars, sevs, plats, agts,
    );
  }).catch(err => {
    container.querySelector<HTMLElement>("#admin-body")!.innerHTML =
      `<div class="error-banner">${escHtml(err.message)}</div>`;
  });
}

// ---------------------------------------------------------------------------
// Render all admin sections
// ---------------------------------------------------------------------------

function renderAdmin(
  body: HTMLElement,
  products: Product[],
  areasList: Area[],
  severitiesList: Severity[],
  platformsList: Platform[],
  agentsList: Agent[],
): void {
  body.innerHTML = `
    ${lookupSectionHtml("product", "Products", "Product name")}
    ${lookupSectionHtml("area", "Areas", "Area name")}
    ${lookupSectionHtml("severity", "Severities", "Severity name")}
    ${lookupSectionHtml("platform", "Platforms", "Platform name")}

    <!-- ---- Agents ---- -->
    <div class="admin-section">
      <h2>API Agents</h2>
      <div id="agents-list"></div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px">
        <input class="form-control" id="new-agent-name" type="text"
          placeholder="Agent name" style="max-width:200px" />
        <input class="form-control" id="new-agent-desc" type="text"
          placeholder="Description (optional)" style="max-width:240px" />
        <button class="btn btn-secondary" id="add-agent-btn">Register</button>
      </div>
      <div class="form-error" id="agent-error"></div>
      <div id="new-key-display" style="display:none">
        <div class="form-hint" style="margin-top:8px">
          ⚠️ Save this key — it will not be shown again.
        </div>
        <div class="key-display" id="new-key-value"></div>
      </div>
    </div>
  `;

  renderLookupTable(body, products, "product", "Product", productsApi);
  renderLookupTable(body, areasList, "area", "Area", areasApi);
  renderLookupTable(body, severitiesList, "severity", "Severity", severitiesApi);
  renderLookupTable(body, platformsList, "platform", "Platform", platformsApi);
  renderAgents(body, agentsList);
}

// ---------------------------------------------------------------------------
// Agents renderer (unique structure — not generic)
// ---------------------------------------------------------------------------

function renderAgents(body: HTMLElement, list: Agent[]): void {
  const el = body.querySelector<HTMLElement>("#agents-list")!;

  function refresh(items: Agent[]): void {
    el.innerHTML = items.length === 0
      ? `<div class="empty-state" style="padding:12px 0">No agents registered.</div>`
      : items.map(a => `
          <div class="admin-row">
            <div class="admin-row-info">
              <div class="admin-row-name">${escHtml(a.name)}
                ${!a.active ? `<span class="badge badge-closed" style="margin-left:6px">revoked</span>` : ""}
              </div>
              <div class="admin-row-meta">${escHtml(a.description ?? "—")}</div>
            </div>
            ${a.active ? `
            <div class="admin-row-actions">
              <button class="btn btn-danger revoke-btn" data-key="${escHtml(a.key)}"
                style="font-size:0.78rem;min-height:36px">Revoke</button>
            </div>` : ""}
          </div>
        `).join("");

    el.querySelectorAll<HTMLButtonElement>(".revoke-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const key = btn.dataset["key"]!;
        if (!confirm("Revoke this agent key?")) return;
        agentsApi.revoke(key).then(() => agentsApi.list())
          .then(updated => refresh(updated))
          .catch(err => {
            body.querySelector<HTMLElement>("#agent-error")!.textContent = err.message;
          });
      });
    });
  }

  refresh(list);

  body.querySelector("#add-agent-btn")!.addEventListener("click", () => {
    const name = (body.querySelector<HTMLInputElement>("#new-agent-name")!).value.trim();
    const desc = (body.querySelector<HTMLInputElement>("#new-agent-desc")!).value.trim();
    if (!name) return;
    agentsApi.register(name, desc || undefined).then(result => {
      const keyDisplay = body.querySelector<HTMLElement>("#new-key-display")!;
      const keyValue = body.querySelector<HTMLElement>("#new-key-value")!;
      keyDisplay.style.display = "block";
      keyValue.textContent = result.key;
      body.querySelector<HTMLInputElement>("#new-agent-name")!.value = "";
      body.querySelector<HTMLInputElement>("#new-agent-desc")!.value = "";
      body.querySelector<HTMLElement>("#agent-error")!.textContent = "";
      return agentsApi.list();
    }).then(updated => refresh(updated))
      .catch(err => {
        body.querySelector<HTMLElement>("#agent-error")!.textContent = err.message;
      });
  });
}
