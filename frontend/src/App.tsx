import { useState, useEffect } from 'react'
import './App.css'

// Types
interface Campaign {
  id: number
  brief: {
    product_name: string
    factual_product_description: string
    target_audience: string
    campaign_objective: string
    tone: string
    call_to_action: string
    verified_claims: string[]
  }
  selected_angle_id: number | null
  created_at: string
  is_mock: boolean
  research_output: string | null
  creative_spec: string | null
  assets: any[]
  stage_runs: StageRun[]
}

interface CampaignListItem {
  id: number
  product_name: string
  created_at: string
  status: string
  is_mock: boolean
}

interface StageRun {
  id: number
  campaign_id: number
  stage: string
  status: string
  attempt: number
  error: string | null
  started_at: string | null
  finished_at: string | null
}

interface ResearchOutput {
  angles: any[]
  sources: any[]
  tool_calls: any[]
  source_gap: string | null
}

function App() {
  const [currentScreen, setCurrentScreen] = useState<'brief' | 'research' | 'generate' | 'results' | 'history'>('brief')
  const [campaigns, setCampaigns] = useState<CampaignListItem[]>([])
  const [currentCampaign, setCurrentCampaign] = useState<Campaign | null>(null)
  const [stageRuns, setStageRuns] = useState<StageRun[]>([])
  const [researchOutput, setResearchOutput] = useState<ResearchOutput | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const API_BASE = '/api/campaigns'

  // Fetch campaigns on mount
  useEffect(() => {
    fetchCampaigns()
  }, [])

  // Poll for updates when generating
  useEffect(() => {
    if (currentCampaign && (currentScreen === 'research' || currentScreen === 'generate')) {
      const interval = setInterval(() => {
        fetchCampaign(currentCampaign.id)
      }, 2000)
      return () => clearInterval(interval)
    }
  }, [currentCampaign, currentScreen])

  const fetchCampaigns = async () => {
    try {
      const response = await fetch(API_BASE)
      const data = await response.json()
      setCampaigns(data)
    } catch (error) {
      console.error('Failed to fetch campaigns:', error)
      setError('Failed to fetch campaigns')
    }
  }

  const fetchCampaign = async (id: number) => {
    try {
      const response = await fetch(`${API_BASE}/${id}`)
      const data = await response.json()
      setCurrentCampaign(data)
      setStageRuns(data.stage_runs || [])
      if (data.research_output) {
        try {
          setResearchOutput(JSON.parse(data.research_output))
        } catch (e) {
          console.error('Failed to parse research output:', e)
          setResearchOutput(null)
        }
      } else {
        setResearchOutput(null)
      }
      setError(null)
    } catch (error) {
      console.error('Failed to fetch campaign:', error)
      setError('Failed to fetch campaign')
    }
  }

  const createCampaign = async (brief: any) => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(API_BASE, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(brief)
      })
      const data = await response.json()
      setCurrentCampaign(data)
      setCurrentScreen('research')
      setLoading(false)
    } catch (error) {
      console.error('Failed to create campaign:', error)
      setError('Failed to create campaign')
      setLoading(false)
    }
  }

  const startResearch = async () => {
    if (!currentCampaign) return
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${API_BASE}/${currentCampaign.id}/research/start`, { method: 'POST' })
      if (!response.ok) {
        throw new Error('Failed to start research')
      }
      setLoading(false)
    } catch (error) {
      console.error('Failed to start research:', error)
      setError('Failed to start research')
      setLoading(false)
    }
  }

  const selectAngle = async (angleId: number) => {
    if (!currentCampaign) return
    setLoading(true)
    setError(null)
    try {
      console.log('Selecting angle:', angleId)
      const response = await fetch(`${API_BASE}/${currentCampaign.id}/angle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ angle_id: angleId })
      })
      
      console.log('Response status:', response.status)
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to select angle')
      }
      
      const result = await response.json()
      console.log('Angle selection result:', result)
      
      await fetchCampaign(currentCampaign.id)
      setCurrentScreen('generate')
      setLoading(false)
    } catch (error: any) {
      console.error('Failed to select angle:', error)
      setError(error.message || 'Failed to select angle')
      setLoading(false)
    }
  }

  const generateCreatives = async () => {
    if (!currentCampaign) return
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${API_BASE}/${currentCampaign.id}/generate`, { method: 'POST' })
      if (!response.ok) {
        throw new Error('Failed to generate creatives')
      }
      setLoading(false)
    } catch (error) {
      console.error('Failed to generate creatives:', error)
      setError('Failed to generate creatives')
      setLoading(false)
    }
  }

  const BriefForm = () => (
    <div className="screen">
      <h1>Create Campaign Brief</h1>
      {error && <div className="error-message">{error}</div>}
      <form onSubmit={(e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault()
        const formData = new FormData(e.target as HTMLFormElement)
        const brief = {
          product_name: formData.get('product_name'),
          factual_product_description: formData.get('factual_product_description'),
          target_audience: formData.get('target_audience'),
          campaign_objective: formData.get('campaign_objective'),
          tone: formData.get('tone'),
          call_to_action: formData.get('call_to_action'),
          verified_claims: formData.get('verified_claims')?.toString().split(',').map(s => s.trim()).filter(s => s) || []
        }
        createCampaign(brief)
      }}>
        <div className="form-group">
          <label>Product Name</label>
          <input name="product_name" required placeholder="e.g., Beast Protein" />
        </div>
        <div className="form-group">
          <label>Product Description</label>
          <textarea name="factual_product_description" required placeholder="Describe your product factually" />
        </div>
        <div className="form-group">
          <label>Target Audience</label>
          <input name="target_audience" required placeholder="e.g., Busy gym-goers aged 25-40" />
        </div>
        <div className="form-group">
          <label>Campaign Objective</label>
          <select name="campaign_objective" required>
            <option value="">Select objective...</option>
            <option value="introduce">Introduce</option>
            <option value="drive_conversion">Drive Conversion</option>
            <option value="brand_awareness">Brand Awareness</option>
            <option value="launch">Launch</option>
          </select>
        </div>
        <div className="form-group">
          <label>Tone</label>
          <select name="tone" required>
            <option value="">Select tone...</option>
            <option value="practical_energetic">Practical Energetic</option>
            <option value="sophisticated">Sophisticated</option>
            <option value="playful">Playful</option>
            <option value="authentic">Authentic</option>
          </select>
        </div>
        <div className="form-group">
          <label>Call to Action</label>
          <input name="call_to_action" required placeholder="e.g., Explore the range." />
        </div>
        <div className="form-group">
          <label>Verified Claims (comma-separated)</label>
          <input name="verified_claims" placeholder="20g protein per serving, No artificial sweeteners" />
        </div>
        <div className="button-group">
          <button type="submit" disabled={loading} className="primary-button">
            {loading ? 'Creating...' : 'Create Campaign'}
          </button>
          <button type="button" onClick={() => setCurrentScreen('history')} className="secondary-button">
            View History
          </button>
        </div>
      </form>
    </div>
  )

  const ResearchReview = () => (
    <div className="screen">
      <h1>Research Review</h1>
      {currentCampaign?.is_mock && <div className="mock-badge">MOCK MODE</div>}
      {error && <div className="error-message">{error}</div>}
      
      {!researchOutput ? (
        <div className="action-area">
          <button onClick={startResearch} disabled={loading} className="primary-button">
            {loading ? 'Researching...' : 'Start Research'}
          </button>
          <button onClick={() => setCurrentScreen('brief')} className="secondary-button">
            Back
          </button>
        </div>
      ) : (
        <div>
          <div className="section">
            <h2>Tool Calls</h2>
            <div className="tool-calls-container">
              {researchOutput.tool_calls.map((call, i) => (
                <div key={i} className="tool-call-item">
                  <strong>Step {call.step}:</strong> {call.tool}
                  <br />
                  <em>{call.decision}</em>
                  <br />
                  <small>Latency: {call.latency_ms}ms</small>
                </div>
              ))}
            </div>
          </div>
          
          <div className="section">
            <h2>Sources</h2>
            {researchOutput.sources.map((source, i) => (
              <div key={i} className="source-card">
                <h3>{source.title}</h3>
                <p>{source.excerpt}</p>
                <small>{source.url}</small>
              </div>
            ))}
          </div>
          
          {researchOutput.source_gap && <div className="source-gap">{researchOutput.source_gap}</div>}
          
          <div className="section">
            <h2>Creative Angles</h2>
            {researchOutput.angles.map((angle, i) => (
              <div key={i} className="angle-card">
                <h3>{angle.hook}</h3>
                <p><strong>Audience Insight:</strong> {angle.audience_insight}</p>
                <p><strong>Visual Direction:</strong> {angle.visual_direction}</p>
                <p><strong>Rationale:</strong> {angle.rationale}</p>
                <button 
                  onClick={() => selectAngle(i + 1)} 
                  disabled={loading}
                  className="select-button"
                >
                  {loading ? 'Selecting...' : 'Select This Angle'}
                </button>
              </div>
            ))}
          </div>
          
          <div className="button-group">
            <button onClick={() => setCurrentScreen('brief')} className="secondary-button">
              Back
            </button>
          </div>
        </div>
      )}
    </div>
  )

  const GenerationStatus = () => (
    <div className="screen">
      <h1>Generation Status</h1>
      {currentCampaign?.is_mock && <div className="mock-badge">MOCK MODE</div>}
      {error && <div className="error-message">{error}</div>}
      
      <div className="action-area">
        <button onClick={generateCreatives} disabled={loading} className="primary-button">
          {loading ? 'Generating...' : 'Generate Creatives'}
        </button>
      </div>
      
      <div className="section">
        <h2>Stage Progress</h2>
        {stageRuns.map((run) => (
          <div key={run.id} className={`stage-card ${run.status}`}>
            <h3>{run.stage}</h3>
            <p>Status: {run.status}</p>
            {run.error && <p className="error">Error: {run.error}</p>}
            <p>Started: {run.started_at}</p>
            <p>Finished: {run.finished_at}</p>
          </div>
        ))}
      </div>
      
      <div className="button-group">
        <button onClick={() => setCurrentScreen('results')} className="primary-button">
          View Results
        </button>
        <button onClick={() => setCurrentScreen('brief')} className="secondary-button">
          New Campaign
        </button>
      </div>
    </div>
  )

  const Results = () => {
    if (!currentCampaign) return null
    
    // Parse research output if available
    let parsedResearch: ResearchOutput | null = null
    if (currentCampaign.research_output) {
      try {
        parsedResearch = JSON.parse(currentCampaign.research_output)
      } catch (e) {
        console.error('Failed to parse research output:', e)
      }
    }
    
    // Parse creative spec if available
    let parsedSpec: any = null
    if (currentCampaign.creative_spec) {
      try {
        parsedSpec = JSON.parse(currentCampaign.creative_spec)
      } catch (e) {
        console.error('Failed to parse creative spec:', e)
      }
    }
    
    return (
      <div className="screen">
        <h1>Campaign Results</h1>
        {currentCampaign.is_mock && <div className="mock-badge">MOCK MODE</div>}
        
        <div className="section">
          <h2>Campaign Brief</h2>
          <div className="brief-details">
            <p><strong>Product:</strong> {currentCampaign.brief?.product_name || 'N/A'}</p>
            <p><strong>Description:</strong> {currentCampaign.brief?.factual_product_description || 'N/A'}</p>
            <p><strong>Target Audience:</strong> {currentCampaign.brief?.target_audience || 'N/A'}</p>
            <p><strong>Objective:</strong> {currentCampaign.brief?.campaign_objective || 'N/A'}</p>
            <p><strong>Tone:</strong> {currentCampaign.brief?.tone || 'N/A'}</p>
            <p><strong>Call to Action:</strong> {currentCampaign.brief?.call_to_action || 'N/A'}</p>
            <p><strong>Claims:</strong> {currentCampaign.brief?.verified_claims?.join(', ') || 'None'}</p>
          </div>
        </div>
        
        {parsedResearch && currentCampaign.selected_angle_id && (
          <div className="section">
            <h2>Selected Angle</h2>
            {parsedResearch.angles[currentCampaign.selected_angle_id - 1] ? (
              <div className="angle-card selected">
                <h3>{parsedResearch.angles[currentCampaign.selected_angle_id - 1].hook}</h3>
                <p><strong>Audience Insight:</strong> {parsedResearch.angles[currentCampaign.selected_angle_id - 1].audience_insight}</p>
                <p><strong>Visual Direction:</strong> {parsedResearch.angles[currentCampaign.selected_angle_id - 1].visual_direction}</p>
                <p><strong>Rationale:</strong> {parsedResearch.angles[currentCampaign.selected_angle_id - 1].rationale}</p>
              </div>
            ) : (
              <p>Selected angle not found in research results</p>
            )}
          </div>
        )}
        
        {parsedSpec && (
          <div className="section">
            <h2>Creative Spec</h2>
            <div className="spec-details">
              <p><strong>Hook:</strong> {parsedSpec.hook}</p>
              <p><strong>Headline:</strong> {parsedSpec.approved_headline}</p>
              <p><strong>Body Copy:</strong> {parsedSpec.approved_body_copy}</p>
              <p><strong>Call to Action:</strong> {parsedSpec.call_to_action}</p>
              <p><strong>Scene Description:</strong> {parsedSpec.scene_description}</p>
              <p><strong>Palette:</strong> {parsedSpec.palette?.join(', ')}</p>
            </div>
          </div>
        )}
        
        {currentCampaign.assets && currentCampaign.assets.length > 0 && (
          <div className="section">
            <h2>Generated Assets</h2>
            <div className="assets-grid">
              {currentCampaign.assets.map((asset: any, index: number) => (
                <div key={index} className="asset-card">
                  <h3>{asset.asset_type}</h3>
                  <p><strong>Dimensions:</strong> {asset.width}x{asset.height}</p>
                  {asset.duration_seconds && <p><strong>Duration:</strong> {asset.duration_seconds}s</p>}
                  <p><strong>File:</strong> {asset.file_path}</p>
                  {asset.scene_source && (
                    <p><strong>Source:</strong> {asset.scene_source}</p>
                  )}
                  {asset.fallback_reason && (
                    <p><strong>Fallback Reason:</strong> {asset.fallback_reason}</p>
                  )}
                  {asset.file_path && (
                    <div className="asset-preview">
                      {asset.asset_type.includes('image') ? (
                        <img 
                          src={asset.file_path.startsWith('http') ? asset.file_path : `http://localhost:8000${asset.file_path}`}
                          alt={asset.asset_type}
                          onError={(e: React.SyntheticEvent<HTMLImageElement>) => (e.currentTarget as HTMLImageElement).style.display = 'none'}
                          onLoad={(e: React.SyntheticEvent<HTMLImageElement>) => console.log('Image loaded:', asset.file_path)}
                        />
                      ) : asset.asset_type.includes('video') ? (
                        <video 
                          controls 
                          width="300" 
                          height="auto"
                          preload="metadata"
                          onError={(e: React.SyntheticEvent<HTMLVideoElement>) => console.error('Video error:', asset.file_path, e)}
                          onLoadStart={(e: React.SyntheticEvent<HTMLVideoElement>) => console.log('Video loading:', asset.file_path)}
                          onLoadedMetadata={(e: React.SyntheticEvent<HTMLVideoElement>) => console.log('Video metadata loaded:', asset.file_path)}
                        >
                          <source src={asset.file_path.startsWith('http') ? asset.file_path : `http://localhost:8000${asset.file_path}`} type="video/mp4" />
                          Your browser does not support video.
                        </video>
                      ) : (
                        <p>Preview not available</p>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
        
        <div className="section">
          <h2>Stage History</h2>
          <div className="stage-history">
            {stageRuns.map((run) => (
              <div key={run.id} className={`stage-status ${run.status}`}>
                <span className="stage-name">{run.stage}</span>
                <span className="stage-status-text">{run.status}</span>
                {run.error && <span className="stage-error">{run.error}</span>}
              </div>
            ))}
          </div>
        </div>
        
        <div className="button-group">
          <button onClick={() => setCurrentScreen('history')} className="primary-button">
            Back to History
          </button>
          <button onClick={() => setCurrentScreen('brief')} className="secondary-button">
            New Campaign
          </button>
        </div>
      </div>
    )
  }

  const History = () => (
    <div className="screen">
      <h1>Campaign History</h1>
      <div className="button-group">
        <button onClick={() => setCurrentScreen('brief')} className="primary-button">
          Create New Campaign
        </button>
      </div>
      
      <div className="section">
        {campaigns.length === 0 ? (
          <p>No campaigns yet. Create your first campaign!</p>
        ) : (
          campaigns.map((campaign) => (
            <div 
              key={campaign.id} 
              className="campaign-card" 
              onClick={() => {
                fetchCampaign(campaign.id)
                setCurrentScreen('results')
              }}
            >
              <h3>{campaign.product_name || 'Unknown Campaign'}</h3>
              <p>Created: {new Date(campaign.created_at).toLocaleString()}</p>
              <p>Status: {campaign.status}</p>
              <p>Mode: {campaign.is_mock ? 'Mock' : 'Live'}</p>
            </div>
          ))
        )}
      </div>
    </div>
  )

  return (
    <div className="App">
      {currentScreen === 'brief' && <BriefForm />}
      {currentScreen === 'research' && <ResearchReview />}
      {currentScreen === 'generate' && <GenerationStatus />}
      {currentScreen === 'results' && <Results />}
      {currentScreen === 'history' && <History />}
    </div>
  )
}

export default App