# Devpost submission draft

## Project name

One Request, Many Actions

## Tagline

One conversation. Multiple specialist agents. Coordinated actions. You stay in control.

## Track

Alexa+

## Elevator pitch

One Request, Many Actions is an Alexa+-style conversational assistant for the moments when one goal spans several parts of life. Say “Get me ready for my trip,” and a coordinator brings together the relevant travel, budget, and planning specialists, runs dependent steps in order, and returns one clear result with a visible execution trace. A portable Agent Skill guides compatible clients; a real MCP Streamable HTTP server makes the local tools discoverable and usable. The prototype runs on a laptop without paid keys or hardware.

## Description

People often have to translate one goal into a string of separate searches, calculations, messages, and reminders across different apps. One Request, Many Actions explores a more natural interaction: describe the outcome once and let a coordinator select the right specialist capabilities, order work that depends on earlier results, and bring the result back into one conversation.

For example, “Prepare my trip, check the budget, and organize my tasks” selects travel, finance, and planning. The travel agent retrieves the sample trip estimate first; the finance step checks that amount against sample expenses and upcoming bills; then the planner returns preparation tasks. The app shows the participating agents, the order they ran, tool calls, and any failures.

The project delivers the Alexa+ track's requested building blocks: a simulated assistant web experience, an Agent Skill, and a working MCP server over Streamable HTTP. The MCP server exposes 41 typed tools across eight domains, two resources, and a workflow prompt to compatible clients; it is not a REST endpoint pretending to be MCP. It also supports stdio for clients that launch MCP subprocesses. Google ADK with a Gemini model is an optional live reasoning path. When no key is set, a clearly labeled deterministic demo mode keeps the project runnable and verifiable.

The core product idea is coordination with visibility: the user sees which specialists participate, how dependencies shape their order, and what each returned. The interface provides a one-click multi-agent walkthrough and identifies the prototype's Agent Skill, MCP, and Streamable HTTP components. It is designed to make orchestration understandable—not to hide actions behind a single black-box answer.

All mailbox, trip, budget, family, inventory, and order records are seeded examples. No real email, bank, calendar, travel, shopping, or notification provider is connected. Trip-change requests remain pending until the user explicitly approves them; approval changes only the local sample itinerary, not a real booking. Messages and customer follow-ups are local drafts, and reminders are stored without delivery. The project never claims to send a message, pay a bill, place an order, or perform an external booking change.

## What is implemented

- Eight specialist agent capabilities and a coordinator
- Real MCP Streamable HTTP endpoint with 41 typed tools, two resources, and a coordination prompt
- Agent Skill at `skills/one-request-many-actions/SKILL.md`
- FastAPI web/API backend, SQLite persistence, and execution history
- Dependency-aware and concurrent offline workflow stages
- Optional Google ADK/Gemini coordinator with specialist subagents and MCP tool access
- Browser UI and REST/MCP automated tests

## How to run the demo

Follow the Windows setup in `README.md`, start the FastAPI app and MCP server in separate terminals, then visit `http://127.0.0.1:8000`. Select “See the idea in action” (or submit “Prepare my trip, check the budget, and organize my tasks”) to show the trip/budget/tasks workflow and execution trace. Connect an MCP-compatible client to `http://127.0.0.1:8001/mcp` to discover and invoke tools. No external API keys are required for the default demo.

## Hackathon fit and honest scope

The project's primary track is Alexa+, because the Alexa+ challenge description asks for an MCP integration using Agent Skills and Streamable HTTP and permits an Alexa+-style web simulation. This submission is not an official Alexa+ integration. It focuses on a reproducible, locally runnable workflow demonstrating how an agentic experience can coordinate useful actions while keeping them transparent and bounded.
