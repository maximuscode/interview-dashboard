import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { InterviewDetail } from './pages/InterviewDetail'
import { InterviewList } from './pages/InterviewList'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <div className="min-h-screen bg-slate-50">
        <Routes>
          <Route path="/" element={<InterviewList />} />
          <Route path="/interviews/:id" element={<InterviewDetail />} />
        </Routes>
      </div>
    </BrowserRouter>
  </StrictMode>,
)
