"""
Medical Report Update Tools

Provides structured tools for diagnostic agents to update the final medical report
in the graph state's 'report' field.

Key features:
- Clear workflow separation between diagnostic analysis and report generation
- Traceable: all tool calls are logged in message history
- Flexible: supports incremental report construction
- State-safe: uses Command pattern for guaranteed state updates
"""
from typing import Annotated, Dict, Any
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.prebuilt import InjectedState


@tool
def submit_medical_report(
    report_content: Annotated[str, "完整的医疗诊断报告内容，应包含诊断结论、证据链、建议等"],
    tool_call_id: Annotated[str, InjectedToolCallId],
    state: Annotated[Dict[str, Any], InjectedState]
) -> Command:
    """
    Submit final medical diagnostic report to system state.

    Use this tool after completing all diagnostic analysis.
    Report should include: diagnosis conclusion, supporting evidence
    (literature, HPO analysis), differential diagnoses, and recommended
    tests or treatments.

    Args:
        report_content: Complete medical diagnostic report (markdown format)

    Returns:
        Command: State update command object
    """
    # Validate non-empty report
    if not report_content or not report_content.strip():
        error_msg = "ERROR: Report content cannot be empty. Please provide complete diagnostic report."
        return Command(
            update={
                "messages": [ToolMessage(content=error_msg, tool_call_id=tool_call_id)]
            }
        )

    # Calculate report statistics
    word_count = len(report_content)

    # Build success message
    success_msg = (
        f"SUCCESS: Medical diagnostic report submitted.\n"
        f"Report length: {word_count} characters.\n"
        f"Report saved to system state for downstream processing."
    )

    # Return Command to update state
    return Command(
        update={
            "report": report_content,  # Update report field
            "messages": [ToolMessage(content=success_msg, tool_call_id=tool_call_id)]
        }
    )


@tool
def update_report_section(
    section_name: Annotated[str, "报告章节名称（如：'诊断结论'、'证据链'、'建议'等）"],
    section_content: Annotated[str, "该章节的内容"],
    tool_call_id: Annotated[str, InjectedToolCallId],
    state: Annotated[Dict[str, Any], InjectedState]
) -> Command:
    """
    Incrementally update a specific section of the medical report.

    Use this tool to build the report section by section.
    Finally use submit_medical_report to submit the complete report.

    Args:
        section_name: Section name (e.g., 'Diagnosis', 'Evidence', 'Recommendations')
        section_content: Section content

    Returns:
        Command: State update command object
    """
    # Get current report
    current_report = state.get("report", "")

    # Append new section
    updated_report = current_report + f"\n\n## {section_name}\n\n{section_content}"

    success_msg = f"SUCCESS: Report section '{section_name}' updated."

    return Command(
        update={
            "report": updated_report,
            "messages": [ToolMessage(content=success_msg, tool_call_id=tool_call_id)]
        }
    )


# Export tool list
MEDICAL_REPORT_TOOLS = [submit_medical_report, update_report_section]


if __name__ == "__main__":
    """Test medical report update tools"""
    from typing_extensions import TypedDict
    import asyncio
    from langchain.agents import create_agent
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage
    import operator

    class TestState(TypedDict):
        messages: Annotated[list, operator.add]
        report: str

    async def test_report_tools():
        print("=== Testing Medical Report Update Tools ===\n")

        # Initialize model
                # model_name: "GLM-4.7"
        # base_url: "https://aiping.cn/api/v1"
        # api_key: "QC-25c1cf63e5fba043d6561ae34dbe2f75-6547c332c2240a8bd79ddf103172c896"
        model = ChatOpenAI(
            model="GLM-4.7",
            api_key="QC-25c1cf63e5fba043d6561ae34dbe2f75-6547c332c2240a8bd79ddf103172c896",  # Replace with actual API key
            base_url="https://aiping.cn/api/v1",
            temperature=0
        )

        # Create agent
        agent = create_agent(
            model=model,
            tools=MEDICAL_REPORT_TOOLS,
            state_schema=TestState
        )

        # Test scenario: model generates and submits diagnostic report
        initial_state = {
            "messages": [
                HumanMessage(content="""
You are a medical diagnostic expert. Patient symptoms:
- Periodic pain in extremities
- Hypohidrosis (reduced sweating)
- Angiokeratomas
- Family history of kidney failure

Analyze and use submit_medical_report tool to submit final diagnostic report.
Report should include: diagnosis conclusion, evidence, differential diagnoses, recommendations.
                """)
            ],
            "report": ""
        }

        print("Initial state:")
        print(f"  Report: '{initial_state['report']}'")
        print("\n>>> Starting test...")

        result = await agent.ainvoke(initial_state)

        print("\n=== Final State ===")
        print(f"Report field:\n{result.get('report', '(empty)')}\n")

        print("Message history:")
        for msg in result.get("messages", []):
            print(f"  - {type(msg).__name__}: {msg.content[:100]}...")

    # Run test
    # asyncio.run(test_report_tools())
    print("Note: Update API key and uncomment last line to run test")
