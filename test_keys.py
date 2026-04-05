import traceback
import sys
from dotenv import load_dotenv
import os

load_dotenv(override=True)

# Check keys
keys = [v for k, v in os.environ.items() if k.startswith("GOOGLE_API_KEY")]
print(f"Found {len(keys)} API keys")

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    
    for i, key in enumerate(keys):
        print(f"\n--- Testing key {i+1} ({key[:12]}...) ---")
        try:
            llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                temperature=0,
                api_key=key,
                convert_system_message_to_human=True,
                max_retries=1,
                timeout=30,
            )
            result = llm.invoke("Say hello in one word")
            print(f"  SUCCESS: {result.content}")
        except Exception as e:
            print(f"  FAILED: {e}")
            
except Exception as e:
    print(f"Import error: {e}")
    traceback.print_exc()
