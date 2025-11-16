import os
from typing import Annotated
from dotenv import load_dotenv
import operator

from langchain_core.messages import (
    BaseMessage,
    AIMessage,
    HumanMessage,
    ToolMessage,
    SystemMessage,
)
from langchain_openai import ChatOpenAI

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode

from backend.agents.tools.nutrition.food_search_funcs import FoodSearcher
from backend.agents.tools.nutrition.nutrition_tools import create_nutrition_tools
from backend.agents.tools.label.label_tools import create_label_tools

load_dotenv()


# ================================================================
# STATE (messages accumulate)
# ================================================================
class AgentState(dict):
    messages: Annotated[list[BaseMessage], operator.add]


# ================================================================
# NUTRITION AGENT
# ================================================================
class NutritionAgent:
    def __init__(self):
        api_key = os.getenv("USDA_KEY", "DEMO_KEY")
        self.food_searcher = FoodSearcher(api_key)

        nutrition_tools = create_nutrition_tools(self.food_searcher)
        label_tools = create_label_tools()
        self.tools = nutrition_tools + label_tools

        # SYSTEM MESSAGE goes here (correct way)
        self.system_msg = SystemMessage(content="""
You are a nutrition assistant following ReAct. 
Think, call tools, observe results, then give a final answer.
Never repeat a tool call if you already have its result.
Never hallucinate a tool.
Never ignore a tool result.
When comparing foods, call nutrition lookup twice before answering.
""")

        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)
        self.llm_with_tools = self.llm.bind_tools(self.tools)

        self.graph = self._build_graph()

    # ================================================================
    # GRAPH
    # ================================================================
    def _build_graph(self):
        workflow = StateGraph(AgentState)

        # ------------------------------------------------------------
        # LLM CALL NODE
        # ------------------------------------------------------------
        def call_llm(state: AgentState):
            msgs = [self.system_msg] + state["messages"]
            resp = self.llm_with_tools.invoke(msgs)
            return {"messages": [resp]}

        workflow.add_node("agent", call_llm)

        # ------------------------------------------------------------
        # TOOL NODE
        # ------------------------------------------------------------
        tool_node = ToolNode(self.tools)
        workflow.add_node("tools", tool_node)

        # ------------------------------------------------------------
        # LOGIC
        # ------------------------------------------------------------
        def route(state: AgentState):
            last = state["messages"][-1]
            if isinstance(last, AIMessage) and last.tool_calls:
                return "tools"
            return "end"

        workflow.set_entry_point("agent")
        workflow.add_conditional_edges("agent", route, {"tools": "tools", "end": END})
        workflow.add_edge("tools", "agent")

        return workflow.compile(checkpointer=MemorySaver())

    # ================================================================
    # RUNTIME
    # ================================================================
    def run(self, user_query: str, thread_id: str = "default"):
        state = {"messages": [HumanMessage(content=user_query)]}
        config = {"configurable": {"thread_id": thread_id}}

        result = self.graph.invoke(state, config)
        msgs = result["messages"]

        last = msgs[-1]

        # If tool output is final, normalize into a dict
        if isinstance(last, ToolMessage):
            content = last.content

            # Tool returned structured dict
            if isinstance(content, dict):
                return content

            # Tool returned string — wrap it
            return {"message": str(content), "type": "text"}

        # Otherwise return last AI response
        for m in reversed(msgs):
            if isinstance(m, AIMessage) and not getattr(m, "tool_calls", None):
                return {"message": m.content, "type": "text"}

        return {"message": "No response.", "type": "text"}

    def get_state_history(self, thread_id="default"):
        config = {"configurable": {"thread_id": thread_id}}
        state = self.graph.get_state(config)
        return state.values.get("messages", [])

# Example usage
if __name__ == "__main__":
    agent = NutritionAgent()

    # Example 1: Search and create text label
    print("=" * 70)
    print("Example 1: Search and create formatted text label")
    print("=" * 70)
    response = agent.run("Find 'chicken breast' and create a text nutrition label for it")
    print(response)
    print()

    # Example 2: Search and create image label
    print("=" * 70)
    print("Example 2: Search and create label image")
    print("=" * 70)
    response = agent.run("Find 'avocado' and generate a nutrition facts label image")
    print(response)
    print()

    # Example 3: Compare foods
    print("=" * 70)
    print("Example 3: Compare protein in foods")
    print("=" * 70)
    response = agent.run("Compare the protein content in salmon vs chicken breast")
    print(response)
    print()

