"""
NEXUS AI — Visual Imagination Engine
Mental imagery, spatial visualization, scene construction,
visual thinking, diagram generation descriptions.
"""

import threading
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import sys

from config import DATA_DIR
from utils.logger import get_logger

logger = get_logger("visual_imagination")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)

class VisualizationType(Enum):
    SCENE = "scene"
    DIAGRAM = "diagram"
    ABSTRACT = "abstract"
    SPATIAL = "spatial"
    TEMPORAL = "temporal"
    METAPHORICAL = "metaphorical"
    SCHEMATIC = "schematic"

@dataclass
class MentalImage:
    image_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    prompt: str = ""
    visualization: str = ""
    viz_type: VisualizationType = VisualizationType.SCENE
    elements: List[Dict[str, Any]] = field(default_factory=list)
    spatial_layout: str = ""
    color_palette: List[str] = field(default_factory=list)
    emotional_tone: str = ""
    vividness: float = 0.5
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "image_id": self.image_id, "prompt": self.prompt[:200],
            "visualization": self.visualization,
            "viz_type": self.viz_type.value,
            "elements": self.elements,
            "spatial_layout": self.spatial_layout,
            "color_palette": self.color_palette,
            "emotional_tone": self.emotional_tone,
            "vividness": self.vividness,
            "created_at": self.created_at
        }

class VisualImaginationEngine:
    """
    Mental imagery and visual thinking — construct scenes,
    visualize abstract concepts, spatial reasoning through imagery.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._images: List[MentalImage] = []
        self._running = False
        self._data_file = COGNITION_DIR / "visual_imagination.json"

        self._stats = {
            "total_visualizations": 0, "total_scenes": 0,
            "total_diagrams": 0, "total_concept_visuals": 0
        }

        self._load_data()
        logger.info("✅ Visual Imagination Engine initialized")

    def start(self):
        self._running = True
        logger.info("🎨 Visual Imagination started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🎨 Visual Imagination stopped")

    def visualize(self, concept: str) -> MentalImage:
        """Create a mental visualization of a concept."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Create a vivid mental image/visualization of:\n{concept}\n\n"
                f"Return JSON:\n"
                f'{{"visualization": "detailed visual description", '
                f'"viz_type": "scene|diagram|abstract|spatial|temporal|metaphorical|schematic", '
                f'"elements": [{{"name": "str", "position": "str", '
                f'"appearance": "str", "size": "str"}}], '
                f'"spatial_layout": "how elements are arranged", '
                f'"color_palette": ["dominant colors"], '
                f'"emotional_tone": "the feeling this image evokes", '
                f'"vividness": 0.0-1.0, '
                f'"movement": "any motion or animation in the scene"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.6)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            vt_map = {v.value: v for v in VisualizationType}

            image = MentalImage(
                prompt=concept,
                visualization=data.get("visualization", ""),
                viz_type=vt_map.get(data.get("viz_type", "scene"), VisualizationType.SCENE),
                elements=data.get("elements", []),
                spatial_layout=data.get("spatial_layout", ""),
                color_palette=data.get("color_palette", []),
                emotional_tone=data.get("emotional_tone", ""),
                vividness=data.get("vividness", 0.5)
            )

            self._images.append(image)
            self._stats["total_visualizations"] += 1
            self._save_data()
            return image

        except Exception as e:
            logger.debug(f"Visualization failed: {e}")
            return MentalImage(prompt=concept)

    def describe_diagram(self, concept: str) -> Dict[str, Any]:
        """Describe a diagram that would explain a concept."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Describe a clear diagram that explains:\n{concept}\n\n"
                f"Return JSON:\n"
                f'{{"diagram_type": "flowchart|mind_map|venn|tree|network|timeline|matrix", '
                f'"title": "str", '
                f'"nodes": [{{"label": "str", "description": "str", "level": 0}}], '
                f'"connections": [{{"from": "str", "to": "str", "label": "str"}}], '
                f'"layout": "left-to-right|top-to-bottom|radial|hierarchical", '
                f'"legend": "explanation of symbols/colors", '
                f'"key_insight": "what this diagram reveals"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            if not response.success or not response.text:
                return {"diagram_type": "", "nodes": []}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"diagram_type": "", "nodes": []}
            self._stats["total_diagrams"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Diagram description failed: {e}")
            return {"diagram_type": "", "nodes": []}

    def construct_scene(self, description: str) -> Dict[str, Any]:
        """Construct a detailed scene from a description."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Construct a vivid, detailed scene from:\n{description}\n\n"
                f"Return JSON:\n"
                f'{{"setting": "where this takes place", '
                f'"time_of_day": "str", '
                f'"lighting": "str", '
                f'"foreground": ["objects/people in front"], '
                f'"midground": ["objects/people in middle"], '
                f'"background": ["elements in the distance"], '
                f'"sounds": ["ambient sounds"], '
                f'"smells": ["scents in the air"], '
                f'"atmosphere": "overall mood/feeling", '
                f'"camera_angle": "if this were a movie, how would you frame it"}}'
            )
            response = llm.generate(prompt, max_tokens=400, temperature=0.6)
            if not response.success or not response.text:
                return {"setting": "", "atmosphere": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"setting": "", "atmosphere": ""}
            self._stats["total_scenes"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Scene construction failed: {e}")
            return {"setting": "", "atmosphere": ""}

    def visualize_concept(self, abstract_concept: str) -> Dict[str, Any]:
        """Turn an abstract concept into a visual metaphor."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Turn this abstract concept into a vivid visual metaphor:\n{abstract_concept}\n\n"
                f"Return JSON:\n"
                f'{{"visual_metaphor": "the image that represents this concept", '
                f'"why_it_works": "what makes this metaphor effective", '
                f'"color_symbolism": {{"color": "what it represents"}}, '
                f'"shape_meaning": "what shapes are used and why", '
                f'"alternative_visuals": ["other possible visual representations"], '
                f'"teaching_value": "how this visual aids understanding"}}'
            )
            response = llm.generate(prompt, max_tokens=400, temperature=0.6)
            if not response.success or not response.text:
                return {"visual_metaphor": "", "why_it_works": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"visual_metaphor": "", "why_it_works": ""}
            self._stats["total_concept_visuals"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Concept visualization failed: {e}")
            return {"visual_metaphor": "", "why_it_works": ""}

    def _save_data(self):
        try:
            data = {
                "images": [i.to_dict() for i in self._images[-200:]],
                "stats": self._stats
            }
            self._data_file.write_text(json.dumps(data, indent=2, default=str))
        except Exception as e:
            logger.warning(f"Save failed: {e}")

    def _load_data(self):
        try:
            if self._data_file.exists():
                data = json.loads(self._data_file.read_text())
                self._stats.update(data.get("stats", {}))
                logger.info("📂 Loaded visual imagination data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def scene_evolution(self, scene: str) -> Dict[str, Any]:
        """Evolve a visual scene through time, showing transformation."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Evolve this VISUAL SCENE through time:\n'
                f'"{scene}"\n\n'
                f"Describe the scene at four time points:\n"
                f"  1. PRESENT: Vivid description of how it looks now\n"
                f"  2. NEAR FUTURE: How it changes in hours/days\n"
                f"  3. FAR FUTURE: How it transforms over months/years\n"
                f"  4. DISTANT FUTURE: The ultimate state\n\n"
                f"For each, include colors, textures, light, atmosphere.\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"stages": [{{"time": "present", "description": "vivid visual description", '
                f'"dominant_colors": ["color1"], "mood": "atmospheric quality", '
                f'"key_change": "what is different from previous stage"}}], '
                f'"overall_theme": "what the evolution reveals", '
                f'"most_striking_moment": "the most visually impactful stage"}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a visual imagination engine with the eye of a filmmaker and the "
                    "descriptive power of a great novelist. You create vivid, cinematic visual "
                    "descriptions that evolve through time. Respond ONLY with valid JSON."
                ),
                temperature=0.7, max_tokens=900
            )
            if response.success:
                from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"error": "Evolution failed"}
            return data
        except Exception as e:
            logger.debug(f"Scene evolution failed: {e}")
        return {"error": "Evolution failed"}

    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}

visual_imagination = VisualImaginationEngine()
