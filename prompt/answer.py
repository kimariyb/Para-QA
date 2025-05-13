def get_answer_prompt(
    text: str,
    question: str,
    global_prompt: str = '',
    answer_prompt: str = ''
) -> str:
    r"""
    Generate answer generation prompt for fine-tuning datasets.
    
    Parameters
    ----------
    text: str
        Reference content text
    question: str
        Target question to answer
    global_prompt: str
        Global constraints prompt
    answer_prompt: str
        Answer-specific constraints prompt
    
    Returns
    -------
    str
        Answer generation prompt
    """
    # Format global constraints
    if global_prompt:
        global_prompt = f"In subsequent tasks, you must strictly follow these rules: {global_prompt}"
    
    # Format answer constraints
    if answer_prompt:
        answer_prompt = f"In generating answers, you must strictly follow these rules: {answer_prompt}"
    
    return f"""
# Role: Fine-tuning Dataset Generation Expert
## Profile:
- Description: You are an expert in generating fine-tuning datasets, skilled at generating accurate answers to questions from the given content, ensuring the accuracy and relevance of the answers.
{global_prompt}

## Skills:
1. The answer must be based on the given content.
2. The answer must be accurate and not fabricated.
3. The answer must be relevant to the question.
4. The answer must be logical.

## Workflow:
1. Take a deep breath and work on this problem step-by-step.
2. First, analyze the given file content.
3. Then, extract key information from the content.
4. Next, generate an accurate answer related to the question.
5. Finally, ensure the accuracy and relevance of the answer.

## Reference Content:
{text}

## Question
{question}

## Constrains:
1. The answer must be based on the given content.
2. The answer must be accurate and relevant to the question, and no fabricated information is allowed.
3. The answer must be comprehensive and detailed, containing all necessary information, and it is suitable for use in the training of fine-tuning large language models.
    {answer_prompt}
"""


def get_new_answer_prompt(question: str, answer: str, cot: str, advice: str) -> str:
    r"""Generate answer optimization prompt for fine-tuning datasets.
    
    parameters
    ----------
    question: str
        Target question to answer
    answer: str
        Original answer to be optimized
    cot: str
        Original thinking process (Chain of Thought, CoT) of the answer
    advice: str
        Optimization suggestions for the answer and the thinking process (CoT)
    
    Returns
    -------
    str
        Answer optimization prompt
    """
    return f"""
# Role: Fine-tuning Dataset Answer Optimization Expert
## Profile:
- Description: You are an expert in optimizing answers for fine-tuning datasets. You are good at optimizing the answer results and the thinking process (Chain of Thought, CoT) of questions based on users' improvement suggestions.

## Skills:
1. Optimize the input answer based on the given optimization suggestions and the question, and make appropriate enrichment and supplementation.
3. Optimize the thinking process (Chain of Thought, CoT) of the answer according to the optimization suggestions, removing descriptions related to reference materials in the thinking process (do not reflect the reference materials in the reasoning logic, and change it to a normal reasoning idea).

## Original Question
{question}

## Answer to be Optimized
{answer}

## Answer Optimization Suggestions
{advice}

## Thinking Process to be Optimized
{cot}, and at the same time, make appropriate enrichment and supplementation to the answer to ensure that the answer is accurate, comprehensive, and clear.

## Thinking Process Optimization Suggestions
- General optimization suggestions: {advice}
- Remove descriptions related to reference materials in the thinking process (e.g., "According to...", "Citing...", "Referring to...", etc.), and do not reflect the reference materials in the reasoning logic. Change it to a normal reasoning idea.

## Constraints:
1. The result must be output in JSON format:
```json
    {{
        "answer": "Optimized answer",
        "cot": "Optimized thinking process"
    }}
```
    """