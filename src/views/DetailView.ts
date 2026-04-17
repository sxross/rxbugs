import { bugs as bugsApi, annotations as annotationsApi, artifacts as artifactsApi } from "../api";
import type { Bug } from "../types";
import { navigate, escHtml, formatAge, priorityBadge, severityBadge } from "../utils";
import { showCloseDialog } from "./CloseDialog";

export function render(container: HTMLElement, bugId: string): void {
  container.innerHTML = `<div class="loading-center"><div class="spinner"></div></div>`;
  bugsApi.get(bugId).then(bug => renderBug(container, bug)).catch(err => {
    container.innerHTML = `<div class="error-banner">${escHtml(err.message)}</div>`;
  });
}

function renderBug(container: HTMLElement, bug: Bug): void {
  const isClosed = bug.status === "closed";

  container.innerHTML = `
    <header>
      <button class="back-btn" id="back">← Bugs</button>
      <span class="badge badge-${bug.status}">${bug.status}</span>
      <div></div>
    </header>

    <div class="detail-header">
      <div class="detail-id">${escHtml(bug.id)} · ${escHtml(bug.product)}</div>
      <h2 class="detail-title">${escHtml(bug.title)}</h2>
      <div class="detail-badges">
        ${bug.priority ? priorityBadge(bug.priority) : ""}
        ${bug.severity ? severityBadge(bug.severity) : ""}
        ${bug.area ? `<span class="badge" style="background:var(--surface2);color:var(--text-dim)">${escHtml(bug.area)}</span>` : ""}
        ${isClosed ? `<span class="badge" style="background:var(--surface2);color:var(--text-dim)">${escHtml(bug.resolution)}</span>` : ""}
      </div>
      <div class="detail-meta">
        Created ${formatAge(bug.created_at)} · Updated ${formatAge(bug.updated_at)}
      </div>
    </div>

    <!-- Action bar -->
    <div class="action-bar">
      <button class="btn btn-secondary" id="edit-btn">Edit</button>
      <button class="btn btn-secondary" id="annotate-btn">Annotate</button>
      <button class="btn btn-secondary" id="attach-btn">Attach</button>
      <input type="file" id="file-input" style="display:none" />
      ${!isClosed
        ? `<button class="btn btn-danger" id="close-btn">Close</button>`
        : `<button class="btn btn-secondary" id="reopen-btn">Reopen</button>`
      }
    </div>

    ${bug.description ? `
    <div class="detail-section">
      <h3>Description</h3>
      <div class="description-body">${escHtml(bug.description)}</div>
    </div>` : ""}

    ${bug.related_bugs.length ? `
    <div class="detail-section">
      <h3>Related</h3>
      <div class="related-list">
        ${bug.related_bugs.map(id =>
          `<a class="related-chip" href="#/bugs/${escHtml(id)}">${escHtml(id)}</a>`
        ).join("")}
      </div>
    </div>` : ""}

    <div class="detail-section" id="annotations-section">
      <h3>Annotations (${bug.annotations.length})</h3>
      <div id="annotations-list">
        ${bug.annotations.map(a => `
          <div class="annotation ${a.author_type === "agent" ? "annotation-agent" : ""}">
            <div class="annotation-header">
              <span class="annotation-author">${escHtml(a.author)}${a.author_type === "agent" ? " 🤖" : ""}</span>
              <span class="annotation-time">${formatAge(a.created_at)}</span>
            </div>
            <div class="annotation-body">${escHtml(a.body)}</div>
          </div>
        `).join("")}
        ${bug.annotations.length === 0 ? `<div class="empty-state" style="padding:16px 0">No annotations yet.</div>` : ""}
      </div>
      <div id="inline-annotate" style="display:none">
        <div class="inline-annotate">
          <textarea class="form-control" id="annotation-body" placeholder="Add a note…" rows="3"></textarea>
          <div style="display:flex;gap:8px">
            <button class="btn btn-primary" id="annotation-submit">Post</button>
            <button class="btn btn-secondary" id="annotation-cancel">Cancel</button>
          </div>
          <div class="form-error" id="annotation-error"></div>
        </div>
      </div>
    </div>

    ${bug.artifacts.length ? `
    <div class="detail-section">
      <h3>Attachments (${bug.artifacts.length})</h3>
      <div id="artifacts-list">
        ${bug.artifacts.map(a => `
          <div class="artifact-row">
            <div>
              <div class="artifact-name">${escHtml(a.filename)}</div>
              <div class="artifact-meta">${escHtml(a.mime_type ?? "unknown")} · ${formatAge(a.uploaded_at)}</div>
            </div>
            <a class="btn btn-secondary" href="${escHtml(a.url)}" download="${escHtml(a.filename)}" style="font-size:0.8rem;min-height:36px">↓</a>
          </div>
        `).join("")}
      </div>
    </div>` : ""}
  `;

  // ---- Back ----
  container.querySelector("#back")!.addEventListener("click", () => navigate("/"));

  // ---- Edit ----
  container.querySelector("#edit-btn")!.addEventListener("click", () => navigate(`/bugs/${bug.id}/edit`));

  // ---- Close ----
  const closeBtn = container.querySelector<HTMLButtonElement>("#close-btn");
  if (closeBtn) {
    closeBtn.addEventListener("click", () => {
      showCloseDialog(bug.id, () => render(container, bug.id));
    });
  }

  // ---- Reopen ----
  const reopenBtn = container.querySelector<HTMLButtonElement>("#reopen-btn");
  if (reopenBtn) {
    reopenBtn.addEventListener("click", () => {
      bugsApi.reopen(bug.id).then(() => render(container, bug.id)).catch(err => {
        alert(err.message);
      });
    });
  }

  // ---- Annotate toggle ----
  const annotateBtn = container.querySelector("#annotate-btn")!;
  const inlineAnnotate = container.querySelector<HTMLElement>("#inline-annotate")!;
  annotateBtn.addEventListener("click", () => {
    const isShown = inlineAnnotate.style.display !== "none";
    inlineAnnotate.style.display = isShown ? "none" : "block";
    if (!isShown) container.querySelector<HTMLTextAreaElement>("#annotation-body")?.focus();
  });
  container.querySelector("#annotation-cancel")!.addEventListener("click", () => {
    inlineAnnotate.style.display = "none";
  });
  container.querySelector("#annotation-submit")!.addEventListener("click", async () => {
    const body = container.querySelector<HTMLTextAreaElement>("#annotation-body")!.value.trim();
    if (!body) return;
    const errEl = container.querySelector<HTMLElement>("#annotation-error")!;
    try {
      await annotationsApi.create(bug.id, body);
      render(container, bug.id);
    } catch (err: unknown) {
      errEl.textContent = (err as Error).message;
    }
  });

  // ---- Attach file ----
  const attachBtn = container.querySelector("#attach-btn")!;
  const fileInput = container.querySelector<HTMLInputElement>("#file-input")!;
  attachBtn.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", async () => {
    const file = fileInput.files?.[0];
    if (!file) return;
    try {
      await artifactsApi.upload(bug.id, file);
      render(container, bug.id);
    } catch (err: unknown) {
      alert((err as Error).message);
    }
  });
}
