/** Shared UI utility functions. */

import { marked } from "marked";
import DOMPurify from "dompurify";

marked.setOptions({ breaks: true, gfm: true });

const MD_ALLOWED_TAGS = [
  "p", "em", "strong", "code", "pre", "ul", "ol", "li",
  "blockquote", "a", "br", "h1", "h2", "h3", "h4", "hr",
  "del", "s",
];
const MD_ALLOWED_ATTR = ["href", "title"];

/**
 * Parse markdown and sanitize the resulting HTML.
 * Safe to inject into innerHTML.
 */
export function renderMarkdown(src: string | null | undefined): string {
  if (!src) return "";
  const raw = marked.parse(src, { async: false }) as string;
  return DOMPurify.sanitize(raw, {
    ALLOWED_TAGS: MD_ALLOWED_TAGS,
    ALLOWED_ATTR: MD_ALLOWED_ATTR,
  });
}

export function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  attrs: Record<string, string> = {},
  textContent?: string,
): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "className") e.className = v;
    else e.setAttribute(k, v);
  }
  if (textContent !== undefined) e.textContent = textContent;
  return e;
}

export function navigate(path: string): void {
  window.location.hash = `#${path}`;
}

export function escHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function formatAge(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60_000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d < 30) return `${d}d ago`;
  return new Date(iso).toLocaleDateString();
}

export function priorityBadge(p: number | null): string {
  if (!p) return "";
  return `<span class="badge badge-p${p}">P${p}</span>`;
}

export function severityBadge(s: string | null): string {
  if (!s) return "";
  return `<span class="badge badge-${s}">${s.replace("_", " ")}</span>`;
}
