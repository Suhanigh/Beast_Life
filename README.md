# AI Campaign Creative Studio

An AI-powered campaign creative generation system for Beast Life. Captures product briefs, runs research, generates creative angles, and produces ad creatives (images + video) with AI-assisted generation.

## Quickstart

### Prerequisites
- Python 3.13+
- Node.js 18+
- FFmpeg (for video generation)
- API keys (optional, see below)

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys (optional)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Run a Campaign
1. Open http://localhost:5173
2. Create a campaign brief (product name, description, audience, etc.)
3. Start research (generates 3 creative angles)
4. Select an angle
5. Generate creatives (produces 2 images + 1 video)
6. View results in the Results screen

### Mock Mode
Set `MOCK_MODE=1` in `.env` to use mock data instead of real AI providers.

## What It Does

- **Research**: Web search + page reading via Tavily + Gemini LLM
- **Creative Angles**: 3 angles with audience insights, hooks, visual direction
- **Creative Specs**: Detailed specifications from selected angle
- **Image Generation**: Cloudflare AI (Stable Diffusion XL) with procedural fallback
- **Video Generation**: FFmpeg video with zoom effect on AI-generated background
- **Campaign History**: Track campaigns, retry failed stages, view results

## Architecture

FastAPI backend + React frontend + SQLite database. Background worker executes stages sequentially. Input hash reuse prevents duplicate work. AI generation falls back to procedural rendering for reliability.

See [docs/HLD.md](docs/HLD.md) for detailed architecture, data models, workflow, and security design.

## API Keys (Optional)

For production-quality AI generation, configure these in `.env`:
- `GEMINI_API_KEY`: Google Gemini for LLM (research, spec, scene)
- `TAVILY_API_KEY`: Tavily for web search
- `CLOUDFLARE_ACCOUNT_ID`: Cloudflare account ID
- `CLOUDFLARE_API_KEY`: Cloudflare API key for image generation

Without these, the system runs in mock mode with scripted outputs.

## Status

**Implemented and Tested:**
- Campaign CRUD and history
- Research agent with bounded tool calling
- Angle selection gate
- Creative spec generation
- Image generation (Cloudflare AI + procedural fallback)
- Video generation (FFmpeg with zoom effect)
- Stage retry mechanism
- Input hash reuse

**Mocked/Untested:**
- Production deployment (Docker, K8s)
- Rate limiting
- Authentication
- Large-scale concurrency
- Real video AI generation (uses AI image + FFmpeg instead)

**Known Limitations:**
- Sequential stage execution (no parallelism)
- SQLite only (not tested with PostgreSQL)
- Single-process worker (no horizontal scaling)
- System fonts only (no bundled open-license font)

## Development

### Backend
```bash
cd backend
source venv/bin/activate
pytest tests/  # Run tests
uvicorn app.main:app --reload  # Start dev server
```

### Frontend
```bash
cd frontend
npm run build  # Build for production
npm run type-check  # TypeScript check
```

### Configuration
See `.env.example` for all environment variables. Key ones:
- `MOCK_MODE=1`: Enable mock mode
- `WORKER_POLL_INTERVAL=2`: Worker poll interval (seconds)
- `RESEARCH_WALL_CLOCK=90`: Research timeout (seconds)

## Documentation

- [docs/HLD.md](docs/HLD.md) - High-level design, architecture, data models, workflow
- Backend API: http://localhost:8000/docs (FastAPI auto-docs)

## Troubleshooting

**Worker not picking up stages:** Check backend logs for worker startup and polling.

**Images not visible:** Check that `./data/campaigns/` directory exists and files are generated.

**Video not playing:** Verify FFmpeg is installed and in PATH.

**Cloudflare errors:** Check that CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_KEY are set correctly in `.env`.

## License

This is a hiring assignment for Beast Life AI & Engineering.