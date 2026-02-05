
---
description: Verify the logical consistency between the paper text and the underlying engineering constants/results.
---

def logic_verifier(text_claim, reference_code_or_data):
    """
    Verifies if a textual claim in the paper matches the engineering reality (code constants or CSV results).

    Args:
        text_claim (str): The sentence or paragraph from the paper making a quantitative or logical claim.
        reference_code_or_data (str): The relevant python code snippets or CSV data to check against.

    Returns:
        VerificationResult: Pass/Fail with evidence.
    """

    verification_prompt = f"""
    You are a Forensic Logic Auditor. Your job is to catch "Hallucinations" in scientific writing.

    Claim under investigation:
    "{text_claim}"

    Evidence (Code/Data):
    {reference_code_or_data}

    Task:
    1. Extract numerical values or logical relationships from the Claim.
    2. Compare them strictly against the Evidence.
    3. **Verdict**:
       - [MATCH]: If they align within reasonable rounding errors.
       - [CONTRADICTION]: If they disagree (e.g., text says "linear", code says "exponential"; text says "20 years", data says "25 years").
       - [UNSUPPORTED]: If the claim has no basis in the provided evidence.

    If [CONTRADICTION], you must draft a correction note explaining *exactly* what the math says.
    """

    return verification_prompt
