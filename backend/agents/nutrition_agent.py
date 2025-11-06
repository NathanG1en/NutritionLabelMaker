import os
from typing import Annotated
from dotenv import load_dotenv
import operator

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode

from backend.agents.tools.nutrition.food_search_funcs import FoodSearcher
from backend.agents.tools.nutrition.nutrition_tools import create_nutrition_tools
from backend.agents.tools.label.label_tools import create_label_tools

load_dotenv()


class AgentState(dict):
    """State for the nutrition agent with proper message accumulation."""
    messages: Annotated[list[BaseMessage], operator.add]


class NutritionAgent:
    def __init__(self):
        # Initialize FoodSearcher
        api_key = os.getenv("USDA_KEY", "DEMO_KEY")
        self.food_searcher = FoodSearcher(api_key)
        
        # Create tools using factory functions
        nutrition_tools = create_nutrition_tools(self.food_searcher)
        label_tools = create_label_tools()
        
        # Combine all tools
        self.tools = nutrition_tools + label_tools
        
        # Initialize LLM with tools
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)
        self.llm_with_tools = self.llm.bind_tools(self.tools)

        # Build the graph
        self.graph = self._build_graph()

    def _build_graph(self):
        """Build the LangGraph workflow."""
        
        # Create the graph with proper state annotation
        workflow = StateGraph(AgentState)

        # Define the agent node - this is where the LLM decides what to do
        def call_model(state: AgentState):
            """LLM decides which tool to call based on conversation history."""
            messages = state["messages"]
            response = self.llm_with_tools.invoke(messages)
            return {"messages": [response]}

        # Define tool execution node using ToolNode
        tool_node = ToolNode(self.tools)

        # Add nodes
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", tool_node)

        # Define conditional edge - should we use tools or finish?
        def should_continue(state: AgentState):
            """Determine if we should continue to tools or end."""
            messages = state["messages"]
            last_message = messages[-1]
            
            # If the LLM makes a tool call, continue to tools
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "tools"
            
            # Otherwise, we're done
            return "end"

        # Set up the flow
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges(
            "agent",
            should_continue,
            {
                "tools": "tools",
                "end": END
            }
        )
        
        # After tools are executed, go back to the agent
        workflow.add_edge("tools", "agent")

        # Compile with memory
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)

    def run(self, user_query: str, thread_id: str = "default"):
        """
        Run the agent with a user query.
        
        Args:
            user_query: The user's question or request
            thread_id: Conversation thread ID for memory persistence
        
        Returns:
            The agent's final response
        """
        config = {"configurable": {"thread_id": thread_id}}
        
        # Create initial state
        initial_state = {
            "messages": [HumanMessage(content=user_query)]
        }
        
        # Run the graph
        result = self.graph.invoke(initial_state, config)
        
        # Return the last AI message content
        messages = result["messages"]
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and not msg.tool_calls:
                return msg.content
        
        return "No response generated"

    def stream(self, user_query: str, thread_id: str = "default"):
        """
        Stream the agent's response.
        
        Args:
            user_query: The user's question or request
            thread_id: Conversation thread ID for memory persistence
        
        Yields:
            Dict with node name and messages
        """
        config = {"configurable": {"thread_id": thread_id}}
        
        initial_state = {
            "messages": [HumanMessage(content=user_query)]
        }
        
        for event in self.graph.stream(initial_state, config, stream_mode="updates"):
            yield event

    def get_state_history(self, thread_id: str = "default"):
        """Get the conversation history for a thread."""
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
