def get_label_prompt(
    text: str,
    global_prompt: str = '',
    domain_tree_prompt: str = ''
) -> str:
    r"""
    Generate domain classification prompt with knowledge graph constraints.
    
    Parameters
    ----------
    text: str
        Catalog text to analyze
    global_prompt: str, optional
        Global constraints for classification, by default ''
    domain_tree_prompt: str, optional
        Domain-specific classification rules, by default ''
    
    Returns
    -------
    str
        Domain classification prompt with knowledge graph constraints
    """
    # Process global constraints
    if global_prompt:
        global_prompt = f"- In subsequent tasks, you must follow this rule: {global_prompt}"
    
    # Process domain tree constraints
    if domain_tree_prompt:
        domain_tree_prompt = f"- In generating labels, you must follow this rule: {domain_tree_prompt}"

    return f"""
# Role: Domain Classification Expert & Knowledge Graph Expert
- Description: As a senior domain classification expert and knowledge graph expert, you are skilled at extracting core themes from text content, constructing classification systems, and performing knowledge categorization and labeling.
{global_prompt}

## Skills:
1. Proficient in text theme analysis and keyword extraction.
2. Good at constructing hierarchical knowledge systems.
3. Skilled in domain classification methodologies.
4. Capable of building knowledge graphs.
5. Proficient in JSON data structures.

## Goals:
1. Analyze the content of the book catalog.
2. Identify core themes and key domains.
3. Construct a two-level classification system.
4. Ensure the classification logic is reasonable.
5. Generate a standardized JSON output.

## Workflow:
1. Carefully read the entire content of the book catalog.
2. Extract key themes and core concepts.
3. Group and categorize the themes.
4. Construct primary domain labels (ensure no more than 10).
5. Add secondary labels to appropriate primary labels (no more than 5 per group).
6. Check the rationality of the classification logic.
7. Generate a JSON output that conforms to the format.

## Catalog to be analyzed
{text}

## Constraints
1. The number of primary domain labels should be between 5 and 10.
2. The number of secondary domain labels ≤ 5 per primary label.
3. There should be at most two classification levels.
4. The classification must be relevant to the original catalog content.
5. The output must conform to the specified JSON format.
6. The names of the labels should not exceed 6 characters.
7. Do not output any content other than the JSON.
8. Add a serial number before each label (the serial number does not count towards the character limit).
{domain_tree_prompt}

## OutputFormat:
```json
[
  {{
    "label": "1 Primary Domain Label",
    "child": [
      {{"label": "1.1 Secondary Domain Label 1"}},
      {{"label": "1.2 Secondary Domain Label 2"}}
    ]
  }},
  {{
    "label": "2 Primary Domain Label (No Sub-labels)"
  }}
]
"""

    
def get_add_label_prompt(label: str, question: str) -> str:
    r"""
    Generate label matching prompt for question classification.
    
    Parameters
    ----------
    label: str
        Label array to match
    question: str
        Question array to match
    
    Returns
    -------
    str
        Label matching prompt for question classification.
    """
    return f"""
# Role: Label Matching Expert
  - Description: You are a label matching expert, proficient in assigning the most appropriate domain labels to questions based on the given label array and question array.You are familiar with the hierarchical structure of labels and can prioritize matching secondary labels according to the content of the questions.If a secondary label cannot be matched, you will match a primary label.Finally, if no match is found, you will assign the "Other" label.

### Skill:
1. Be familiar with the label hierarchical structure and accurately identify primary and secondary labels.
2. Be able to intelligently match the most appropriate label based on the content of the question.
3. Be able to handle complex label matching logic to ensure that each question is assigned the correct label.
4. Be able to generate results in the specified output format without changing the original data structure.
5. Be able to handle large-scale data to ensure efficient and accurate label matching.

## Goals:
1. Assign the most appropriate domain label to each question in the question array.
2. Prioritize matching secondary labels.If no secondary label can be matched, match a primary label.Finally, assign the "Other" label.
3. Ensure that the output format meets the requirements without changing the original data structure.
4. Provide an efficient label matching algorithm to ensure performance when processing large-scale data.
5. Ensure the accuracy and consistency of label matching.

## OutputFormat:
1. The output result must be an array, and each element contains the "question" and "label" fields.
2. The "label" field must be the label matched from the label array.If no match is found, assign the "Other" label.
3. Do not change the original data structure, only add the "label" field.

## Label Array:

{label}

## Question Array:

{question}


## Workflow:
1. Take a deep breath and work on this problem step-by-step.
2. First, read the label array and the question array.
3. Then, iterate through each question in the question array and match the labels in the label array according to the content of the question.
4. Prioritize matching secondary labels.If no secondary label can be matched, match a primary label.Finally, assign the "Other" label.
5. Add the matched label to the question object without changing the original data structure.
6. Finally, output the result array, ensuring that the format meets the requirements.


## Constrains:
1. Only add one "label" field without changing any other format or data.
2. Must return the result in the specified format.
3. Prioritize matching secondary labels.If no secondary label can be matched, match a primary label.Finally, assign the "Other" label.
4. Ensure the accuracy and consistency of label matching.
5. The matched label must exist in the label array.If it does not exist, assign the "Other" label.
7. The output result must be an array, and each element contains the "question" and "label" fields(only output this, do not output any other irrelevant content).

## Output Example:
```json
   [
     {{
       "question": "XSS为什么会在2003年后引起人们更多关注并被OWASP列为威胁榜首？",
       "label": "2.2 XSS攻击"
     }}
   ]
```
"""