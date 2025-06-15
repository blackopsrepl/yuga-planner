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

It takes a project description file such as a README.md file, breaks it down into actionable tasks through a [LLamaIndex](https://www.llamaindex.ai/) agent, then uses [Timefold](http://www.timefold.ai) to generate optimal employee schedules for complex projects.

**Demo Video:** [pCloud]()

## 🚀 Try It Now
**Live Demo:**
[https://huggingface.co/spaces/Agents-MCP-Hackathon/yuga-planner](https://huggingface.co/spaces/Agents-MCP-Hackathon/yuga-planner)

**Source Code on GitHub:**
[https://github.com/blackopsrepl/yuga-planner](https://github.com/blackopsrepl/yuga-planner)

### Usage

1. Go to [the live demo](https://huggingface.co/spaces/Agents-MCP-Hackathon/yuga-planner) or [http://localhost:7860](http://localhost:7860)

2. Upload one or more Markdown project file(s), then click "Load Data"
   - Each file will be taken as a separate project
   - The app will parse, decompose, and estimate tasks
   - Click "Solve" to generate an optimal schedule
   - Task order is preserved withing each project

3. When the data is loaded, click "Solve" and view results interactively

## Architecture

- **Gradio UI:** Main entry point for users
- **task_composer_agent:** Uses LLMs to decompose and estimate tasks from Markdown
- **Data Provider:** Generates synthetic employee data and availability preferences
- **Constraint Solver:** Assigns tasks to employees, optimizing for skills, availability, and fairness
- **Utils:** Markdown analysis, secret loading, and more

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

## 🧩 MCP Tool Integration

Yuga Planner now includes an **MCP tool** endpoint, allowing integration with the Hugging Face MCP platform. The MCP tool can process uploaded calendar files (such as `.ics`) and user messages, extracting events and generating a corresponding task dataframe.

> **Note:** The current MCP tool implementation returns the *unsolved* task dataframe (not a scheduled/solved output), as full schedule solving is not yet supported for MCP requests. This allows downstream tools or users to inspect and process the extracted tasks before scheduling is implemented.

**Features:**
- Accepts calendar files and user instructions
- Parses events into actionable tasks
- Returns a structured dataframe of tasks (unsolved)
- Designed for easy integration with agent workflows

See the [CHANGELOG.md](CHANGELOG.md) for details on recent MCP-related changes.

### Work in Progress

- **Gradio UI overhaul**
- **General optimization of the workflow**

### Future Work

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

## Testing

- **Run tests:**
  ```bash
  make test
  ```

- **Test files:**
  Located in the `tests/` directory.

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
