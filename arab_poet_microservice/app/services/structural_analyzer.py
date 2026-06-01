import torch
import torch.nn as nn
import torch.nn.functional as F
import json
import re
import os
from typing import Dict, Any

# 1. Architecture Components (Must match the trained model exactly)
class Attention(nn.Module):
    def __init__(self, hidden_dim):
        super(Attention, self).__init__()
        self.attention = nn.Linear(hidden_dim, 1)

    def forward(self, lstm_output):
        attn_weights = self.attention(lstm_output)
        attn_weights = F.softmax(attn_weights, dim=1) 
        context_vector = torch.sum(attn_weights * lstm_output, dim=1)
        return context_vector, attn_weights

class SOTA_ArabPoetDualModel(nn.Module):
    def __init__(self, vocab_size, num_meters, num_rhymes, embed_dim=128):
        super(SOTA_ArabPoetDualModel, self).__init__()
        self.embedding = nn.Embedding(num_embeddings=vocab_size, embedding_dim=embed_dim, padding_idx=0)
        
        self.meter_lstm = nn.LSTM(input_size=embed_dim, hidden_size=128, num_layers=2, batch_first=True, bidirectional=True, dropout=0.3)
        self.meter_attention = Attention(hidden_dim=256)
        
        self.error_conv = nn.Conv1d(in_channels=embed_dim, out_channels=128, kernel_size=5, padding=2)
        self.error_relu = nn.ReLU()
        self.error_pool = nn.MaxPool1d(kernel_size=2)
        self.error_lstm = nn.LSTM(input_size=128, hidden_size=64, num_layers=1, batch_first=True, bidirectional=True)
        
        self.rhyme_conv = nn.Conv1d(in_channels=embed_dim, out_channels=64, kernel_size=3, padding=1)
        self.rhyme_relu = nn.ReLU()
        self.dropout = nn.Dropout(0.4)
        
        self.meter_head = nn.Sequential(nn.Linear(256, 128), nn.ReLU(), nn.Dropout(0.3), nn.Linear(128, num_meters))
        self.error_head = nn.Sequential(nn.Linear(128, 64), nn.ReLU(), nn.Dropout(0.3), nn.Linear(64, 1))
        self.rhyme_head = nn.Sequential(nn.Linear(64, 128), nn.ReLU(), nn.Dropout(0.3), nn.Linear(128, num_rhymes))

    def forward(self, verse_seq, char_seq):
        verse_embed = self.embedding(verse_seq)
        rhyme_embed = self.embedding(char_seq)
        
        meter_lstm_out, _ = self.meter_lstm(verse_embed)
        meter_features, _ = self.meter_attention(meter_lstm_out)
        meter_features = self.dropout(meter_features)
        
        x_error = verse_embed.permute(0, 2, 1) 
        x_error = self.error_conv(x_error)
        x_error = self.error_relu(x_error)
        x_error = self.error_pool(x_error)
        x_error = x_error.permute(0, 2, 1)
        error_lstm_out, _ = self.error_lstm(x_error)
        error_features, _ = torch.max(error_lstm_out, dim=1)
        error_features = self.dropout(error_features)

        x_rhyme = rhyme_embed.permute(0, 2, 1)
        x_rhyme = self.rhyme_conv(x_rhyme)
        x_rhyme = self.rhyme_relu(x_rhyme)
        char_features, _ = torch.max(x_rhyme, dim=2)
        char_features = self.dropout(char_features)

        return self.meter_head(meter_features), self.rhyme_head(char_features), self.error_head(error_features)

# 2. Preprocessor
class CharLevelPreprocessor:
    def __init__(self, max_verse_len=150, max_rhyme_len=10):
        self.max_verse_len = max_verse_len
        self.max_rhyme_len = max_rhyme_len
        self.arabic_alphabet = list("ءآأؤإئابتثجحخدذرزسشصضطظعغفقكلمنهويىةَُِّْ")
        self.char_to_id = {char: idx + 1 for idx, char in enumerate(self.arabic_alphabet)}
        self.vocab_size = len(self.char_to_id) + 1 

    def encode_full_verse(self, verse):
        verse_clean = re.sub(r'[^\u0621-\u064A\u064B-\u0652]', '', str(verse))
        encoded = [self.char_to_id.get(c, 0) for c in verse_clean]
        if len(encoded) > self.max_verse_len: return encoded[:self.max_verse_len]
        return encoded + [0] * (self.max_verse_len - len(encoded))

    def encode_rhyme_chars(self, verse):
        clean_verse = re.sub(r'[\u064B-\u0652]', '', str(verse)).strip()
        last_chars = list(clean_verse.replace(" ", ""))[-self.max_rhyme_len:]
        encoded_chars = [self.char_to_id.get(c, 0) for c in last_chars]
        if len(encoded_chars) < self.max_rhyme_len:
            encoded_chars = [0] * (self.max_rhyme_len - len(encoded_chars)) + encoded_chars
        return encoded_chars

# 3. Main Analyzer Service
class StructuralAnalyzer:
    def __init__(self):
        print("--- Initializing Structural Analyzer (PyTorch) ---")
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.preprocessor = CharLevelPreprocessor()
        self.error_threshold = 0.40 # Determined via our threshold tuning!
        
        self._load_mappings()
        self._load_model()

    def _load_mappings(self):
        with open('weights/dl_meter_mapping.json', 'r', encoding='utf-8') as f:
            self.meter_map = json.load(f)
            self.rev_meter_map = {v: k for k, v in self.meter_map.items()}
        
        with open('weights/dl_rhyme_mapping.json', 'r', encoding='utf-8') as f:
            self.rhyme_map = json.load(f)
            self.rev_rhyme_map = {v: k for k, v in self.rhyme_map.items()}

    def _load_model(self):
        self.model = SOTA_ArabPoetDualModel(
            vocab_size=43,
            num_meters=len(self.meter_map),
            num_rhymes=len(self.rhyme_map),
            embed_dim=128
        )
        model_path = 'weights/hybrid_mtl_best_sota.pt'
        if os.path.exists(model_path):
            state_dict = torch.load(model_path, map_location=self.device)
            clean_state_dict = {k.replace('module.', ''): v for k, v in state_dict.items()}
            self.model.load_state_dict(clean_state_dict)
            self.model.to(self.device)
            self.model.eval()
            print("PyTorch model loaded successfully.")
        else:
            print(f"WARNING: Weights not found at {model_path}. Structural analysis will fail.")

    def analyze(self, verse_text: str) -> Dict[str, Any]:
        verse_seq = torch.tensor([self.preprocessor.encode_full_verse(verse_text)], dtype=torch.long).to(self.device)
        char_seq = torch.tensor([self.preprocessor.encode_rhyme_chars(verse_text)], dtype=torch.long).to(self.device)

        with torch.no_grad():
            m_logits, r_logits, e_logits = self.model(verse_seq, char_seq)
            
            m_pred = torch.argmax(m_logits, dim=1).item()
            m_prob = F.softmax(m_logits, dim=1).max().item()
            
            r_pred = torch.argmax(r_logits, dim=1).item()
            r_prob = F.softmax(r_logits, dim=1).max().item()
            
            e_prob = torch.sigmoid(e_logits).item()
            is_broken = bool(e_prob > self.error_threshold)

        return {
            "meter": {"result": self.rev_meter_map[m_pred], "confidence": m_prob, "fail": False, "source": "local_pytorch"},
            "rhyme": {"result": self.rev_rhyme_map[r_pred], "confidence": r_prob, "fail": False, "source": "local_pytorch"},
            "errors": {"result": "مكسور" if is_broken else "سليم", "confidence": e_prob, "fail": False, "source": "local_pytorch"}
        }

structural_analyzer = StructuralAnalyzer()