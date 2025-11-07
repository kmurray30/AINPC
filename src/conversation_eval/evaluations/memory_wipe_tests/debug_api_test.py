#!/usr/bin/env python3
"""
Debug script to test API calls and isolate the issue
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

def test_api_step_by_step():
    print("🔍 Debugging API call issue...")
    
    try:
        print("1. Testing environment loading...")
        from src.utils.Utilities import init_dotenv
        init_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        print(f"   ✅ API key loaded: {api_key[:20]}...{api_key[-10:]}")
        
        print("2. Testing OpenAI client creation...")
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        print("   ✅ OpenAI client created")
        
        print("3. Testing simple API call...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'Hello' in one word"}],
            max_tokens=5
        )
        print(f"   ✅ API call successful: {response.choices[0].message.content}")
        
        print("4. Testing ChatBot class...")
        from src.utils.ChatBot import ChatBot
        print("   ✅ ChatBot imported")
        
        print("5. Testing ChatBot API call...")
        messages = [{"role": "user", "content": "Say 'Test' in one word"}]
        result = ChatBot.call_llm(messages)
        print(f"   ✅ ChatBot call successful: {result}")
        
        print("6. Testing NPC0...")
        from src.npcs.npc0.npc0 import NPC0
        npc = NPC0("You are a test assistant. Respond with exactly one word.")
        print("   ✅ NPC0 created")
        
        print("7. Testing NPC0 chat...")
        response = npc.chat("Say hello")
        print(f"   ✅ NPC0 chat successful: {response.response}")
        
        print("\n🎉 All tests passed! The API is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Error at step: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_api_step_by_step()
