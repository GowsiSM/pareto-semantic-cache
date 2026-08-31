# debug_moss.py
"""
Debug MOSS dataset structure to understand the actual format.
"""

import json
import os

def debug_moss(file_path, num_lines=5):
    """Inspect the actual structure of MOSS dataset."""
    
    print(f"📂 Debugging: {file_path}")
    print(f"📝 Reading first {num_lines} lines\n")
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for i in range(num_lines):
            line = f.readline()
            if not line:
                break
            
            print(f"{'='*60}")
            print(f"Line {i+1}:")
            print(f"{'='*60}")
            
            try:
                data = json.loads(line)
                
                # Print all top-level keys
                print(f"\n📋 Top-level keys: {list(data.keys())}")
                
                # Print conversation_id
                if 'conversation_id' in data:
                    print(f"   conversation_id: {data['conversation_id']}")
                
                # Print meta_instruction preview
                if 'meta_instruction' in data:
                    preview = data['meta_instruction'][:100] + "..."
                    print(f"   meta_instruction: {preview}")
                
                # Inspect chat structure
                if 'chat' in data:
                    chat = data['chat']
                    print(f"\n📋 chat type: {type(chat).__name__}")
                    
                    if isinstance(chat, dict):
                        print(f"   chat keys: {list(chat.keys())[:5]}")
                        
                        # Inspect first few turns
                        for key in list(chat.keys())[:3]:
                            turn = chat[key]
                            print(f"\n   Turn {key}:")
                            print(f"      Type: {type(turn).__name__}")
                            print(f"      Keys: {list(turn.keys()) if isinstance(turn, dict) else 'Not a dict'}")
                            
                            if isinstance(turn, dict):
                                if 'Human' in turn:
                                    preview = turn['Human'][:80] + "..."
                                    print(f"      Human: {preview}")
                                if 'MOSS' in turn:
                                    preview = turn['MOSS'][:80] + "..."
                                    print(f"      MOSS: {preview}")
                    
                    elif isinstance(chat, list):
                        print(f"   chat length: {len(chat)}")
                        for j, turn in enumerate(chat[:3]):
                            print(f"\n   Turn {j}:")
                            print(f"      Type: {type(turn).__name__}")
                            if isinstance(turn, dict):
                                print(f"      Keys: {list(turn.keys())}")
                                if 'role' in turn:
                                    print(f"      role: {turn.get('role')}")
                                if 'content' in turn:
                                    preview = turn.get('content', '')[:80] + "..."
                                    print(f"      content: {preview}")
                
            except json.JSONDecodeError as e:
                print(f"❌ JSON decode error: {e}")
                print(f"   Line preview: {line[:100]}...")

if __name__ == "__main__":
    debug_moss("moss-sample-10k.jsonl", num_lines=3)