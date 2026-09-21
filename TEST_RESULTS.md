# Test Results and Generated Assets

**Last updated**: September 21, 2026 (~12:48 IST)  
**Configuration**: Real API keys in `backend/.env`, `MOCK_MODE=0`  
**Raw logs**: [`pytest_output.txt`](pytest_output.txt), [`e2e_campaign_output.txt`](e2e_campaign_output.txt)

---

## Automated Test Results (pytest)

**Command**:

```bash
cd backend && source venv/bin/activate && pytest tests/ -v
```

| Test | Result |
|------|--------|
| `test_create_campaign` | PASSED |
| `test_list_campaigns` | PASSED |
| `test_get_campaign` | PASSED |
| `test_research_stage` | PASSED |
| `test_reuse_stage` | PASSED |
| `test_angle_selection` | PASSED |
| `test_retry_succeeded_stage` | PASSED |

**Summary**: **7 passed, 0 failed** (~5.7s)

### `test_create_campaign` fix (Sep 21)

The test previously hard-coded `assert data["is_mock"] is True`. It now asserts `data["is_mock"] is config.MOCK_MODE`, so it passes with both `MOCK_MODE=0` (real APIs) and `MOCK_MODE=1` (mock).

Full pytest output: [`pytest_output.txt`](pytest_output.txt).

---

## Manual API verification (backend running)

**Command** (with `uvicorn` on port 8000):

```bash
curl http://localhost:8000/health
# → {"status":"healthy","mock_mode":false}

curl -X POST http://localhost:8000/api/campaigns \
  -H 'Content-Type: application/json' \
  -d '{
    "product_name": "Beast Protein",
    "factual_product_description": "High quality whey protein for fitness enthusiasts.",
    "target_audience": "Gym-goers aged 25-40",
    "campaign_objective": "introduce",
    "tone": "practical_energetic",
    "call_to_action": "Try it today",
    "verified_claims": []
  }'
# → HTTP 200, campaign id 25 (Sep 21 session)
```

**Validation example (HTTP 422)** — fields too short:

```json
{
  "detail": [
    {"loc": ["body", "factual_product_description"], "msg": "String should have at least 10 characters"},
    {"loc": ["body", "target_audience"], "msg": "String should have at least 10 characters"}
  ]
}
```

---

## UI / “campaign not creating” troubleshooting

| Symptom | Cause | Fix |
|---------|--------|-----|
| Generic network error | Backend not running or wrong port | `cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000` |
| Form submits but nothing works | Old frontend ignored HTTP 422 | Updated `App.tsx`: shows validation errors; `minLength={10}` on description & audience |
| Empty objective/tone | Dropdown left on “Select…” | Choose **Campaign Objective** and **Tone** before submit |

**UI stack**:

```bash
# Terminal 1 — must run from backend/ (DB + assets paths)
cd backend && source venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2
cd frontend && npm run dev
```

Open http://localhost:5173 (Vite proxies `/api` → `localhost:8000`).

---

## End-to-end campaign run (real APIs)

**Script**: `backend/scripts/run_full_campaign.py`  
**Product**: Beast Protein  
**Campaign ID**: **24**  
**Overall status**: **Completed** (6/6 stages succeeded)  
**Duration**: ~91 seconds (research → video)

### Stage timeline

| Stage | Status | Duration (approx.) |
|-------|--------|-------------------|
| research | succeeded | ~3s |
| spec | succeeded | <1s |
| scene | succeeded | <1s |
| image_1x1 | succeeded | ~28s (Cloudflare AI) |
| image_9x16 | succeeded | ~35s (Cloudflare AI) |
| video | succeeded | ~4s (FFmpeg) |

### Generated assets (Campaign #24)

| Asset | Path | Dimensions | Source |
|-------|------|------------|--------|
| image_1x1 | `backend/data/campaigns/image_1x1_a33300d3-1ba6-4686-842b-6f51f5ecb5ff.png` | 1080×1080 | Cloudflare AI |
| image_9x16 | `backend/data/campaigns/image_9x16_a33300d3-1ba6-4686-842b-6f51f5ecb5ff.png` | 1080×1920 | Cloudflare AI |
| video | `backend/data/campaigns/video_a33300d3-1ba6-4686-842b-6f51f5ecb5ff.mp4` | 1080×1920, 8.0s | FFmpeg (H.264) |

**Verified**: ffprobe 1080×1920, 8.0s; PNG dimensions via `file`.

**Copies** (outside gitignored `data/`):

| Location | Contents |
|----------|----------|
| `generated_assets/campaign_24/` | 2 PNG + 1 MP4 from run #24 |
| `generated_assets/campaign_24_summary.json` | Stage runs + asset metadata |

### Provider usage (campaign #24)

- **Gemini** — research / LLM stages  
- **Tavily** — web search in research  
- **Cloudflare Workers AI** — both images (`scene_source: cloudflare`, no procedural fallback)  
- **FFmpeg** — vertical 8s MP4  

---

## Saved assets on disk

| Location | Count / notes |
|----------|----------------|
| `backend/data/campaigns/` | **12 PNG** files (+ matching MP4s from prior runs) |
| `generated_assets/campaign_24/` | Latest E2E run (2 images + 1 video) |
| `backend/data/campaigns.db` | SQLite history (campaigns including #24, #25, etc.) |

---

## Reproduce full test + E2E

```bash
cd backend
source venv/bin/activate
# .env: GEMINI_API_KEY, TAVILY_API_KEY, CLOUDFLARE_*, MOCK_MODE=0

pytest tests/ -v | tee ../pytest_output.txt
python scripts/run_full_campaign.py | tee ../e2e_campaign_output.txt
```

---

## Notes

- API keys live in `backend/.env` (gitignored). Never commit `.env`.
- Rotate keys if they were shared in chat or logs.
- Pytest suite expects **7/7** with the updated `test_create_campaign` assertion.
