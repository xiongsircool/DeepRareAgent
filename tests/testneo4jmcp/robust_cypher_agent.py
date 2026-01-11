from typing import Annotated, Dict, Any, List, Optional
from typing_extensions import TypedDict
from langchain_neo4j import Neo4jGraph
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END

# Define State
class GraphState(TypedDict):
    question: str
    cypher: str
    result: str
    error: Optional[str]
    steps: List[str]

# Setup (using config from your notebook)
graph = Neo4jGraph(
    url="neo4j://localhost:7687", 
    database="monarch-kg", 
    username="neo4j", 
    password="xxy123456"
)

# Note: Ideally load API Key from env vars
model = ChatOpenAI(
    model_name="MiniMax-M2.1",
    base_url="https://aiping.cn/api/v1",
    api_key="QC-25c1cf63e5fba043d6561ae34dbe2f75-6547c332c2240a8bd79ddf103172c896",
    temperature=0
)

# Prompts
cypher_gen_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a Neo4j expert. Given an input question, convert it to a Cypher query. Output ONLY the Cypher query, no markdown."),
    ("human", "Question: {question}\nSchema: {schema}")
])

cypher_fix_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a Neo4j expert. The following Cypher query caused an error. Fix it based on the error and schema. Output ONLY the fixed Cypher query."),
    ("human", "Question: {question}\nCypher: {cypher}\nError: {error}\nSchema: {schema}")
])

# Nodes
def generate_cypher(state: GraphState):
    print("---GENERATING CYPHER---")
    schema = graph.get_schema
    cypher = (cypher_gen_prompt | model | StrOutputParser()).invoke({"question": state["question"], "schema": schema})
    # Clean up markdown if present
    cypher = cypher.replace("```cypher", "").replace("```", "").strip()
    return {"cypher": cypher, "steps": ["generate"], "error": None}

def execute_cypher(state: GraphState):
    print("---EXECUTING CYPHER---")
    try:
        # Use allow_dangerous_requests=True equivalent by just calling query
        result = graph.query(state["cypher"])
        return {"result": str(result), "error": None}
    except Exception as e:
        print(f"Cypher Error: {e}")
        return {"error": str(e)}

def fix_cypher(state: GraphState):
    print("---FIXING CYPHER---")
    schema = graph.get_schema
    new_cypher = (cypher_fix_prompt | model | StrOutputParser()).invoke(
        {"question": state["question"], "cypher": state["cypher"], "error": state["error"], "schema": schema}
    )
    new_cypher = new_cypher.replace("```cypher", "").replace("```", "").strip()
    # Append 'fix' to steps
    current_steps = state.get("steps", [])
    return {"cypher": new_cypher, "steps": current_steps + ["fix"]}

# Edges
def check_error(state: GraphState):
    if state.get("error"):
        steps = state.get("steps", [])
        # Prevent infinite loops - max 3 retries
        fix_count = len([s for s in steps if s == "fix"])
        if fix_count >= 3:
            print("---MAX RETRIES REACHED---")
            return END
        return "fix_cypher"
    return END

# Build Graph
workflow = StateGraph(GraphState)
workflow.add_node("generate_cypher", generate_cypher)
workflow.add_node("execute_cypher", execute_cypher)
workflow.add_node("fix_cypher", fix_cypher)

workflow.set_entry_point("generate_cypher")
workflow.add_edge("generate_cypher", "execute_cypher")
workflow.add_conditional_edges("execute_cypher", check_error, {"fix_cypher": "fix_cypher", END: END})
workflow.add_edge("fix_cypher", "execute_cypher")

app = workflow.compile()

# Example usage
if __name__ == "__main__":
    inputs = {"question": "帮我随机查一下某个症状的疾病有哪些，主要想测试下你对于知识图谱处理性能"}
    print(f"Processing: {inputs['question']}")
    for output in app.stream(inputs):
        pass
    print("Final State Finished")
