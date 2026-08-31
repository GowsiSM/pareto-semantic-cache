# backend/experiment/moss_loader.py
import json
import os
import re
from typing import List, Tuple, Optional, Dict, Any

class MOSSLoader:
    """
    MOSS dataset loader for SCALM experiments.
    
    MOSS format (from debug):
    {
        "conversation_id": 1,
        "meta_instruction": "...",
        "num_turns": 5,
        "chat": {
            "turn_1": {"Human": "<|Human|>: ...", "MOSS": "<|MOSS|>: ..."},
            "turn_2": {"Human": "<|Human|>: ...", "MOSS": "<|MOSS|>: ..."}
        },
        "category": "..."
    }
    """
    
    def __init__(self, file_path: str, limit: Optional[int] = None):
        self.file_path = file_path
        self.limit = limit
        self.conversations = []
        self._load()
    
    def _load(self):
        """Load conversations with limit."""
        if not os.path.exists(self.file_path):
            print(f"❌ File not found: {self.file_path}")
            return
        
        size = os.path.getsize(self.file_path)
        size_mb = size / (1024**2)
        print(f"📊 File size: {size_mb:.1f} MB")
        
        loaded = 0
        with open(self.file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if self.limit and loaded >= self.limit:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                try:
                    conv = json.loads(line)
                    self.conversations.append(conv)
                    loaded += 1
                except json.JSONDecodeError:
                    continue
        
        print(f"✅ Loaded {len(self.conversations):,} conversations")
    
    def _clean_text(self, text: str) -> str:
        """Remove special tokens like <|Human|>, <|MOSS|>, <eoh>."""
        # Remove <|Human|>: and <|MOSS|>: tags
        text = re.sub(r'<\|Human\|>:\s*', '', text)
        text = re.sub(r'<\|MOSS\|>:\s*', '', text)
        # Remove <eoh> (end of human) tags
        text = re.sub(r'<eoh>', '', text)
        # Remove any other special tokens
        text = re.sub(r'<\|.*?\|>', '', text)
        return text.strip()
    
    def get_first_turn_pairs(self) -> List[Tuple[str, str]]:
        """
        Extract first turn (Human, MOSS) from each conversation.
        """
        pairs = []
        
        for conv in self.conversations:
            chat = conv.get('chat', {})
            
            if isinstance(chat, dict):
                # Get the first turn (turn_1)
                first_turn = chat.get('turn_1', {})
                
                if 'Human' in first_turn and 'MOSS' in first_turn:
                    human_text = self._clean_text(first_turn['Human'])
                    moss_text = self._clean_text(first_turn['MOSS'])
                    
                    # Skip if empty after cleaning
                    if human_text and moss_text:
                        pairs.append((human_text, moss_text))
        
        return pairs
    
    def get_all_turns_pairs(self) -> List[Tuple[str, str]]:
        """Extract all turns as (Human, MOSS) pairs."""
        pairs = []
        
        for conv in self.conversations:
            chat = conv.get('chat', {})
            
            if isinstance(chat, dict):
                # Get all turns sorted by key
                for key in sorted(chat.keys()):
                    turn = chat[key]
                    if 'Human' in turn and 'MOSS' in turn:
                        human_text = self._clean_text(turn['Human'])
                        moss_text = self._clean_text(turn['MOSS'])
                        if human_text and moss_text:
                            pairs.append((human_text, moss_text))
        
        return pairs
    
    def get_turns_by_category(self, category: str) -> List[Tuple[str, str]]:
        """Get all turns from conversations with a specific category."""
        pairs = []
        for conv in self.conversations:
            if conv.get('category') == category:
                chat = conv.get('chat', {})
                if isinstance(chat, dict):
                    for key in sorted(chat.keys()):
                        turn = chat[key]
                        if 'Human' in turn and 'MOSS' in turn:
                            human_text = self._clean_text(turn['Human'])
                            moss_text = self._clean_text(turn['MOSS'])
                            if human_text and moss_text:
                                pairs.append((human_text, moss_text))
        return pairs
    
    def inspect_first_conversation(self):
        """Print structure of first conversation for debugging."""
        if not self.conversations:
            print("No conversations loaded")
            return
        
        conv = self.conversations[0]
        print("\n📋 First conversation structure:")
        print(json.dumps(conv, indent=2, ensure_ascii=False)[:1500])
    
    def get_stats(self) -> dict:
        """Get dataset statistics."""
        total_turns = 0
        categories = {}
        
        for conv in self.conversations:
            chat = conv.get('chat', {})
            if isinstance(chat, dict):
                total_turns += len(chat)
            
            category = conv.get('category', 'unknown')
            categories[category] = categories.get(category, 0) + 1
        
        return {
            "total_conversations": len(self.conversations),
            "total_turns": total_turns,
            "avg_turns_per_conversation": total_turns / len(self.conversations) if len(self.conversations) > 0 else 0,
            "categories": categories
        }
    
    def __len__(self) -> int:
        return len(self.conversations)