# from app.services.llm import LLMService


# llm = LLMService()

# response = llm.generate([
#     {
#         "role": "user",
#         "content": "Explain what an evidence-based investigation system is in one paragraph."
#     }
# ])

# print(response)
from app.investigator.planner import InvestigationPlanner


planner = InvestigationPlanner()

result = planner.create_plan(
    "Investigate whether NVIDIA's dominance in AI GPUs is sustainable."
)

print(result)