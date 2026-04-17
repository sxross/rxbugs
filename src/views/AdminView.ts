import { agents as agentsApi, products as productsApi } from "../api";
import type { Agent, Product } from "../types";
import { navigate, escHtml } from "../utils";

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

  Promise.all([productsApi.list(true), agentsApi.list()]).then(([prods, agts]) => {
    renderAdmin(container.querySelector<HTMLElement>("#admin-body")!, prods, agts);
  }).catch(err => {
    container.querySelector<HTMLElement>("#admin-body")!.innerHTML =
      `<div class="error-banner">${escHtml(err.message)}</div>`;
  });
}

function renderAdmin(
  body: HTMLElement,
  products: Product[],
  agentsList: Agent[],
): void {
  body.innerHTML = `
    <!-- ---- Products ---- -->
    <div class="admin-section">
      <h2>Products</h2>
      <div id="products-list"></div>
      <div style="display:flex;gap:8px;margin-top:10px">
        <input class="form-control" id="new-product-name" type="text"
          placeholder="Product name" style="max-width:200px" />
        <button class="btn btn-secondary" id="add-product-btn">Add</button>
      </div>
      <div class="form-error" id="product-error"></div>
    </div>

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

  // ---- Render helpers ----
  function renderProducts(list: Product[]): void {
    const el = body.querySelector<HTMLElement>("#products-list")!;
    el.innerHTML = list.length === 0
      ? `<div class="empty-state" style="padding:12px 0">No products yet.</div>`
      : list.map(p => `
          <div class="admin-row" data-product="${escHtml(p.name)}">
            <div class="admin-row-info">
              <div class="admin-row-name">${escHtml(p.name)}${p.archived ? " (archived)" : ""}</div>
              <div class="admin-row-meta">${p.bug_count} bug${p.bug_count !== 1 ? "s" : ""}</div>
            </div>
            <div class="admin-row-actions">
              <button class="btn btn-secondary rename-btn" data-name="${escHtml(p.name)}"
                style="font-size:0.78rem;min-height:36px">Rename</button>
              ${!p.archived ? `<button class="btn btn-danger archive-btn" data-name="${escHtml(p.name)}"
                style="font-size:0.78rem;min-height:36px">Archive</button>` : ""}
            </div>
          </div>
        `).join("");

    el.querySelectorAll<HTMLButtonElement>(".rename-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const old = btn.dataset["name"]!;
        const newName = prompt(`Rename "${old}" to:`, old);
        if (!newName || newName === old) return;
        productsApi.rename(old, newName).then(() => {
          return productsApi.list(true);
        }).then(updated => renderProducts(updated)).catch(err => {
          body.querySelector<HTMLElement>("#product-error")!.textContent = err.message;
        });
      });
    });

    el.querySelectorAll<HTMLButtonElement>(".archive-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const name = btn.dataset["name"]!;
        if (!confirm(`Archive "${name}"?`)) return;
        productsApi.archive(name).then(() => productsApi.list(true))
          .then(updated => renderProducts(updated))
          .catch(err => {
            body.querySelector<HTMLElement>("#product-error")!.textContent = err.message;
          });
      });
    });
  }

  function renderAgents(list: Agent[]): void {
    const el = body.querySelector<HTMLElement>("#agents-list")!;
    el.innerHTML = list.length === 0
      ? `<div class="empty-state" style="padding:12px 0">No agents registered.</div>`
      : list.map(a => `
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
          .then(updated => renderAgents(updated))
          .catch(err => {
            body.querySelector<HTMLElement>("#agent-error")!.textContent = err.message;
          });
      });
    });
  }

  renderProducts(products);
  renderAgents(agentsList);

  // ---- Add product ----
  body.querySelector("#add-product-btn")!.addEventListener("click", () => {
    const name = (body.querySelector<HTMLInputElement>("#new-product-name")!).value.trim();
    if (!name) return;
    productsApi.create(name).then(() => productsApi.list(true))
      .then(updated => {
        renderProducts(updated);
        body.querySelector<HTMLInputElement>("#new-product-name")!.value = "";
        body.querySelector<HTMLElement>("#product-error")!.textContent = "";
      })
      .catch(err => {
        body.querySelector<HTMLElement>("#product-error")!.textContent = err.message;
      });
  });

  // ---- Register agent ----
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
    }).then(updated => renderAgents(updated))
      .catch(err => {
        body.querySelector<HTMLElement>("#agent-error")!.textContent = err.message;
      });
  });
}
