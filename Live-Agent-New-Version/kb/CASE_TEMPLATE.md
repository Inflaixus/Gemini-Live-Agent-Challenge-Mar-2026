# Case Template Guide

When creating a new case, create a folder: `kb/cases/CASE_ID/`

## Required Files

### 1. opening.yaml
```yaml
chunk_id: CASE_ID_OPENING
case_id: CASE_ID
topic: presenting_issue
visibility_rule: volunteer_opening_only
content: |
  "Patient's opening statement here."
```

### 2. emotional_profile.yaml
```yaml
chunk_id: CASE_ID_EMOTIONAL_PROFILE
case_id: CASE_ID
scenario_type: case_specific
topic: emotional_profile
audience: patient_agent
visibility_rule: always_available
content: |
  Emotional tone and personality:
  - Describe patient's demeanor
  - Communication style
  - Concerns and anxieties
  - Response patterns
  - Keep responses short (1–3 sentences)
  - Use natural patient language
```

### 3. symptoms.yaml
```yaml
chunk_id: CASE_ID_SYMPTOMS
case_id: CASE_ID
scenario_type: case_specific
topic: symptoms_and_expectations
audience: patient_agent
visibility_rule: answer_only_if_asked
ask_patterns:
  - "pain"
  - "hurt"
  - "symptoms"
  - "bothers you"
content: |
  If asked about symptoms:
  - List symptoms here
```

### 4. medhx_condition.yaml
```yaml
chunk_id: CASE_ID_MEDHX_CONDITION
case_id: CASE_ID
topic: medical_history_condition
visibility_rule: answer_only_if_asked
ask_patterns:
  - "medical condition"
  - "any conditions"
  - "health problems"
  - "medical history"
content: |
  If asked about medical conditions: "Answer here"
```

### 5. identity_job.yaml
```yaml
chunk_id: CASE_ID_IDENTITY_JOB
case_id: CASE_ID
scenario_type: case_specific
topic: social_history_job
audience: patient_agent
visibility_rule: only_if_asked
ask_patterns:
  - "name"
  - "age"
  - "what do you do"
  - "occupation"
  - "job"
content: |
  If asked about name/age:
  - "Name and age"
  
  If asked what you do:
  - "Occupation"
```

### 6. nudges.yaml
```yaml
chunk_id: CASE_ID_NUDGES
case_id: CASE_ID
scenario_type: case_specific
topic: nudges
audience: controller_only
content:
  - id: NUDGE_ID_1
    trigger:
      phase: planning  # or discussion, discussion_or_planning
      missing: medical_history_checked  # or options_presented, risks_discussed
    patient_prompt: "Nudge question here"
    fire_once: true
```

## Optional Files

- dental_history.yaml
- allergies.yaml
- hidden_constraints.yaml
- acceptance_plan.yaml
- medhx_control.yaml
- medhx_carries.yaml

## Best Practices

1. **Always include ask_patterns** - helps retrieval and topic tracking
2. **Keep content focused** - one topic per file
3. **Use visibility_rule correctly**:
   - `volunteer_opening_only` - only for opening statement
   - `answer_only_if_asked` - most content
   - `only_if_asked` - hidden constraints
   - `always_available` - emotional profile only
4. **Make ask_patterns comprehensive** - include variations, synonyms, common phrasings
5. **Keep patient responses natural** - avoid clinical jargon unless repeating doctor's words
