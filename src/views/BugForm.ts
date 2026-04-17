/**
 * Shared bug form — used for both new bug creation and editing.
 * Takes an optional initialValues object for pre-population (edit mode).
 */

import { bugs as bugsApi, products as productsApi, relations as relationsApi } from "../api";
import type { Bug, BugSummary } from "../types";
import { navigate, escHtml } from "../utils";

interface FormValues {
  product: string;
  title: string;
  description: string;
  area: string;
  priority: string;
  severity: string;
}

export function render(
  container: HTMLElement,
  opts: {
    title: string;
    initial?: Partial<Bug>;
    bugId?: string; // set when editing
    onSuccess: (bug: BugSummary) => void;
  },
): void {
  const iv = opts.initial ?? {};

  container.innerHTML = `
    <header>
      <button class="back-btn" id="back">← Back</button>
      <h1 style="font-size:1rem;color:var(--text)">${escHtml(opts.title)}</h1>
      <div></div>
    </header>

    <form id="bug-form">
      <div class="form-group">
        <label class="form-label" for="product">Product *</label>
        <input class="form-control" id="product" name="product" type="text"
          autocomplete="off" list="product-list" required value="${escHtml(iv.product ?? "")}" />
        <datalist id="product-list"></datalist>
        <div class="form-error" id="product-error"></div>
      </div>

      <div class="form-group">
        <label class="form-label" for="title">Title *</label>
        <input class="form-control" id="title" name="title" type="text"
          required value="${escHtml(iv.title ?? "")}" />
        <div class="form-error" id="title-error"></div>
      </div>

      <div class="form-group">
        <label class="form-label" for="description">Description</label>
        <textarea class="form-control" id="description" name="description"
          placeholder="Markdown supported">${escHtml(iv.description ?? "")}</textarea>
      </div>

      <div class="form-group">
        <label class="form-label" for="area">Area</label>
        <select class="form-control" id="area" name="area">
          <option value="">— none —</option>
          <option value="ui"${iv.area === "ui" ? " selected" : ""}>UI</option>
          <option value="middleware"${iv.area === "middleware" ? " selected" : ""}>Middleware</option>
          <option value="backend"${iv.area === "backend" ? " selected" : ""}>Backend</option>
          <option value="database"${iv.area === "database" ? " selected" : ""}>Database</option>
          <option value="sync"${iv.area === "sync" ? " selected" : ""}>Sync</option>
        </select>
      </div>

      <div class="form-group">
        <label class="form-label">Priority</label>
        <div class="segmented" id="priority-seg">
          <button type="button" class="segmented-btn${iv.priority === 1 ? " active" : ""}" data-val="1">P1</button>
          <button type="button" class="segmented-btn${iv.priority === 2 ? " active" : ""}" data-val="2">P2</button>
          <button type="button" class="segmented-btn${iv.priority === 3 ? " active" : ""}" data-val="3">P3</button>
        </div>
        <input type="hidden" id="priority" name="priority" value="${iv.priority ?? ""}" />
      </div>

      <div class="form-group">
        <label class="form-label" for="severity">Severity</label>
        <select class="form-control" id="severity" name="severity">
          <option value="">— none —</option>
          <option value="showstopper"${iv.severity === "showstopper" ? " selected" : ""}>Showstopper</option>
          <option value="serious"${iv.severity === "serious" ? " selected" : ""}>Serious</option>
          <option value="enhancement"${iv.severity === "enhancement" ? " selected" : ""}>Enhancement</option>
          <option value="nice_to_have"${iv.severity === "nice_to_have" ? " selected" : ""}>Nice to have</option>
        </select>
      </div>

      ${opts.bugId ? `
      <div class="form-group" id="relations-group">
        <label class="form-label">Related Bugs</label>
        <div id="related-list" style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px"></div>
        <div style="display:flex;gap:8px">
          <input class="form-control" id="add-related-input" type="text"
            placeholder="BUG-XXXX" style="max-width:160px" />
          <button type="button" class="btn btn-secondary" id="add-related-btn">Add</button>
        </div>
        <div class="form-error" id="related-error"></div>
      </div>` : ""}

      <div class="form-error" id="form-error"></div>

      <div class="form-actions">
        <button type="submit" class="btn btn-primary" id="submit-btn">
          ${opts.bugId ? "Save changes" : "Create bug"}
        </button>
        <button type="button" class="btn btn-secondary" id="cancel-btn">Cancel</button>
      </div>
    </form>
  `;

  // ---- product autocomplete ----
  productsApi.list().then(list => {
    const dl = container.querySelector<HTMLDataListElement>("#product-list")!;
    list.forEach(p => {
      const opt = document.createElement("option");
      opt.value = p.name;
      dl.appendChild(opt);
    });
  }).catch(() => { /* non-fatal */ });

  // ---- priority segmented control ----
  let selectedPriority: string = String(iv.priority ?? "");
  const priorityHidden = container.querySelector<HTMLInputElement>("#priority")!;
  container.querySelectorAll<HTMLButtonElement>("#priority-seg .segmented-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const val = btn.dataset["val"]!;
      if (selectedPriority === val) {
        selectedPriority = "";
      } else {
        selectedPriority = val;
      }
      priorityHidden.value = selectedPriority;
      container.querySelectorAll("#priority-seg .segmented-btn").forEach(b =>
        b.classList.toggle("active", (b as HTMLElement).dataset["val"] === selectedPriority)
      );
    });
  });

  // ---- related bugs (edit mode only) ----
  const relatedBugs: string[] = [...(iv.related_bugs ?? [])];
  function renderRelated(): void {
    const list = container.querySelector<HTMLElement>("#related-list");
    if (!list) return;
    list.innerHTML = "";
    relatedBugs.forEach(id => {
      const chip = document.createElement("span");
      chip.className = "related-chip";
      chip.style.cursor = "default";
      chip.innerHTML = `${escHtml(id)} <button type="button" style="background:none;border:none;color:var(--text-dim);cursor:pointer;padding:0 0 0 6px;min-height:unset;min-width:unset" data-id="${escHtml(id)}">×</button>`;
      chip.querySelector("button")!.addEventListener("click", () => {
        relationsApi.remove(opts.bugId!, id).then(() => {
          relatedBugs.splice(relatedBugs.indexOf(id), 1);
          renderRelated();
        }).catch(err => {
          const errEl = container.querySelector<HTMLElement>("#related-error");
          if (errEl) errEl.textContent = err.message;
        });
      });
      list.appendChild(chip);
    });
  }
  if (opts.bugId) {
    renderRelated();
    const addInput = container.querySelector<HTMLInputElement>("#add-related-input")!;
    container.querySelector("#add-related-btn")!.addEventListener("click", () => {
      const val = addInput.value.trim().toUpperCase();
      if (!val) return;
      relationsApi.add(opts.bugId!, val).then(() => {
        relatedBugs.push(val);
        addInput.value = "";
        renderRelated();
      }).catch(err => {
        const errEl = container.querySelector<HTMLElement>("#related-error");
        if (errEl) errEl.textContent = err.message;
      });
    });
  }

  // ---- form submission ----
  const formEl = container.querySelector<HTMLFormElement>("#bug-form")!;
  const submitBtn = container.querySelector<HTMLButtonElement>("#submit-btn")!;
  const formError = container.querySelector<HTMLElement>("#form-error")!;

  formEl.addEventListener("submit", async e => {
    e.preventDefault();
    const fd = new FormData(formEl);
    const vals: FormValues = {
      product: (fd.get("product") as string).trim(),
      title: (fd.get("title") as string).trim(),
      description: (fd.get("description") as string).trim(),
      area: fd.get("area") as string,
      priority: selectedPriority,
      severity: fd.get("severity") as string,
    };

    // Client-side validation
    let valid = true;
    if (!vals.product) {
      container.querySelector<HTMLElement>("#product-error")!.textContent = "Product is required.";
      valid = false;
    } else {
      container.querySelector<HTMLElement>("#product-error")!.textContent = "";
    }
    if (!vals.title) {
      container.querySelector<HTMLElement>("#title-error")!.textContent = "Title is required.";
      valid = false;
    } else {
      container.querySelector<HTMLElement>("#title-error")!.textContent = "";
    }
    if (!valid) return;

    submitBtn.disabled = true;
    submitBtn.textContent = "Saving…";
    formError.textContent = "";

    const payload: Record<string, unknown> = {
      product: vals.product,
      title: vals.title,
    };
    if (vals.description) payload["description"] = vals.description;
    if (vals.area) payload["area"] = vals.area;
    if (vals.priority) payload["priority"] = parseInt(vals.priority, 10);
    if (vals.severity) payload["severity"] = vals.severity;

    try {
      let bug: BugSummary;
      if (opts.bugId) {
        bug = await bugsApi.update(opts.bugId, payload as Parameters<typeof bugsApi.update>[1]);
      } else {
        bug = await bugsApi.create(payload as Parameters<typeof bugsApi.create>[0]);
      }
      opts.onSuccess(bug);
    } catch (err: unknown) {
      formError.textContent = (err as Error).message;
      submitBtn.disabled = false;
      submitBtn.textContent = opts.bugId ? "Save changes" : "Create bug";
    }
  });

  container.querySelector("#back")!.addEventListener("click", () => history.back());
  container.querySelector("#cancel-btn")!.addEventListener("click", () => history.back());
}
