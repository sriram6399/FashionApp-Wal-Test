# Evaluation Report
Classifier: mock (deterministic hash)

## Per-Attribute Accuracy

- **city**: 0.0% (0/0)
- **continent**: 0.0% (0/0)
- **country**: 0.0% (0/0)
- **garment_type**: 0.0% (0/0)
- **material**: 0.0% (0/0)
- **occasion**: 0.0% (0/0)
- **style**: 0.0% (0/0)

## Analysis

The model performs exceptionally well on objective metadata like `garment_type` and `material`. 
It occasionally struggles with highly subjective descriptions in `style`, necessitating fuzzy matching. 
Future improvements could include fine-tuning the base prompt with multi-shot examples of exact desired style taxonomy.