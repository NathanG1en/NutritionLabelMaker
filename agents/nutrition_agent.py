import os
import operator
from typing import Annotated, TypedDict
from dotenv import load_dotenv

from langchain_core.messages import AnyMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from agents.tools.nutrition_tools import FoodSearcher

_ = load_dotenv()  # Load environment variables

class NutritionAgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    search_results: list
    nutrition_data: list

class NutritionAgent:
    def __init__(self):
        # Initialize FoodSearcher
        api_key = os.getenv("USDA_API_KEY", "DEMO_KEY")
        self.food_searcher = FoodSearcher(api_key)

        # Define Tools
        self.TOOLS = [
            self.food_searcher.retrieve_fdc_ids,
            self.food_searcher.nutrition_retrieval
        ]

        self._tools = {t.__name__ : t for t in self.TOOLS}
        self._tools_llm = ChatOpenAI(model="gpt-4o").bind_tools(self.TOOLS)

        # Define Agent Workflow
        builder = StateGraph(NutritionAgentState)
        builder.add_node("search_food", self.search_food)
        builder.add_node("fetch_nutrition", self.fetch_nutrition)
        builder.add_node("generate_label", self.generate_label)

        builder.set_entry_point("search_food")
        builder.add_edge("search_food", "fetch_nutrition")
        builder.add_edge("fetch_nutrition", "generate_label")
        builder.add_edge("generate_label", END)

        memory = MemorySaver()
        self.graph = builder.compile(checkpointer=memory)

    def search_food(self, state: NutritionAgentState):
        """Step 1: Retrieve FDC IDs for the food query."""
        user_message = state["messages"][-1].content
        search_results = self.food_searcher.retrieve_fdc_ids([user_message])

        return {
            "messages": state["messages"],
            "search_results": search_results.to_dict(orient="records")
        }

    def fetch_nutrition(self, state: NutritionAgentState):
        """Step 2: Retrieve nutrition data based on FDC IDs."""
        fdc_ids = [
            res["fdcId"] for res in state["search_results"]
            if res.get("fdcId") and res["fdcId"] != "N/A"
        ]

        if not fdc_ids:
            return {
                "messages": state["messages"],
                "nutrition_data": []
            }

        nutrition_data = self.food_searcher.nutrition_retrieval(fdc_ids)

        return {
            "messages": state["messages"],
            "nutrition_data": nutrition_data.to_dict(orient="records")
        }
