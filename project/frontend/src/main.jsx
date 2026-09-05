import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './intel.css'
import App from './App.jsx'
import { initTheme } from './lib/theme.js'
import ErrorBoundary from './components/ErrorBoundary.jsx'

initTheme()

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
)
