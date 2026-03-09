```mermaid
graph TD
A[Case] --> B[Evaluation Runner]
B --> C[Pipeline]
C --> D[Retrieval]
C --> E[Tools]
C --> F[LLM]
F --> G[Validator]
G --> H[Artifacts]