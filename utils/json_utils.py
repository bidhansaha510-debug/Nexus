
import json
import re
from typing import Any, Dict, List, Union

def _clean_json_string(text: str) -> str:
    """Clean common LLM JSON mistakes before parsing."""
    # Strip BOM and control characters (except newlines/tabs)
    text = text.replace('\ufeff', '')
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    # Remove trailing commas before } or ]
    text = re.sub(r',\s*([}\]])', r'\1', text)
    # Replace single quotes with double quotes (only for simple cases)
    # Be careful not to break contractions like "don't"
    if "'" in text and '"' not in text:
        text = text.replace("'", '"')
    return text


def extract_json(text: str) -> Union[Dict, List, None]:
    """
    Extracts and parses JSON from a string that might contain other text.
    Handles markdown blocks, comments, trailing commas, and pre/post-amble.
    """
    if not text:
        return None

    # Strip leading/trailing whitespace
    text = text.strip()

    # 1. Try direct parsing
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 1b. Try after cleaning
    try:
        return json.loads(_clean_json_string(text))
    except json.JSONDecodeError:
        pass

    # 2. Extract from markdown blocks
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        block = match.group(1).strip()
        try:
            return json.loads(block)
        except json.JSONDecodeError:
            pass
        try:
            return json.loads(_clean_json_string(block))
        except json.JSONDecodeError:
            pass

    # 3. Find first { or [ and last } or ]
    try:
        # Find start
        start_brace = text.find('{')
        start_bracket = text.find('[')

        if start_brace == -1 and start_bracket == -1:
            return None

        start = 0
        if start_brace != -1 and (start_bracket == -1 or start_brace < start_bracket):
            start = start_brace
            end = text.rfind('}') + 1
        else:
            start = start_bracket
            end = text.rfind(']') + 1

        if end > start:
            json_str = text[start:end]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
            # Try cleaned version
            try:
                return json.loads(_clean_json_string(json_str))
            except json.JSONDecodeError:
                pass

    except json.JSONDecodeError:
        pass

    return None
