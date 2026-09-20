# High-Level Design: AI Campaign Creative Studio

## 1. Purpose and Scope

### In Scope
- Product brief capture with validation
- Research agent with web search and page reading
- Creative angle generation (3 angles)
- User angle selection gate
- Creative specification generation
- Asset generation: 1080×1080 image, 1080×1920 image, 1080×1920 video (6-10s)
- Campaign history and retry mechanism
- Mock mode for testing

### Out of Scope
- Authentication, user accounts, multi-tenancy
- Publishing to ad platforms (Meta, Google, etc.)
- Billing, usage tracking, cost management
- Real-time collaboration
- Meta connection or ad account integration
- Model training or fine-tuning
- Analytics or performance tracking

## 2. Design Principles

- **Deterministic reuse**: Stages with identical input hash reuse previous successful outputs
- **Idempotency**: Same stage+input cannot run concurrently via idempotency_key
- **Graceful degradation**: AI generation falls back to procedural rendering
- **Bounded execution**: Research agent has hard limits on tool calls, time, and page size
- **Fail-fast validation**: Input validation at API boundary before expensive operations
- **Background processing**: Stages run asynchronously via polling worker
- **State persistence**: All state in database; no in-memory-only state

## 3. System Architecture

```
┌─────────────┐
│   Frontend  │ (React + Vite + TypeScript)
│  localhost:5173│
└──────┬──────┘
       │ HTTP API
       ▼
┌─────────────────────────────────────────────┐
│        FastAPI Backend (localhost:8000)     │
│  ┌───────────────────────────────────────┐  │
│  │  Campaign API (/api/campaigns)      │  │
│  │  - CRUD, stage orchestration, retry  │  │
│  └───────────┬───────────────────────────┘  │
│              │                               │
│  ┌───────────▼───────────────────────────┐  │
│  │  Workflow Runner (stage lifecycle)   │  │
│  │  - Input hash reuse                  │  │
│  │  - Idempotency enforcement          │  │
│  │  - Heartbeat monitoring             │  │
│  └───────────┬───────────────────────────┘  │
│              │                               │
│  ┌───────────▼───────────────────────────┐  │
│  │  Background Worker (polling)         │  │
│  │  - Executes pending stages           │  │
│  │  - Recovers stale stages             │  │
│  └───────────┬───────────────────────────┘  │
│              │                               │
│    ┌─────────┴─────────┬───────────────┐  │
│    ▼                   ▼               ▼  │
│ ┌────────┐    ┌────────────┐  ┌────────┐ │
│ │Research│    │  Creative   │  │Rendering│ │
│ │ Agent  │    │  Pipeline   │  │ Engine  │ │
│ └───┬────┘    └──────┬─────┘  └───┬────┘ │
│     │                │            │     │
│     ▼                ▼            ▼     │
│ ┌────────┐    ┌────────────┐  ┌────────┐ │
│ │LLM/    │    │    LLM     │  │Cloudflare│ │
│ │Search  │    │    Providers│  │  AI    │ │
│ │Page    │    │  (Spec/Scene)│  │  +     │ │
│ │Reader  │    │             │  │Procedural│ │
│ └────────┘    └────────────┘  └────────┘ │
└─────────────────────────────────────────────┘
       │                   │
       ▼                   ▼
┌─────────────┐    ┌─────────────┐
│ SQLite DB   │    │   Assets    │
│ (campaigns, │    │   (images/  │
│ stage_runs, │    │    videos)  │
│   assets)   │    │ ./data/     │
└─────────────┘    └─────────────┘
```

## 4. Component Table

| Component | Responsibility | Technology | File Path |
|-----------|---------------|------------|------------|
| Campaign API | CRUD, stage orchestration, retry, response building | FastAPI, SQLModel | `backend/app/api/campaigns.py` |
| Workflow Runner | Stage lifecycle, input hash reuse, idempotency, heartbeat | Python, SQLModel | `backend/app/workflow/runner.py` |
| Background Worker | Polls pending stages, executes handlers, recovers stale stages | Threading, SQLModel | `backend/app/workflow/worker.py` |
| Research Agent | Tool-calling LLM, bounded search/page reading, validation | Python, LLM API | `backend/app/agents/research/agent.py` |
| Spec Generator | LLM-based creative spec from selected angle | Python, LLM API | `backend/app/workflow/stages/spec.py` |
| Scene Generator | Scene configuration from spec | Python, LLM API | `backend/app/workflow/stages/scene.py` |
| Image Compositor | AI image generation (Cloudflare) + procedural fallback | Pillow, FFmpeg, requests | `backend/app/rendering/compositor.py` |
| Video Generator | FFmpeg video from AI image with zoom effect | FFmpeg subprocess | `backend/app/rendering/video.py` |
| LLM Provider | Generic LLM client (Gemini) | HTTP, API | `backend/app/providers/llm.py` |
| Search Provider | Web search (Tavily) | HTTP, API | `backend/app/providers/search.py` |
| Page Reader | Web page fetching and text extraction | HTTP, BeautifulSoup | `backend/app/providers/page_reader.py` |
| Image Generator | Cloudflare Workers AI (Stable Diffusion XL) | HTTP, API | `backend/app/providers/image_generator.py` |
| URL Guard | SSRF protection, URL validation | Python, ipaddress | `backend/app/security/url_guard.py` |
| Frontend | React SPA with screen-based navigation | React, Vite, TypeScript | `frontend/src/App.tsx` |

## 5. Workflow

### Stage List (In Order)
1. **research** - Research agent gathers sources and generates 3 angles
2. **spec** - Generate creative specification from selected angle
3. **scene** - Generate scene configuration from spec
4. **image_1x1** - Generate 1080×1080 square image
5. **image_9x16** - Generate 1080×1920 vertical image
6. **video** - Generate 1080×1920, 8s video with zoom effect

### Dependencies
- `spec` depends on: research completion + user angle selection
- `scene` depends on: spec completion
- `image_1x1` depends on: scene completion
- `image_9x16` depends on: scene completion
- `video` depends on: image_9x16 completion (uses as background)

### Concurrency
- Stages run sequentially (no parallel execution)
- Background worker polls every 2 seconds (`WORKER_POLL_INTERVAL`)
- Only one stage per campaign runs at a time

### User Gate
- **Angle selection**: User must select angle_id before `generate` can proceed
- Gate enforced in `POST /campaigns/{id}/generate` (returns 400 if no angle selected)

### Stage States
- `pending` - Created, awaiting worker pickup
- `running` - Worker executing (with heartbeat)
- `succeeded` - Completed successfully
- `failed` - Failed with error message
- `interrupted` - Stale heartbeat recovered

### Input Hash Reuse
- Computed via SHA256 of JSON-serialized input (sorted keys)
- Implementation: `compute_input_hash()` in `backend/app/workflow/runner.py`
- Lookup: StageRun with same campaign_id, stage, input_hash, status="succeeded"
- If found: returns existing run, skips execution
- If not found: creates new run

## 6. Data Model

### Tables (from `backend/app/models.py`)

**Campaign**
- `id` (PK, int)
- `product_name` (str)
- `factual_product_description` (str)
- `target_audience` (str)
- `campaign_objective` (str)
- `tone` (str)
- `call_to_action` (str)
- `verified_claims` (str, JSON)
- `reference_image_path` (str, nullable)
- `selected_angle_id` (int, nullable)
- `created_at` (datetime)
- `is_mock` (bool)

**StageRun**
- `id` (PK, int)
- `campaign_id` (FK, int)
- `stage` (str)
- `status` (str)
- `attempt` (int)
- `input_hash` (str)
- `output_json` (str, nullable, JSON)
- `output_ref` (str, nullable)
- `error` (str, nullable)
- `started_at` (datetime, nullable)
- `finished_at` (datetime, nullable)
- `heartbeat_at` (datetime, nullable)
- `provider_usage` (str, nullable, JSON)
- `idempotency_key` (str, nullable, indexed)

**Asset**
- `id` (PK, int)
- `campaign_id` (FK, int)
- `asset_id` (str, UUID)
- `asset_type` (str) - "image_1x1", "image_9x16", "video"
- `spec_id` (str, UUID)
- `file_path` (str)
- `width` (int)
- `height` (int)
- `duration_seconds` (float, nullable)
- `prompt_params` (str, nullable, JSON)
- `scene_source` (str, nullable) - "cloudflare", "procedural"
- `fallback_reason` (str, nullable)
- `created_at` (datetime)

### Binary File Storage
- Location: `./data/campaigns/` (configurable via `ASSET_DIR`)
- Naming: `image_1x1_{spec_id}.png`, `image_9x16_{spec_id}.png`, `video_{spec_id}.mp4`
- Served via FastAPI static files mount at `/data/`

## 7. Contracts

### BriefCreate (`backend/app/schemas.py`)
- `product_name`: str, 1-200 chars
- `factual_product_description`: str, 10-2000 chars
- `target_audience`: str, 10-500 chars
- `campaign_objective`: CampaignObjective enum
- `tone`: Tone enum
- `call_to_action`: str, 1-100 chars
- `verified_claims`: List[str], max 10 items, each ≤200 chars

### ResearchOutput
- `angles`: List[Angle], exactly 3 items
- `sources`: List[Source]
- `tool_calls`: List[dict]
- `source_gap`: Optional[str]

### Angle
- `audience_insight`: str
- `hook`: str
- `visual_direction`: str
- `rationale`: str
- `source_ids`: List[int]
- `statements`: List[AngleStatement]
  - `text`: str
  - `label`: str, pattern "^(sourced_observation|creative_interpretation)$"

### CreativeSpec
- `spec_id`: str (UUID)
- `version`: int
- `hook`: str
- `approved_headline`: str
- `approved_body_copy`: Optional[str]
- `call_to_action`: str
- `product_identity`: dict
- `scene_description`: str
- `palette`: List[str] (hex colors)
- `composition_1x1`: dict
- `composition_9x16`: dict
- `video_outline`: dict

### Asset
- `asset_id`: str
- `asset_type`: str
- `spec_id`: str
- `file_path`: str
- `width`: int
- `height`: int
- `duration_seconds`: Optional[float]
- `prompt_params`: Optional[dict]

## 8. Research Agent

### Tools
- **web_search**: Executes web search via Tavily API
- **read_page**: Fetches and extracts text from URL (with SSRF guard)
- **finish**: Ends research and returns results

### Loop
- Agent runs tool-calling loop until finish or limits hit
- LLM decides which tool to call based on research goal
- State tracking: tool_calls, sources, search_results_cache

### Configured Bounds (from `backend/app/config.py`)
- `MAX_TOOL_CALLS`: 8 (default)
- `MAX_FOLLOWUP_SEARCHES`: 2 (default)
- `PAGE_FETCH_TIMEOUT`: 10s (default)
- `RESEARCH_WALL_CLOCK`: 90s (default)
- `PAGE_TEXT_CAP`: 20000 chars (default)
- `LLM_RETRIES`: 1 (default)

### Trace Logging
- All tool calls logged with step number, args, result_summary, decision, latency_ms
- Research output includes complete tool_calls array for audit

### Post-Validation Checks
- Validates exactly 3 angles returned
- Validates each angle has required fields
- Validates source_ids reference actual sources
- Reports source_gap if fewer than 3 sources found

### Untrusted Content / Prompt Injection Defences
- **SSRF protection**: URL validation blocks private IPs, localhost, metadata services
- **Search validation**: Only fetch pages from search results (via `is_from_search_results()`)
- **Text capping**: PAGE_TEXT_CAP limits extracted text size
- **Time bounding**: RESEARCH_WALL_CLOCK prevents infinite loops
- **Tool limits**: MAX_TOOL_CALLS bounds iteration
- **URL sanitization**: Fragments removed, domains blocked

## 9. Creative Generation and Consistency Strategy

### Scene Generation
- Scene configuration generated by LLM from spec
- Includes palette, composition layouts, video outline
- Not directly used in image/video generation (passed for reference)

### Packshot Generation
- Procedural fallback generates product packshot with transparent background
- Rounded rectangle with product name centered
- Used in both 1x1 and 9x16 procedural images

### Text Overlays
- Headline drawn with shadow for contrast
- CTA drawn as filled rounded pill
- Text wrapping for long headlines
- Safe zones respected (250px for 9x16)

### Per-Format Layouts
- **1x1**: 50px margin, headline top center, CTA bottom center, product center
- **9x16**: 250px safe zones, headline below top safe zone, CTA above bottom safe zone, product center middle

### Scene Source and Fallback Logic
- **Primary**: Cloudflare AI image generation with product-specific prompts
- **Fallback**: Improved procedural generation with gradients, packshots, text overlays
- **Tracking**: `scene_source` field stores "cloudflare" or "procedural"
- **Fallback reason**: Stored in `fallback_reason` field when AI fails

### Asset Metadata Storage
- Each asset stores `prompt_params` as JSON including:
  - `spec_id`: Links asset to creative spec
  - `scene_source`: Cloudflare or procedural
  - `fallback_reason`: Why fallback was used (if applicable)
  - File path, dimensions, duration

## 10. Video Pipeline

### FFmpeg Approach
- **Primary**: Uses AI-generated 9x16 image as background with zoom effect
- **Fallback**: Simple image loop without zoom if zoom fails
- **Final fallback**: Solid color video if image unavailable

### Timings
- Duration: 8 seconds (configurable in video.py)
- FPS: 30
- Zoom effect: 10% zoom over 8 seconds (min(zoom+0.002,1.1))

### Codec Settings
- Codec: H.264 (libx264)
- Preset: fast
- CRF: 23
- Pixel format: yuv420p
- Movflags: +faststart (for streaming)
- Audio: None (silent video)

### Timeout
- Generation timeout: 30 seconds
- Verification timeout: 10 seconds

### FFprobe Verification
- Validates dimensions: 1080×1920
- Validates duration: 6-10 seconds
- Skipped if ffprobe not available

### Status Transitions
- `pending` → `running` → `succeeded` or `failed`
- Stale `running` → `interrupted` (via heartbeat recovery)

## 11. API Surface

### Endpoints

**POST /api/campaigns**
- Creates campaign from brief
- Validation: BriefCreate schema
- Response: CampaignResponse with brief, id, is_mock

**GET /api/campaigns**
- Lists all campaigns (history)
- Response: List[CampaignListResponse] (simplified: id, product_name, created_at, status, is_mock)

**GET /api/campaigns/{campaign_id}**
- Gets full campaign state
- Response: CampaignResponse with nested research_output, creative_spec, assets, stage_runs

**POST /api/campaigns/{campaign_id}/research/start**
- Starts research stage
- Uses idempotency_key to prevent duplicate concurrent runs
- Response: {stage_run_id, status}

**POST /api/campaigns/{campaign_id}/angle**
- Selects angle from research results
- Validation: angle_id required
- Response: {status, angle_id}

**POST /api/campaigns/{campaign_id}/generate**
- Starts creative generation pipeline
- Validation: angle_id must be selected
- Creates stage runs for: spec, scene, image_1x1, image_9x16, video
- Response: {stages: [{stage, stage_run_id, status}]}

**POST /api/campaigns/{campaign_id}/stages/{stage}/retry**
- Retries failed/interrupted stage
- Validation: Cannot retry succeeded stage
- Increments attempt counter
- Response: {stage_run_id, attempt}

### Error Format
- HTTP status codes: 400 (validation), 404 (not found), 422 (unprocessable)
- Error response: {"detail": "error message"}

## 12. Reliability and Recovery

### Startup Recovery
- `recover_stale_running_stages()` called on worker startup
- Marks stages with stale heartbeat as "interrupted"
- Cutoff: current time - WORKER_HEARTBEAT_TIMEOUT (30s default)

### Retry Endpoint Behavior
- Creates new StageRun with incremented attempt
- Reuses same input data with new idempotency_key
- Cannot retry succeeded stages (returns 400)

### Duplicate-Submission Protection
- Idempotency_key indexed on StageRun
- In-flight check prevents concurrent same-key submissions
- Input hash reuse prevents duplicate successful work

### Malformed LLM Output Handling
- Research agent validates LLM output against ResearchOutput schema
- If validation fails: agent retries or returns error
- Stage marked as failed with validation error message

### Timeouts
- Research wall clock: 90s default
- Page fetch timeout: 10s default
- Video generation timeout: 30s
- FFmpeg verification timeout: 10s

### Remaining Duplicate-Call Risks
- No protection against same campaign + same angle being generated multiple times sequentially
- Different idempotency_keys allow multiple "generate" calls
- Input hash reuse only works for exact same input data

## 13. Security

### Secrets Handling
- API keys in environment variables (GEMINI_API_KEY, TAVILY_API_KEY, CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_KEY)
- Loaded via python-dotenv from .env file
- Never logged or exposed in API responses
- Frontend has no access to backend secrets

### Upload Validation
- MAX_UPLOAD_SIZE: 5MB default
- ALLOWED_UPLOAD_TYPES: ["image/png", "image/jpeg", "image/webp"]
- File upload not currently implemented (planned feature)

### SSRF Guard
- Validates URLs against allowed schemes (http, https)
- Blocks private IP ranges (127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
- Blocks metadata services (metadata.google.internal, 169.254.169.254)
- Additional check: only fetch pages from search results

### What Is Not Covered
- Authentication/authorization (no user accounts)
- Rate limiting
- Input sanitization beyond Pydantic validation
- SQL injection (handled by SQLModel)
- XSS (not applicable - no user-generated HTML)

## 14. Mock and Failure-Injection Mode

### Environment Flags
- `MOCK_MODE=1`: Enables mock mode
- `FAIL_STAGE=<stage_name>`: Forces stage to fail
- `FAIL_ONCE=<stage_name>`: Fails stage once, then succeeds

### Mock Behavior
- Research agent returns scripted mock angles and sources
- LLM responses use mock fixtures
- Campaign.is_mock set to True
- Frontend displays "Mock" in campaign status

### Fixtures
- Mock research output in `backend/app/agents/research/prompts.py`
- Mock angles, sources, tool_calls
- Used when MOCK_MODE=1 or LLM unavailable

### How to Reproduce Failure and Retry
1. Set `FAIL_STAGE=video` in .env
2. Run campaign generation
3. Video stage will fail with injected error
4. Call `POST /api/campaigns/{id}/stages/video/retry`
5. Remove FAIL_STAGE env var and retry

## 15. Testing and Verification

### Test Suite (`backend/tests/test_campaign_flow.py`)
- `test_create_campaign`: Creates campaign, validates response
- `test_list_campaigns`: Lists campaigns, validates array
- `test_get_campaign`: Gets specific campaign by ID
- `test_research_stage`: Starts research, validates stage_run_id
- `test_reuse_stage`: Tests input hash reuse
- `test_angle_selection`: Tests angle selection (may fail if research incomplete)
- `test_retry_succeeded_stage`: Tests retry rejection of succeeded stages

### What verify_campaign.py Checks
- No verify_campaign.py script exists in repository
- Manual verification done via API calls and frontend testing

### Actual Last Run Results
- Tests pass in mock mode (MOCK_MODE=1)
- Integration tests may time out waiting for worker
- Angle selection test accepts 400/422/404 responses (research timing)

## 16. Configuration

### Environment Variables (from .env.example)

| Variable | Default | Purpose |
|----------|---------|---------|
| DATABASE_URL | sqlite:///./data/campaigns.db | Database connection string |
| MAX_TOOL_CALLS | 8 | Max research agent tool calls |
| MAX_FOLLOWUP_SEARCHES | 2 | Max follow-up searches |
| PAGE_FETCH_TIMEOUT | 10 | Page fetch timeout (seconds) |
| RESEARCH_WALL_CLOCK | 90 | Research max duration (seconds) |
| PAGE_TEXT_CAP | 20000 | Max page text length (chars) |
| LLM_RETRIES | 1 | LLM API retry attempts |
| WORKER_POLL_INTERVAL | 2 | Worker poll interval (seconds) |
| WORKER_HEARTBEAT_TIMEOUT | 30 | Stage heartbeat timeout (seconds) |
| MOCK_MODE | 0 | Enable mock mode (1=enabled) |
| FAIL_STAGE | None | Force stage to fail |
| FAIL_ONCE | None | Fail stage once |
| ASSET_DIR | ./data/campaigns | Asset storage directory |
| GEMINI_API_KEY | None | Google Gemini API key |
| TAVILY_API_KEY | None | Tavily search API key |
| CLOUDFLARE_ACCOUNT_ID | None | Cloudflare account ID |
| CLOUDFLARE_API_KEY | None | Cloudflare API key |
| MAX_UPLOAD_SIZE | 5 | Max upload size (MB) |
| ALLOWED_UPLOAD_TYPES | image/png,image/jpeg,image/webp | Allowed upload types |

## 17. Key Design Decisions

### Decision 1: Polling Worker vs Task Queue
**Alternatives**: Task queue (Celery, RQ), event-driven, polling
**Trade-off**: Chose polling for simplicity and zero infrastructure dependencies
**Impact**: 2-second poll interval, eventual consistency acceptable for assignment

### Decision 2: Input Hash Reuse vs Always Regenerate
**Alternatives**: Always regenerate, version-based caching, hash-based reuse
**Trade-off**: Chose hash-based reuse for efficiency and consistency
**Impact**: Same inputs always produce same outputs, faster on repeat operations

### Decision 3: Cloudflare AI with Procedural Fallback
**Alternatives**: Only AI, only procedural, multiple AI providers
**Trade-off**: Chose Cloudflare AI + fallback for reliability and cost-effectiveness
**Impact**: Always produces output, AI failures graceful, user gets visual results

## 18. Deviations from Plan, Known Limitations, Unverified Items

### Deviations from Plan
- **No reference image upload**: Reference_image_path exists in model but no upload endpoint
- **No product image in spec**: Product identity is dict, not actual image file
- **No true video AI**: Video uses AI image background + FFmpeg zoom, not AI video generation
- **No font bundling**: Uses system fonts, not bundled open-license font as requested
- **Simplified research**: Uses example.com URLs in mock mode, which return 404

### Known Limitations
- **Sequential execution**: No parallel stage execution
- **No rate limiting**: API endpoints have no rate limiting
- **No authentication**: No user accounts or API keys
- **SQLite only**: No PostgreSQL/MySQL support tested
- **Single process**: Worker runs in single process, no horizontal scaling
- **Frontend TypeScript errors**: Fixed but not all edge cases tested

### Unverified or Mocked Items
- **Cloudflare AI**: Configured and tested, but not all edge cases verified
- **Production deployment**: No deployment configuration (Docker, K8s, etc.)
- **Video zoom effect**: Tested with AI image, long-term stability unknown
- **Large-scale testing**: Only tested with single concurrent campaign
- **Performance**: No load testing or performance benchmarks

## 19. Traceability Guide

### Follow One Campaign Through the Code

**Step 1: Create Campaign**
- POST /api/campaigns with brief data
- Handler: `create_campaign()` in `backend/app/api/campaigns.py`
- Creates Campaign record, sets is_mock from MOCK_MODE
- Returns CampaignResponse with id

**Step 2: Start Research**
- POST /api/campaigns/{id}/research/start
- Handler: `start_research()` in `backend/app/api/campaigns.py`
- Calls `get_or_create_stage_run()` in `backend/app/workflow/runner.py`
- Computes input_hash, checks for reuse, creates StageRun
- Worker picks up pending stage

**Step 3: Execute Research**
- Worker calls `execute_research_stage()` in `backend/app/workflow/worker.py`
- Creates ResearchAgent from `backend/app/agents/research/agent.py`
- Agent runs tool-calling loop via LLM (Gemini)
- Tools: web_search, read_page (with SSRF guard)
- Returns ResearchOutput with angles, sources, tool_calls
- Marked as succeeded via `mark_stage_success()`

**Step 4: Select Angle**
- POST /api/campaigns/{id}/angle with angle_id
- Handler: `select_angle()` in `backend/app/api/campaigns.py`
- Updates Campaign.selected_angle_id

**Step 5: Generate Creatives**
- POST /api/campaigns/{id}/generate
- Handler: `generate_creatives()` in `backend/app/api/campaigns.py`
- Creates stage runs for: spec, scene, image_1x1, image_9x16, video
- Worker executes sequentially

**Step 6: Execute Spec**
- Handler: `execute_spec_stage()` in `backend/app/workflow/worker.py`
- Calls `generate_spec()` in `backend/app/workflow/stages/spec.py`
- LLM generates CreativeSpec from selected angle
- Stored in StageRun.output_json

**Step 7: Execute Scene**
- Handler: `execute_scene_stage()` in `backend/app/workflow/worker.py`
- Calls `generate_scene()` in `backend/app/workflow/stages/scene.py`
- LLM generates scene configuration
- Stored in StageRun.output_json

**Step 8: Execute Image 1x1**
- Handler: `execute_image_1x1_stage()` in `backend/app/workflow/worker.py`
- Calls compositor.generate_image_1x1() in `backend/app/rendering/compositor.py`
- Tries Cloudflare AI with product-specific prompt
- Falls back to procedural generation
- Returns (path, scene_source, fallback_reason)
- Asset record created with scene_source metadata

**Step 9: Execute Image 9x16**
- Handler: `execute_image_9x16_stage()` in `backend/app/workflow/worker.py`
- Calls compositor.generate_image_9x16() in `backend/app/rendering/compositor.py`
- Similar AI/fallback logic as 1x1
- Asset record created

**Step 10: Execute Video**
- Handler: `execute_video_stage()` in `backend/app/workflow/worker.py`
- Finds 9x16 image for background
- Calls video_generator.generate_video() in `backend/app/rendering/video.py`
- FFmpeg creates video with zoom effect on AI image
- Asset record created

**Step 11: View Results**
- GET /api/campaigns/{id}
- Handler: `get_campaign()` in `backend/app/api/campaigns.py`
- Calls `build_campaign_response()` to aggregate data
- Returns full campaign with assets, stage_runs, research_output, creative_spec
- Frontend displays images/video at /data/ URLs

---

## Uncertainties and Manual Verification Needed

1. **Cloudflare AI Model Behavior**: Exact prompt-response characteristics not fully documented
2. **FFmpeg Zoom Effect Stability**: Long-term reliability of zoompan filter unknown
3. **Font Cross-Platform Compatibility**: System font usage may vary across OS
4. **Large-Scale Concurrency**: No testing with multiple concurrent campaigns
5. **Production Database Performance**: SQLite limitations at scale untested
6. **Memory Usage**: No profiling of memory consumption during generation
7. **API Rate Limits**: Unknown if external providers (Gemini, Tavily, Cloudflare) have strict limits
8. **Video File Size**: Generated video sizes not optimized for bandwidth
9. **Error Recovery Coverage**: Not all error paths tested (network failures, API errors)
10. **Frontend State Consistency**: Edge cases in state updates not fully tested