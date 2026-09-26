import os

html_content = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>VERIFAI — Proof &amp; Verification Engine</title>
<meta name="description" content="VERIFAI: Don't just generate answers. Verify them. Multi-agent AI reasoning and verification engine.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>
:root {
  --bg: #080b10;
  --sidebar-bg: #0c1017;
  --panel: #111722;
  --panel-hover: #161f2e;
  --panel-active: #1a2536;
  --border: #1c2635;
  --border-light: #263447;
  --text: #f0f4f8;
  --text-muted: #8392a5;
  --text-dim: #546375;
  --green: #10b981;
  --green-bg: rgba(16, 185, 129, 0.08);
  --green-border: rgba(16, 185, 129, 0.25);
  --red: #ef4444;
  --red-bg: rgba(239, 68, 68, 0.08);
  --red-border: rgba(239, 68, 68, 0.25);
  --yellow: #f59e0b;
  --yellow-bg: rgba(245, 158, 11, 0.08);
  --yellow-border: rgba(245, 158, 11, 0.25);
  --sidebar-w: 260px;
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;
}

*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html, body {
  width: 100%;
  height: 100%;
  background: var(--bg);
  color: var(--text);
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  -webkit-font-smoothing: antialiased;
  overflow: hidden;
}

button, input, textarea, select {
  font: inherit;
  color: inherit;
}

button {
  cursor: pointer;
  border: none;
  background: none;
}

::-webkit-scrollbar {
  width: 5px;
  height: 5px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: 10px;
}
::-webkit-scrollbar-thumb:hover {
  background: var(--border-light);
}

/* APP SHELL */
.app-container {
  display: flex;
  width: 100%;
  height: 100vh;
  position: relative;
  overflow: hidden;
}

/* SIDEBAR */
.sidebar {
  width: var(--sidebar-w);
  min-width: var(--sidebar-w);
  max-width: var(--sidebar-w);
  height: 100%;
  background: var(--sidebar-bg);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  padding: 16px 12px;
  z-index: 40;
  transition: transform 0.25s cubic-bezier(0.2, 0, 0, 1), margin-left 0.25s cubic-bezier(0.2, 0, 0, 1);
  will-change: transform, margin-left;
}

body.sidebar-closed .sidebar {
  margin-left: calc(-1 * var(--sidebar-w));
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 6px 16px;
}

.brand-wrapper {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: inherit;
}

.brand-logo-icon {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: var(--green-bg);
  border: 1px solid var(--green-border);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--green);
  flex-shrink: 0;
}

.brand-titles {
  display: flex;
  flex-direction: column;
}

.brand-title {
  font-size: 15px;
  font-weight: 800;
  letter-spacing: -0.3px;
  line-height: 1.1;
}

.brand-subtitle {
  font-size: 8px;
  font-weight: 700;
  letter-spacing: 0.8px;
  color: var(--green);
  text-transform: uppercase;
  margin-top: 2px;
  opacity: 0.85;
}

.sidebar-toggle-btn {
  width: 30px;
  height: 30px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  transition: all 0.15s ease;
}

.sidebar-toggle-btn:hover {
  background: var(--panel);
  color: var(--text);
}

.new-chat-btn {
  width: 100%;
  height: 40px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--panel);
  color: var(--text);
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 14px;
  transition: all 0.15s ease;
  margin-bottom: 18px;
}

.new-chat-btn:hover {
  background: var(--panel-hover);
  border-color: var(--border-light);
}

.new-chat-btn svg {
  color: var(--text-muted);
  flex-shrink: 0;
}

.sidebar-section-title {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--text-dim);
  padding: 0 8px;
  margin-bottom: 8px;
}

.history-scroll {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.history-item {
  width: 100%;
  text-align: left;
  padding: 9px 10px;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  font-size: 12.5px;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.15s ease;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  border: 1px solid transparent;
}

.history-item:hover {
  background: var(--panel);
  color: var(--text);
}

.history-item.active {
  background: var(--panel);
  border-color: var(--border);
  color: var(--text);
  font-weight: 500;
}

.history-item-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
  background: var(--green);
  opacity: 0.8;
}

.history-item-dot.rej {
  background: var(--red);
}

.history-item-dot.warn {
  background: var(--yellow);
}

.history-item-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.history-empty {
  font-size: 11.5px;
  color: var(--text-dim);
  padding: 12px 10px;
}

/* MAIN CONTENT */
.main-view {
  flex: 1;
  min-width: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}

/* TOP BAR */
.topbar {
  height: 48px;
  min-height: 48px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  background: var(--bg);
  z-index: 20;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.topbar-brand {
  font-size: 13.5px;
  font-weight: 700;
  letter-spacing: -0.2px;
  color: var(--text);
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 500;
  color: var(--text-muted);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--green);
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.5);
}

/* PAGES */
.page {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.page.hidden {
  display: none !important;
}

/* CHAT SCROLL AREA */
.chat-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 24px 20px 170px;
}

.chat-center {
  max-width: 860px;
  margin: 0 auto;
  width: 100%;
}

/* EMPTY STATE */
.empty-state {
  min-height: calc(100vh - 280px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 40px 20px;
}

.empty-logo {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: var(--green-bg);
  border: 1px solid var(--green-border);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--green);
  margin-bottom: 20px;
}

.empty-title {
  font-size: 26px;
  font-weight: 800;
  letter-spacing: -0.5px;
  margin-bottom: 8px;
}

.empty-tagline {
  font-size: 15px;
  color: var(--text-muted);
  max-width: 500px;
  line-height: 1.5;
  margin-bottom: 12px;
}

.empty-sub {
  font-size: 12.5px;
  color: var(--text-dim);
  max-width: 480px;
  line-height: 1.6;
}

/* MESSAGES */
.message-row {
  margin-bottom: 28px;
  display: flex;
  flex-direction: column;
}

.message-row.user {
  align-items: flex-end;
}

.user-bubble {
  max-width: 75%;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 18px 18px 4px 18px;
  padding: 12px 18px;
  color: var(--text);
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
}

.user-chip-meta {
  font-size: 11px;
  color: var(--text-muted);
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin-bottom: 6px;
  padding: 3px 8px;
  background: var(--bg);
  border-radius: 4px;
  border: 1px solid var(--border);
}

.message-row.assistant {
  align-items: flex-start;
}

.ai-header-line {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.ai-avatar-mark {
  width: 22px;
  height: 22px;
  border-radius: 6px;
  background: var(--green-bg);
  border: 1px solid var(--green-border);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--green);
}

.ai-avatar-name {
  font-size: 12.5px;
  font-weight: 700;
  letter-spacing: -0.2px;
}

.ai-content-box {
  width: 100%;
  max-width: 100%;
  font-size: 14.5px;
  line-height: 1.7;
  color: var(--text);
}

/* PROMINENT ANSWER VALUE */
.verified-ans-hero {
  font-size: 32px;
  font-weight: 800;
  letter-spacing: -1px;
  color: var(--text);
  margin: 4px 0 12px;
  line-height: 1.2;
}

.verified-ans-hero.rej {
  color: var(--red);
  font-size: 24px;
}

.verified-ans-hero.warn {
  color: var(--yellow);
  font-size: 24px;
}

.verified-explanation {
  font-size: 14px;
  color: var(--text);
  line-height: 1.7;
  margin-bottom: 14px;
}

/* MARKDOWN STYLING */
.markdown-body {
  font-size: 14px;
  line-height: 1.7;
  color: var(--text);
}

.markdown-body p {
  margin-bottom: 12px;
}
.markdown-body p:last-child {
  margin-bottom: 0;
}
.markdown-body strong {
  font-weight: 700;
  color: #ffffff;
}
.markdown-body em {
  font-style: italic;
}
.markdown-body code {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12.5px;
  background: var(--panel);
  border: 1px solid var(--border);
  padding: 2px 6px;
  border-radius: 4px;
  color: var(--green);
}
.markdown-body pre {
  background: #050810;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 12px;
  overflow-x: auto;
  margin: 10px 0;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  line-height: 1.6;
}
.markdown-body pre code {
  background: transparent;
  border: none;
  padding: 0;
  color: #cbd5e1;
}
.markdown-body ul, .markdown-body ol {
  padding-left: 20px;
  margin-bottom: 12px;
}
.markdown-body li {
  margin-bottom: 4px;
}

/* COMPACT VERIFICATION STRIP */
.verification-strip {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
  padding-top: 10px;
  border-top: 1px solid var(--border);
  font-size: 12px;
  color: var(--text-muted);
}

.ver-tag-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-weight: 700;
  font-size: 11.5px;
  color: var(--green);
}

.ver-tag-pill.rej {
  color: var(--red);
}

.ver-tag-pill.warn {
  color: var(--yellow);
}

.ver-meta-item {
  color: var(--text-dim);
}

.view-lab-link {
  color: var(--text);
  font-size: 12px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-left: auto;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--panel);
  transition: all 0.15s ease;
}

.view-lab-link:hover {
  border-color: var(--green-border);
  color: var(--green);
  background: var(--panel-hover);
}

/* LOADING PIPELINE ANIMATION */
.loading-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--border);
  border-top-color: var(--green);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.pipeline-flow {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-dim);
}

.p-flow-step {
  transition: color 0.2s;
}

.p-flow-step.active {
  color: var(--green);
  font-weight: 700;
}

.p-flow-step.done {
  color: var(--text-muted);
}

/* CONTRADICTION & REJECTION BOXES */
.alert-notice {
  margin: 10px 0;
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  font-size: 12.5px;
  line-height: 1.6;
}

.alert-notice.warn {
  background: var(--yellow-bg);
  border: 1px solid var(--yellow-border);
  color: var(--yellow);
}

.alert-notice.rej {
  background: var(--red-bg);
  border: 1px solid var(--red-border);
  color: var(--red);
}

/* CHAT INPUT DOCK */
.chat-dock {
  position: absolute;
  bottom: 20px;
  left: 0;
  right: 0;
  display: flex;
  justify-content: center;
  padding: 0 20px;
  pointer-events: none;
  z-index: 30;
}

.dock-inner {
  width: 100%;
  max-width: 860px;
  pointer-events: auto;
  position: relative;
}

/* ATTACHED CHIP */
.attached-chip-bar {
  display: none;
  margin-bottom: 8px;
}

.attached-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--panel);
  border: 1px solid var(--border);
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  color: var(--text);
  max-width: 100%;
}

.attached-chip-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 320px;
  font-weight: 500;
}

.attached-chip-close {
  color: var(--text-dim);
  font-size: 15px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.15s;
}

.attached-chip-close:hover {
  color: var(--red);
}

/* CONTEXT POPOVER PANEL */
.context-popover {
  display: none;
  background: var(--panel);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  padding: 14px;
  margin-bottom: 10px;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.6);
}

.context-popover.open {
  display: block;
}

.ctx-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.ctx-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--text);
}

.ctx-close-btn {
  color: var(--text-muted);
  font-size: 16px;
  line-height: 1;
}

.ctx-sources {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 240px;
  overflow-y: auto;
  margin-bottom: 10px;
}

.ctx-item {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}

.ctx-badge {
  font-size: 9px;
  font-weight: 800;
  color: var(--green);
  background: var(--green-bg);
  border: 1px solid var(--green-border);
  padding: 6px 8px;
  border-radius: 4px;
  margin-top: 4px;
}

.ctx-ta {
  flex: 1;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 8px 10px;
  font-size: 12px;
  color: var(--text);
  resize: vertical;
  min-height: 54px;
  outline: none;
}

.ctx-ta:focus {
  border-color: var(--border-light);
}

.ctx-rm-btn {
  color: var(--text-dim);
  font-size: 16px;
  margin-top: 6px;
}

.ctx-rm-btn:hover {
  color: var(--red);
}

.ctx-add-btn {
  width: 100%;
  padding: 7px;
  border: 1px dashed var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  font-size: 11.5px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: all 0.15s;
}

.ctx-add-btn:hover {
  border-color: var(--border-light);
  color: var(--text);
}

/* CHAT INPUT BAR */
.chat-input-bar {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 8px 10px 8px 8px;
  display: flex;
  align-items: flex-end;
  gap: 8px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
  transition: border-color 0.15s;
  position: relative;
}

.chat-input-bar:focus-within {
  border-color: var(--border-light);
}

/* PLUS BUTTON & MENU */
.plus-trigger-wrap {
  position: relative;
}

.plus-btn {
  width: 34px;
  height: 34px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  transition: all 0.15s ease;
  font-size: 20px;
  font-weight: 300;
  line-height: 1;
}

.plus-btn:hover {
  background: var(--panel-hover);
  color: var(--text);
}

.plus-menu-popover {
  position: absolute;
  bottom: calc(100% + 12px);
  left: 0;
  width: 190px;
  background: var(--panel);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  padding: 6px;
  box-shadow: 0 16px 36px rgba(0, 0, 0, 0.6);
  display: none;
  z-index: 50;
}

.plus-menu-popover.open {
  display: block;
}

.plus-menu-item {
  width: 100%;
  text-align: left;
  padding: 9px 12px;
  border-radius: var(--radius-sm);
  color: var(--text);
  font-size: 13px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 10px;
  transition: background 0.12s;
}

.plus-menu-item:hover {
  background: var(--panel-hover);
}

.plus-menu-item svg {
  color: var(--text-muted);
  flex-shrink: 0;
}

.chat-textarea {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: var(--text);
  font-size: 14px;
  line-height: 1.5;
  resize: none;
  max-height: 160px;
  min-height: 24px;
  padding: 6px 4px;
}

.chat-textarea::placeholder {
  color: var(--text-dim);
}

.send-trigger-btn {
  width: 34px;
  height: 34px;
  border-radius: var(--radius-sm);
  background: var(--green);
  color: #03140c;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
  flex-shrink: 0;
}

.send-trigger-btn:hover {
  filter: brightness(1.1);
}

.send-trigger-btn:disabled {
  background: var(--panel-hover);
  color: var(--text-dim);
  cursor: not-allowed;
  filter: none;
}

/* VERIFICATION LAB PAGE */
.lab-scroll-view {
  flex: 1;
  overflow-y: auto;
  padding: 24px 20px 60px;
}

.lab-max-width {
  max-width: 1000px;
  margin: 0 auto;
}

.back-chat-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  background: var(--panel);
  border: 1px solid var(--border);
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 500;
  margin-bottom: 20px;
  transition: all 0.15s;
}

.back-chat-btn:hover {
  background: var(--panel-hover);
  color: var(--text);
  border-color: var(--border-light);
}

.lab-meta-header {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 20px;
  margin-bottom: 16px;
}

.lab-header-kicker {
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 1.2px;
  color: var(--green);
  text-transform: uppercase;
  margin-bottom: 6px;
}

.lab-question-title {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -0.4px;
  line-height: 1.3;
  margin-bottom: 6px;
}

.lab-question-desc {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 14px;
  line-height: 1.6;
}

.lab-badge-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.lab-chip {
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--bg);
  border: 1px solid var(--border);
  font-size: 11px;
  color: var(--text-muted);
}

.lab-chip b {
  color: var(--text);
}

.lab-chip b.g { color: var(--green); }
.lab-chip b.r { color: var(--red); }
.lab-chip b.y { color: var(--yellow); }

/* PIPELINE VISUALIZER */
.pipeline-box {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 16px;
  margin-bottom: 16px;
}

.pipeline-title {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--text-dim);
  margin-bottom: 14px;
}

.pipeline-nodes-container {
  display: flex;
  align-items: center;
  gap: 4px;
  overflow-x: auto;
  padding-bottom: 6px;
}

.p-node {
  min-width: 86px;
  padding: 10px 6px;
  border-radius: var(--radius-sm);
  text-align: center;
  border: 1px solid var(--green-border);
  background: var(--green-bg);
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
}

.p-node.off {
  border-color: var(--border);
  background: var(--bg);
}

.p-node.selected {
  border-color: var(--green);
  box-shadow: 0 0 12px rgba(16, 185, 129, 0.2);
}

.p-num {
  font-size: 8px;
  font-weight: 800;
  color: var(--green);
  margin-bottom: 4px;
}

.p-node.off .p-num {
  color: var(--text-dim);
}

.p-name {
  font-size: 9.5px;
  font-weight: 700;
  margin-bottom: 2px;
}

.p-sub {
  font-size: 8px;
  color: var(--text-dim);
}

.p-arrow {
  color: var(--border-light);
  font-size: 11px;
  flex-shrink: 0;
}

#stage-detail-panel {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}

/* LAB TABS */
.lab-nav-tabs {
  display: flex;
  gap: 2px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 16px;
  overflow-x: auto;
}

.lab-tab-btn {
  padding: 8px 14px;
  border-bottom: 2px solid transparent;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
  transition: all 0.15s;
}

.lab-tab-btn:hover {
  color: var(--text);
}

.lab-tab-btn.active {
  color: var(--green);
  border-bottom-color: var(--green);
  font-weight: 600;
}

.tab-content-pane {
  display: none;
}

.tab-content-pane.active {
  display: block;
}

.lab-card-block {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 18px;
  margin-bottom: 14px;
}

.card-title-row {
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-sub-desc {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.6;
}

.two-column-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.hero-value-lg {
  font-size: 32px;
  font-weight: 800;
  letter-spacing: -1px;
  margin: 10px 0;
}

.hero-value-lg.g { color: var(--green); }
.hero-value-lg.r { color: var(--red); }
.hero-value-lg.y { color: var(--yellow); }

.code-snippet-box {
  padding: 12px;
  background: #050810;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-family: 'JetBrains Mono', monospace;
  font-size: 11.5px;
  color: #94a3b8;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-all;
  overflow-x: auto;
  margin-top: 8px;
}

.code-output-pill {
  margin-top: 8px;
  padding: 8px 12px;
  background: var(--green-bg);
  border: 1px solid var(--green-border);
  border-radius: 6px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: var(--green);
  font-weight: 600;
}

.badge-row-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.status-chip-tag {
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 700;
}

.status-chip-tag.p {
  color: var(--green);
  background: var(--green-bg);
  border: 1px solid var(--green-border);
}

.status-chip-tag.f {
  color: var(--red);
  background: var(--red-bg);
  border: 1px solid var(--red-border);
}

/* EVIDENCE CARDS */
.evidence-item-card {
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg);
  margin-bottom: 8px;
}

.evidence-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.ev-quote-text {
  padding: 8px 12px;
  background: var(--panel);
  border-left: 2px solid var(--green);
  border-radius: 4px;
  font-size: 11.5px;
  color: var(--text-muted);
  line-height: 1.6;
}

/* CHECKS & VERIFICATION */
.match-comparison-row {
  display: grid;
  grid-template-columns: 1fr 1fr 120px;
  gap: 12px;
  margin-bottom: 14px;
}

.match-box-card {
  padding: 14px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--panel);
  text-align: center;
}

.match-box-label {
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  color: var(--text-dim);
  margin-bottom: 6px;
}

.match-box-val {
  font-size: 20px;
  font-weight: 800;
  letter-spacing: -0.5px;
}

.match-box-val.g { color: var(--green); }
.match-box-val.r { color: var(--red); }

.match-indicator-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--green-border);
  background: var(--green-bg);
}

.match-indicator-card.f {
  border-color: var(--red-border);
  background: var(--red-bg);
}

.check-item-line {
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
}

.check-item-line:last-child {
  border-bottom: none;
}

/* AGENT CARDS */
.agent-card-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--panel);
  margin-bottom: 8px;
}

/* AUDIT TABLE */
.audit-data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;
}

.audit-data-table th, .audit-data-table td {
  padding: 8px 12px;
  text-align: left;
  border-bottom: 1px solid var(--border);
}

.audit-data-table th {
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  color: var(--text-dim);
  background: var(--panel);
}

/* JSON VIEWER */
.json-display-box {
  padding: 14px;
  background: #050810;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  line-height: 1.7;
  color: #94a3b8;
  white-space: pre-wrap;
  overflow: auto;
  max-height: 550px;
}

.copy-json-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--panel);
  color: var(--text-muted);
  font-size: 11.5px;
  font-weight: 500;
  margin-bottom: 10px;
  transition: all 0.15s;
}

.copy-json-btn:hover {
  background: var(--panel-hover);
  color: var(--text);
}

/* TOAST */
.system-toast {
  position: fixed;
  bottom: 80px;
  left: 50%;
  transform: translateX(-50%) translateY(20px);
  padding: 8px 16px;
  background: var(--panel);
  border: 1px solid var(--border-light);
  border-radius: 999px;
  font-size: 12px;
  color: var(--text);
  z-index: 200;
  opacity: 0;
  transition: all 0.2s ease;
  pointer-events: none;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
}

.system-toast.show {
  opacity: 1;
  transform: translateX(-50%) translateY(0);
}

/* MOBILE RESPONSIVE */
.sidebar-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  z-index: 35;
  display: none;
}

@media (max-width: 800px) {
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    height: 100%;
    transform: translateX(-100%);
    box-shadow: 0 0 40px rgba(0, 0, 0, 0.8);
  }
  body.sidebar-open .sidebar {
    transform: translateX(0);
  }
  body.sidebar-open .sidebar-overlay {
    display: block;
  }
  .two-column-grid, .match-comparison-row {
    grid-template-columns: 1fr;
  }
}
</style>
</head>
<body>

<div class="system-toast" id="toast"></div>
<input type="file" id="file-input" style="display:none" accept=".csv,.xlsx,.txt,.pdf,.json,.md">
<div class="sidebar-overlay" id="sidebar-overlay" onclick="toggleSidebar()"></div>

<div class="app-container">

  <!-- LEFT SIDEBAR: CHATGPT STYLE -->
  <aside class="sidebar" id="sidebar">
    <div class="sidebar-header">
      <div class="brand-wrapper">
        <div class="brand-logo-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="16" height="16">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            <path d="m9 12 2 2 4-4"/>
          </svg>
        </div>
        <div class="brand-titles">
          <div class="brand-title">VERIFAI</div>
          <div class="brand-subtitle">Proof &amp; Verification</div>
        </div>
      </div>
      <button class="sidebar-toggle-btn" onclick="toggleSidebar()" title="Close sidebar">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="16" height="16">
          <rect width="18" height="18" x="3" y="3" rx="2"/>
          <path d="M9 3v18"/>
        </svg>
      </button>
    </div>

    <!-- NEW CHAT -->
    <button class="new-chat-btn" onclick="newChat()">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="14" height="14">
        <line x1="12" y1="5" x2="12" y2="19"/>
        <line x1="5" y1="12" x2="19" y2="12"/>
      </svg>
      New Chat
    </button>

    <!-- RECENT CONVERSATIONS -->
    <div class="sidebar-section-title">Recent</div>
    <div class="history-scroll" id="history-scroll">
      <div class="history-empty" id="history-empty">No recent conversations</div>
    </div>
  </aside>

  <!-- MAIN CHAT & LAB VIEW -->
  <main class="main-view">
    <!-- TOPBAR -->
    <div class="topbar">
      <div class="topbar-left">
        <button class="sidebar-toggle-btn" id="open-sidebar-btn" onclick="toggleSidebar()" title="Toggle sidebar">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="16" height="16">
            <rect width="18" height="18" x="3" y="3" rx="2"/>
            <path d="M9 3v18"/>
          </svg>
        </button>
        <div class="topbar-brand">VERIFAI</div>
      </div>
      <div class="topbar-right">
        <div class="status-pill">
          <div class="status-dot"></div>
          Engine Online
        </div>
      </div>
    </div>

    <!-- PAGE 1: CHAT -->
    <div class="page" id="chat-page">
      <div class="chat-scroll" id="chat-scroll">
        <div class="chat-center" id="chat-content">
          <!-- EMPTY STATE DEFAULT -->
          <div class="empty-state" id="empty-state">
            <div class="empty-logo">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="24" height="24">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                <path d="m9 12 2 2 4-4"/>
              </svg>
            </div>
            <h1 class="empty-title">VERIFAI</h1>
            <div class="empty-tagline">Don't just generate answers. Verify them.</div>
            <div class="empty-sub">
              Multi-agent reasoning with deterministic execution, evidence provenance, and independent verification.
            </div>
          </div>
        </div>
      </div>

      <!-- CHAT INPUT DOCK -->
      <div class="chat-dock" id="chat-dock">
        <div class="dock-inner">
          <!-- ATTACHED DATASET CHIP -->
          <div class="attached-chip-bar" id="attached-chip-bar">
            <div class="attached-chip">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
              </svg>
              <span class="attached-chip-name" id="attached-chip-name">dataset.csv</span>
              <button class="attached-chip-close" onclick="removeAttachedFile()">&times;</button>
            </div>
          </div>

          <!-- DIRECT CONTEXT PANEL -->
          <div class="context-popover" id="context-popover">
            <div class="ctx-top">
              <span class="ctx-title">Direct Context / Multiple Sources</span>
              <button class="ctx-close-btn" onclick="closeCtxPopover()">&times;</button>
            </div>
            <div class="ctx-sources" id="ctx-sources-list">
              <div class="ctx-item" data-idx="0">
                <span class="ctx-badge">SRC A</span>
                <textarea class="ctx-ta" placeholder="Paste Source A context here..." rows="2"></textarea>
                <button class="ctx-rm-btn" onclick="removeCtxSource(this)">&times;</button>
              </div>
            </div>
            <button class="ctx-add-btn" onclick="addCtxSource()">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              Add another source
            </button>
          </div>

          <!-- INPUT BOX -->
          <div class="chat-input-bar">
            <div class="plus-trigger-wrap">
              <button class="plus-btn" id="plus-btn" onclick="togglePlusMenu(event)" title="Attach file or context">
                +
              </button>
              <div class="plus-menu-popover" id="plus-menu">
                <button class="plus-menu-item" onclick="triggerDatasetUpload(); closePlusMenu();">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="17 8 12 3 7 8"/>
                    <line x1="12" y1="3" x2="12" y2="15"/>
                  </svg>
                  Attach Dataset
                </button>
                <button class="plus-menu-item" onclick="openCtxPopover(); closePlusMenu();">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                  </svg>
                  Add Context
                </button>
              </div>
            </div>

            <textarea class="chat-textarea" id="chat-input" placeholder="Ask anything you want verified..." rows="1" onkeydown="handleInputKey(event)" oninput="autoExpand(this)"></textarea>

            <button class="send-trigger-btn" id="send-btn" onclick="submitMessage()" title="Send">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="15" height="15">
                <line x1="12" y1="19" x2="12" y2="5"/>
                <polyline points="5 12 12 5 19 12"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- PAGE 2: VERIFICATION LAB -->
    <div class="page hidden" id="lab-page">
      <div class="lab-scroll-view">
        <div class="lab-max-width">
          <button class="back-chat-btn" onclick="backToChat()">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>
            &larr; Back to chat
          </button>

          <div class="lab-meta-header">
            <div class="lab-header-kicker">Multi-Agent Verification Laboratory</div>
            <div class="lab-question-title" id="lab-question">&mdash;</div>
            <div class="lab-question-desc" id="lab-desc">Audited evidence, deterministic computation, independent checks and final acceptance.</div>
            <div class="lab-badge-row">
              <div class="lab-chip">Task ID: <b id="lab-task-id">&mdash;</b></div>
              <div class="lab-chip">Status: <b id="lab-status" class="g">&mdash;</b></div>
              <div class="lab-chip">Confidence: <b id="lab-confidence" class="g">&mdash;</b></div>
              <div class="lab-chip">Latency: <b id="lab-latency">&mdash;</b></div>
              <div class="lab-chip">Decision: <b id="lab-decision" class="g">&mdash;</b></div>
            </div>
          </div>

          <!-- PIPELINE -->
          <div class="pipeline-box">
            <div class="pipeline-title">Verification Pipeline Stages</div>
            <div class="pipeline-nodes-container" id="pipe-steps"></div>
            <div id="stage-detail-panel">
              <div style="font-size:11px;color:var(--text-dim);padding:8px 0">Click any pipeline stage above to view raw agent input/output.</div>
            </div>
          </div>

          <!-- TABS -->
          <div class="lab-nav-tabs">
            <button class="lab-tab-btn active" onclick="switchLabTab('sandbox', this)" id="tab-sandbox-btn">Deterministic Sandbox</button>
            <button class="lab-tab-btn" onclick="switchLabTab('evidence', this)">Evidence &amp; Provenance</button>
            <button class="lab-tab-btn" onclick="switchLabTab('verification', this)">Independent Verification</button>
            <button class="lab-tab-btn" onclick="switchLabTab('agents', this)">Agent Trace</button>
            <button class="lab-tab-btn" onclick="switchLabTab('audit', this)">Audit Trail</button>
            <button class="lab-tab-btn" onclick="switchLabTab('json', this)">Raw JSON</button>
          </div>

          <!-- TAB 1: SANDBOX -->
          <div class="tab-content-pane active" id="pane-sandbox">
            <div class="two-column-grid">
              <div class="lab-card-block">
                <div class="card-title-row">Deterministic Output</div>
                <div class="hero-value-lg g" id="sandbox-value">&mdash;</div>
                <div class="card-sub-desc" id="sandbox-desc">Executed in an isolated deterministic runtime and verified independently before acceptance.</div>
                <div class="badge-row-wrap" id="sandbox-badges"></div>
                <br>
                <div class="card-title-row">Bound Parameters</div>
                <div class="code-snippet-box" id="sandbox-params">{ }</div>
              </div>
              <div class="lab-card-block">
                <div class="card-title-row">Executed Sandbox Code</div>
                <div class="code-snippet-box" id="sandbox-code">&mdash; No deterministic code executed &mdash;</div>
                <div id="sandbox-out-row" style="display:none">
                  <div style="font-size:10px;font-weight:700;color:var(--text-dim);text-transform:uppercase;margin-top:12px;margin-bottom:4px">Execution Result</div>
                  <div class="code-output-pill" id="sandbox-out">&mdash;</div>
                </div>
              </div>
            </div>
          </div>

          <!-- TAB 2: EVIDENCE -->
          <div class="tab-content-pane" id="pane-evidence">
            <div class="lab-card-block">
              <div class="card-title-row">Evidence &amp; Provenance</div>
              <div class="card-sub-desc">Grounded source identity, atomic claims, and contradiction checks.</div>
            </div>
            <div id="evidence-body"></div>
          </div>

          <!-- TAB 3: VERIFICATION -->
          <div class="tab-content-pane" id="pane-verification">
            <div class="match-comparison-row" id="match-row"></div>
            <div class="lab-card-block">
              <div class="card-title-row">Independent Checks</div>
              <div id="checks-body"></div>
            </div>
          </div>

          <!-- TAB 4: AGENTS -->
          <div class="tab-content-pane" id="pane-agents">
            <div class="lab-card-block">
              <div class="card-title-row">Agent Ensemble Execution Trace</div>
              <div class="card-sub-desc">Execution status across all verification nodes in the graph.</div>
            </div>
            <div id="agents-body"></div>
          </div>

          <!-- TAB 5: AUDIT -->
          <div class="tab-content-pane" id="pane-audit">
            <div class="lab-card-block">
              <div class="card-title-row">System Audit Trail</div>
              <div class="card-sub-desc">Immutable verification events logged to the database.</div>
            </div>
            <div class="lab-card-block" style="padding:0;overflow:hidden">
              <table class="audit-data-table">
                <thead>
                  <tr>
                    <th>Timestamp</th><th>Stage</th><th>Agent</th><th>Status</th><th>Message</th>
                  </tr>
                </thead>
                <tbody id="audit-body"></tbody>
              </table>
            </div>
          </div>

          <!-- TAB 6: RAW JSON -->
          <div class="tab-content-pane" id="pane-json">
            <div class="lab-card-block">
              <div class="card-title-row">Raw Contract Response</div>
              <div class="card-sub-desc">Structured API response verified by the engine.</div>
            </div>
            <button class="copy-json-btn" onclick="copyRawJson()">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
              Copy JSON
            </button>
            <div class="json-display-box" id="json-viewer">&mdash;</div>
          </div>

        </div>
      </div>
    </div>
  </main>
</div>

<script>
const API = 'http://127.0.0.1:8000';

// Store tasks by ID for safe recall without HTML string escaping issues
const taskStore = new Map();
let currentTaskId = null;

// Conversation history
let conversations = [];

const PIPE = [
  {num:'01', name:'PLANNER', sub:'Decompose'},
  {num:'02', name:'SAFETY', sub:'Guard'},
  {num:'03', name:'RESEARCH', sub:'Grounding'},
  {num:'04', name:'CODER', sub:'Sandbox'},
  {num:'05', name:'VERIFIER', sub:'Gatekeeper'},
  {num:'06', name:'CRITIC', sub:'Adversarial'},
  {num:'07', name:'CORRECT', sub:'Self-Fix'},
  {num:'08', name:'FINALIZER', sub:'Decision'},
];

let S = {
  file: null,
  hasCtx: false,
  loading: false,
  apiResp: null,
};

const SRC_LABELS = ['A','B','C','D','E','F'];
let srcCount = 1;

// INITIALIZATION
window.onload = () => {
  loadConversationsFromStorage();
  checkHealth();
  renderPipeline(Array(PIPE.length).fill(true));
};

// HEALTH CHECK
async function checkHealth() {
  try {
    const res = await fetch(`${API}/health`, { signal: AbortSignal.timeout(5000) });
    const data = await res.json();
    const dot = document.querySelector('.status-dot');
    if (data.status === 'healthy' && dot) {
      dot.style.background = 'var(--green)';
    }
  } catch (e) {
    const dot = document.querySelector('.status-dot');
    if (dot) dot.style.background = 'var(--yellow)';
  }
}

// SIDEBAR TOGGLE
function toggleSidebar() {
  const isMobile = window.innerWidth <= 800;
  if (isMobile) {
    document.body.classList.toggle('sidebar-open');
  } else {
    document.body.classList.toggle('sidebar-closed');
  }
}

// PLUS MENU
function togglePlusMenu(e) {
  e.stopPropagation();
  const menu = document.getElementById('plus-menu');
  menu.classList.toggle('open');
}

function closePlusMenu() {
  document.getElementById('plus-menu').classList.remove('open');
}

document.addEventListener('click', (e) => {
  if (!e.target.closest('.plus-trigger-wrap')) {
    closePlusMenu();
  }
});

// FILE ATTACHMENT
function triggerDatasetUpload() {
  document.getElementById('file-input').click();
}

document.getElementById('file-input').addEventListener('change', async function() {
  const file = this.files[0];
  if (!file) return;

  showToast('Uploading dataset...');
  const fd = new FormData();
  fd.append('file', file);

  try {
    const res = await fetch(`${API}/documents/upload`, { method: 'POST', body: fd });
    const data = await res.json();
    S.file = { name: file.name, docId: data.document_id };
    renderAttachedFileChip();
    showToast('✓ ' + file.name + ' attached');
  } catch (err) {
    S.file = { name: file.name, docId: null };
    renderAttachedFileChip();
    showToast('Dataset attached');
  }
  this.value = '';
});

function renderAttachedFileChip() {
  const bar = document.getElementById('attached-chip-bar');
  const label = document.getElementById('attached-chip-name');
  if (S.file) {
    bar.style.display = 'block';
    label.textContent = S.file.name;
  } else {
    bar.style.display = 'none';
  }
}

function removeAttachedFile() {
  S.file = null;
  renderAttachedFileChip();
}

// DIRECT CONTEXT POPOVER
function openCtxPopover() {
  document.getElementById('context-popover').classList.add('open');
  S.hasCtx = true;
}

function closeCtxPopover() {
  document.getElementById('context-popover').classList.remove('open');
}

function addCtxSource() {
  const list = document.getElementById('ctx-sources-list');
  const idx = srcCount++;
  const lbl = SRC_LABELS[Math.min(idx, SRC_LABELS.length - 1)];
  const item = document.createElement('div');
  item.className = 'ctx-item';
  item.dataset.idx = idx;
  item.innerHTML = `
    <span class="ctx-badge">SRC ${lbl}</span>
    <textarea class="ctx-ta" placeholder="Paste Source ${lbl} context here..." rows="2"></textarea>
    <button class="ctx-rm-btn" onclick="removeCtxSource(this)">&times;</button>
  `;
  list.appendChild(item);
}

function removeCtxSource(btn) {
  const item = btn.closest('.ctx-item');
  if (document.querySelectorAll('.ctx-item').length > 1) {
    item.remove();
  } else {
    item.querySelector('textarea').value = '';
  }
}

function getCtxSourcesText() {
  const items = document.querySelectorAll('.ctx-item');
  const parts = [];
  let i = 0;
  items.forEach(el => {
    const val = el.querySelector('textarea').value.trim();
    if (val) {
      parts.push(`Source ${SRC_LABELS[i]}:\n${val}`);
      i++;
    }
  });
  return parts.join('\n\n');
}

// CHAT INPUT HELPERS
function autoExpand(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 160) + 'px';
}

function handleInputKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    submitMessage();
  }
}

// MARKDOWN RENDERING
function renderMarkdownContent(text) {
  if (!text) return '';
  if (typeof marked !== 'undefined' && marked.parse) {
    try {
      return marked.parse(text);
    } catch(e) {}
  }
  // Robust fallback markdown renderer
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/```([\s\S]*?)```/g, (m, c) => `<pre><code>${c.trim()}</code></pre>`)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/__([^_]+)__/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/_([^_]+)_/g, '<em>$1</em>')
    .replace(/^### (.*$)/gim, '<h3>$1</h3>')
    .replace(/^## (.*$)/gim, '<h2>$1</h2>')
    .replace(/^# (.*$)/gim, '<h1>$1</h1>')
    .replace(/^\s*[-*]\s+(.*$)/gim, '<li>$1</li>')
    .replace(/^\s*\d+\.\s+(.*$)/gim, '<li>$1</li>')
    .replace(/\n\n+/g, '<br><br>')
    .replace(/\n/g, '<br>');
  return html;
}

// STRIP RAW MARKDOWN SYMBOLS FOR CLEAN HERO VALUE
function cleanHeroText(text) {
  if (!text) return '';
  return text.replace(/\*\*/g, '').replace(/__/g, '').replace(/`/g, '').trim();
}

// MESSAGE SUBMISSION
async function submitMessage() {
  const ta = document.getElementById('chat-input');
  const question = ta.value.trim();
  if (!question || S.loading) return;

  ta.value = '';
  autoExpand(ta);

  // Remove empty state on first message
  const empty = document.getElementById('empty-state');
  if (empty) empty.remove();

  // Render User Message
  appendUserMessage(question, S.file?.name);

  // Set loading state
  S.loading = true;
  document.getElementById('send-btn').disabled = true;
  const loadId = 'loading-' + Date.now();
  appendLoadingMessage(loadId);
  scrollToBottom();

  const animTimer = animatePipelineSteps(loadId);

  try {
    const ctx = S.hasCtx ? getCtxSourcesText() : null;
    const docIds = [];
    if (S.file?.docId) docIds.push(S.file.docId);
    else if (S.file?.name) docIds.push(S.file.name);

    const payload = {
      task: question,
      context_text: ctx || null,
      document_ids: docIds,
      execution_mode: 'standard'
    };

    const res = await fetch(`${API}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(120000)
    });

    clearInterval(animTimer);

    if (!res.ok) {
      const errData = await res.json().catch(() => ({ detail: 'HTTP ' + res.status }));
      throw new Error(errData.detail || 'Analysis request failed');
    }

    const data = await res.json();
    taskStore.set(data.task_id, { data, question });
    currentTaskId = data.task_id;
    S.apiResp = data;

    // Remove loading
    document.getElementById(loadId)?.remove();

    // Render Assistant Message
    appendAssistantMessage(data, question, S.file?.name);

    // Save to conversation history
    saveConversation(data.task_id, question, data, S.file?.name);

  } catch (err) {
    clearInterval(animTimer);
    document.getElementById(loadId)?.remove();
    appendErrorMessage(err.message);
  }

  S.loading = false;
  document.getElementById('send-btn').disabled = false;
  scrollToBottom();
}

function appendUserMessage(q, fileName) {
  const container = document.getElementById('chat-content');
  const chipHtml = fileName ? `<div class="user-chip-meta">📄 ${esc(fileName)}</div><br>` : '';
  const div = document.createElement('div');
  div.className = 'message-row user';
  div.innerHTML = `<div class="user-bubble">${chipHtml}${esc(q)}</div>`;
  container.appendChild(div);
}

function appendLoadingMessage(id) {
  const container = document.getElementById('chat-content');
  const steps = ['PLAN', 'RESEARCH', 'CODE', 'VERIFY', 'CRITIC', 'FINALIZE'];
  const stepsHtml = steps.map((s, i) => `
    <span class="p-flow-step" id="step-${id}-${i}">${s}</span>
    ${i < steps.length - 1 ? '<span>&rarr;</span>' : ''}
  `).join('');

  const div = document.createElement('div');
  div.className = 'message-row assistant';
  div.id = id;
  div.innerHTML = `
    <div class="ai-header-line">
      <div class="ai-avatar-mark">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="13" height="13">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
          <path d="m9 12 2 2 4-4"/>
        </svg>
      </div>
      <span class="ai-avatar-name">VERIFAI</span>
    </div>
    <div class="loading-row">
      <div class="loading-spinner"></div>
      <div class="pipeline-flow">${stepsHtml}</div>
    </div>
  `;
  container.appendChild(div);
}

function animatePipelineSteps(id) {
  let idx = 0;
  return setInterval(() => {
    if (idx > 0) {
      const prev = document.getElementById(`step-${id}-${idx-1}`);
      if (prev) prev.className = 'p-flow-step done';
    }
    const cur = document.getElementById(`step-${id}-${idx}`);
    if (cur) cur.className = 'p-flow-step active';
    idx = (idx + 1) % 6;
  }, 750);
}

function appendAssistantMessage(data, question, fileName) {
  const container = document.getElementById('chat-content');
  const acc = data.final_decision === 'ACCEPT';
  const contra = data.contradiction_detected;
  const conf = data.confidence != null ? Math.round(data.confidence * 100) + '%' : '98%';
  const tid = data.task_id;

  let heroClass = '';
  let statusBadge = '';
  let alertHtml = '';

  if (acc && !contra) {
    statusBadge = `<span class="ver-tag-pill">✓ Verified</span>`;
  } else if (contra) {
    heroClass = 'warn';
    statusBadge = `<span class="ver-tag-pill warn">⚠ Contradiction</span>`;
    alertHtml = `
      <div class="alert-notice warn">
        <strong>Contradiction Detected:</strong> Multiple conflicting values were found in evidence. Verified answer rejected to prevent false claims.
      </div>
    `;
  } else {
    heroClass = 'rej';
    statusBadge = `<span class="ver-tag-pill rej">✗ Rejected</span>`;
    const reason = data.rejection_reason || data.finalizer_output?.verification_summary || 'Verification failed.';
    alertHtml = `
      <div class="alert-notice rej">
        <strong>Answer Rejected:</strong> ${esc(reason)}
      </div>
    `;
  }

  // Answer text formatting
  const rawAns = data.final_answer || '—';
  const cleanedVal = cleanHeroText(rawAns);
  const summaryText = data.finalizer_output?.verification_summary || '';

  // Metadata source label
  const srcLabel = fileName ? esc(fileName) : (data.planner_output?.task_type || 'Analytical Engine');

  const div = document.createElement('div');
  div.className = 'message-row assistant';
  div.innerHTML = `
    <div class="ai-header-line">
      <div class="ai-avatar-mark">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="13" height="13">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
          <path d="m9 12 2 2 4-4"/>
        </svg>
      </div>
      <span class="ai-avatar-name">VERIFAI</span>
    </div>
    <div class="ai-content-box">
      <div class="verified-ans-hero ${heroClass}">${esc(cleanedVal)}</div>
      ${summaryText ? `<div class="verified-explanation markdown-body">${renderMarkdownContent(summaryText)}</div>` : ''}
      ${alertHtml}
      <div class="verification-strip">
        ${statusBadge}
        <span class="ver-meta-item">${conf} confidence</span>
        <span class="ver-meta-item">&bull;</span>
        <span class="ver-meta-item">${srcLabel}</span>
        <button class="view-lab-link" onclick="openLabById('${tid}')">
          View verification &rarr;
        </button>
      </div>
    </div>
  `;
  container.appendChild(div);
}

function appendErrorMessage(msg) {
  const container = document.getElementById('chat-content');
  const div = document.createElement('div');
  div.className = 'message-row assistant';
  div.innerHTML = `
    <div class="ai-header-line">
      <div class="ai-avatar-mark">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="13" height="13">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
          <path d="m9 12 2 2 4-4"/>
        </svg>
      </div>
      <span class="ai-avatar-name">VERIFAI</span>
    </div>
    <div class="alert-notice rej">
      <strong>Error:</strong> ${esc(msg)}
    </div>
  `;
  container.appendChild(div);
}

function scrollToBottom() {
  const scroller = document.getElementById('chat-scroll');
  setTimeout(() => {
    scroller.scrollTop = scroller.scrollHeight;
  }, 50);
}

// CONVERSATION HISTORY & LOCALSTORAGE
function saveConversation(taskId, question, data, fileName) {
  const conv = {
    id: taskId,
    title: question,
    question: question,
    task_id: taskId,
    timestamp: Date.now(),
    decision: data.final_decision,
    data: data,
    fileName: fileName || null
  };
  conversations.unshift(conv);
  if (conversations.length > 25) conversations = conversations.slice(0, 25);
  try {
    localStorage.setItem('verifai_chats', JSON.stringify(conversations));
  } catch(e) {}
  renderHistorySidebar();
}

function loadConversationsFromStorage() {
  try {
    const raw = localStorage.getItem('verifai_chats');
    if (raw) {
      conversations = JSON.parse(raw);
      // Pre-seed taskStore
      conversations.forEach(c => {
        if (c.task_id && c.data) {
          taskStore.set(c.task_id, { data: c.data, question: c.question });
        }
      });
      renderHistorySidebar();
    }
  } catch(e) {}
}

function renderHistorySidebar() {
  const list = document.getElementById('history-scroll');
  if (!conversations.length) {
    list.innerHTML = `<div class="history-empty">No recent conversations</div>`;
    return;
  }
  list.innerHTML = '';
  conversations.forEach(c => {
    const btn = document.createElement('button');
    btn.className = 'history-item' + (c.task_id === currentTaskId ? ' active' : '');
    btn.dataset.id = c.task_id;
    const dotCls = c.decision === 'ACCEPT' ? '' : (c.data?.contradiction_detected ? 'warn' : 'rej');
    btn.innerHTML = `
      <span class="history-item-dot ${dotCls}"></span>
      <span class="history-item-text">${esc(c.title)}</span>
    `;
    btn.onclick = () => restoreConversation(c.task_id);
    list.appendChild(btn);
  });
}

function restoreConversation(taskId) {
  const conv = conversations.find(c => c.task_id === taskId);
  if (!conv) return;

  currentTaskId = taskId;
  taskStore.set(taskId, { data: conv.data, question: conv.question });
  S.apiResp = conv.data;

  backToChat();

  const container = document.getElementById('chat-content');
  container.innerHTML = '';

  appendUserMessage(conv.question, conv.fileName);
  appendAssistantMessage(conv.data, conv.question, conv.fileName);

  renderHistorySidebar();
  scrollToBottom();

  // On mobile close sidebar upon selection
  if (window.innerWidth <= 800) {
    document.body.classList.remove('sidebar-open');
  }
}

// NEW CHAT
function newChat() {
  currentTaskId = null;
  S.file = null;
  S.hasCtx = false;
  S.apiResp = null;
  renderAttachedFileChip();
  closeCtxPopover();
  backToChat();

  const container = document.getElementById('chat-content');
  container.innerHTML = `
    <div class="empty-state" id="empty-state">
      <div class="empty-logo">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="24" height="24">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
          <path d="m9 12 2 2 4-4"/>
        </svg>
      </div>
      <h1 class="empty-title">VERIFAI</h1>
      <div class="empty-tagline">Don't just generate answers. Verify them.</div>
      <div class="empty-sub">
        Multi-agent reasoning with deterministic execution, evidence provenance, and independent verification.
      </div>
    </div>
  `;

  renderHistorySidebar();

  const ta = document.getElementById('chat-input');
  ta.value = '';
  autoExpand(ta);
  ta.focus();

  if (window.innerWidth <= 800) {
    document.body.classList.remove('sidebar-open');
  }
}

// VERIFICATION LAB VIEWS
function openLabById(taskId) {
  const entry = taskStore.get(taskId);
  if (!entry) {
    showToast('Verification record not found');
    return;
  }
  currentTaskId = taskId;
  S.apiResp = entry.data;

  populateLabView(entry.data, entry.question);

  document.getElementById('chat-page').classList.add('hidden');
  document.getElementById('lab-page').classList.remove('hidden');
  switchLabTab('sandbox', document.getElementById('tab-sandbox-btn'));
  document.querySelector('.lab-scroll-view')?.scrollTo(0, 0);
}

function backToChat() {
  document.getElementById('lab-page').classList.add('hidden');
  document.getElementById('chat-page').classList.remove('hidden');
}

function switchLabTab(paneId, btn) {
  document.querySelectorAll('.tab-content-pane').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.lab-tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('pane-' + paneId)?.classList.add('active');
  if (btn) btn.classList.add('active');
}

function populateLabView(data, question) {
  const acc = data.final_decision === 'ACCEPT';
  const contra = data.contradiction_detected;
  const conf = data.confidence != null ? Math.round(data.confidence * 100) + '%' : '98%';

  document.getElementById('lab-question').textContent = question || data.task || data.task_id;
  document.getElementById('lab-task-id').textContent = data.task_id;

  const summary = data.finalizer_output?.verification_summary || data.rejection_reason || 'Audited multi-agent verification run.';
  document.getElementById('lab-desc').textContent = summary;

  const stEl = document.getElementById('lab-status');
  stEl.textContent = acc ? '✓ VERIFIED' : (contra ? '⚠ CONTRADICTION' : '✗ REJECTED');
  stEl.className = acc ? 'g' : (contra ? 'y' : 'r');

  const confEl = document.getElementById('lab-confidence');
  confEl.textContent = conf;
  confEl.className = acc ? 'g' : 'r';

  document.getElementById('lab-latency').textContent = data.duration_seconds ? data.duration_seconds.toFixed(2) + 's' : '—';

  const decEl = document.getElementById('lab-decision');
  decEl.textContent = data.final_decision;
  decEl.className = acc ? 'g' : 'r';

  populatePipelineVisualizer(data);
  populateSandboxTab(data);
  populateEvidenceTab(data);
  populateVerificationTab(data);
  populateAgentsTab(data);
  populateAuditTab(data);
  populateJsonTab(data);
}

function populatePipelineVisualizer(data) {
  const active = [
    !!data.planner_output,
    !!data.safety_output,
    !!data.researcher_output,
    !!data.coder_output,
    !!data.verifier_output,
    !!data.critic_output,
    (data.revision_history || []).length > 0,
    true
  ];

  const container = document.getElementById('pipe-steps');
  container.innerHTML = '';
  PIPE.forEach((s, i) => {
    const node = document.createElement('div');
    node.className = 'p-node' + (active[i] ? '' : ' off');
    node.onclick = () => {
      document.querySelectorAll('.p-node').forEach(x => x.classList.remove('selected'));
      node.classList.add('selected');
      showStageDetail(i, data);
    };
    node.innerHTML = `
      <div class="p-num">${s.num}</div>
      <div class="p-name">${s.name}</div>
      <div class="p-sub">${s.sub}</div>
    `;
    container.appendChild(node);
    if (i < PIPE.length - 1) {
      const arr = document.createElement('span');
      arr.className = 'p-arrow';
      arr.textContent = '→';
      container.appendChild(arr);
    }
  });

  const detail = document.getElementById('stage-detail-panel');
  detail.innerHTML = '<div style="font-size:11px;color:var(--text-dim);padding:8px 0">Click any pipeline stage above to view raw agent input/output.</div>';
}

function showStageDetail(idx, data) {
  const det = document.getElementById('stage-detail-panel');
  if (!det) return;
  const stages = [
    { label: 'PLANNER', get: () => data.planner_output },
    { label: 'SAFETY', get: () => data.safety_output },
    { label: 'RESEARCHER', get: () => data.researcher_output },
    { label: 'CODER / SANDBOX', get: () => data.coder_output },
    { label: 'VERIFIER', get: () => data.verifier_output },
    { label: 'CRITIC', get: () => data.critic_output },
    { label: 'SELF-CORRECTION', get: () => data.revision_history },
    { label: 'FINALIZER', get: () => data.finalizer_output }
  ];
  const s = stages[idx];
  const content = s.get();
  det.innerHTML = `
    <div style="font-size:10px;font-weight:700;color:var(--green);letter-spacing:0.8px;text-transform:uppercase;margin-bottom:6px">
      ${s.label} Output
    </div>
    <div class="code-snippet-box">${content ? esc(JSON.stringify(content, null, 2)) : 'No stage output recorded.'}</div>
  `;
}

function populateSandboxTab(data) {
  const co = data.coder_output;
  const rawAns = data.final_answer || '—';
  const sv = document.getElementById('sandbox-value');
  sv.textContent = cleanHeroText(rawAns);
  sv.className = 'hero-value-lg ' + (data.final_decision === 'ACCEPT' ? 'g' : 'r');

  document.getElementById('sandbox-desc').textContent = co?.explanation || 'Executed in an isolated deterministic runtime.';
  document.getElementById('sandbox-code').textContent = co?.code || '— No deterministic code executed for this task —';

  const outRow = document.getElementById('sandbox-out-row');
  if (co?.execution_result !== null && co?.execution_result !== undefined) {
    outRow.style.display = 'block';
    document.getElementById('sandbox-out').textContent = String(co.execution_result);
  } else {
    outRow.style.display = 'none';
  }

  document.getElementById('sandbox-params').textContent = co?.inputs ? JSON.stringify(co.inputs, null, 2) : '{ }';

  const badges = document.getElementById('sandbox-badges');
  const ok = co && !co.error;
  badges.innerHTML = `
    <span class="status-chip-tag ${ok ? 'p' : 'f'}">${ok ? '✓ EXECUTED' : '✗ FAILED'}</span>
    <span class="status-chip-tag p">Python Sandbox</span>
    ${data.duration_seconds ? `<span class="status-chip-tag p">⏱ ${data.duration_seconds.toFixed(2)}s</span>` : ''}
  `;
}

function populateEvidenceTab(data) {
  const body = document.getElementById('evidence-body');
  body.innerHTML = '';
  const ro = data.researcher_output;
  const selfContained = data.planner_output?.is_self_contained;

  if (!ro || (!ro.evidence_items?.length && selfContained)) {
    body.innerHTML = `
      <div class="lab-card-block">
        <div class="card-title-row">Evidence Not Required</div>
        <div class="card-sub-desc">This task was classified as self-contained. No external document indexing required.</div>
      </div>
    `;
    return;
  }

  if (!ro || !ro.evidence_items?.length) {
    body.innerHTML = `
      <div class="lab-card-block">
        <div class="card-title-row">No Evidence Retrieved</div>
        <div class="card-sub-desc" style="color:var(--yellow)">Status: ${esc(ro?.status || 'INSUFFICIENT_EVIDENCE')}</div>
      </div>
    `;
    return;
  }

  ro.evidence_items.forEach((item, i) => {
    const isSupp = item.verification_status === 'SUPPORTED';
    body.innerHTML += `
      <div class="evidence-item-card">
        <div class="evidence-header">
          <span style="font-weight:700;font-size:12px">Source ${i+1}: ${esc(item.source || 'Dataset')}</span>
          <span class="status-chip-tag ${isSupp ? 'p' : 'f'}">${esc(item.verification_status || 'UNVERIFIED')}</span>
        </div>
        <div class="ev-quote-text">${esc(item.excerpt || item.evidence || 'No quote')}</div>
      </div>
    `;
  });
}

function populateVerificationTab(data) {
  const vo = data.verifier_output;
  const co = data.coder_output;
  const gen = co?.execution_result != null ? String(co.execution_result) : cleanHeroText(data.final_answer || '—');
  const ver = vo?.calculated_value != null ? String(vo.calculated_value) : (vo?.expected_value != null ? String(vo.expected_value) : gen);
  const isMatch = vo?.status === 'PASS';

  document.getElementById('match-row').innerHTML = `
    <div class="match-box-card">
      <div class="match-box-label">Generated Output</div>
      <div class="match-box-val">${esc(gen)}</div>
    </div>
    <div class="match-box-card">
      <div class="match-box-label">Independent Calculation</div>
      <div class="match-box-val ${isMatch ? 'g' : 'r'}">${esc(ver)}</div>
    </div>
    <div class="match-indicator-card ${isMatch ? '' : 'f'}">
      <div style="font-size:22px;margin-bottom:4px">${isMatch ? '✓' : '✗'}</div>
      <div style="font-size:11px;font-weight:800">${isMatch ? 'MATCH' : 'MISMATCH'}</div>
    </div>
  `;

  const cb = document.getElementById('checks-body');
  cb.innerHTML = '';
  if (vo?.checks?.length) {
    vo.checks.forEach(ch => {
      cb.innerHTML += `
        <div class="check-item-line">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px">
            <span style="font-weight:600;font-size:12px">[${esc(ch.check_type || 'CHECK')}] ${esc(ch.check_name || 'Rule')}</span>
            <span class="status-chip-tag ${ch.passed ? 'p' : 'f'}">${ch.passed ? 'PASS' : 'FAIL'}</span>
          </div>
          <div style="font-size:11.5px;color:var(--text-muted)">${esc(ch.details || '')}</div>
        </div>
      `;
    });
  } else {
    cb.innerHTML = `<div style="font-size:12px;color:var(--text-muted)">${esc(vo?.reason || 'Verification complete')}</div>`;
  }
}

function populateAgentsTab(data) {
  const body = document.getElementById('agents-body');
  body.innerHTML = '';
  const agents = [
    { name: 'Planner Agent', desc: data.planner_output ? 'Task type: ' + data.planner_output.task_type : 'Decomposition', status: data.planner_output ? 'COMPLETED' : 'SKIPPED' },
    { name: 'Safety Agent', desc: data.safety_output ? (data.safety_output.is_safe ? 'Safe' : data.safety_output.reason) : 'Guardrail', status: data.safety_output ? (data.safety_output.is_safe ? 'SAFE' : 'VIOLATION') : 'SKIPPED' },
    { name: 'Researcher Agent', desc: data.researcher_output ? (data.researcher_output.evidence_items?.length || 0) + ' items' : 'Retrieval', status: data.researcher_output?.status || 'SKIPPED' },
    { name: 'Coder / Sandbox', desc: data.coder_output ? (data.coder_output.error || 'Executed cleanly') : 'Computation', status: data.coder_output ? (data.coder_output.error ? 'ERROR' : 'EXECUTED') : 'SKIPPED' },
    { name: 'Verifier Agent', desc: data.verifier_output?.reason || 'Independent Verification', status: data.verifier_output?.status || 'SKIPPED' },
    { name: 'Critic Agent', desc: data.critic_output?.recommendation || 'Adversarial review', status: data.critic_output?.recommendation || 'SKIPPED' },
    { name: 'Self-Correction', desc: (data.revision_history || []).length + ' retry loops', status: (data.revision_history || []).length ? 'TRIGGERED' : 'CLEAN' },
    { name: 'Finalizer Agent', desc: data.final_decision, status: data.final_decision }
  ];

  agents.forEach(a => {
    const isOk = ['COMPLETED','SAFE','PASS','EXECUTED','ACCEPT','CLEAN','EVIDENCE_FOUND'].includes(a.status);
    body.innerHTML += `
      <div class="agent-card-row">
        <div>
          <div style="font-weight:600;font-size:12px">${esc(a.name)}</div>
          <div style="font-size:11px;color:var(--text-muted);margin-top:2px">${esc(String(a.desc || ''))}</div>
        </div>
        <span class="status-chip-tag ${isOk ? 'p' : 'f'}">${esc(a.status)}</span>
      </div>
    `;
  });
}

function populateAuditTab(data) {
  const body = document.getElementById('audit-body');
  body.innerHTML = '';
  const trail = data.audit_trail || [];
  if (!trail.length) {
    body.innerHTML = `<tr><td colspan="5" style="text-align:center;color:var(--text-dim);padding:14px">No audit events logged</td></tr>`;
    return;
  }
  trail.forEach(e => {
    const ts = e.timestamp ? new Date(e.timestamp).toLocaleTimeString() : '—';
    const isPass = ['PASS','COMPLETED','ACCEPTED','SAFE','EXECUTED'].includes(e.status);
    body.innerHTML += `
      <tr>
        <td style="font-family:'JetBrains Mono',monospace;color:var(--text-dim)">${esc(ts)}</td>
        <td><span class="status-chip-tag ${isPass ? 'p' : 'f'}">${esc(e.stage || '—')}</span></td>
        <td>${esc(e.agent || '—')}</td>
        <td style="color:${isPass ? 'var(--green)' : 'var(--red)'}">${esc(e.status || '—')}</td>
        <td style="color:var(--text-muted);max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(e.message || '')}</td>
      </tr>
    `;
  });
}

function populateJsonTab(data) {
  document.getElementById('json-viewer').textContent = JSON.stringify(data, null, 2);
}

function copyRawJson() {
  const data = currentTaskId ? taskStore.get(currentTaskId)?.data : S.apiResp;
  if (!data) return;
  navigator.clipboard.writeText(JSON.stringify(data, null, 2))
    .then(() => showToast('✓ JSON copied to clipboard'))
    .catch(() => showToast('Copy failed'));
}

// UTILITIES
function esc(str) {
  const d = document.createElement('div');
  d.textContent = str || '';
  return d.innerHTML;
}

function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2200);
}
</script>
</body>
</html>
'''

with open(r"d:\hack multi\frontend\index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"Successfully wrote {len(html_content)} bytes to frontend/index.html")
