# # nutrition_agent.py
# import operator
# import os
# import datetime
# from typing import Annotated, TypedDict
# import pandas as pd
#
# from dotenv import load_dotenv
# from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage, ToolMessage
# from langchain_openai import ChatOpenAI
# from langgraph.graph import StateGraph, END
# from langgraph.checkpoint.memory import MemorySaver
#
# from agents.food_search_agent import FoodSearchAgent
#
# _ = load_dotenv()
# CURRENT_YEAR = datetime.datetime.now().year
#
# # Initialize Food Search Agent
# # api_key = os.getenv("USDA_API_KEY", "DEMO_KEY")
# api_key = "DEMO_KEY"
# food_agent = FoodSearchAgent(api_key)
#
#
# # Define Agent State
# class NutritionAgentState(TypedDict):
#     messages: Annotated[list[AnyMessage], operator.add]
#     search_results: dict
#     nutrition_data: dict
#
#
# # Define System Prompt for AI Assistance
# NUTRITION_SYSTEM_PROMPT = f"""
# You are a smart nutrition assistant. Use the tools to look up information about food items.
# You can retrieve FDC IDs, get nutrition data, and generate labels.
# The current year is {CURRENT_YEAR}.
# """
#
# # Define Tools
# TOOLS = [food_agent.retrieve_fdc_ids, food_agent.nutrition_retrieval, food_agent.generate_label]
#
#
# class NutritionAgent:
#     def __init__(self):
#         self._tools = {t.__name__: t for t in TOOLS}
#         self._tools_llm = ChatOpenAI(model="gpt-4o").bind_tools(TOOLS)
#
#         # Define Agent Workflow
#         builder = StateGraph(NutritionAgentState)
#         builder.add_node("search_food", self.search_food)
#         builder.add_node("fetch_nutrition", self.fetch_nutrition)
#         builder.add_node("generate_label", self.generate_label)
#
#         builder.set_entry_point("search_food")
#         builder.add_edge("search_food", "fetch_nutrition")
#         builder.add_edge("fetch_nutrition", "generate_label")
#         builder.add_edge("generate_label", END)
#
#         memory = MemorySaver()
#         self.graph = builder.compile(checkpointer=memory)
#
#     def search_food(self, state: NutritionAgentState):
#         """Step 1: Retrieve FDC IDs for the food query."""
#         user_message = state["messages"][-1].content
#         search_results = food_agent.retrieve_fdc_ids([user_message])
#         return {"messages": state["messages"], "search_results": search_results}
#
#     def fetch_nutrition(self, state: NutritionAgentState):
#         """Step 2: Retrieve nutrition data based on FDC IDs."""
#         fdc_ids = state["search_results"]["fdcId"].dropna().tolist()
#         if not fdc_ids:
#             return {"messages": state["messages"], "nutrition_data": None}
#
#         nutrition_data = food_agent.nutrition_retrieval(fdc_ids)
#         return {"messages": state["messages"], "nutrition_data": nutrition_data}
#
#     def generate_label(self, state: NutritionAgentState):
#         """Step 3: Generate a nutrition label."""
#         if state["nutrition_data"] is None:
#             return {"messages": state["messages"], "nutrition_data": "No nutrition data found"}
#
#         processed_data = food_agent.preprocess_nutrients(state["nutrition_data"])
#         label_text = food_agent.generate_label("User Food", processed_data)
#         return {"messages": [ToolMessage(name="nutrition_label", content=label_text)]}
#
