import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.storage.firebase_client import get_firebase_client

async def main():
    try:
        db = get_firebase_client()
        calls = await db.get_recent_calls(limit=1)
        
        if not calls:
            print("No calls found in Firestore.")
            return

        last_call = calls[0]
        print(f"=== Last Call ID: {last_call.get('call_id')} ===")
        print(f"Date: {last_call.get('created_at')}")
        print(f"Status: {last_call.get('status')}")
        
        print("\n--- Transcript ---")
        transcript = last_call.get('transcript', [])
        for entry in transcript:
            role = entry.get('role', 'unknown')
            content = entry.get('content', '')
            print(f"[{role.upper()}]: {content}")
            
            # Check for tool calls
            if 'tool_calls' in entry and entry['tool_calls']:
                print(f"  >>> TOOL CALLS: {entry['tool_calls']}")

        print("\n--- Cost Data ---")
        print(last_call.get('cost_data', {}))

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
