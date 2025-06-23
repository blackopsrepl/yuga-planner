---
title: Yuga Planner
emoji: 🐍
colorFrom: purple
colorTo: gray
sdk: docker
app_port: 7860
license: apache-2.0
tags: ["agent-demo-track"]
---

# Yuga Planner 🐍

**This project was developed for the [Hugging Face Agents MCP Hackathon](https://huggingface.co/Agents-MCP-Hackathon)!**

Yuga Planner is a neuro-symbolic system prototype: it provides an agent-powered team scheduling and task allocation platform built on [Gradio](https://gradio.app/).

It takes a project description, breaks it down into actionable tasks through a [LLamaIndex](https://www.llamaindex.ai/) agent, then uses [Timefold](http://www.timefold.ai) to generate optimal employee schedules for complex projects.

## 🚀 Try It Now
**Live Demo:**
[https://huggingface.co/spaces/blackopsrepl/yuga-planner](https://huggingface.co/spaces/blackopsrepl/yuga-planner)

**Source Code on GitHub:**
[https://github.com/blackopsrepl/yuga-planner](https://github.com/blackopsrepl/yuga-planner)

### MCP Chat Interface Usage

1. **Navigate to the Chat tab** in the Gradio interface
2. **Upload your calendar file (.ics)** to provide existing commitments (optional)
3. **Type your scheduling request** using natural language:
   ```
   "Create a new EC2 instance on AWS"
   "Create a Svelte UI that allows me to query a postgresql database"
   "Develop a chatbot UI based on Gradio"
   ```
4. **Receive intelligent responses** that combine conversational AI with task scheduling capabilities
5. **View formatted schedules** with rich table output and status indicators

### MCP Tool Usage
1. **In any MCP-compatible chatbot or agent platform:**
   ```
   use yuga-planner mcp tool
   Task Description: [Your task description]
   ```
2. **Attach your calendar file (.ics)** to provide existing commitments
3. **Receive optimized schedule** that integrates your new task with existing calendar events

## Architecture

Yuga Planner follows a **service-oriented architecture** with clear separation of concerns:

### Core Services Layer
- **DataService:** Handles data loading, processing, and format conversion from various sources (Markdown, calendars)
- **ScheduleService:** Orchestrates schedule generation, solver management, and solution polling
- **StateService:** Centralized state management for job tracking and schedule storage
- **LoggingService:** Real-time log streaming for UI feedback and debugging
- **MockProjectService:** Provides sample project data for testing and demos
- **MCPClientWrapper:** Manages MCP server functionality and tool definitions

### MCP Integration Components
- **ToolCallAssembler:** Processes streaming tool call deltas from Nebius API into complete tool calls
- **ToolCallProcessor:** Executes completed tool calls via MCP backend with JSON repair functionality
- **Chat Interface:** Unified conversational AI + task scheduling with intelligent tool detection
- **Streaming Handler:** Real-time response processing with progress indicators and error recovery

### System Components
- **Gradio UI:** Modern web interface with real-time updates and interactive schedule visualization
- **Task Composer Agent:** Uses [LLamaIndex](https://www.llamaindex.ai/) + [Nebius AI](https://nebius.ai/) for intelligent task decomposition and estimation
- **Constraint Solver:** [Timefold](http://www.timefold.ai) optimization engine for optimal task-to-employee assignments
- **MCP Integration:** Model Context Protocol endpoint for agent workflow integration

---

## 🌟 Key Features
| Feature | Description | Status |
|---------|-------------|--------|
| **Markdown Project Parsing** | Automatic extraction of tasks from Markdown docs | ✅ |
| **LLM-Powered Task Analysis** | [LLamaIndex](https://www.llamaindex.ai/) + [Nebius AI](https://nebius.ai/) for task decomposition & estimation | ✅ |
| **Constraint-Based Scheduling** | [Timefold](http://www.timefold.ai) optimization engine for schedule assignments | ✅ |
| **Skills Matching** | Detection of skills required for each task | ✅ |
| **Task Dependencies** | Sequential workflow modeling | ✅ |
| **Multiple Projects Support** | Load and schedule multiple projects simultaneously | ✅ |
| **Live Log Streaming** | Real-time solver progress and status updates in UI | ✅ |
| **Configurable Parameters** | Adjustable employee count and schedule duration | ✅ |
| **Mock Project Loading** | Pre-configured sample projects for quick testing | ✅ |
| **Calendar Parsing & Pinning** | Extracts and preserves calendar events from .ics files at original times | ✅ |
| **Business Hours Enforcement** | Respects 9:00-18:00 working hours with lunch break exclusion | ✅ |
| **Weekend Scheduling Prevention** | Hard constraint preventing weekend task assignments | ✅ |
| **MCP Endpoint** | API endpoint for MCP tool integration with calendar support | ✅ |
| **Chat Interface with MCP** | Unified conversational AI + task scheduling interface | ✅ |
| **Streaming Tool Calls** | Real-time processing of tool calls from Nebius API | ✅ |
| **Intelligent Tool Detection** | Keyword-based detection for scheduling requests | ✅ |
| **JSON Repair & Recovery** | Robust handling of malformed streaming data | ✅ |
| **Dual Response System** | Nebius API with MCP fallback for reliability | ✅ |

## 🎯 Two Usage Modes
Yuga Planner operates as **two separate systems** serving different use cases:

### 1. 💬 MCP Chat Interface
**Purpose:** Conversational AI with integrated task scheduling capabilities
- **Access:** Chat tab in the Gradio interface
- **Input:** Natural language requests + optional `.ics` calendar files
- **Features:**
  - Intelligent tool detection based on scheduling keywords
  - Streaming responses with real-time tool call assembly
  - Rich table formatting for schedule results
  - Dual response system (Nebius API + MCP fallback)
- **Use Case:** Interactive scheduling through natural conversation

### 2. 🤖 MCP Personal Tool
**Purpose:** Individual task scheduling integrated with personal calendars
- **Access:** Through MCP-compatible chatbots and agent platforms
- **Input:** Attach `.ics` calendar files + natural language task descriptions
- **Team:** Schedules against your **personal calendar** and existing commitments
- **Use Case:** Personal productivity and task planning around existing appointments

**Example MCP Usage:**
```
User: use yuga-planner mcp tool
Task Description: Create a new EC2 instance on AWS
[Attaches calendar.ics file]

Tool Response: Optimized schedule created - EC2 setup task assigned to
available time slots around your existing meetings
```

## 🧩 MCP Chat Interface Technical Details
### Intelligent Tool Detection
The chat interface automatically detects scheduling requests using keyword analysis:
```python
scheduling_keywords = [
    'schedule', 'task', 'calendar', 'plan', 'organize',
    'meeting', 'appointment', 'project', 'deadline',
    'create', 'setup', 'implement', 'develop'
]
```

### Streaming Tool Call Processing
- **Delta Assembly:** Collects 200+ streaming deltas into complete tool calls
- **JSON Repair:** Handles malformed JSON from streaming responses
- **Progress Indicators:** Real-time feedback during tool processing
- **Timeout Protection:** 60-second timeout for MCP operations

### Dual Response System
- **Primary:** Nebius API with tool calling capabilities
- **Fallback:** Direct MCP backend invocation when tool assembly fails
- **Error Recovery:** Comprehensive error handling and graceful degradation

**Features:**
- Accepts calendar files and user task descriptions via chat interface
- Parses existing calendar events and new task requirements
- **Full schedule solving support** - generates optimized task assignments
- Returns complete solved schedules integrated with personal calendar
- Designed for seamless chatbot and agent workflow integration

**Current Limitations:**
- **Multi-timezone support:** Currently operates in a single timezone context with UTC conversion for consistency. Calendar events from different timezones are normalized to the same scheduling context.

See the [CHANGELOG.md](CHANGELOG.md) for details on recent MCP-related changes.

### Work in Progress
- **🔧 Gradio UI overhaul:** Enhanced user experience and visual improvements
- **🔍 Migration to Pydantic models:** Type-safe data validation and serialization
- **⚡ Enhanced timezone support:** Multi-timezone calendar integration for international scheduling

### Future Work
#### System Integration Roadmap
- **Unified scheduling engine** that can handle both team management and personal productivity in one interface
- **Hybrid workflows** where personal tasks can be coordinated with team projects
- **Cross-system data sharing** between web demo projects and personal MCP calendars
- **Seamless switching** between team management and individual task planning modes

#### Core Feature Enhancements
- **Multi-Tool Support:** Extend chat interface to support additional MCP tools beyond scheduling
- **Calendar Integration:** Direct calendar service integration (Google, Outlook)
- **Performance Optimization:** Enhanced streaming assembly for large tool calls
- **RAG:** validation of task decomposition and estimation against industry relevant literature
- **More granular task dependency:** representation of tasks in a DAG instead of a list to allow overlap within projects, where feasible/convenient
- **Input from GitHub issues:** instead of processing markdown directly, it creates a list by parsing issue
- **Reinforcement learning:** training the agent to improve task decomposition and estimation from GitHub history (e.g. diffs in timestamps, issue comments etc.)

## Prerequisites (Local/GitHub)
- Python 3.10
- Java 17+
- Docker (optional, for containerized deployment)
- Nebius API credentials (for LLM-powered features)

### Installation
1. **Clone the repository:**
   ```bash
   git clone https://github.com/blackopsrepl/yuga-planner.git
   cd yuga-planner
   ```
2. **Create a virtual environment:**
   ```bash
   make venv
   ```
3. **Install dependencies:**
   ```bash
   make install
   ```
4. **Set up environment variables / secrets:**
   ```bash
   make setup-secrets
   # Then edit tests/secrets/cred.py to add your API credentials
   ```
5. **Run the app:**
   ```bash
   make run
   ```

#### Docker (Local/GitHub)
1. **Build the image:**
   ```bash
   docker build -t yuga-planner .
   ```
2. **Run the container:**
   ```bash
   docker run -p 7860:7860 yuga-planner
   ```

---

## Python Dependencies
See `requirements.txt` for full list.

---

## License
This project is licensed under the Apache 2.0 License. See [LICENSE.txt](LICENSE.txt) for details.

---

## Acknowledgements
- [Hugging Face](https://huggingface.co/)
- [Gradio](https://gradio.app/)
- [Nebius LLM](https://nebius.ai/)
- [llama-index](https://github.com/jerryjliu/llama_index)
- [Timefold](https://timefold.ai/)
