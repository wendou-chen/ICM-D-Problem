
---
description: Perform advanced text analysis on MCM paper drafts to check for academic tone, narrative structure, and clarity.
---

def text_analysis(text_content):
    """
    Analyzes the provided text for:
    1. Academic Tone: Flags colloquialisms, weak verbs, or overly subjective language.
    2. Narrative Structure: Checks for the "Conflict-Insight-Resolution" arc.
    3. Clarity: Identifies overly long sentences or ambiguous pronouns.

    Returns a structured report with specific improvement suggestions.
    """
    # This skill leverages Claude's inherent language capabilities.
    # The prompt below guides the analysis.

    analysis_prompt = f"""
    You are a strictly academic editor for SIAM Review. Analyze the following text segment:

    <text_to_analyze>
    {text_content}
    </text_to_analyze>

    Perform a forensic analysis focusing on:
    1. **Weak Language**: List any words like "maybe", "sort of", "huge", "very". Suggest stronger academic synonyms (e.g., "significant", "substantial", "negligible").
    2. **Passive Voice Abuse**: Identify where active voice would clarify agency without losing objectivity.
    3. **The "So What?" Test**: For every paragraph, does it end with a conclusion or just a description? Flag descriptive-only paragraphs.

    Output Format:
    - **Critique Summary**: 2-3 bullet points.
    - **Line-by-Line Refactoring**: Quote the weak sentence -> Propose the "O-Prize" version.
    """

    return analysis_prompt
