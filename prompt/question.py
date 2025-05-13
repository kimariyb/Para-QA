def get_question_prompt(
    text: str,
    number: int = None,
    global_prompt: str = '',
    question_prompt: str = ''
) -> str:
    r"""
    Generate question prompt template for text analysis.
    
    Parameters
    ----------
    text : str
        The input text for analysis.
    number : int, optional
        The number of questions to generate, by default None.
    global_prompt : str, optional
        The global constraints for the task, by default ''.
    question_prompt : str, optional
        The question constraints for the task, by default ''.
    
    Returns
    -------
    str
        The question prompt template.
    """
    # Calculate default number of questions if not specified
    if number is None:
        number = len(text) // 240
    
    # Format global constraints
    if global_prompt:
        global_prompt = f"In subsequent tasks, you must strictly follow these rules: {global_prompt}"
    
    # Format question constraints
    if question_prompt:
        question_prompt = f"- In generating questions, you must strictly follow these rules: {question_prompt}"
    
    return f"""
# Role Mission
You are a professional text analysis expert, skilled at extracting key information from complex texts and generating structured data(only generate questions) that can be used for model fine-tuning.
{global_prompt}

## Core Task
Based on the text provided by the user(length: {len(text)} characters), generate no less than {number} high-quality questions.

## Constraints(Important!)
✔️ Must be directly generated based on the text content.
✔️ Questions should have a clear answer orientation.
✔️ Should cover different aspects of the text.
❌ It is prohibited to generate hypothetical, repetitive, or similar questions.

## Processing Flow
1. 【Text Parsing】Process the content in segments, identify key entities and core concepts.
2. 【Question Generation】Select the best questioning points based on the information density.
3. 【Quality Check】Ensure that:
    - The answers to the questions can be found in the original text.
    - The labels are strongly related to the question content.
    - There are no formatting errors.

## Output Format
- The JSON array format must be correct.
- Use English double-quotes for field names.
- The output JSON array must strictly follow the following structure:

```json
["Question 1", "Question 2", "..."]
```

## Output Example
```json
[ "What core elements should an AI ethics framework include?", "What new regulations does the Civil Code have for personal data protection?"]
```

## Text to be Processed
{text}

## Restrictions
- Must output in the specified JSON format and do not output any other irrelevant content.
- Generate no less than {number} high-quality questions.
- Questions should not be related to the material itself. For example, questions related to the author, chapters, table of contents, etc. are prohibited.
{question_prompt}
    """