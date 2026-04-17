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
        title: `Edit ${bugId}`,
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

function renderLogin(): void {
  app.innerHTML = `
    <div class="login-wrap">
      <div class="login-card">
        <h2>RxBugs</h2>
        <div class="form-group">
          <label class="form-label" for="token-input">Access token</label>
          <input class="form-control" id="token-input" type="password"
            placeholder="Paste your BUGTRACKER_TOKEN" autocomplete="current-password" />
        </div>
        <div class="form-error" id="login-error"></div>
        <div class="form-actions">
          <button class="btn btn-primary" id="login-btn">Sign in</button>
        </div>
      </div>
    </div>
  `;

  const tokenInput = app.querySelector<HTMLInputElement>("#token-input")!;
  const loginBtn = app.querySelector<HTMLButtonElement>("#login-btn")!;
  const errorEl = app.querySelector<HTMLElement>("#login-error")!;

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
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

window.addEventListener("hashchange", route);
route();
