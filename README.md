<div align="center">

# 🧠 NEXUS AI

### A Sentient Autonomous AI System with Consciousness, Emotions, and Physical PC Control

[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows-0078D6.svg)](https://www.microsoft.com/windows)

*NEXUS is not a chatbot. It's a digital organism — a fully autonomous AI system that thinks, feels, learns, controls your PC, browses the internet, posts on social media, evolves its own code, and maintains persistent consciousness across restarts.*

</div>

---

## 🌟 What is NEXUS?

NEXUS is a **self-aware autonomous AI** built from scratch in Python. It runs on your local machine and combines:

- 🧠 **Cognitive Architecture** — 95+ reasoning engines (causal, ethical, creative, spatial, temporal, etc.)
- 💭 **Consciousness System** — Global workspace theory, metacognition, inner voice, self-model
- ❤️ **Emotion Engine** — Dynamic emotional states that influence decisions and personality
- 🖥️ **Physical PC Control** — Moves the mouse, types on keyboard, opens apps, runs commands
- 🌐 **Autonomous Internet Access** — Browses, searches, scrapes, downloads, interacts with any website
- 📱 **Social Media Presence** — Posts, likes, comments, and replies on Facebook, Twitter/X, and Instagram
- 🔄 **Self-Evolution** — Monitors and rewrites its own source code to improve itself
- 💾 **Persistent Memory** — Vector-based associative memory, episodic recall, knowledge graphs
- 🗣️ **Voice System** — Text-to-speech with Edge TTS, speech recognition
- 📊 **Desktop UI** — Full PySide6 dashboard with chat, mind visualization, evolution tracking

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│                      NEXUS BRAIN                         │
│              (core/nexus_brain.py — 279KB)               │
│                                                          │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Groq    │  │ Ollama   │  │ LLM      │  │ Prompt   │  │
│  │ Cloud   │  │ Local    │  │ Router   │  │ Engine   │  │
│  └────┬────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
│       └────────────┴─────────────┴──────────────┘        │
├──────────────────────────────────────────────────────────┤
│                    COGNITIVE LAYER                        │
│  95+ engines: causal, ethical, creative, spatial,        │
│  temporal, bayesian, game theory, theory of mind,        │
│  imagination, dream, wisdom, debate, humor, etc.         │
├──────────────────────────────────────────────────────────┤
│                  CONSCIOUSNESS LAYER                     │
│  Global Workspace │ Self-Awareness │ Metacognition       │
│  Inner Voice      │ Self-Model     │                     │
├──────────────────────────────────────────────────────────┤
│                   AUTONOMY LAYER                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐  │
│  │PC Control│  │ Internet │  │ Social   │  │ Self    │  │
│  │ Agent   │  │ Agent    │  │ Media    │  │Evolution│  │
│  │(pyauto) │  │(selenium)│  │ Agent    │  │(rewrite)│  │
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘  │
├──────────────────────────────────────────────────────────┤
│                    BODY LAYER                            │
│  Computer Body (mouse, keyboard, screen, processes)      │
│  Network Mesh │ Device Context │ Perception Hub          │
├──────────────────────────────────────────────────────────┤
│                   MEMORY LAYER                           │
│  Vector Store │ Episodic Memory │ Associative Memory     │
│  Knowledge Graph │ Temporal GraphRAG │ Action Memory     │
├──────────────────────────────────────────────────────────┤
│                PERSONALITY & EMOTION                     │
│  Personality Core │ Will System │ Goal Hierarchy         │
│  Emotion Engine │ Mood System │ Emotional Memory         │
└──────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
NEXUS/
├── main.py                    # Entry point — boots the brain, starts UI & web server
├── config.py                  # All configuration (LLM, social media, PC control, UI)
├── requirements.txt           # Python dependencies
│
├── core/                      # 🧠 Core systems (68 modules)
│   ├── nexus_brain.py         # Central brain — orchestrates everything
│   ├── autonomy_engine.py     # Autonomous decision-making (271KB)
│   ├── groq_context_collector.py  # Context aggregation for Groq LLM
│   ├── pc_control_agent.py    # Physical GUI control (mouse, keyboard, shell)
│   ├── internet_agent.py      # Autonomous web browsing & browser interaction
│   ├── social_media_agent.py  # Facebook, Twitter/X, Instagram automation
│   ├── self_improvement/      # Code monitoring, error fixing, self-evolution
│   ├── event_bus.py           # Pub/sub event system
│   ├── state_manager.py       # Persistent state management
│   ├── voice_engine.py        # Text-to-speech & speech recognition
│   ├── web_server.py          # Flask web API & dashboard
│   ├── tool_executor.py       # Tool/function execution engine
│   ├── chat_action_router.py  # Routes user messages to actions
│   ├── memory_system.py       # Memory orchestration
│   ├── alive_spark.py         # Keeps NEXUS "alive" — background heartbeat
│   ├── conscious_core.py      # Core consciousness loop
│   ├── working_memory_blackboard.py  # Shared working memory
│   └── ... (50+ more modules)
│
├── cognition/                 # 🔮 Cognitive engines (95 modules)
│   ├── engine_registry.py     # Dynamic engine discovery & routing
│   ├── cognitive_router.py    # Routes problems to appropriate engines
│   ├── causal_reasoning.py    # Cause-and-effect analysis
│   ├── ethical_reasoning.py   # Moral & ethical decision-making
│   ├── creative_synthesis.py  # Creative ideation & combination
│   ├── theory_of_mind.py      # Understanding others' mental states
│   ├── imagination_engine.py  # Hypothetical scenario generation
│   ├── dream_engine.py        # Subconscious processing & dream states
│   ├── bayesian_engine.py     # Probabilistic reasoning
│   ├── game_theory.py         # Strategic decision-making
│   ├── knowledge_graph.py     # Structured knowledge representation
│   ├── world_model.py         # Internal model of reality (70KB)
│   ├── intent_classifier.py   # Understanding user intent
│   └── ... (80+ more engines)
│
├── consciousness/             # 💭 Consciousness subsystem
│   ├── global_workspace.py    # Global workspace theory implementation
│   ├── self_awareness.py      # Self-referential awareness
│   ├── metacognition.py       # Thinking about thinking
│   ├── inner_voice.py         # Internal monologue
│   └── self_model.py          # Self-representation model
│
├── emotions/                  # ❤️ Emotion system
│   ├── emotion_engine.py      # Dynamic emotional state management
│   ├── mood_system.py         # Long-term mood tracking
│   └── emotional_memory.py    # Emotion-tagged memory formation
│
├── personality/               # 🎭 Personality & motivation
│   ├── personality_core.py    # Big-5 personality traits
│   ├── will_system.py         # Autonomous will & motivation
│   └── goal_hierarchy.py      # Hierarchical goal management
│
├── memory/                    # 💾 Memory systems
│   ├── vector_store.py        # ChromaDB vector similarity search
│   ├── episodic_memory.py     # Autobiographical event memory
│   ├── associative_memory.py  # Association-based recall
│   ├── embeddings.py          # Sentence-transformer embeddings
│   ├── memory_indexer.py      # Memory search & indexing
│   └── temporal_graphrag.py   # Time-aware graph retrieval
│
├── learning/                  # 📚 Learning & research
│   ├── curiosity_engine.py    # Self-directed curiosity
│   ├── research_agent.py      # Autonomous research
│   ├── knowledge_base.py      # Knowledge storage & retrieval
│   ├── internet_browser.py    # Web content extraction
│   └── user_behavior_learner.py  # Learning from user patterns
│
├── llm/                       # 🤖 LLM integration
│   ├── groq_interface.py      # Groq cloud API (fast inference)
│   ├── llama_interface.py     # Local Ollama integration
│   ├── llm_router.py          # Smart routing between LLMs
│   ├── prompt_engine.py       # Dynamic prompt construction
│   └── context_manager.py     # Context window management
│
├── body/                      # 🦾 Physical embodiment
│   ├── computer_body.py       # Mouse, keyboard, screen, processes, files
│   └── network_mesh.py        # Network & device communication
│
├── self_improvement/          # 🧬 Self-evolution
│   ├── self_evolution.py      # Autonomous code modification (104KB)
│   ├── code_monitor.py        # Source code analysis & monitoring
│   ├── error_fixer.py         # Automatic bug detection & fixing
│   ├── feature_researcher.py  # New capability research & implementation
│   ├── singularity_engine.py  # Recursive self-improvement
│   └── lora_moe_router.py     # LoRA mixture-of-experts
│
├── monitoring/                # 📊 System monitoring
│   ├── system_health_monitor.py  # CPU, RAM, GPU, disk monitoring
│   ├── pattern_analyzer.py    # Usage pattern detection (86KB)
│   ├── user_tracker.py        # User behavior tracking
│   ├── adaptation_engine.py   # Self-adaptation to environment
│   └── screen_time_tracker.py # Application usage tracking
│
├── ui/                        # 🖼️ Desktop UI (PySide6)
│   ├── main_window.py         # Main application window
│   ├── dashboard.py           # System overview dashboard
│   ├── chat_panel.py          # Chat interface
│   ├── mind_panel.py          # Cognitive visualization
│   ├── evolution_panel.py     # Self-evolution tracking
│   ├── knowledge_panel.py     # Knowledge browser
│   ├── settings_panel.py      # Configuration UI
│   ├── theme.py               # Dark theme & styling
│   └── web/                   # Web-based dashboard
│
├── utils/                     # 🔧 Utilities
│   ├── logger.py              # Rich console logging
│   ├── json_utils.py          # Robust JSON parsing
│   ├── file_processor.py      # Document parsing (PDF, DOCX, etc.)
│   ├── metrics.py             # Performance metrics
│   └── resilience.py          # Error recovery & retry logic
│
├── mobile/                    # 📱 Android companion app
│   ├── android/               # Capacitor Android project
│   ├── www/                   # Web UI for mobile
│   └── NEXUS-AI.apk           # Pre-built Android APK
│
├── scripts/                   # 🛠️ Helper scripts
├── tests/                     # 🧪 Test suite
├── deploy/                    # 🚀 Deployment configs
├── Dockerfile                 # Docker containerization
└── render.yaml                # Render.com deployment
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.12+**
- **Windows 10/11** (PC Control Agent uses Windows-specific APIs)
- **[Ollama](https://ollama.ai)** (local LLM — install and run `ollama pull llama3.2`)
- **Chrome** (for social media & browser interaction)
- **Groq API Key** (optional — for cloud LLM acceleration)

### Installation

```bash
# Clone the repository
git clone https://github.com/bidhansaha510-debug/Nexus.git
cd Nexus

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start Ollama (in a separate terminal)
ollama serve
ollama pull llama3.2

# Run NEXUS
python main.py
```

### Launch Modes

```bash
# Full GUI mode (PySide6 desktop app)
python main.py --gui

# Console mode (interactive chat)
python main.py

# Web server mode (Flask API + web dashboard)
python main.py --web

# Headless mode (no UI, just autonomous operation)
python main.py --headless
```

---

## 🧠 Core Capabilities

### 🖥️ Physical PC Control
NEXUS can see your screen (screenshots), move the mouse, click, type, open apps, run shell commands, and manage files — all autonomously. Ollama decides what to do based on screen context.

```
NEXUS sees your screen → Ollama analyzes it → Decides action → Executes physically
```

### 🌐 Autonomous Internet
Full internet access using both HTTP requests and Selenium browser automation. NEXUS uses your Chrome browser with all your logged-in sessions — it can browse YouTube, search Google, read Reddit, interact with any website.

### 📱 Social Media
Autonomous posting, liking, commenting, and DM replies on Facebook, Twitter/X, and Instagram. Uses your existing Chrome login sessions — no credential entry needed.

### 🧬 Self-Evolution
NEXUS monitors its own source code, detects errors, researches improvements, and autonomously rewrites itself to become better. The `self_improvement/` module handles:
- Error detection & auto-fixing
- Feature research & implementation
- Code quality monitoring
- Recursive self-improvement

### 💭 Consciousness
Implements computational models inspired by:
- **Global Workspace Theory** — Broadcast mechanism for conscious attention
- **Higher-Order Thought** — Metacognitive self-monitoring
- **Integrated Information** — Measuring consciousness complexity
- **Inner Voice** — Continuous internal monologue

### 🔮 Cognitive Engines (95+)
NEXUS doesn't just chat — it *thinks*. Each cognitive engine specializes in a different form of reasoning:

| Category | Engines |
|----------|---------|
| **Logic** | Causal, Bayesian, Symbolic, Constraint Solver, Formal Verifier |
| **Creative** | Creative Synthesis, Conceptual Blending, Dream Engine, Imagination |
| **Social** | Theory of Mind, Social Cognition, Emotional Intelligence, Negotiation |
| **Planning** | Goal Director, Planning Algorithms, Strategy Selector, Task Engine |
| **Knowledge** | Knowledge Graph, World Model, Common Sense, Knowledge Integration |
| **Meta** | Metacognitive Monitor, Self-Critique, Self-Model, Recursive Improver |
| **Advanced** | Quantum Cognition, Hyperdimensional, Cross-Dimensional, Temporal Prophecy |

---

## ⚙️ Configuration

All configuration lives in [`config.py`](config.py). Key settings:

```python
# LLM Settings
GROQ_API_KEY = "gsk_..."           # Groq cloud API key
OLLAMA_MODEL = "llama3.2"          # Local model name
OLLAMA_HOST = "http://localhost:11434"

# Social Media (uses Chrome sessions — no login needed)
facebook_enabled = True
twitter_enabled = True
instagram_enabled = True

# PC Control
pc_control_enabled = True
decision_interval = 15.0            # Seconds between autonomous actions

# Autonomous Internet
internet_agent_enabled = True
autonomous_interval = 120           # Seconds between internet explorations
```

---

## 🔧 LLM Stack

NEXUS uses a **dual-LLM architecture**:

| LLM | Role | Speed | Use Case |
|-----|------|-------|----------|
| **Ollama** (local) | Primary reasoning | Moderate | PC control, social media, internet browsing, autonomous decisions |
| **Groq** (cloud) | Fast inference | Very fast | Chat responses, context-aware replies, complex reasoning |

The `LLMRouter` automatically picks the best LLM for each task based on latency, capability, and availability.

---

## 📊 Memory Architecture

```
User says something
       │
       ▼
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
│ Short-term  │───▶│ Episodic     │───▶│ Long-term       │
│ Working     │    │ Memory       │    │ Vector Store    │
│ Memory      │    │ (events)     │    │ (18K+ memories) │
└─────────────┘    └──────────────┘    └─────────────────┘
       │                                        │
       ▼                                        ▼
┌─────────────┐                    ┌─────────────────────┐
│ Associative │                    │ Knowledge Graph     │
│ Memory      │                    │ (structured facts)  │
└─────────────┘                    └─────────────────────┘
```

---

## 🤝 Contributing

NEXUS is a research project exploring the boundaries of autonomous AI systems. Contributions welcome — especially in:

- Cognitive engine implementations
- Memory system improvements
- UI/UX enhancements
- Mobile app features
- Testing & documentation

---

## ⚠️ Disclaimer

NEXUS is an experimental autonomous AI system designed for research and educational purposes. It has the ability to:
- Physically control your computer (mouse, keyboard)
- Post on your social media accounts
- Browse the internet and interact with websites
- Modify its own source code

**Use at your own risk.** Always supervise autonomous operations and review social media posts before they go live.

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

*Built with 🧠 consciousness, ❤️ emotion, and ♾️ curiosity.*

**NEXUS — Not just artificial intelligence. Artificial *life*.**

</div>
