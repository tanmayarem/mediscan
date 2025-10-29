"""
Medicine Interaction Checker Module

This module checks for dangerous drug interactions between multiple medicines.
Uses RxNav API (free, no API key required) to check drug interactions.

API Endpoint: https://rxnav.nlm.nih.gov/
"""

import requests
import json
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)
try:
    from .groq_client import groq_chat
except Exception:
    groq_chat = None

class MedicineInteractionChecker:
    """
    Checks for drug interactions using RxNav API.
    
    How it works:
    1. Takes list of medicine names
    2. Uses RxNav to find RxCUI (RxNorm Concept Unique Identifiers)
    3. Checks interactions between all pairs
    4. Returns warnings with severity levels
    """
    
    BASE_URL = "https://rxnav.nlm.nih.gov/REST"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "MedScan/1.0"
        })
    
    def find_rxcui(self, medicine_name: str) -> Optional[str]:
        """
        Find RxCUI (RxNorm Concept Unique Identifier) for a medicine name.
        
        Args:
            medicine_name: Name of the medicine
            
        Returns:
            RxCUI string or None if not found
        """
        try:
            # Clean the medicine name (remove common words like "tablet", "capsule", etc.)
            clean_name = self._clean_medicine_name(medicine_name)
            
            url = f"{self.BASE_URL}/rxcui"
            params = {"name": clean_name, "allsrc": 1}
            
            response = self.session.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            # Extract RxCUI from response
            if "idGroup" in data and "rxnormId" in data["idGroup"]:
                rxcuis = data["idGroup"]["rxnormId"]
                if rxcuis:
                    return rxcuis[0]  # Return first match
            
            return None
        except Exception as e:
            logger.error(f"Error finding RxCUI for {medicine_name}: {e}")
            return None
    
    def check_interactions(self, rxcui1: str, rxcui2: str) -> Optional[Dict]:
        """
        Check interaction between two drugs by RxCUI.
        
        Args:
            rxcui1: First drug's RxCUI
            rxcui2: Second drug's RxCUI
            
        Returns:
            Interaction details or None if no interaction found
        """
        try:
            url = f"{self.BASE_URL}/interaction"
            params = {"rxcui": f"{rxcui1} {rxcui2}"}
            
            response = self.session.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if "fullInteractionTypeGroup" in data:
                # Interaction found
                interactions = []
                for group in data["fullInteractionTypeGroup"]:
                    for interaction_type in group.get("fullInteractionType", []):
                        interaction = {
                            "severity": interaction_type.get("interactionPair", [{}])[0].get("severity", "Unknown"),
                            "description": interaction_type.get("interactionPair", [{}])[0].get("description", "No description"),
                            "drugs": [
                                drug.get("minConcept", {}).get("name", "Unknown")
                                for drug in interaction_type.get("interactionPair", [{}])[0].get("interactionConcept", [])
                            ]
                        }
                        interactions.append(interaction)
                
                if interactions:
                    return {
                        "has_interaction": True,
                        "interactions": interactions
                    }
            
            return {"has_interaction": False, "interactions": []}
        except Exception as e:
            logger.error(f"Error checking interaction between {rxcui1} and {rxcui2}: {e}")
            return None
    
    def check_multiple_medicines(self, medicine_names: List[str]) -> Dict:
        """
        Check interactions between multiple medicines.
        
        Args:
            medicine_names: List of medicine names to check
            
        Returns:
            Dictionary with interaction warnings and details
        """
        if len(medicine_names) < 2:
            return {
                "status": "success",
                "warnings": [],
                "message": "Need at least 2 medicines to check interactions"
            }
        
        # Find RxCUIs for all medicines
        medicine_rxcuis = {}
        for med_name in medicine_names:
            rxcui = self.find_rxcui(med_name)
            if rxcui:
                medicine_rxcuis[med_name] = rxcui
            else:
                logger.warning(f"Could not find RxCUI for: {med_name}")
        
        if len(medicine_rxcuis) < 2:
            return {
                "status": "partial",
                "warnings": [{
                    "type": "info",
                    "message": "Could not verify some medicines. Please check spelling or use generic names.",
                    "medicine": list(set(medicine_names) - set(medicine_rxcuis.keys()))
                }],
                "checked_medicines": list(medicine_rxcuis.keys())
            }
        
        # Check all pairs
        warnings = []
        checked_pairs = set()
        
        med_list = list(medicine_rxcuis.items())
        for i in range(len(med_list)):
            for j in range(i + 1, len(med_list)):
                med1_name, rxcui1 = med_list[i]
                med2_name, rxcui2 = med_list[j]
                
                pair_key = tuple(sorted([med1_name, med2_name]))
                if pair_key in checked_pairs:
                    continue
                checked_pairs.add(pair_key)
                
                interaction_result = self.check_interactions(rxcui1, rxcui2)
                
                if interaction_result and interaction_result.get("has_interaction"):
                    for interaction in interaction_result.get("interactions", []):
                        severity = interaction.get("severity", "Unknown").lower()
                        
                        warnings.append({
                            "type": "danger" if severity == "major" else "warning" if severity == "moderate" else "caution",
                            "severity": severity,
                            "medicine1": med1_name,
                            "medicine2": med2_name,
                            "description": interaction.get("description", "Interaction detected"),
                            "drugs": interaction.get("drugs", [])
                        })
        
        # Check for duplicate active ingredients (same medicine with different names)
        duplicate_warnings = self._check_duplicate_ingredients(medicine_names)
        warnings.extend(duplicate_warnings)
        
        result = {
            "status": "success",
            "warnings": warnings,
            "checked_medicines": list(medicine_rxcuis.keys()),
            "total_checked": len(checked_pairs)
        }

        # AI summary using Groq (optional)
        try:
            if groq_chat and warnings:
                bullets = "\n".join(
                    [f"- {w.get('medicine1')} + {w.get('medicine2')}: {w.get('severity','unknown').upper()} — {w.get('description','')}" for w in warnings]
                )
                messages = [
                    {"role": "system", "content": "You are a pharmacology expert. Summarize drug interaction warnings clearly and conservatively. Always advise consulting a doctor."},
                    {"role": "user", "content": f"Summarize these interaction warnings for a layperson, with a short actionable recommendation.\n\n{bullets}"}
                ]
                summary = groq_chat(messages, max_tokens=220) if groq_chat else None
                if summary:
                    result["ai_summary"] = summary
        except Exception:
            pass

        return result
    
    def _clean_medicine_name(self, name: str) -> str:
        """
        Clean medicine name by removing common suffixes.
        """
        # Remove common suffixes that might not be in RxNav
        suffixes = [
            " tablet", " tablets", " tab", " tabs",
            " capsule", " capsules", " cap", " caps",
            " injection", " injections", " inj",
            " syrup", " syrups",
            " mg", " gm", " g"
        ]
        cleaned = name.lower().strip()
        for suffix in suffixes:
            if cleaned.endswith(suffix):
                cleaned = cleaned[:-len(suffix)].strip()
        return cleaned
    
    def _check_duplicate_ingredients(self, medicine_names: List[str]) -> List[Dict]:
        """
        Check if medicines might have the same active ingredient.
        This is a simple heuristic - in production, you'd compare actual ingredients.
        """
        warnings = []
        # This is a placeholder - you'd need to compare actual composition data
        # For now, we'll check common cases like "Paracetamol" vs "Dolo 650"
        common_name_mappings = {
            "paracetamol": ["dolo", "calpol", "pcm", "acetaminophen"],
            "ibuprofen": ["brufen", "ibu", "advil"],
            "azithromycin": ["azithral", "azee", "azi"],
        }
        
        med_lower = [m.lower() for m in medicine_names]
        for generic, brand_names in common_name_mappings.items():
            matches = [m for m in med_lower if generic in m or any(bn in m for bn in brand_names)]
            if len(matches) > 1:
                warnings.append({
                    "type": "info",
                    "severity": "low",
                    "medicine1": matches[0],
                    "medicine2": matches[1],
                    "description": f"Both medicines may contain {generic.title()}. Avoid taking both to prevent overdose.",
                    "drugs": []
                })
        
        return warnings


def check_medicine_interactions(medicine_names: List[str]) -> Dict:
    """
    Convenience function to check interactions.
    
    Usage:
        result = check_medicine_interactions(["Ibuprofen", "Aspirin"])
        if result["warnings"]:
            print("Warning: These medicines may interact!")
    """
    checker = MedicineInteractionChecker()
    return checker.check_multiple_medicines(medicine_names)

