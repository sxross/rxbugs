import "./style.css";
import { getToken, setToken } from "./api";
import * as ListView from "./views/ListView";
import * as DetailView from "./views/DetailView";
import * as BugForm from "./views/BugForm";
import * as AdminView from "./views/AdminView";
import { bugs as bugsApi } from "./api";
import { navigate, escHtml } from "./utils";

const app = document.getElementById("app")!;

// ---------------------------------------------------------------------------
// Router
// ---------------------------------------------------------------------------

function route(): void {
  const hash = window.location.hash.slice(1) || "/";
  const token = getToken();

  if (!token || hash === "/login") {
    renderLogin();
    return;
  }

  // /bugs/:id/edit
  const editMatch = hash.match(/^\/bugs\/([^/]+)\/edit$/);
  if (editMatch) {
    const bugId = editMatch[1];
    bugsApi.get(bugId).then(bug => {
      BugForm.render(app, {
        title: `Edit ${escHtml(bugId)}`,
        initial: bug,
        bugId,
        onSuccess: () => navigate(`/bugs/${bugId}`),
      });
    }).catch(() => {
      BugForm.render(app, {
        title: `Edit ${escHtml(bugId)}`,
        bugId,
        onSuccess: () => navigate(`/bugs/${bugId}`),
      });
    });
    return;
  }

  // /bugs/new
  if (hash === "/bugs/new") {
    BugForm.render(app, {
      title: "New Bug",
      onSuccess: (bug) => navigate(`/bugs/${bug.id}`),
    });
    return;
  }

  // /bugs/:id
  const detailMatch = hash.match(/^\/bugs\/([^/]+)$/);
  if (detailMatch) {
    DetailView.render(app, detailMatch[1]);
    return;
  }

  // /admin
  if (hash === "/admin") {
    AdminView.render(app);
    return;
  }

  // default: /
  ListView.render(app);
}

// ---------------------------------------------------------------------------
// Login screen
// ---------------------------------------------------------------------------

const _isMobile = /Mobi|Android|iPhone|iPad|iPod/i.test(navigator.userAgent)
  || (navigator.maxTouchPoints > 1 && window.matchMedia("(pointer: coarse)").matches);

function renderLogin(): void {
  const qrBlock = _isMobile
    ? `<div class="qr-section qr-mobile-hint">
         <p class="qr-label">Sign in on desktop</p>
         <p class="qr-hint">Open RxBugs on a desktop browser, click <strong>Show QR Code</strong>, then scan it with this device.</p>
       </div>`
    : `<div class="qr-section" id="qr-section">
         <button class="btn btn-secondary" id="show-qr-btn">Show QR Code</button>
         <p class="qr-label" id="qr-label" style="display:none">Scan with your phone to sign in</p>
         <img class="qr-code" id="qr-img" src="/auth/qr" alt="QR code magic link" style="display:none" />
       </div>`;

  app.innerHTML = `
    <div class="login-wrap">
      <div class="login-card">
        <h2>RxBugs</h2>
        ${qrBlock}
        <div class="qr-divider"><span>or paste token</span></div>
        <div class="form-group">
          <label class="form-label" for="token-input">Access token</label>
          <input class="form-control" id="token-input" type="password"
            placeholder="Paste your BUGTRACKER_TOKEN" autocomplete="current-password" />
        </div>
        <div class="form-error" id="login-error"></div>
        <div class="form-actions">
          <button class="btn btn-primary" id="login-btn">Sign in</button>
        </div>
        <div style="text-align: center; margin-top: 1.5rem; padding-top: 1.5rem; border-top: 1px solid #ccc;">
          <p style="margin-bottom: 1rem; color: #666;">Or scan with your phone:</p>
          <button class="btn" id="show-qr-btn" style="margin-bottom: 1rem;">Show QR Code</button>
          <div id="qr-container" style="display: none;">
            <img id="qr-image" src="" alt="QR Code" style="max-width: 256px; margin: 0 auto; display: block;" />
            <p style="margin-top: 0.5rem; font-size: 0.875rem; color: #666;">Expires in 5 minutes</p>
          </div>
        </div>
      </div>
    </div>
  `;

  if (!_isMobile) {
    const showQrBtn = app.querySelector<HTMLButtonElement>("#show-qr-btn")!;
    const qrImg = app.querySelector<HTMLImageElement>("#qr-img")!;
    const qrLabel = app.querySelector<HTMLElement>("#qr-label")!;
    showQrBtn.addEventListener("click", () => {
      showQrBtn.style.display = "none";
      qrLabel.style.display = "";
      qrImg.style.display = "";
    });
  }

  const tokenInput = app.querySelector<HTMLInputElement>("#token-input")!;
  const loginBtn = app.querySelector<HTMLButtonElement>("#login-btn")!;
  const errorEl = app.querySelector<HTMLElement>("#login-error")!;
  const showQrBtn = app.querySelector<HTMLButtonElement>("#show-qr-btn")!;
  const qrContainer = app.querySelector<HTMLElement>("#qr-container")!;
  const qrImage = app.querySelector<HTMLImageElement>("#qr-image")!;

  async function tryLogin(): Promise<void> {
    const token = tokenInput.value.trim();
    if (!token) return;
    setToken(token);
    // Test the token with a lightweight request
    try {
      await bugsApi.list({ status: "open" });
      navigate("/");
    } catch {
      errorEl.textContent = "Invalid token. Please try again.";
      loginBtn.disabled = false;
      loginBtn.textContent = "Sign in";
    }
  }

  loginBtn.addEventListener("click", () => {
    loginBtn.disabled = true;
    loginBtn.textContent = "Checking…";
    tryLogin();
  });

  tokenInput.addEventListener("keydown", e => {
    if (e.key === "Enter") {
      loginBtn.disabled = true;
      loginBtn.textContent = "Checking…";
      tryLogin();
    }
  });

  showQrBtn.addEventListener("click", () => {
    // Note: QR endpoint requires auth, so we need a valid token first.
    // For desktop users, they paste token, then can show QR for mobile.
    const token = getToken() || tokenInput.value.trim();
    if (!token) {
      errorEl.textContent = "Please enter your token first to generate QR code.";
      return;
    }
    
    // Temporarily set token to make the request
    const previousToken = getToken();
    setToken(token);
    
    // Fetch QR code
    fetch("/auth/qr", {
      headers: { "Authorization": `Bearer ${token}` }
    })
      .then(resp => {
        if (!resp.ok) throw new Error("Failed to generate QR code");
        return resp.blob();
      })
      .then(blob => {
        qrImage.src = URL.createObjectURL(blob);
        qrContainer.style.display = "block";
        showQrBtn.style.display = "none";
      })
      .catch(() => {
        errorEl.textContent = "Failed to generate QR code. Check your token.";
        // Restore previous token state
        if (previousToken) {
          setToken(previousToken);
        }
      });
  });
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

// Handle magic-link token from QR code scan: ?token=<TOKEN>
const _urlToken = new URLSearchParams(window.location.search).get("token");
if (_urlToken) {
  setToken(_urlToken);
  // Remove the token from the address bar before routing
  history.replaceState(null, "", window.location.pathname + window.location.hash);
}

window.addEventListener("hashchange", route);
route();
