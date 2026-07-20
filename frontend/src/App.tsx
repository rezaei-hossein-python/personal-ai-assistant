import { useEffect, useState } from 'react'
import './App.css'
import { getHealth } from './api/health'

type BackendStatus = 'loading' | 'connected' | 'unavailable'

function App() {
  const [backendStatus, setBackendStatus] = useState<BackendStatus>('loading')

  useEffect(() => {
    let isMounted = true

    getHealth()
      .then(() => {
        if (isMounted) {
          setBackendStatus('connected')
        }
      })
      .catch(() => {
        if (isMounted) {
          setBackendStatus('unavailable')
        }
      })

    return () => {
      isMounted = false
    }
  }, [])

  return (
    <main>
      <h1>Personal AI Assistant</h1>
      <p className={`backend-status backend-status--${backendStatus}`}>
        {getBackendStatusText(backendStatus)}
      </p>
    </main>
  )
}

function getBackendStatusText(status: BackendStatus): string {
  if (status === 'connected') {
    return 'Backend connected'
  }

  if (status === 'unavailable') {
    return 'Backend unavailable'
  }

  return 'Checking backend...'
}

export default App
