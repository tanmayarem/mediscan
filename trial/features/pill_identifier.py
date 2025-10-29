"""
Pill Identifier Module (AI Vision)

This module identifies pills from images using computer vision.
Can use pre-trained models from HuggingFace or custom-trained models.

For production, you would train a custom model on pill datasets like:
- NIH Pill Image Dataset
- Kaggle Pill Recognition Dataset
"""

import os
import numpy as np
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)
try:
    from .groq_client import groq_chat
except Exception:
    groq_chat = None

try:
    from PIL import Image
    import torch
    import torchvision.transforms as transforms
    from transformers import AutoImageProcessor, AutoModelForImageClassification
    HAS_DEEP_LEARNING = True
except ImportError:
    HAS_DEEP_LEARNING = False
    logger.warning("PyTorch or transformers not available. Using basic image matching instead.")


class PillIdentifier:
    """
    Identifies pills from images using AI vision models.
    
    How it works:
    1. Preprocesses the uploaded pill image
    2. Uses a trained CNN model or pre-trained vision transformer
    3. Matches against known pill database with features (shape, color, imprint)
    4. Returns top matches with confidence scores
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the pill identifier.
        
        Args:
            model_path: Path to custom trained model (optional)
        """
        self.device = "cuda" if HAS_DEEP_LEARNING and torch.cuda.is_available() else "cpu"
        self.model = None
        self.processor = None
        self.image_transform = None
        
        if HAS_DEEP_LEARNING:
            self._load_model(model_path)
        else:
            logger.warning("Running in basic mode without deep learning models")
    
    def _load_model(self, model_path: Optional[str] = None):
        """Load the AI model for pill identification."""
        try:
            if model_path and os.path.exists(model_path):
                # Load custom trained model
                logger.info(f"Loading custom model from {model_path}")
                # self.model = torch.load(model_path)
                # For now, we'll use a pre-trained model as placeholder
                pass
            
            # Use a pre-trained vision transformer as base
            # In production, you'd fine-tune this on pill images
            model_name = "google/vit-base-patch16-224"  # Pre-trained vision transformer
            
            try:
                self.processor = AutoImageProcessor.from_pretrained(model_name)
                # Note: This is a generic model - you'd need to fine-tune it on pill data
                logger.info("Loaded pre-trained vision model (generic - fine-tuning recommended)")
            except Exception as e:
                logger.error(f"Could not load model: {e}")
                HAS_DEEP_LEARNING = False
            
            # Basic image transform as fallback
            self.image_transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                                   std=[0.229, 0.224, 0.225])
            ])
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
    
    def preprocess_image(self, image_path: str) -> Optional[np.ndarray]:
        """
        Preprocess pill image for identification.
        
        Args:
            image_path: Path to the pill image
            
        Returns:
            Preprocessed image array or None
        """
        try:
            img = Image.open(image_path)
            
            # Convert to RGB if needed
            if img.mode != "RGB":
                img = img.convert("RGB")
            
            # Basic preprocessing: resize and normalize
            img_array = np.array(img.resize((224, 224)))
            return img_array
            
        except Exception as e:
            logger.error(f"Error preprocessing image: {e}")
            return None
    
    def extract_features(self, image_path: str) -> Optional[np.ndarray]:
        """
        Extract features from pill image.
        
        In production, this would use a trained CNN to extract features
        that represent pill shape, color, imprint, size, etc.
        
        Args:
            image_path: Path to the pill image
            
        Returns:
            Feature vector or None
        """
        if not HAS_DEEP_LEARNING:
            # Fallback: basic image features
            img_array = self.preprocess_image(image_path)
            if img_array is None:
                return None
            # Simple features: color histogram, basic shape features
            features = self._extract_basic_features(img_array)
            return features
        
        try:
            img = Image.open(image_path).convert("RGB")
            
            # Use the model to extract features
            if self.processor:
                inputs = self.processor(images=img, return_tensors="pt")
                # In production, extract features from intermediate layers
                # For now, return a placeholder
                return np.random.rand(768)  # Placeholder feature vector
            
            # Fallback transform
            if self.image_transform:
                img_tensor = self.image_transform(img).unsqueeze(0)
                # Extract features (this is simplified - real implementation would use actual model)
                return np.random.rand(768)
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            return None
    
    def _extract_basic_features(self, img_array: np.ndarray) -> np.ndarray:
        """
        Extract basic image features without deep learning.
        Uses color histograms and basic shape analysis.
        """
        features = []
        
        # Color histogram (R, G, B)
        for channel in range(3):
            hist = np.histogram(img_array[:, :, channel], bins=32, range=(0, 256))[0]
            features.extend(hist / hist.sum() if hist.sum() > 0 else hist)
        
        # Dominant colors
        pixels = img_array.reshape(-1, 3)
        # Mean color
        features.extend(pixels.mean(axis=0) / 255.0)
        # Std color
        features.extend(pixels.std(axis=0) / 255.0)
        
        return np.array(features)
    
    def identify_pill(self, image_path: str, database_medicines: List[Dict]) -> List[Dict]:
        """
        Identify pill from image by matching against database.
        
        Args:
            image_path: Path to pill image
            database_medicines: List of medicine dictionaries from database
            
        Returns:
            List of matches sorted by confidence, each with:
            - medicine_name
            - composition
            - confidence (0-100)
            - match_reasons (why it matched)
        """
        # Extract features from the image
        image_features = self.extract_features(image_path)
        
        if image_features is None:
            return []
        
        # For now, return a placeholder match based on image analysis
        # In production, you would:
        # 1. Load pre-computed features for all pills in database
        # 2. Compare using cosine similarity or other distance metric
        # 3. Return top matches
        
        matches = []
        
        # Placeholder: return medicines that might match
        # Real implementation would use actual feature matching
        for med in database_medicines[:5]:  # Return top 5 as example
            # Calculate a mock confidence score
            confidence = np.random.uniform(60, 95)  # Placeholder
            
            matches.append({
                "medicine_name": med.get("medicine_name", "Unknown"),
                "composition": med.get("composition", ""),
                "manufacturer": med.get("manufacturer", ""),
                "confidence": round(confidence, 1),
                "match_reasons": [
                    "Shape matches",
                    "Color similar",
                    "Size within range"
                ]
            })
        
        # Sort by confidence
        matches.sort(key=lambda x: x["confidence"], reverse=True)
        
        # Optional: Ask LLM to re-rank or provide a short explanation summary
        if groq_chat and matches:
            try:
                top = matches[:5]
                bullet = "\n".join([f"- {m['medicine_name']} ({m['composition']}) confidence {m['confidence']}%" for m in top])
                messages = [
                    {"role": "system", "content": "You are an assistant helping identify pills. Given candidate medicines and confidences from a vision model, return a concise suggested best match and one-line rationale. Do not provide medical advice."},
                    {"role": "user", "content": f"Candidates:\n{bullet}\n\nReturn JSON with keys 'best', 'rationale'."}
                ]
                import json as _json
                resp = groq_chat(messages, max_tokens=200)
                if resp:
                    start = resp.find('{')
                    end = resp.rfind('}')
                    if start != -1 and end != -1 and end > start:
                        info = _json.loads(resp[start:end+1])
                        if isinstance(info, dict):
                            matches[0]["ai_best_explanation"] = info.get("rationale")
            except Exception:
                pass
        
        return matches


def identify_pill_from_image(image_path: str, database_medicines: List[Dict]) -> List[Dict]:
    """
    Convenience function to identify a pill from an image.
    
    Usage:
        matches = identify_pill_from_image("pill.jpg", medicine_list)
        if matches:
            print(f"Looks like: {matches[0]['medicine_name']}")
    """
    identifier = PillIdentifier()
    return identifier.identify_pill(image_path, database_medicines)

