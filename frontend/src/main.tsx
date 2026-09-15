import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import 'bootstrap/dist/css/bootstrap.min.css'
import 'bootstrap-icons/font/bootstrap-icons.css'
import './styles.css'
import './operations.css'
import './brand.css'
import './store.css'
import './settings.css'
import './marketplace.css'
import './quotes.css'
import './navfix.css'
import './designs.css'
import './messages.css'
import './admin.css'
import './notifications.css'
import App from './App'

const queryClient = new QueryClient({defaultOptions:{queries:{retry:1,staleTime:30_000}}})
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><QueryClientProvider client={queryClient}><BrowserRouter><App/></BrowserRouter></QueryClientProvider></React.StrictMode>)
if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js'))
}
