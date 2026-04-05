import traceback
import sys
from dotenv import load_dotenv

load_dotenv(override=True)

try:
    from agents.supervisor import build_multi_agent_graph
    from langchain_core.messages import HumanMessage
    graph = build_multi_agent_graph()
    graph.invoke({'messages': [HumanMessage(content='hi')]})
    print('SUCCESS')
except Exception as e:
    print('ERROR DETAILS (saved to test_error_log.txt)')
    with open('test_error_log.txt', 'w', encoding='utf-8') as f:
        traceback.print_exc(file=f)
