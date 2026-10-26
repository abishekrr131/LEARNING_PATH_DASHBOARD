"""Script to create a rich, comprehensive, multi-tiered prerequisite DAG for every career subject.

Connects concepts naturally into 1-hop and 2-hop prerequisite chains:
- Divisibility -> HCF/LCM -> Percentages -> Profit, Loss and Discount (Commercial Math)
- Series Completion -> Analogy and Classification -> Coding-Decoding & Direction Sense (Reasoning)
- Simplification -> Profit & Loss -> Table DI -> Pie Chart -> Line Graph -> Radar DI (Banking Quant)
- Linear Algebra (Vectors -> Matrices -> Inverses -> SVD/Eigen) -> ML (Regression -> Trees -> Neural Nets)
- Tokenization (BPE) -> Dense Embeddings -> Self-Attention -> Positional Encoding -> Transformers -> PEFT/LoRA -> Alignment
- OSI/TCP-IP -> Port Scanning/Firewalls -> Ciphers/Hashes -> PKI/TLS -> OWASP/Auth -> Forensics

Validates that the resulting graph is strictly a Directed Acyclic Graph (DAG) with 0 cycles.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.db.session import SessionLocal
from backend.app.models.core import CareerTarget, Concept, ConceptDependency, Skill, Topic
from ml.graph.dag_validator import SimpleDiGraph, is_directed_acyclic_graph, find_cycle


# Explicit, domain-accurate prerequisite edge definitions (Prerequisite -> Dependent)
# Format: (Target ID, "Prerequisite Concept Substring", "Dependent Concept Substring", weight)
PREREQUISITE_RULES = [
    # =========================================================================
    # TARGET 1: MACHINE LEARNING ENGINEERING (46 concepts)
    # =========================================================================
    # Linear Algebra
    (1, "Vectors and Matrices", "Matrix Multiplication", 1.0),
    (1, "Matrix Multiplication", "Matrix Inversion", 1.0),
    (1, "Matrix Multiplication", "Eigenvalues and Eigenvectors", 1.0),
    (1, "Eigenvalues and Eigenvectors", "Principal Component Analysis", 1.0),

    # Calculus & Optimization
    (1, "Derivatives and Gradients", "Convexity and Loss Surfaces", 1.0),
    (1, "Convexity and Loss Surfaces", "Gradient Descent", 1.0),
    (1, "Gradient Descent", "Stochastic Gradient Descent", 1.0),

    # Probability & Statistics
    (1, "Probability Distributions", "Conditional Probability", 1.0),
    (1, "Conditional Probability", "Maximum Likelihood Estimation", 1.0),
    (1, "Probability Distributions", "Hypothesis Testing", 1.0),

    # Supervised Learning
    (1, "Vectors and Matrices", "Linear Regression", 1.0),
    (1, "Derivatives and Gradients", "Linear Regression", 0.9),
    (1, "Linear Regression", "L1 and L2 Regularization", 1.0),
    (1, "Linear Regression", "Logistic Regression", 1.0),
    (1, "Maximum Likelihood Estimation", "Logistic Regression", 1.0),
    (1, "Decision Trees", "Random Forests", 1.0),
    (1, "Random Forests", "Gradient Boosted Trees", 1.0),
    (1, "Convexity and Loss Surfaces", "Support Vector Machines", 1.0),

    # Unsupervised Learning
    (1, "Vectors and Matrices", "K-Means Clustering", 1.0),
    (1, "K-Means Clustering", "Hierarchical Clustering", 1.0),
    (1, "Principal Component Analysis", "t-SNE and UMAP", 1.0),

    # Evaluation & Validation
    (1, "Linear Regression", "Bias-Variance Tradeoff", 1.0),
    (1, "Bias-Variance Tradeoff", "Cross-Validation", 1.0),
    (1, "Logistic Regression", "Confusion Matrix", 1.0),
    (1, "Confusion Matrix", "Precision and Recall", 1.0),
    (1, "Precision and Recall", "ROC and AUC", 1.0),

    # Neural Foundations
    (1, "Logistic Regression", "Perceptrons and Activations", 1.0),
    (1, "Perceptrons and Activations", "Multilayer Perceptrons", 1.0),
    (1, "Derivatives and Gradients", "Backpropagation", 1.0),
    (1, "Multilayer Perceptrons", "Backpropagation", 1.0),
    (1, "Backpropagation", "Vanishing and Exploding Gradients", 1.0),

    # Vision & Sequence
    (1, "Multilayer Perceptrons", "Convolutional Layers", 1.0),
    (1, "Convolutional Layers", "Pooling and Downsampling", 1.0),
    (1, "Multilayer Perceptrons", "Recurrent Neural Networks", 1.0),
    (1, "Recurrent Neural Networks", "LSTM and GRU", 1.0),

    # Transformers
    (1, "Vectors and Matrices", "Self-Attention Mechanism", 0.9),
    (1, "LSTM and GRU", "Self-Attention Mechanism", 0.9),
    (1, "Self-Attention Mechanism", "Multi-Head Attention", 1.0),
    (1, "Multi-Head Attention", "Positional Encoding", 1.0),
    (1, "Positional Encoding", "Transformer Encoder-Decoder", 1.0),

    # Deployment & Monitoring
    (1, "Linear Regression", "Model Serialization", 0.9),
    (1, "Model Serialization", "Inference Serving", 1.0),
    (1, "Inference Serving", "Docker for ML", 1.0),
    (1, "Inference Serving", "Feature Stores", 0.9),
    (1, "Inference Serving", "Data and Concept Drift", 1.0),
    (1, "Docker for ML", "CI/CD for ML", 1.0),
    (1, "Data and Concept Drift", "CI/CD for ML", 0.9),

    # =========================================================================
    # TARGET 2: FULL STACK DEVELOPMENT (39 concepts)
    # =========================================================================
    # Modern JavaScript & DOM
    (2, "ES6+ Syntax and Closures", "Asynchronous JS and Promises", 1.0),
    (2, "ES6+ Syntax and Closures", "DOM Manipulation & Events", 1.0),
    (2, "Asynchronous JS and Promises", "Web APIs and Fetch", 1.0),

    # React Fundamentals
    (2, "DOM Manipulation & Events", "JSX and Component Lifecycle", 1.0),
    (2, "JSX and Component Lifecycle", "React Hooks: useState and useEffect", 1.0),
    (2, "Props and Component Composition", "Custom Hooks", 1.0),
    (2, "React Hooks: useState and useEffect", "Custom Hooks", 1.0),

    # State Management & Routing
    (2, "React Hooks: useState and useEffect", "Context API & Prop Drilling", 1.0),
    (2, "Context API & Prop Drilling", "Global State Stores", 1.0),
    (2, "React Hooks: useState and useEffect", "Client-Side Routing", 1.0),
    (2, "Client-Side Routing", "Server-Side Rendering (SSR)", 1.0),

    # Node.js & Async Runtime
    (2, "Asynchronous JS and Promises", "Node Event Loop and Libuv", 1.0),
    (2, "Node Event Loop and Libuv", "Streams and Buffers", 1.0),
    (2, "Node Event Loop and Libuv", "Node Modules & Package Management", 0.9),

    # RESTful & GraphQL APIs
    (2, "Web APIs and Fetch", "HTTP Protocols & Status Codes", 1.0),
    (2, "HTTP Protocols & Status Codes", "RESTful Resource Design", 1.0),
    (2, "RESTful Resource Design", "API Validation & Middleware", 1.0),
    (2, "RESTful Resource Design", "GraphQL Schemas and Resolvers", 1.0),
    (2, "HTTP Protocols & Status Codes", "WebSockets and Real-time Communication", 1.0),

    # Authentication & Security
    (2, "API Validation & Middleware", "JWT and Session Management", 1.0),
    (2, "JWT and Session Management", "OAuth2 and OpenID Connect", 1.0),
    (2, "DOM Manipulation & Events", "Web Security: XSS and CSRF", 1.0),
    (2, "API Validation & Middleware", "SQL Injection & Input Sanitization", 1.0),
    (2, "API Validation & Middleware", "Rate Limiting and DDoS Mitigation", 1.0),

    # Relational Databases & SQL
    (2, "Relational Modeling & Normalization", "Complex SQL Queries & Joins", 1.0),
    (2, "Complex SQL Queries & Joins", "Database Indexing & B-Trees", 1.0),
    (2, "Complex SQL Queries & Joins", "ACID Properties & Transactions", 1.0),
    (2, "Complex SQL Queries & Joins", "ORMs and Query Optimization", 1.0),

    # NoSQL & Caching Systems
    (2, "Relational Modeling & Normalization", "Document Stores: MongoDB", 1.0),
    (2, "Complex SQL Queries & Joins", "Key-Value Stores: Redis", 1.0),
    (2, "Key-Value Stores: Redis", "Cache Invalidation Strategies", 1.0),

    # Containers & CI/CD
    (2, "Node Modules & Package Management", "Docker Containerization", 1.0),
    (2, "Docker Containerization", "Docker Compose", 1.0),
    (2, "Docker Compose", "CI/CD Automation Pipelines", 1.0),

    # Web Performance & Monitoring
    (2, "DOM Manipulation & Events", "Core Web Vitals", 1.0),
    (2, "HTTP Protocols & Status Codes", "CDN and Asset Optimization", 1.0),
    (2, "CI/CD Automation Pipelines", "Application Monitoring & Logging", 1.0),

    # =========================================================================
    # TARGET 3: CYBER SECURITY (38 concepts)
    # =========================================================================
    # Network Fundamentals & Firewalls
    (3, "OSI and TCP/IP Models", "TCP Handshake and Flags", 1.0),
    (3, "OSI and TCP/IP Models", "IP Addressing and Subnetting", 1.0),
    (3, "IP Addressing and Subnetting", "DNS Architecture and Security", 1.0),
    (3, "TCP Handshake and Flags", "Packet Filtering & Stateful Firewalls", 1.0),
    (3, "Packet Filtering & Stateful Firewalls", "Next-Gen Firewalls (NGFW)", 1.0),
    (3, "IP Addressing and Subnetting", "Virtual Private Networks (VPN)", 1.0),
    (3, "Packet Filtering & Stateful Firewalls", "Demilitarized Zones (DMZ)", 1.0),

    # Wireless & Endpoint
    (3, "OSI and TCP/IP Models", "Wireless Security (WPA2/WPA3)", 1.0),
    (3, "Demilitarized Zones (DMZ)", "Endpoint Detection and Response (EDR)", 1.0),
    (3, "Endpoint Detection and Response (EDR)", "Host Hardening & Patch Management", 1.0),

    # Symmetric & Asymmetric Encryption, Hashing, TLS
    (3, "Symmetric Ciphers: AES", "Stream Ciphers and ChaCha20", 1.0),
    (3, "Symmetric Ciphers: AES", "Asymmetric Cryptography: RSA", 1.0),
    (3, "Asymmetric Cryptography: RSA", "Elliptic Curve Cryptography (ECC)", 1.0),
    (3, "Symmetric Ciphers: AES", "Cryptographic Hash Functions", 1.0),
    (3, "Cryptographic Hash Functions", "HMAC & Message Integrity", 1.0),
    (3, "HMAC & Message Integrity", "Digital Signatures and Nonce", 1.0),
    (3, "Digital Signatures and Nonce", "Public Key Infrastructure (PKI)", 1.0),
    (3, "Public Key Infrastructure (PKI)", "X.509 Certificates and CSR", 1.0),
    (3, "X.509 Certificates and CSR", "TLS 1.3 Handshake", 1.0),

    # OWASP & Auth
    (3, "DNS Architecture and Security", "SQL Injection Mitigation", 0.9),
    (3, "DNS Architecture and Security", "Cross-Site Scripting (XSS)", 0.9),
    (3, "Cross-Site Scripting (XSS)", "Cross-Site Request Forgery (CSRF)", 1.0),
    (3, "Cross-Site Request Forgery (CSRF)", "Server-Side Request Forgery (SSRF)", 1.0),
    (3, "Server-Side Request Forgery (SSRF)", "Insecure Deserialization", 1.0),
    (3, "Cryptographic Hash Functions", "Password Hashing: bcrypt and Argon2", 1.0),
    (3, "Password Hashing: bcrypt and Argon2", "Multi-Factor Authentication (MFA)", 1.0),
    (3, "Multi-Factor Authentication (MFA)", "Session Hijacking & Fixation", 1.0),

    # OS Security, SIEM & Forensics
    (3, "Host Hardening & Patch Management", "Access Control: DAC and MAC", 1.0),
    (3, "Access Control: DAC and MAC", "Privilege Escalation Techniques", 1.0),
    (3, "Privilege Escalation Techniques", "Memory Corruption & Buffer Overflows", 1.0),
    (3, "Packet Filtering & Stateful Firewalls", "Intrusion Detection Systems (Snort/Suricata)", 1.0),
    (3, "Intrusion Detection Systems (Snort/Suricata)", "SIEM Log Aggregation", 1.0),
    (3, "SIEM Log Aggregation", "MITRE ATT&CK Framework", 1.0),
    (3, "MITRE ATT&CK Framework", "Incident Response Lifecycle (NIST)", 1.0),
    (3, "Incident Response Lifecycle (NIST)", "Memory and Disk Forensics", 1.0),
    (3, "Memory and Disk Forensics", "Malware Analysis Fundamentals", 1.0),

    # =========================================================================
    # TARGET 4: GENERATIVE AI (40 concepts)
    # =========================================================================
    # Tokenization & Attention
    (4, "Byte-Pair Encoding (BPE)", "WordPiece and Unigram Tokenization", 1.0),
    (4, "Byte-Pair Encoding (BPE)", "Dense Text Embeddings", 1.0),
    (4, "Dense Text Embeddings", "Embedding Dimensionality & Normalization", 1.0),
    (4, "Dense Text Embeddings", "Self-Attention Foundations", 1.0),
    (4, "Self-Attention Foundations", "Multi-Query and Grouped-Query Attention", 1.0),
    (4, "Multi-Query and Grouped-Query Attention", "FlashAttention & Memory Optimization", 1.0),
    (4, "Self-Attention Foundations", "Rotary Positional Embeddings (RoPE)", 1.0),

    # Autoregressive & Prompting
    (4, "Self-Attention Foundations", "Autoregressive Generation & Causal Masking", 1.0),
    (4, "Autoregressive Generation & Causal Masking", "Temperature and Top-P (Nucleus) Sampling", 1.0),
    (4, "Temperature and Top-P (Nucleus) Sampling", "Repetition Penalties & Frequency Penalties", 1.0),
    (4, "Autoregressive Generation & Causal Masking", "KV Caching in Inference", 1.0),
    (4, "Autoregressive Generation & Causal Masking", "Zero-Shot and Few-Shot Prompting", 1.0),
    (4, "Zero-Shot and Few-Shot Prompting", "System Instructions & Persona Framing", 1.0),
    (4, "System Instructions & Persona Framing", "Structured Output Generation", 1.0),
    (4, "Structured Output Generation", "Context Window Limits & Lost-in-the-Middle", 1.0),

    # Advanced Reasoning
    (4, "Zero-Shot and Few-Shot Prompting", "Chain-of-Thought (CoT) Prompting", 1.0),
    (4, "Chain-of-Thought (CoT) Prompting", "Self-Consistency Sampling", 1.0),
    (4, "Self-Consistency Sampling", "Tree of Thoughts (ToT) & Graph of Thoughts", 1.0),
    (4, "Tree of Thoughts (ToT) & Graph of Thoughts", "ReAct: Reasoning and Acting", 1.0),

    # Ingestion & RAG
    (4, "Dense Text Embeddings", "Text Splitting Strategies", 1.0),
    (4, "Text Splitting Strategies", "Chunk Overlap and Context Preservation", 1.0),
    (4, "Chunk Overlap and Context Preservation", "Document Metadata Enrichment", 1.0),
    (4, "Dense Text Embeddings", "Vector Indexing: HNSW and IVF", 1.0),
    (4, "Vector Indexing: HNSW and IVF", "Distance Metrics: Cosine vs Dot Product", 1.0),
    (4, "Distance Metrics: Cosine vs Dot Product", "Metadata Filtering & Hybrid Search", 1.0),
    (4, "Metadata Filtering & Hybrid Search", "Cross-Encoder Re-ranking", 1.0),
    (4, "Cross-Encoder Re-ranking", "Query Expansion & HyDE", 1.0),
    (4, "Query Expansion & HyDE", "Context Compression & Summarization", 1.0),
    (4, "Context Compression & Summarization", "RAG Evaluation: RAGAS Framework", 1.0),

    # PEFT & Alignment
    (4, "Autoregressive Generation & Causal Masking", "Supervised Fine-Tuning (SFT)", 1.0),
    (4, "Supervised Fine-Tuning (SFT)", "LoRA: Low-Rank Adaptation", 1.0),
    (4, "LoRA: Low-Rank Adaptation", "QLoRA & 4-bit NormalFloat Quantization", 1.0),
    (4, "LoRA: Low-Rank Adaptation", "Prefix Tuning and Prompt Tuning", 1.0),
    (4, "Supervised Fine-Tuning (SFT)", "Reward Modeling (RM)", 1.0),
    (4, "Reward Modeling (RM)", "PPO in RLHF", 1.0),
    (4, "PPO in RLHF", "Direct Preference Optimization (DPO)", 1.0),

    # Evaluation & Guardrails
    (4, "Direct Preference Optimization (DPO)", "LLM-as-a-Judge Evaluation", 1.0),
    (4, "Structured Output Generation", "Prompt Injection and Jailbreaking", 1.0),
    (4, "Prompt Injection and Jailbreaking", "Safety Guardrails & Content Moderation", 1.0),

    # =========================================================================
    # TARGET 5: UPSC CIVIL SERVICES (41 concepts)
    # =========================================================================
    # Polity & Governance
    (5, "Making of the Constitution & Constituent Assembly", "Preamble & Constitutional Features", 1.0),
    (5, "Preamble & Constitutional Features", "Union and Its Territory", 1.0),
    (5, "Union and Its Territory", "Citizenship Provisions", 1.0),
    (5, "Citizenship Provisions", "Fundamental Rights (Part III)", 1.0),
    (5, "Fundamental Rights (Part III)", "Writs & Constitutional Remedies (Article 32)", 1.0),
    (5, "Fundamental Rights (Part III)", "Directive Principles of State Policy (Part IV)", 1.0),
    (5, "Directive Principles of State Policy (Part IV)", "Fundamental Duties (Part IV-A)", 1.0),
    (5, "Fundamental Rights (Part III)", "President & Vice-President", 1.0),
    (5, "President & Vice-President", "Prime Minister & Council of Ministers", 1.0),
    (5, "Prime Minister & Council of Ministers", "Parliament: Rajya Sabha & Lok Sabha", 1.0),
    (5, "Parliament: Rajya Sabha & Lok Sabha", "Parliamentary Committees & Budgetary Process", 1.0),
    (5, "Writs & Constitutional Remedies (Article 32)", "Supreme Court of India", 1.0),
    (5, "Supreme Court of India", "High Courts & Subordinate Judiciary", 1.0),
    (5, "Parliament: Rajya Sabha & Lok Sabha", "Election Commission & Finance Commission", 1.0),
    (5, "Parliamentary Committees & Budgetary Process", "Comptroller & Auditor General (CAG)", 1.0),

    # History
    (5, "Indus Valley Civilization", "Vedic Period & Religious Movements", 1.0),
    (5, "Vedic Period & Religious Movements", "Mauryan & Gupta Empires", 1.0),
    (5, "Mauryan & Gupta Empires", "Delhi Sultanate & Mughal Administration", 1.0),
    (5, "Delhi Sultanate & Mughal Administration", "Colonial Expansion: Subsidiary Alliance & Doctrine of Lapse", 1.0),
    (5, "Colonial Expansion: Subsidiary Alliance & Doctrine of Lapse", "Colonial Land Revenue Settlements", 1.0),
    (5, "Colonial Land Revenue Settlements", "Drain of Wealth & Deindustrialization", 1.0),
    (5, "Drain of Wealth & Deindustrialization", "Revolt of 1857 & Aftermath", 1.0),
    (5, "Revolt of 1857 & Aftermath", "Moderate and Extremist Phases (1885-1915)", 1.0),
    (5, "Moderate and Extremist Phases (1885-1915)", "Gandhian Movements (1915-1942)", 1.0),
    (5, "Gandhian Movements (1915-1942)", "Constitutional Developments & Partition", 1.0),

    # Geography & Environment
    (5, "Geomorphology & Plate Tectonics", "Atmospheric Circulation & Monsoons", 1.0),
    (5, "Atmospheric Circulation & Monsoons", "Drainage Systems of India", 1.0),
    (5, "Ecosystem Ecology & Biomes", "Biodiversity Hotspots & Protected Areas", 1.0),
    (5, "Biodiversity Hotspots & Protected Areas", "Wildlife Protection Act 1972", 1.0),
    (5, "Ecosystem Ecology & Biomes", "UNFCCC, Kyoto Protocol & Paris Agreement", 1.0),
    (5, "UNFCCC, Kyoto Protocol & Paris Agreement", "Biodiversity Conventions (CBD, Ramsar, CMS)", 1.0),

    # Economy
    (5, "National Income Accounting", "Inflation Metrics & Indices", 1.0),
    (5, "Inflation Metrics & Indices", "Reserve Bank of India & Monetary Policy Framework", 1.0),
    (5, "Reserve Bank of India & Monetary Policy Framework", "Commercial Banking, NPAs & Insolvency (IBC)", 1.0),
    (5, "Inflation Metrics & Indices", "Fiscal Deficit & FRBM Act", 1.0),
    (5, "Fiscal Deficit & FRBM Act", "Taxation Structure & GST", 1.0),

    # =========================================================================
    # TARGET 6: SSC CGL (42 concepts)
    # =========================================================================
    # Quantitative Aptitude & Arithmetic
    (6, "Divisibility & Remainder Theorems", "HCF and LCM Applications", 1.0),
    (6, "HCF and LCM Applications", "Percentages and Successive Change", 1.0),
    (6, "Percentages and Successive Change", "Profit, Loss and Discount", 1.0),
    (6, "Percentages and Successive Change", "Simple & Compound Interest", 1.0),
    (6, "Percentages and Successive Change", "Ratio, Proportion & Partnerships", 1.0),
    (6, "Ratio, Proportion & Partnerships", "Averages and Mixtures (Alligation)", 1.0),
    (6, "Ratio, Proportion & Partnerships", "Time and Work Fundamentals", 1.0),
    (6, "Time and Work Fundamentals", "Time, Speed & Distance", 1.0),
    (6, "Divisibility & Remainder Theorems", "Algebraic Identities and Expansions", 1.0),
    (6, "Algebraic Identities and Expansions", "Quadratic Equations and Roots", 1.0),
    (6, "Algebraic Identities and Expansions", "Trigonometric Ratios and Identities", 1.0),
    (6, "Trigonometric Ratios and Identities", "Heights and Distances", 1.0),
    (6, "Algebraic Identities and Expansions", "Triangles: Similarity and Congruence", 1.0),
    (6, "Triangles: Similarity and Congruence", "Triangle Centers: Incenter & Circumcenter", 1.0),
    (6, "Triangles: Similarity and Congruence", "Circles, Chords and Tangents", 1.0),
    (6, "Circles, Chords and Tangents", "2D Mensuration & Plane Figures", 1.0),
    (6, "2D Mensuration & Plane Figures", "3D Solids: Cones, Cylinders & Spheres", 1.0),

    # Verbal & Non-Verbal Reasoning
    (6, "Series Completion: Numbers & Letters", "Analogy and Classification", 1.0),
    (6, "Analogy and Classification", "Coding-Decoding & Substitution", 1.0),
    (6, "Coding-Decoding & Substitution", "Direction Sense & Blood Relations", 1.0),
    (6, "Analogy and Classification", "Syllogisms and Venn Diagrams", 1.0),
    (6, "Mirror and Water Images", "Paper Folding and Cutting", 1.0),
    (6, "Paper Folding and Cutting", "Embedded Figures & Pattern Completion", 1.0),
    (6, "Embedded Figures & Pattern Completion", "Dice and Cube Rotations", 1.0),

    # English Comprehension
    (6, "Subject-Verb Agreement", "Tenses and Conditionals", 1.0),
    (6, "Tenses and Conditionals", "Prepositions and Phrasal Verbs", 1.0),
    (6, "Tenses and Conditionals", "Active and Passive Voice", 1.0),
    (6, "Active and Passive Voice", "Direct and Indirect Speech (Narration)", 1.0),
    (6, "Synonyms and Antonyms", "Idioms and Phrases", 1.0),
    (6, "Synonyms and Antonyms", "One Word Substitution", 1.0),
    (6, "One Word Substitution", "Reading Comprehension & Cloze Tests", 1.0),
    (6, "Prepositions and Phrasal Verbs", "Reading Comprehension & Cloze Tests", 0.9),

    # General Science & Static GK
    (6, "Physics: Mechanics & Optics", "Chemistry: Acids, Bases & Metals", 0.9),
    (6, "Chemistry: Acids, Bases & Metals", "Biology: Human Physiology & Diseases", 0.9),
    (6, "Constitutional Articles & Schedules", "Governor-Generals and Freedom Struggle", 0.9),
    (6, "Governor-Generals and Freedom Struggle", "Important Days, Honors & Classical Dances", 0.9),

    # =========================================================================
    # TARGET 7: BANKING (IBPS PO) (41 concepts)
    # =========================================================================
    # Speed Math, Arithmetic & DI
    (7, "Simplification & Approximation", "Ages & Partnership Calculations", 1.0),
    (7, "Simplification & Approximation", "Profit & Loss with Marked Price", 1.0),
    (7, "Profit & Loss with Marked Price", "Table & Bar Chart DI", 1.0),
    (7, "Ages & Partnership Calculations", "Table & Bar Chart DI", 0.9),
    (7, "Table & Bar Chart DI", "Pie Chart & Degree Conversion", 1.0),
    (7, "Pie Chart & Degree Conversion", "Line Graph & Caselet DI", 1.0),
    (7, "Line Graph & Caselet DI", "Radar & Missing Data DI", 1.0),
    (7, "Simplification & Approximation", "Missing & Wrong Number Series", 1.0),
    (7, "Missing & Wrong Number Series", "Quadratic Comparison (x vs y)", 1.0),
    (7, "Quadratic Comparison (x vs y)", "Data Sufficiency in Quant", 1.0),
    (7, "Profit & Loss with Marked Price", "Data Sufficiency in Quant", 0.9),
    (7, "Time, Speed, Distance & Boats", "Data Sufficiency in Quant", 0.9),
    (7, "Simplification & Approximation", "Time, Speed, Distance & Boats", 0.9),
    (7, "Permutations and Combinations", "Probability of Balls, Cards & Dice", 1.0),
    (7, "Permutations and Combinations", "2D and 3D Mensuration", 1.0),

    # Puzzles & Seating Arrangement
    (7, "Linear Seating Arrangement", "Circular & Square Seating", 1.0),
    (7, "Circular & Square Seating", "Floor & Flat Based Puzzles", 1.0),
    (7, "Floor & Flat Based Puzzles", "Box & Stack Puzzles", 1.0),
    (7, "Box & Stack Puzzles", "Month & Date Scheduling", 1.0),

    # Logical & Analytical Reasoning
    (7, "Inequalities (Coded & Direct)", "Syllogisms: Only a Few & Possibility", 1.0),
    (7, "Syllogisms: Only a Few & Possibility", "Input-Output Step Processing", 1.0),
    (7, "Input-Output Step Processing", "Cause and Effect / Statement Assumptions", 1.0),

    # Computer Architecture & Networking
    (7, "Computer Hardware & Memory Hierarchy", "Networking & OSI Protocol Basics", 1.0),
    (7, "Networking & OSI Protocol Basics", "Cyber Security & Virus Types", 1.0),

    # English Language
    (7, "Sentence Improvement & Fillers", "Error Spotting in Complex Sentences", 1.0),
    (7, "Error Spotting in Complex Sentences", "Para Jumbles & Sentence Rearrangement", 1.0),
    (7, "Para Jumbles & Sentence Rearrangement", "Cloze Test & Word Swap", 1.0),
    (7, "Contextual Vocabulary & Antonyms", "Banking Reading Comprehension", 1.0),
    (7, "Cloze Test & Word Swap", "Banking Reading Comprehension", 0.9),

    # Banking Awareness & Current Affairs
    (7, "RBI Structure & Preamble", "Monetary Policy Tools (LAF, MSF, SDF)", 1.0),
    (7, "Monetary Policy Tools (LAF, MSF, SDF)", "Currency Management & Digital Rupee (CBDC)", 1.0),
    (7, "Types of Bank Accounts & Negotiable Instruments", "NPA Classification & Resolution Framework", 1.0),
    (7, "NPA Classification & Resolution Framework", "Basel III Norms & Capital Adequacy (CRAR)", 1.0),
    (7, "Types of Bank Accounts & Negotiable Instruments", "Priority Sector Lending (PSL) Targets", 1.0),
    (7, "Types of Bank Accounts & Negotiable Instruments", "Payment Systems: UPI, NEFT, RTGS & IMPS", 1.0),
    (7, "Payment Systems: UPI, NEFT, RTGS & IMPS", "Financial Inclusion Schemes (PMJDY, PMSBY)", 1.0),
]


def main():
    print("=" * 80)
    print("Building Comprehensive Prerequisite DAG Across All 7 Career Tracks")
    print("=" * 80)

    db = SessionLocal()

    # Load all concepts mapped by target and clean concept name
    all_concepts = db.query(Concept).all()
    concept_lookup: dict[tuple[int, str], Concept] = {}

    for c in all_concepts:
        topic = db.get(Topic, c.topic_id)
        if topic:
            skill = db.get(Skill, topic.skill_id)
            if skill:
                target_id = skill.target_id
                concept_lookup[(target_id, c.name.lower().strip())] = c

    # Helper function to find concept matching substring
    def find_concept(target_id: int, name_substr: str) -> Concept | None:
        target_cands = [c for (tid, _), c in concept_lookup.items() if tid == target_id]
        name_sub_clean = name_substr.lower().strip()
        # Exact match first
        for c in target_cands:
            if c.name.lower().strip() == name_sub_clean:
                return c
        # Substring match
        for c in target_cands:
            if name_sub_clean in c.name.lower():
                return c
        return None

    # Track existing edges to avoid duplicates
    existing_edges = set()
    for dep in db.query(ConceptDependency).all():
        existing_edges.add((dep.prerequisite_concept_id, dep.dependent_concept_id))

    print(f"Initial concept dependency edges in DB: {len(existing_edges)}")

    added_count = 0
    skipped_count = 0
    warnings_count = 0
    candidate_edges = []

    for target_id, pre_substr, dep_substr, weight in PREREQUISITE_RULES:
        pre_concept = find_concept(target_id, pre_substr)
        dep_concept = find_concept(target_id, dep_substr)

        if not pre_concept:
            print(f"  [WARN] Prerequisite concept not found: '{pre_substr}' in Target {target_id}")
            warnings_count += 1
            continue
        if not dep_concept:
            print(f"  [WARN] Dependent concept not found: '{dep_substr}' in Target {target_id}")
            warnings_count += 1
            continue
        if pre_concept.id == dep_concept.id:
            continue

        edge_tuple = (pre_concept.id, dep_concept.id)
        if edge_tuple in existing_edges:
            skipped_count += 1
            continue

        candidate_edges.append((pre_concept, dep_concept, weight))

    print(f"Candidate edges to evaluate: {len(candidate_edges)} (Warnings: {warnings_count})")

    # Test for cycles and add edges incrementally
    all_graph_edges = list(existing_edges)
    verified_edges = []
    cycle_skipped = 0

    for pre_c, dep_c, weight in candidate_edges:
        test_graph = SimpleDiGraph(all_graph_edges + [(pre_c.id, dep_c.id)])
        if is_directed_acyclic_graph(test_graph):
            all_graph_edges.append((pre_c.id, dep_c.id))
            verified_edges.append((pre_c, dep_c, weight))
        else:
            cycle = find_cycle(test_graph)
            print(f"  [INFO] Skipping edge {pre_c.name} ({pre_c.id}) -> {dep_c.name} ({dep_c.id}) as it would form cycle: {cycle}")
            cycle_skipped += 1

    print(f"DAG validation passed: {len(verified_edges)} edges verified ({cycle_skipped} skipped for cycles).")

    # Insert verified edges
    new_dep_objects = []
    for pre_c, dep_c, weight in verified_edges:
        dep_obj = ConceptDependency(
            prerequisite_concept_id=pre_c.id,
            dependent_concept_id=dep_c.id,
            relation_weight=weight,
            source="expert",
        )
        new_dep_objects.append(dep_obj)
        existing_edges.add((pre_c.id, dep_c.id))
        added_count += 1

    if new_dep_objects:
        db.bulk_save_objects(new_dep_objects)
        db.commit()

    total_edges = db.query(ConceptDependency).count()
    print(f"\nSuccessfully added {added_count} new prerequisite edges! (Skipped {skipped_count} existing).")
    print(f"Total verified prerequisite edges in database: {total_edges}")

    # Check incoming prerequisite coverage per target
    print("\nUpdated Prerequisite Coverage per Target:")
    targets = db.query(CareerTarget).order_by(CareerTarget.id).all()
    for t in targets:
        concepts = (
            db.query(Concept)
            .join(Topic, Concept.topic_id == Topic.id)
            .join(Skill, Topic.skill_id == Skill.id)
            .filter(Skill.target_id == t.id)
            .all()
        )
        with_pre = 0
        without_pre = 0
        for c in concepts:
            incoming = db.query(ConceptDependency).filter(ConceptDependency.dependent_concept_id == c.id).count()
            if incoming > 0:
                with_pre += 1
            else:
                without_pre += 1
        print(f"  Target {t.id}: {t.name:<32} | Concepts with pre: {with_pre:<2}/{len(concepts)} | Root nodes: {without_pre}")

    db.close()
    print("=" * 80)


if __name__ == "__main__":
    main()
