import os
import torch
from pathlib import Path

# Safely import from our isolated CATT core directory
try:
    from .catt_core.ed_pl import TashkeelModel as TashkeelModelED
    from .catt_core.tashkeel_tokenizer import TashkeelTokenizer
    from .catt_core.utils import remove_non_arabic
    IMPORTS_SUCCESSFUL = True
except ImportError as e:
    print(f"Diacritizer Import Warning: Missing CATT files. Details: {e}")
    IMPORTS_SUCCESSFUL = False

class DiacritizerEngine:
    def __init__(self):
        print("--- Initializing Diacritizer Engine (CATT Encoder-Decoder) ---")
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.max_seq_len = 1024
        
        # Pointing to the weights file (Ensure it exists in this exact path)
        base_dir = Path(__file__).parent
        self.ed_ckpt_path = base_dir / 'catt_core' / 'models' / 'best_ed_mlm_ns_epoch_178.pt'
        
        self.is_ready = False
        if IMPORTS_SUCCESSFUL:
            self._load_model()

    def _load_model(self):
        try:
            self.tokenizer = TashkeelTokenizer()
            # Initialize Encoder-Decoder model
            self.ed_model = TashkeelModelED(
                self.tokenizer, 
                max_seq_len=self.max_seq_len, 
                n_layers=3, 
                learnable_pos_emb=False
            )
            
            if os.path.exists(self.ed_ckpt_path):
                # Load weights strictly avoiding missing key errors
                self.ed_model.load_state_dict(torch.load(self.ed_ckpt_path, map_location=self.device))
                self.ed_model.eval().to(self.device)
                self.is_ready = True
                print("Diacritizer model loaded successfully.")
            else:
                print(f"WARNING: Diacritizer weights not found at {self.ed_ckpt_path}. Returning raw text.")
        except Exception as e:
            print(f"Failed to load Diacritizer: {str(e)}")

    def diacritize(self, input_text: str) -> str:
        """
        Processes raw text through the CATT model and returns fully diacritized text.
        """
        if not self.is_ready:
            return input_text
            
        try:
            # 1. Clean the text using their native utility
            clean_text = remove_non_arabic(input_text)
            
            # 2. Run inference (batch_size=1)
            output_texts = self.ed_model.do_tashkeel_batch([clean_text], batch_size=1, verbose=False)
            
            return output_texts[0] if output_texts else input_text
            
        except Exception as e:
            print(f"Diacritization Process Error: {str(e)}")
            return input_text

# Instantiated engine ready for routes.py
diacritizer_engine = DiacritizerEngine()