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

### Gradio Web Demo Usage

1. Go to [the live demo](https://huggingface.co/spaces/blackopsrepl/yuga-planner) or [http://localhost:7860](http://localhost:7860)

2. **Upload project files** or **use mock projects:**
   - Upload one or more Markdown project file(s), then click "Load Data"
   - OR select from pre-configured mock projects for quick testing
   - Each file will be taken as a separate project
   - The app will parse, decompose, and estimate tasks using LLM agents

3. **Generate schedule:**
   - Click "Solve" to generate an optimal schedule against a randomly generated team
   - View results interactively with real-time solver progress
   - Task order is preserved within each project

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
| **Calendar Parsing** | Extracts tasks from uploaded calendar files (.ics) | ✅ |
| **MCP Endpoint** | API endpoint for MCP tool integration | ✅ |

## 🎯 Two Usage Modes

Yuga Planner operates as **two separate systems** serving different use cases:

### 1. 🖥️ Gradio Web Demo
**Purpose:** Interactive team scheduling for project management
- **Access:** [Live demo](https://huggingface.co/spaces/blackopsrepl/yuga-planner) or local web interface
- **Input:** Upload Markdown project files or use pre-configured mock projects
- **Team:** Schedules against a **randomly generated team** with diverse skills and availability
- **Use Case:** Project managers scheduling real teams for complex multi-project workloads

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

## 🧩 MCP Tool Integration Details

**Features:**
- Accepts calendar files and user task descriptions via chat interface
- Parses existing calendar events and new task requirements
- **Full schedule solving support** - generates optimized task assignments
- Returns complete solved schedules integrated with personal calendar
- Designed for seamless chatbot and agent workflow integration

**Current Limitations:**
- **Weekend constraints:** Tasks can be scheduled on weekends (should respect work-week boundaries)
- **Working hours:** No enforcement of standard business hours (8 AM - 6 PM)
- **Calendar pinning:** Tasks from uploaded calendars are solved alongside other tasks but should remain pinned to their original time slots

See the [CHANGELOG.md](CHANGELOG.md) for details on recent MCP-related changes.

### Recent Improvements ✅

- **Service Architecture Refactoring:** Complete service-oriented architecture with proper encapsulation and clean boundaries
- **State Management:** Centralized state handling through dedicated StateService
- **Handler Compliance:** Clean separation between UI handlers and business logic services
- **Method Encapsulation:** Fixed all private method violations for better code maintainability

### Work in Progress

- **Constraint Enhancements:**
  - Weekend respect (prevent scheduling on weekends)
  - Working hours enforcement (8 AM - 6 PM business hours)
  - Calendar task pinning (preserve original time slots for imported calendar events)
- **Gradio UI overhaul:** Enhanced user experience and visual improvements
- **Migration to Pydantic models:** Type-safe data validation and serialization
- **Migrate from violation_analyzer to Timefold dedicated libraries**
- **Include tests for all constraints using ConstraintVerifier**

### Future Work

#### System Integration Roadmap
Currently, the **Gradio web demo** and **MCP personal tool** operate as separate systems. As the project evolves, these will become **more integrated**, enabling:
- **Unified scheduling engine** that can handle both team management and personal productivity in one interface
- **Hybrid workflows** where personal tasks can be coordinated with team projects
- **Cross-system data sharing** between web demo projects and personal MCP calendars
- **Seamless switching** between team management and individual task planning modes

#### Core Feature Enhancements
- **RAG:** validation of task decomposition and estimation against industry relevant literature
- **More granular task dependency:** representation of tasks in a tree instead of a list to allow overlap within projects, where feasible/convenient
- **Input from GitHub issues:** instead of processing markdown directly, it creates a list by parsing issue
- **Chat interface:** detection of user intent, with on-the-fly CRUD operations on team, tasks and schedules
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

2. **Install dependencies:**
   ```bash
   make install
   ```

3. **Set up environment variables / secrets:**
   ```bash
   make setup-secrets
   # Then edit tests/secrets/cred.py to add your API credentials
   ```

4. **Run the app:**
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
   docker run -p 7860:786
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
