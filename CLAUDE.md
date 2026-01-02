# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DeepRareAgent is a LangGraph-based multi-agent system for rare disease diagnosis. It uses a three-stage diagnostic workflow:

1. **Pre-diagnosis Agent (P01)**: Collects patient information through conversational interface
2. **Deep Diagnosis Agent (P02)**: Performs literature research and diagnostic analysis using medical tools
3. **Summary Agent (P03)**: Generates final diagnostic reports

The system is built on LangGraph with structured state management and uses DeepSeek as the LLM provider.

## Development Commands

### Running the Application

```bash
# Start LangGraph development server
uv run langgraph dev

# Or install dependencies first if needed
uv pip install -e . "langgraph-cli[inmem]"
```

The server runs at:
- API: http://127.0.0.1:2024
- Test interface: https://agentchat.vercel.app/?apiUrl=http://localhost:2024&assistantId=agent
- Studio: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024

### Testing

```bash
# Test pre-diagnosis agent
python test/test_pre_diagnosis_agent.py

# Test pre-diagnosis with memory persistence
python test/test_pre_diagnosis_with_memory.py

# Test tools health
python test_tools_health.py
```

### Testing Individual Components

```bash
# Test config loader
python DeepRareAgent/config/loader.py

# Run graph directly (includes test cases)
python DeepRareAgent/graph.py
```

## Architecture

### Agent Workflow (graph.py)

The main workflow is defined in `DeepRareAgent/graph.py`:

- **State**: `DiagnosisAgentState` with `messages`, `patient_info`, and `start_diagnosis` fields
- **Routing**: `route_diagnosis()` conditionally routes to deep diagnosis based on `start_diagnosis` flag
- **Nodes**:
  - `prediagnosis`: Created via `create_pre_diagnosis_node(settings)`
  - `deep_diagnosis`: Created via `create_deep_diagnosis_node(custom_settings)`

### Configuration System

All agents are configured via `config.yml` (root directory):

- **Structure**: YAML-based with nested agent configurations
- **Loader**: `DeepRareAgent/config/loader.py` provides `ConfigObject` that auto-resolves relative paths
- **Access**: Import `settings` from `DeepRareAgent.config`
- **Models**: Each agent specifies:
  - `provider`: "openai" or "anthropic" (selects which LLM client to use)
  - `model_name`: Model identifier (e.g., "deepseek-chat", "claude-3-5-sonnet-20241022")
  - `base_url`: API endpoint (supports both OpenAI and Anthropic compatible APIs)
  - `api_key`: API authentication key
  - `temperature`: Sampling temperature
  - `model_kwargs`: Additional model parameters
  - `system_prompt_path`: Path to prompt template file

The config loader automatically converts relative paths to absolute paths based on project root.

**Model Factory**: All agents use `DeepRareAgent/utils/model_factory.py::create_llm_from_config()` to initialize LLM instances. This supports:
- **OpenAI Compatible**: DeepSeek, OpenAI, GLM (OpenAI mode), custom endpoints
- **Anthropic Compatible**: Claude, GLM (Anthropic mode), custom endpoints

Example configurations:
```yaml
# OpenAI compatible (DeepSeek)
provider: "openai"
model_name: "deepseek-chat"
base_url: "https://api.deepseek.com/v1"

# Anthropic compatible (GLM)
provider: "anthropic"
model_name: "glm-4-plus"
base_url: "https://open.bigmodel.cn/api/paas/v4"
```

### Patient Information Management

Patient data is structured in `patient_info` state field:

```python
{
    "base_info": {},      # Demographics, age, gender, etc.
    "symptoms": [],       # List of symptoms with metadata
    "vitals": [],         # Vital signs measurements
    "exams": [],          # Lab/imaging results
    "medications": [],    # Current medications
    "family_history": [], # Family medical history
    "others": []          # Additional information
}
```

**Key Files**:
- `DeepRareAgent/tools/patientinfo.py`: Tools for CRUD operations on patient info
- Uses `InjectedState` for safe state access in tools
- Returns `Command` objects to update graph state
- `patient_info_to_text()`: Converts structured data to narrative text for diagnosis

### Agent Implementation Patterns

#### P01: Pre-diagnosis Agent (p01pre_diagnosis_agent.py)

- **Purpose**: Conversational patient info collection
- **Output**: `PreDiagnosisReply` with `start_diagnosis` bool and `reply_text`
- **Tools**: `PatientInfoManger` - CRUD tools for patient data
- **Middleware**: `PatientContextPlugin` injects patient context into system messages
- **State**: Uses `PreDiagnosisState` (messages + patient_info)
- **Prompt**: Loaded from file specified in config (`system_prompt_path`)

#### P02: Deep Diagnosis Agent (p02diagnosis_deepagent_agent.py)

- **Architecture**: Main Agent (planning) + Sub Agent (execution) pattern using `deepagents`
- **Main Agent**: Decomposes diagnostic tasks, does NOT call tools directly
- **Sub Agent**: Executes tool calls for literature search and data retrieval
- **Tools**: PubMed, LitSense, HPO, Wikipedia, Baidu search (see `tools/__init__.py`)
- **Input Processing**: Converts structured `patient_info` to narrative text via `patient_info_to_text()`
- **Prompts**: Separate prompts for main and sub agents loaded from config

#### P03: Summary Agent (p03summary_agent.py)

Currently in prototype phase.

### Tools System

**Location**: `DeepRareAgent/tools/`

**Available Tools**:
- `pubmed_tools.py`: PubMed literature search
- `litsense_tool.py`: NCBI LitSense semantic search
- `hpo_tools.py`: HPO (Human Phenotype Ontology) lookup
- `wiki_tools.py`: Wikipedia medical search
- `baidu_tools.py`: Baidu search fallback
- `biomcp_tool.py`: BioMCP integration (optional, requires external service)
- `patientinfo.py`: Patient information CRUD operations

**Tool Loading**:
- `get_all_tools()`: Returns basic tool set (no biomcp)
- `get_all_tools_async(include_biomcp=True)`: Async loading with optional biomcp
- `get_all_tools_with_biomcp_sync()`: Sync version with biomcp

### State Management

**Key Pattern**: Use `InjectedState` for tools that need to read/modify graph state:

```python
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

@tool
def my_tool(
    arg: str,
    state: Annotated[Dict[str, Any], InjectedState]
) -> Command:
    # Read state
    patient_info = state.get("patient_info", {})

    # Return Command to update state
    return Command(update={"patient_info": new_info})
```

**Important**: Direct state mutations don't persist. Always return `Command` objects.

## File Naming Convention

Agent files use `p01`, `p02`, `p03` prefixes (prototype versions) instead of `01`, `02`, `03` to avoid Python import issues with numeric prefixes.

## Common Gotchas

1. **Config Paths**: Always use relative paths in `config.yml` - they're auto-resolved to absolute paths
2. **State Updates**: Tools must return `Command(update={...})` to modify state
3. **Patient Info Structure**: Always initialize with all required fields (use `init_patient_info()` helper)
4. **BioMCP Tools**: Optional and require external service - handle gracefully if unavailable
5. **Provider Selection**: Set `provider: "openai"` or `provider: "anthropic"` in config to match your API's compatibility
6. **API Keys**: Update API keys in `config.yml` for each agent's LLM provider

## Environment Setup

1. Copy `.env.example` to `.env` (though most config is in `config.yml`)
2. Update API keys in `config.yml` if needed
3. Python 3.12+ required (specified in `langgraph.json`)

## Known Issues

- Deep diagnosis agent may encounter errors with specific tools (noted in `运行指南.md`)
- Patient info persistence in test graphs requires proper checkpointer setup
- BioMCP integration requires external service setup
