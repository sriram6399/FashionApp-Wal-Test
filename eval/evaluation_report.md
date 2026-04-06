# Evaluation Report
Classifier: OpenRouter

## Per-Attribute Accuracy

- **city**: 4.0% (2/50)
- **continent**: 38.0% (19/50)
- **country**: 14.0% (7/50)
- **garment_type**: 86.0% (43/50)
- **material**: 64.0% (32/50)
- **occasion**: 48.0% (24/50)
- **style**: 66.0% (33/50)


## Analysis

_The bullets below are generated from the table above; add your own interpretation for reviewers._

**Relatively stronger on this run:** `garment_type` 86% (43/50); `style` 66% (33/50); `material` 64% (32/50).

**Weaker on this run:** `continent` 38% (19/50); `country` 14% (7/50); `city` 4% (2/50).

**Improvements with more time:** align **garment_type** labels with the prompt taxonomy (or add few-shot JSON examples); constrain or synonym-map subjective fields (**style**, **occasion**); add more non-null **material** labels to score coverage; standardize **location** strings (continent / country / city); consider a smaller specialized classifier for garment type if cost/latency allow.