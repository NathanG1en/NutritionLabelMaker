import os
from typing import Annotated
from dotenv import load_dotenv
import operator
import json

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode

from agents.food_search_funcs import FoodSearcher

load_dotenv()


class AgentState(dict):
    """State for the nutrition agent with proper message accumulation."""
    messages: Annotated[list[BaseMessage], operator.add]


class NutritionAgent:
    def __init__(self):
        # Initialize FoodSearcher
        api_key = os.getenv("USDA_KEY", "DEMO_KEY")
        self.food_searcher = FoodSearcher(api_key)

        # Define LangChain-compatible tools
        from langchain_core.tools import tool

        @tool
        def search_food_items(food_items: str, branded: bool = True, alpha: float = 0.5) -> str:
            """
            Search for food items in the USDA database and retrieve their FDC IDs.
            
            Args:
                food_items: Comma-separated list of food item names to search for (e.g., "chicken breast, salmon")
                branded: Whether to prioritize branded food items
                alpha: Weight for SBERT vs fuzzy matching (0.0-1.0)
            
            Returns:
                JSON string containing FDC IDs and food descriptions
            """
            try:
                # Parse comma-separated string into list
                items_list = [item.strip() for item in food_items.split(",")]
                results = self.food_searcher.retrieve_fdc_ids(items_list, branded=branded, alpha=alpha)
                
                if results.empty:
                    return json.dumps({"error": "No food items found", "results": []})
                
                return results.to_json(orient="records", indent=2)
            except Exception as e:
                return json.dumps({"error": f"Error searching for food items: {str(e)}", "results": []})

        @tool
        def get_nutrition_data(fdc_ids: str) -> str:
            """
            Retrieve detailed nutrition information for given FDC IDs.
            
            Args:
                fdc_ids: Comma-separated list of FDC ID numbers (e.g., "12345, 67890")
            
            Returns:
                JSON string containing nutrition data (calories, protein, vitamins, etc.)
            """
            try:
                # Parse comma-separated string into list of integers
                ids_list = [int(id_str.strip()) for id_str in fdc_ids.split(",")]
                
                # Call nutrition_retrieval WITHOUT descriptors - let it use defaults
                nutrition_df = self.food_searcher.nutrition_retrieval(ids_list)
                
                if nutrition_df.empty:
                    return json.dumps({"error": "No nutrition data found", "results": []})
                
                # Convert to dict for better JSON serialization
                result = nutrition_df.to_dict(orient="records")
                return json.dumps(result, indent=2)
            except ValueError as e:
                return json.dumps({"error": f"Invalid FDC ID format: {str(e)}", "results": []})
            except Exception as e:
                return json.dumps({"error": f"Error retrieving nutrition data: {str(e)}", "results": []})

        @tool
        def compare_nutrients(food_data: str, nutrient_name: str) -> str:
            """
            Compare a specific nutrient across multiple foods.
            
            Args:
                food_data: JSON string containing nutrition data from get_nutrition_data
                nutrient_name: Name of nutrient to compare (e.g., "protein", "energy", "calcium")
            
            Returns:
                Comparison summary as a string
            """
            try:
                data = json.loads(food_data)
                
                if isinstance(data, dict) and "error" in data:
                    return f"Cannot compare: {data['error']}"
                
                comparison = []
                for item in data:
                    name = item.get('name', 'Unknown')
                    value = item.get(nutrient_name, 0)
                    comparison.append(f"{name}: {value}")
                
                return "\n".join(comparison)
            except Exception as e:
                return f"Error comparing nutrients: {str(e)}"

        # Store tools
        self.tools = [search_food_items, get_nutrition_data, compare_nutrients]
        
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
    
    # Example 1: Simple query
    print("=" * 70)
    print("Example 1: Search for a food item")
    print("=" * 70)
    response = agent.run("Find nutrition information for 'organic whole milk'")
    print(response)
    print()
    
    # Example 2: Compare foods
    print("=" * 70)
    print("Example 2: Compare foods")
    print("=" * 70)
    response = agent.run(
        "Compare the protein content of 'chicken breast' and 'ground beef'",
        thread_id="comparison"
    )
    print(response)
    print()
