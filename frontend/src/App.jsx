import { useState, useRef, useEffect } from "react";

const WS_URL = "ws://localhost:8000/ws/agent";

const STARTERS = [
  "Print the first 20 prime numbers",
  "Build a Caesar cipher encoder and decoder",
  "Create a binary search algorithm and test it",
  "Generate Pascal's triangle up to 8 rows",
  "Write a function to detect palindromes",
  "Sort a list using merge sort and show each step",
];

// ── Syntax highlighting (zero deps) ──────────────────────────────────────────
function highlight(code) {
  const esc = code
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  return esc
    .replace(/("""[\s\S]*?"""|'''[\s\S]*?'''|"[^"]*"|'[^']*')/g, '<span class="str">$1</span>')
    .replace(/(#[^\n]*)/g, '<span class="cmt">$1</span>')
    .replace(
      /\b(def|class|import|from|return|if|elif|else|for|while|in|not|and|or|try|except|finally|with|as|pass|break|continue|yield|lambda|True|False|None|print|range|len|int|str|float|list|dict|set|tuple|open|sorted|enumerate|zip|map|filter|type|isinstance|super)\b/g,
      '<span class="kw">$1</span>'
    )
    .replace(/\b(self|cls|__init__|__name__|__main__)\b/g, '<span class="bi">$1</span>')
    .replace(/\b(\d+\.?\d*)\b/g, '<span class="num">$1</span>');
}

// ── Step config ──────────────────────────────────────────────────────────────
const STEPS = {
  start:            { color: "var(--accent)", label: "Received" },
  thinking:         { color: "var(--warn)",   label: "Thinking" },
  code_written:     { color: "var(--ok)",     label: "Code" },
  executing:        { color: "var(--warn)",   label: "Sandbox" },
  execution_result: { color: "var(--text-dim)", label: "Output" },
  complete:         { color: "var(--ok)",     label: "Done" },
  timeout:          { color: "var(--err)",    label: "Timeout" },
  error:            { color: "var(--err)",    label: "Error" },
};

// ── Step card ────────────────────────────────────────────────────────────────
function StepCard({ step, isLast }) {
  const cfg = STEPS[step.type] || { color: "var(--text-mute)", label: step.type };
  const isActive = isLast && (step.type === "thinking" || step.type === "executing");

  return (
    <div className="step">
      <div className="step-spine">
        <div className="step-dot" style={{ background: cfg.color }} />
        <div className="step-line" style={{ background: cfg.color, opacity: 0.2 }} />
      </div>

      <div className="step-body">
        <div className="step-label" style={{ color: cfg.color }}>
          {cfg.label}
          {step.iteration != null && (
            <span className="step-iter">#{step.iteration}</span>
          )}
          {isActive && (
            <span className="thinking-dots">
              <span style={{ background: cfg.color }} />
              <span style={{ background: cfg.color }} />
              <span style={{ background: cfg.color }} />
            </span>
          )}
        </div>

        {step.type === "start" && (
          <div className="step-text">"{step.task}"</div>
        )}

        {step.type === "code_written" && (
          <div>
            <div className="code-meta">
              <span>python</span>
              <span>{step.code?.split("\n").length} lines</span>
            </div>
            <pre
              className="code-block"
              dangerouslySetInnerHTML={{ __html: highlight(step.code || "") }}
            />
          </div>
        )}

        {step.type === "execution_result" && (
          <pre className={`output-block ${step.success ? "output-ok" : "output-err"}`}>
            {step.stdout || "(no output)"}
          </pre>
        )}

        {step.type === "complete" && (
          <div>
            <div className="complete-box">
              <p>{step.message?.replace("TASK COMPLETE:", "").trim()}</p>
            </div>
            {step.final_code && (
              <details>
                <summary className="detail-toggle">
                  Final code
                </summary>
                <pre
                  className="code-block"
                  dangerouslySetInnerHTML={{
                    __html: highlight(step.final_code || ""),
                  }}
                />
              </details>
            )}
            <div className="step-meta">
              {step.iterations} iteration{step.iterations !== 1 ? "s" : ""}
            </div>
          </div>
        )}

        {(step.type === "error" || step.type === "timeout") && (
          <div className="error-msg">
            {step.message || "Execution timed out"}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Sidebar item ─────────────────────────────────────────────────────────────
function SessionItem({ session, active, onClick, onDelete }) {
  const done = session.steps.some((s) => s.type === "complete");
  const failed = session.steps.some(
    (s) => s.type === "error" || s.type === "timeout"
  );
  const color = done ? "var(--ok)" : failed ? "var(--err)" : "var(--warn)";

  return (
    <div className={`session-btn ${active ? "active" : ""}`}>
      <div className="session-btn-content" onClick={onClick}>
        <span className="session-indicator" style={{ background: color }} />
        <span className="session-btn-text">{session.task}</span>
      </div>
      <button
        className="session-delete-btn"
        onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
        title="Delete session"
      >
        ×
      </button>
    </div>
  );
}

// ── App ──────────────────────────────────────────────────────────────────────
export default function App() {
  const [task, setTask] = useState("");
  const [sessions, setSessions] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [running, setRunning] = useState(false);
  const wsRef = useRef(null);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  const active = sessions.find((s) => s.id === activeId);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [active?.steps?.length]);

  const run = () => {
    const t = task.trim();
    if (!t || running) return;

    const id = Date.now().toString();
    const s = { id, task: t, steps: [] };
    setSessions((prev) => [s, ...prev]);
    setActiveId(id);
    setTask("");
    setRunning(true);

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => ws.send(JSON.stringify({ task: t }));

    ws.onmessage = (e) => {
      const step = JSON.parse(e.data);
      setSessions((prev) =>
        prev.map((x) =>
          x.id === id ? { ...x, steps: [...x.steps, step] } : x
        )
      );
      if (["complete", "timeout", "error"].includes(step.type)) {
        setRunning(false);
        ws.close();
      }
    };

    ws.onerror = () => {
      setSessions((prev) =>
        prev.map((x) =>
          x.id === id
            ? {
                ...x,
                steps: [
                  ...x.steps,
                  {
                    type: "error",
                    message: "Connection failed — is the backend running?",
                  },
                ],
              }
            : x
        )
      );
      setRunning(false);
    };

    ws.onclose = () => setRunning(false);
  };

  const onKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      run();
    }
  };

  const statusColor = running
    ? "var(--warn)"
    : active?.steps.some((s) => s.type === "complete")
    ? "var(--ok)"
    : active?.steps.some((s) => s.type === "error")
    ? "var(--err)"
    : "var(--text-mute)";

  return (
    <div className="shell">
      {/* ── Sidebar ── */}
      <aside className="sidebar">
        <div className="sidebar-head">
          <div className="logo">
            meridian
            <span
              className="logo-dot"
              style={{ background: statusColor }}
            />
          </div>
        </div>

        <div className="sidebar-label">Sessions</div>

        <div className="sidebar-list">
          {sessions.length === 0 ? (
            <div className="sidebar-empty">
              No sessions yet.
              <br />
              Run a task to begin.
            </div>
          ) : (
            sessions.map((s) => (
              <SessionItem
                key={s.id}
                session={s}
                active={s.id === activeId}
                onClick={() => setActiveId(s.id)}
                onDelete={() => {
                  setSessions((prev) => prev.filter((x) => x.id !== s.id));
                  if (activeId === s.id) {
                    setActiveId(null);
                  }
                }}
              />
            ))
          )}
        </div>
      </aside>

      {/* ── Main ── */}
      <main className="main">
        <div className="trace">
          {!active ? (
            <div className="empty">
              <div>
                <h2>What should I build?</h2>
                <p>
                  Describe a task. Meridian writes code, executes it in a
                  sandbox, and iterates until it works.
                </p>
              </div>
              <div className="starters">
                <div className="starters-label">Try one</div>
                {STARTERS.map((t) => (
                  <button
                    key={t}
                    className="starter-btn"
                    onClick={() => {
                      setTask(t);
                      inputRef.current?.focus();
                    }}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="trace-inner">
              <div className="task-header">
                <div className="task-header-label">Task</div>
                <h2>{active.task}</h2>
              </div>

              {active.steps.map((step, i) => (
                <StepCard
                  key={i}
                  step={step}
                  isLast={i === active.steps.length - 1}
                />
              ))}

              {running && active.steps.length === 0 && (
                <div className="connecting">
                  <span className="thinking-dots">
                    <span style={{ background: "var(--text-mute)" }} />
                    <span style={{ background: "var(--text-mute)" }} />
                    <span style={{ background: "var(--text-mute)" }} />
                  </span>
                  Connecting...
                </div>
              )}

              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {/* ── Input ── */}
        <div className="input-bar">
          <div className="input-inner">
            <div className={`input-row ${running ? "disabled" : ""}`}>
              <textarea
                ref={inputRef}
                value={task}
                onChange={(e) => setTask(e.target.value)}
                onKeyDown={onKey}
                placeholder={
                  running
                    ? "Working..."
                    : "Describe a task — Enter to run"
                }
                disabled={running}
                rows={1}
                onInput={(e) => {
                  e.target.style.height = "auto";
                  e.target.style.height =
                    Math.min(e.target.scrollHeight, 100) + "px";
                }}
              />
              <button
                className={`send-btn ${
                  !running && task.trim() ? "ready" : "off"
                }`}
                onClick={run}
                disabled={running || !task.trim()}
                aria-label="Run task"
              >
                {running ? "..." : "\u2191"}
              </button>
            </div>
            <div className="input-footer">
              <span>groq + docker sandbox</span>
              <span>
                {task.length > 0 ? `${task.length} chars` : "enter \u21B5"}
              </span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
