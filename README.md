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

Yuga Planner is a neuro-symbolic system prototype: it provides an agent-powered team scheduling and task allocation platform build on [Gradio](https://gradio.app/).

It takes a project description file such as a README.md file, breaks it down into actionable tasks through a [LLamaIndex](https://www.llamaindex.ai/) agent, then uses [Timefold](http://www.timefold.ai) to generate optimal employee schedules for complex projects.

## 🚀 Try It Now
**Live Demo:**
[https://huggingface.co/spaces/Agents-MCP-Hackathon/yuga-planner](https://huggingface.co/spaces/Agents-MCP-Hackathon/yuga-planner)

**Source Code on GitHub:**
[https://github.com/blackopsrepl/yuga-planner](https://github.com/blackopsrepl/yuga-planner)

### Usage

1. Go to [the live demo](https://huggingface.co/spaces/Agents-MCP-Hackathon/yuga-planner) or [http://localhost:7860](http://localhost:7860)

2. Upload a Markdown project file, click "Load Data"
    - The app will parse, decompose, and estimate tasks
    - Click "Solve" to generate an optimal schedule

3. When the data is loaded, click "Solve" and view results interactively

## Architecture

- **Gradio UI:** Main entry point for users
- **TaskComposerAgent:** Uses LLMs to decompose and estimate tasks from Markdown
- **Data Provider:** Generates synthetic employee data and availability
- **Constraint Solver:** Assigns tasks to employees, optimizing for skills, availability, and fairness
- **Utils:** Markdown analysis, secret loading, and more

---

## 🌟 Key Features
| Feature | Description | Status |
|---------|-------------|--------|
| **Markdown Project Parsing** | Automatic extraction of tasks from Markdown docs | ✅ |
| **LLM-Powered Task Analysis** | [LLamaIndex](https://www.llamaindex.ai/) + [Nebius AI](https://nebius.ai/) for task decomposition & estimation | ✅ |
| **Constraint-Based Scheduling** | [Timefold](http://www.timefold.ai) optimization engine for schedule assignments | ✅ |
| **Skills Matching** | Detection of skills required for tasks | 🚧 WIP |
| **Task Dependencies** | Sequential workflow modeling | 🚧 WIP |

### Work in Progress

- **Skills matching:** currently random, working on LLM-based skill matching
- **Task dependencies:** currently random, working on task dependency detection system; may use LLMs or not

### Future Work

- **Input from GitHub issues:** instead of processing markdown directly, it creates a list by parsing issues/comments
- **Chat interface:** detection of user commands for CRUD operations on tasks and schedules

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
