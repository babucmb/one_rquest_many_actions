const agentColors = ["#b59bff", "#f1c27d", "#73dbb7", "#87b4fa", "#b99cf3", "#f0a96e", "#e98eaa", "#79d3ce"];
const conversation = document.querySelector("#conversation");
const form = document.querySelector("#composer");
const input = document.querySelector("#request-input");
const sendButton = form.querySelector("button[type=submit]");

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

async function loadStatus() {
  const label = document.querySelector("#connection-label");
  try {
    const [response, runtimeResponse] = await Promise.all([
      fetch("/ready"),
      fetch("/api/v1/runtime")
    ]);
    if (!response.ok || !runtimeResponse.ok) throw new Error("Backend readiness check failed");
    const runtime = await runtimeResponse.json();
    label.textContent = "Local systems ready";
    document.querySelector("#mode-label").textContent = runtime.mode === "google_adk"
      ? `Google ADK · ${runtime.model}`
      : "Offline demo mode";
  } catch {
    label.textContent = "Reconnecting";
  }
}

async function loadAgents() {
  const response = await fetch("/api/v1/agents");
  if (!response.ok) throw new Error("Could not load the agent list.");
  const agents = await response.json();
  const list = document.querySelector("#agent-list");
  document.querySelector("#agent-count").textContent = String(agents.length);
  agents.forEach((agent, index) => {
    const row = element("div", "agent-link");
    const dot = element("span", "agent-dot");
    dot.style.setProperty("--agent-color", agentColors[index % agentColors.length]);
    row.append(dot, element("span", "", agent.name));
    list.append(row);
  });
}

function addUserMessage(text) {
  conversation.append(element("div", "message-user", text));
}

function showLoading() {
  const card = element("div", "result-card");
  const head = element("div", "result-head", "✳  COORDINATING YOUR REQUEST");
  const dots = element("span", "loading-dots");
  dots.setAttribute("aria-label", "Agents working");
  [0, 1, 2].forEach(() => dots.append(element("i")));
  head.append(dots);
  card.append(head);
  card.append(element("div", "result-text", "Finding the right specialists and organizing the work…"));
  conversation.append(card);
  return card;
}

function renderWorkflow(workflow, card) {
  card.replaceChildren();
  document.querySelector("#mode-label").textContent = workflow.mode === "google_adk"
    ? "Google ADK · Gemini"
    : "Offline demo mode";
  const head = element("div", "result-head", `✳  ${workflow.mode === "google_adk" ? "GOOGLE ADK AGENT TEAM" : "OFFLINE DEMO AGENT TEAM"}`);
  const statusText = workflow.status === "completed" ? "COMPLETE" : workflow.status.toUpperCase();
  head.append(element("span", "result-state", statusText));
  const answer = element("div", "result-text");
  answer.append(element("p", "", workflow.response || "No final response was returned."));
  card.append(head, answer);

  if (workflow.agents?.length) {
    const summaries = element("div", "trace-list");
    workflow.agents.forEach(result => {
      const row = element("div", "trace-row");
      row.append(element("span", "trace-symbol", "✓"));
      row.append(element("span", "trace-agent", result.agent));
      row.append(element("span", "", result.summary || "Completed"));
      summaries.append(row);
      if (result.data && Object.keys(result.data).length) {
        const details = element("details", "agent-data");
        details.append(element("summary", "", "View specialist result"));
        const output = element("pre", "result-json", JSON.stringify(result.data, null, 2));
        details.append(output);
        summaries.append(details);
      }
    });
    card.append(summaries);
  }

  const traceButton = element("button", "trace-toggle", `View execution trace · ${workflow.events?.length || 0} events`);
  traceButton.type = "button";
  const trace = element("div", "trace-list");
  trace.hidden = true;
  (workflow.events || []).forEach(event => {
    const row = element("div", "trace-row");
    row.append(element("span", "trace-symbol", event.event_type === "failed" ? "!" : "•"));
    const label = element("span", "trace-agent", `${event.agent} · ${event.event_type}`);
    const description = event.details?.tool_calls?.length
      ? `${event.message} · Tools: ${event.details.tool_calls.join(", ")}`
      : event.message;
    row.append(label, element("span", "", description));
    trace.append(row);
  });
  traceButton.addEventListener("click", () => {
    trace.hidden = !trace.hidden;
    traceButton.textContent = `${trace.hidden ? "View" : "Hide"} execution trace · ${workflow.events?.length || 0} events`;
  });
  card.append(traceButton, trace);
}

function showError(card, message) {
  card.replaceChildren();
  card.append(element("div", "result-head", "REQUEST COULD NOT BE COMPLETED"));
  card.append(element("div", "result-text", message));
}

async function submitRequest(text) {
  if (!text.trim()) return;
  addUserMessage(text.trim());
  input.value = "";
  sendButton.disabled = true;
  const card = showLoading();
  try {
    const response = await fetch("/api/v1/workflows", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ request: text.trim() })
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "The workflow service returned an error.");
    renderWorkflow(payload, card);
  } catch (error) {
    showError(card, error.message);
  } finally {
    sendButton.disabled = false;
    input.focus();
    card.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
}

form.addEventListener("submit", event => {
  event.preventDefault();
  submitRequest(input.value);
});

input.addEventListener("keydown", event => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

document.querySelectorAll(".suggestion").forEach(button => {
  button.addEventListener("click", () => {
    input.value = button.dataset.prompt;
    input.focus();
    form.requestSubmit();
  });
});

loadStatus();
loadAgents().catch(error => {
  document.querySelector("#connection-label").textContent = error.message;
});
