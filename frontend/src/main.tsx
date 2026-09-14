import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import ResearchWorkspace from './v2/ResearchWorkspace'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ResearchWorkspace />
  </StrictMode>,
)
