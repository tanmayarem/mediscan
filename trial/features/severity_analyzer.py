"""
Side Effect Severity Analyzer Module

This module categorizes side effects by severity (mild/moderate/severe)
using NLP classification.

How it works:
1. Takes a list of side effects
2. Uses keyword matching and NLP models to classify severity
3. Returns categorized side effects with color codes
"""

import re
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)
try:
    from .groq_client import groq_chat
except Exception:
    groq_chat = None

# Severity keywords database
SEVERITY_KEYWORDS = {
    "severe": [
        "anaphylaxis", "allergic reaction", "severe allergic", "shock", "coma",
        "severe bleeding", "hemorrhage", "organ failure", "liver failure",
        "kidney failure", "heart attack", "stroke", "seizure", "convulsion",
        "difficulty breathing", "wheezing", "chest pain", "irregular heartbeat",
        "severe rash", "blistering", "peeling skin", "death", "fatal",
        "suicidal", "severe depression", "psychosis", "hallucination"
    ],
    "moderate": [
        "moderate", "significant", "persistent", "ongoing", "prolonged",
        "nausea", "vomiting", "diarrhea", "constipation", "upset stomach",
        "dizziness", "headache", "fatigue", "weakness", "fever",
        "rash", "itching", "hives", "swelling", "redness",
        "insomnia", "anxiety", "nervousness", "irritability",
        "muscle pain", "joint pain", "back pain", "cramps",
        "increased heart rate", "palpitations", "high blood pressure",
        "dry mouth", "dry skin", "blurred vision", "ringing in ears"
    ],
    "mild": [
        "mild", "slight", "minor", "temporary", "transient",
        "mild headache", "mild nausea", "mild dizziness",
        "dry mouth", "thirst", "increased urination",
        "mild rash", "slight itching", "mild stomach upset",
        "sleepiness", "drowsiness", "feeling tired",
        "taste change", "loss of appetite", "mild anxiety"
    ]
}

# Common side effects and their typical severity
COMMON_EFFECTS_SEVERITY = {
    # Severe effects
    "anaphylaxis": "severe",
    "severe allergic reaction": "severe",
    "shock": "severe",
    "organ failure": "severe",
    "difficulty breathing": "severe",
    "chest pain": "severe",
    "irregular heartbeat": "severe",
    "seizure": "severe",
    
    # Moderate effects
    "nausea": "moderate",
    "vomiting": "moderate",
    "diarrhea": "moderate",
    "dizziness": "moderate",
    "headache": "moderate",
    "fatigue": "moderate",
    "rash": "moderate",
    "itching": "moderate",
    "hives": "moderate",
    "insomnia": "moderate",
    "anxiety": "moderate",
    "muscle pain": "moderate",
    "joint pain": "moderate",
    "palpitations": "moderate",
    "high blood pressure": "moderate",
    
    # Mild effects
    "dry mouth": "mild",
    "thirst": "mild",
    "taste change": "mild",
    "sleepiness": "mild",
    "drowsiness": "mild",
    "mild headache": "mild",
    "mild nausea": "mild",
    "mild dizziness": "mild"
}


class SideEffectSeverityAnalyzer:
    """
    Analyzes and categorizes side effects by severity level.
    """
    
    def __init__(self):
        self.keywords = SEVERITY_KEYWORDS
        self.common_effects = COMMON_EFFECTS_SEVERITY
    
    def analyze_side_effects(self, side_effects_text: str) -> Dict:
        """
        Analyze side effects and categorize by severity.
        
        Args:
            side_effects_text: String containing side effects (space or comma separated)
            
        Returns:
            Dictionary with categorized side effects:
            {
                "mild": [...],
                "moderate": [...],
                "severe": [...],
                "unknown": [...]
            }
        """
        if not side_effects_text or not side_effects_text.strip():
            return {
                "mild": [],
                "moderate": [],
                "severe": [],
                "unknown": [],
                "summary": {
                    "total": 0,
                    "mild_count": 0,
                    "moderate_count": 0,
                    "severe_count": 0
                }
            }
        
        # Parse side effects into individual items
        side_effects = self._parse_side_effects(side_effects_text)
        
        categorized = {
            "mild": [],
            "moderate": [],
            "severe": [],
            "unknown": []
        }
        
        # If Groq is available, try AI classification first (fallback to rules)
        ai_labels = {}
        if groq_chat and side_effects:
            try:
                joined = "\n".join([f"- {e}" for e in side_effects])
                messages = [
                    {"role": "system", "content": "Classify each side effect as mild, moderate, or severe. Return JSON with keys 'mild', 'moderate', 'severe' listing the effects. Be conservative and move serious symptoms (e.g., chest pain, difficulty breathing) to severe."},
                    {"role": "user", "content": f"Classify:\n{joined}"}
                ]
                import json as _json
                resp = groq_chat(messages, max_tokens=300)
                if resp:
                    # Try to extract JSON
                    start = resp.find('{')
                    end = resp.rfind('}')
                    if start != -1 and end != -1 and end > start:
                        parsed = _json.loads(resp[start:end+1])
                        for label in ("mild","moderate","severe"):
                            if isinstance(parsed.get(label), list):
                                for e in parsed[label]:
                                    ai_labels[e.strip().lower()] = label
            except Exception:
                ai_labels = {}

        for effect in side_effects:
            key = effect.strip().lower()
            severity = ai_labels.get(key) if ai_labels else None
            if not severity:
                severity = self._classify_severity(effect)
            categorized[severity].append({
                "effect": effect.strip(),
                "severity": severity,
                "color": self._get_severity_color(severity)
            })
        
        # Create summary
        categorized["summary"] = {
            "total": len(side_effects),
            "mild_count": len(categorized["mild"]),
            "moderate_count": len(categorized["moderate"]),
            "severe_count": len(categorized["severe"]),
            "unknown_count": len(categorized["unknown"])
        }
        
        return categorized
    
    def _parse_side_effects(self, text: str) -> List[str]:
        """
        Parse side effects text into individual items.
        Handles various formats: comma-separated, space-separated, etc.
        """
        # Replace common separators with newlines
        text = text.replace(",", "\n").replace(";", "\n").replace(". ", "\n")
        
        # Split by newlines
        effects = [line.strip() for line in text.split("\n") if line.strip()]
        
        # If we got only one item, try splitting by multiple spaces or capitalization
        if len(effects) == 1:
            # Try splitting by capital letters (e.g., "HeadacheNausea" -> ["Headache", "Nausea"])
            parts = re.split(r'(?=[A-Z][a-z])', effects[0])
            if len(parts) > 1:
                effects = [p.strip() for p in parts if p.strip()]
        
        return effects
    
    def _classify_severity(self, effect: str) -> str:
        """
        Classify a single side effect by severity.
        
        Returns: "mild", "moderate", "severe", or "unknown"
        """
        effect_lower = effect.lower()
        
        # Check against common effects database first
        for common_effect, severity in self.common_effects.items():
            if common_effect.lower() in effect_lower:
                return severity
        
        # Check against severity keywords
        for severity in ["severe", "moderate", "mild"]:
            for keyword in self.keywords[severity]:
                if keyword.lower() in effect_lower:
                    return severity
        
        # Default classification based on keywords in text
        if any(word in effect_lower for word in ["severe", "serious", "dangerous", "fatal", "life-threatening"]):
            return "severe"
        elif any(word in effect_lower for word in ["mild", "slight", "minor", "temporary"]):
            return "mild"
        elif any(word in effect_lower for word in ["moderate", "significant", "persistent"]):
            return "moderate"
        
        # Default to moderate if unsure (err on the side of caution)
        return "moderate"
    
    def _get_severity_color(self, severity: str) -> str:
        """
        Get color code for severity level.
        
        Returns: Color hex code or emoji representation
        """
        colors = {
            "mild": "#22c55e",  # Green
            "moderate": "#f59e0b",  # Orange
            "severe": "#ef4444",  # Red
            "unknown": "#94a3b8"  # Gray
        }
        return colors.get(severity, colors["unknown"])
    
    def get_severity_emoji(self, severity: str) -> str:
        """Get emoji representation for severity."""
        emojis = {
            "mild": "🟢",
            "moderate": "🟠",
            "severe": "🔴",
            "unknown": "⚪"
        }
        return emojis.get(severity, "⚪")


def analyze_side_effect_severity(side_effects_text: str) -> Dict:
    """
    Convenience function to analyze side effects.
    
    Usage:
        result = analyze_side_effect_severity("Nausea, Dizziness, Severe allergic reaction")
        print(f"Severe effects: {result['severe']}")
    """
    analyzer = SideEffectSeverityAnalyzer()
    return analyzer.analyze_side_effects(side_effects_text)

