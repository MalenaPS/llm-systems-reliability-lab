# Reproducibility

Each run generates a manifest describing the execution context.

Example:

run_manifest.json
{
"model": "...",
"backend": "...",
"config_hash": "...",
"prompt_hash": "...",
"retrieval_docs": [...],
"metrics": {...}
}


This allows:

• experiment tracking  
• reproducible evaluation  
• debugging historical runs