"""
MedVoice AI - Cost Calculations
Service for estimating financial costs of calls.
"""

from typing import Dict, Optional

class CostService:
    """
    Calculates estimated costs for various services used during a call.
    Rates are in USD.
    """
    
    # Rates (USD)
    RATES = {
        # Twilio Voice (Inbound/Outbound mix estimate) - per minute
        "twilio_voice_min": 0.014,
        
        # Deepgram Nova-2 (Streaming) - per minute
        "deepgram_min": 0.0043,
        
        # Google Cloud TTS (Journey/Premium) - per 1000 characters
        "google_tts_1k_chars": 0.016, 
        
        # LLM - DeepSeek V3 (Approximate) - per 1M tokens
        # Note: Using high-end estimate to be safe
        "deepseek_input_1m": 0.14,
        "deepseek_output_1m": 0.28,
        
        # LLM - GPT-4o-mini (Fallback) - per 1M tokens
        "gpt4omini_input_1m": 0.15,
        "gpt4omini_output_1m": 0.60,
    }

    @classmethod
    def calculate_call_cost(
        cls,
        duration_seconds: int,
        tts_characters: int,
        llm_input_tokens: int,
        llm_output_tokens: int,
        model_name: str = "deepseek"
    ) -> Dict[str, float]:
        """
        Calculate cost breakdown for a call.
        
        Args:
            duration_seconds: Total call duration
            tts_characters: Total characters synthesized
            llm_input_tokens: Total LLM prompt tokens
            llm_output_tokens: Total LLM completion tokens
            model_name: 'deepseek' or 'gpt-4o-mini'
            
        Returns:
            Dictionary with cost breakdown and total
        """
        duration_minutes = duration_seconds / 60.0
        
        # 1. Voice & ASR (Time-based)
        # Twilio bills per minute (rounded up usually, but we'll estimate raw)
        twilio_cost = duration_minutes * cls.RATES["twilio_voice_min"]
        
        # Deepgram bills per minute
        deepgram_cost = duration_minutes * cls.RATES["deepgram_min"]
        
        # 2. TTS (Character-based)
        tts_cost = (tts_characters / 1000.0) * cls.RATES["google_tts_1k_chars"]
        
        # 3. Intelligence (Token-based)
        is_gpt = "gpt" in model_name.lower()
        if is_gpt:
            input_rate = cls.RATES["gpt4omini_input_1m"]
            output_rate = cls.RATES["gpt4omini_output_1m"]
        else:
            input_rate = cls.RATES["deepseek_input_1m"]
            output_rate = cls.RATES["deepseek_output_1m"]
            
        llm_input_cost = (llm_input_tokens / 1_000_000.0) * input_rate
        llm_output_cost = (llm_output_tokens / 1_000_000.0) * output_rate
        llm_total_cost = llm_input_cost + llm_output_cost
        
        total_cost = twilio_cost + deepgram_cost + tts_cost + llm_total_cost
        
        return {
            "total_cost": round(total_cost, 5),
            "breakdown": {
                "telephony": round(twilio_cost, 5),
                "asr": round(deepgram_cost, 5),
                "tts": round(tts_cost, 5),
                "llm": round(llm_total_cost, 5)
            },
            "usage": {
                "duration_min": round(duration_minutes, 2),
                "tts_chars": tts_characters,
                "input_tokens": llm_input_tokens,
                "output_tokens": llm_output_tokens
            }
        }
