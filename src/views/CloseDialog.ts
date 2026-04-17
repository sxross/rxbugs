import { bugs as bugsApi } from "../api";
import type { Resolution } from "../types";
import { escHtml } from "../utils";

const RESOLUTIONS: { value: Resolution; label: string }[] = [
  { value: "fixed", label: "Fixed" },
  { value: "no_repro", label: "No Repro" },
  { value: "duplicate", label: "Duplicate" },
  { value: "wont_fix", label: "Won't Fix" },
];

export function showCloseDialog(bugId: string, onClosed: () => void): void {
  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";

  overlay.innerHTML = `
    <div class="modal" role="dialog" aria-modal="true" aria-label="Close bug">
      <div class="modal-title">Close ${escHtml(bugId)}</div>

      <div class="form-group">
        <label class="form-label">Resolution *</label>
        <div class="segmented" id="res-seg" style="flex-wrap:wrap;gap:6px">
          ${RESOLUTIONS.map(r => `
            <button type="button" class="segmented-btn" data-val="${r.value}"
              style="flex:1 1 auto;min-width:100px">${escHtml(r.label)}</button>
          `).join("")}
        </div>
        <div class="form-error" id="res-error"></div>
      </div>

      <div id="duplicate-field" style="display:none" class="form-group">
        <label class="form-label">Canonical bug ID</label>
        <input class="form-control" id="duplicate-id" type="text" placeholder="BUG-XXXX" />
        <div class="form-hint">Link the original bug before or after closing.</div>
      </div>

      <div class="form-group">
        <label class="form-label">Annotation (optional)</label>
        <textarea class="form-control" id="close-annotation" rows="3"
          placeholder="Describe the fix, reason, or next steps…"></textarea>
      </div>

      <div id="warnings" style="display:none" class="warning-banner"></div>
      <div class="form-error" id="close-error"></div>

      <div class="form-actions">
        <button class="btn btn-danger" id="confirm-btn">Confirm close</button>
        <button class="btn btn-secondary" id="cancel-btn">Cancel</button>
      </div>
    </div>
  `;

  document.body.appendChild(overlay);

  let selectedResolution: Resolution | null = null;

  // Resolution selection
  overlay.querySelectorAll<HTMLButtonElement>("#res-seg .segmented-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      selectedResolution = btn.dataset["val"] as Resolution;
      overlay.querySelectorAll("#res-seg .segmented-btn").forEach(b =>
        b.classList.toggle("active", (b as HTMLElement).dataset["val"] === selectedResolution)
      );
      const dupField = overlay.querySelector<HTMLElement>("#duplicate-field")!;
      dupField.style.display = selectedResolution === "duplicate" ? "block" : "none";
    });
  });

  // Close on overlay click
  overlay.addEventListener("click", e => {
    if (e.target === overlay) cleanup();
  });

  overlay.querySelector("#cancel-btn")!.addEventListener("click", cleanup);

  overlay.querySelector("#confirm-btn")!.addEventListener("click", async () => {
    const resError = overlay.querySelector<HTMLElement>("#res-error")!;
    if (!selectedResolution) {
      resError.textContent = "Please select a resolution.";
      return;
    }
    resError.textContent = "";

    const annotation = overlay.querySelector<HTMLTextAreaElement>("#close-annotation")!.value.trim();
    const confirmBtn = overlay.querySelector<HTMLButtonElement>("#confirm-btn")!;
    const closeError = overlay.querySelector<HTMLElement>("#close-error")!;
    const warningsEl = overlay.querySelector<HTMLElement>("#warnings")!;

    confirmBtn.disabled = true;
    confirmBtn.textContent = "Closing…";
    closeError.textContent = "";

    try {
      const result = await bugsApi.close(bugId, selectedResolution, annotation || undefined);
      if (result.warnings?.length) {
        warningsEl.textContent = result.warnings.join("\n");
        warningsEl.style.display = "block";
      }
      cleanup();
      onClosed();
    } catch (err: unknown) {
      closeError.textContent = (err as Error).message;
      confirmBtn.disabled = false;
      confirmBtn.textContent = "Confirm close";
    }
  });

  // Trap focus
  setTimeout(() => {
    overlay.querySelector<HTMLButtonElement>("#res-seg .segmented-btn")?.focus();
  }, 50);

  function cleanup(): void {
    overlay.remove();
  }
}
