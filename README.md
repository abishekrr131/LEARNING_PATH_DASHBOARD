# Personalized Learning Path Dashboard (RCT-GAT)

A journal-grade, full-stack adaptive learning platform and psychometric knowledge tracing dashboard combining **Randomized Controlled Trial Graph Attention Networks (RCT-GAT)** with a **Gemini AI Assistance Layer**.

---

## 🏛️ System Architecture

```
                                  ┌───────────────────────────────┐
                                  │      Learner Web Client       │
                                  │   React 18 + Vite + Tailwind  │
                                  │     (All 21 Spec Screens)     │
                                  └───────────────┬───────────────┘
                                                  │
                                                  ▼
                                  ┌───────────────────────────────┐
                                  │     FastAPI API Gateway       │
                                  │ (JWT Auth, Psychometrics F12) │
                                  └───────┬───────────────┬───────┘
                                          │               │
                  ┌───────────────────────┴──────┐        └───────────────────────┐
                  ▼                              ▼                                ▼
┌─────────────────────────────────┐ ┌───────────────────────────┐ ┌─────────────────────────────────┐
│       PostgreSQL 16 Engine      │ │      Redis & Celery       │ │    RCT-GAT Inference Service    │
│  - 28 Relational Tables         │ │  - Rate Limiting (Slowapi)│ │  - Prerequisite GAT Layer       │
│  - pgvector HNSW Index          │ │  - Spaced Review Cron     │ │  - Causal Sequence Transformer  │
│  - Prerequisite DAG Constraints │ │  - Ebbinghaus Decay F15   │ │  - Attention Entropy Head (F8)  │
└─────────────────────────────────┘ └───────────────────────────┘ └─────────────────────────────────┘
```

---

## 📐 Mathematical Formulations & Psychometric Rigor

1. **Root-Cause Normalized Attention Entropy (Formula 8)**:
   $$\bar{H} = \frac{-\sum_{j \in \text{Ancestors}(k)} \alpha_{kj} \ln \alpha_{kj}}{\ln |\text{Ancestors}(k)|}$$
   - **Honesty Guard**: If $\bar{H} > 0.70$, the UI surfaces two root-cause candidates rather than over-confidently naming one.

2. **Expected Response Time & Ratio (Formulas 10 & 11)**:
   $$\mu_{q} = \beta_0 + \beta_1 b_q + \beta_2 \text{len}(q), \quad \text{TimeRatio} = \frac{t_{\text{resp}}}{\mu_q}$$

3. **Learning Gap Score (Formula 12)**:
   $$\text{Gap}_c = w_1 (1 - \hat{m}_c) + w_2 \max(0, \text{TimeRatio} - 1) + w_3 \mathbb{I}(\text{skipped}) + w_4 \mathbb{I}(\text{timed\_out})$$

4. **Exam Urgency Priority (Formula 14)**:
   $$\text{Priority}_c = \text{Gap}_c \cdot w_{\text{skill}} \cdot \exp\left(-\frac{\Delta t_{\text{exam}}}{\tau_{\text{urgency}}}\right)$$

5. **Memory Decay (Formula 15)** & **Spaced Review Intervals (Formula 16)**:
   $$m(t) = m_0 \cdot \exp\left(-\frac{\Delta t}{\tau_{\text{decay}}}\right), \quad \Delta t_{\text{review}} = \Delta t_0 \cdot \exp(\gamma \cdot m_c)$$

6. **Curriculum Coverage Readiness Index (Formula 17)**:
   $$R = \sum_{s=1}^S w_s \cdot \bar{m}_s \quad \text{labeled strictly as \textbf{"estimate, not guarantee"}}$$

7. **Trial Effect Size (Formula 23)**:
   $$d = \frac{\bar{x}_1 - \bar{x}_2}{s_{\text{pooled}}} \quad \text{where} \quad s_{\text{pooled}} = \sqrt{\frac{(n_1 - 1)s_1^2 + (n_2 - 1)s_2^2}{n_1 + n_2 - 2}}$$

---

## 🛡️ Non-Negotiable System Invariants

1. **Authentication**: Strictly Google Sign-In only (`@react-oauth/google` $\rightarrow$ `POST /api/auth/google`). No password forms anywhere. `MOCK_GOOGLE_AUTH` is strictly refused when `ENV=production`.
2. **Scored Test Integrity**: The Gemini AI assistant is strictly disabled (`HTTP 403` / UI silenced) during all scored assessments (Initial Diagnostic, Special Test, Verification Probes, Follow-Up).
3. **Psychometric Capture Timing**: Response timers use `performance.now()` with paint synchronization via `requestAnimationFrame`. Timing pauses during tab blur (`visibilitychange`). Server assigns authoritative timestamps `answered_at`.
4. **Leakage Invariants**:
   - **I1**: Label at $t$ is strictly $y_{t+1}$. No feature incorporates future responses.
   - **I2**: Causal lower-triangular attention mask prevents future sequence attention.
   - **I3**: Sequence ordering is strictly sorted by server-assigned timestamp ascending. Zero learner-ID embedding is used to ensure demographic generalizability.
5. **Cold-Start Guard**: When $< 20$ user responses exist, a prominent Cold-Start Mode Banner is shown.
6. **Synthetic Data Policy**: Datasets labeled `pipeline-test-synthetic` are reserved exclusively for pipeline verification and rejected from evaluation reports.

---

## 🚀 Quickstart & Reproduction

### 1. Run with Docker Compose
```bash
docker compose up -d
```
All 6 services will initialize and expose:
- **Web App**: http://localhost:5173 (or http://localhost:8000 via SPA mount)
- **API Server**: http://localhost:8000
- **ML Inference**: http://localhost:8100

### 2. Local Host Run
#### Backend:
```bash
py -3.13 database/seed/seed_all.py --approve-all
py -3.13 -m uvicorn backend.app.main:app --port 8000
```
#### Frontend:
```bash
cd frontend
npm install
npm run dev
```

---

## 🧪 Automated Test Verification

Execute all test suites across the entire monorepo:

```bash
# 1. Backend API & Psychometric Unit Tests (37 tests)
py -3.13 -m pytest tests/backend -v

# 2. Deep ML Architecture, GAT Layers & Invariant Tests (15 tests)
py -3.12 -m pytest tests/ml -v

# 3. Frontend Precision Timers & Psychometric Runner Tests (5 tests)
cd frontend
npm test
```
**Total: 57 / 57 Automated Tests Passing (100% Green)**.
