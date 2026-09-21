import { Component, type ErrorInfo, type ReactNode } from 'react'

type Props = { children: ReactNode }
type State = { hasError: boolean }

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(): State {
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Error inesperado al renderizar EstampaFlow', error, info)
  }

  render() {
    if (!this.state.hasError) return this.props.children

    return (
      <main className="error-boundary" role="alert" aria-live="assertive">
        <section className="error-boundary__card">
          <img
            className="error-boundary__logo"
            src="/brand/estampaflow-logo.png"
            alt="EstampaFlow"
          />
          <div className="error-boundary__icon" aria-hidden="true">
            <i className="bi bi-exclamation-circle" />
          </div>
          <h1>Algo salió mal</h1>
          <p>
            La aplicación encontró un problema inesperado. Recarga la página para continuar.
          </p>
          <div className="error-boundary__actions">
            <button className="btn btn-primary" type="button" onClick={() => window.location.reload()}>
              <i className="bi bi-arrow-clockwise me-2" />
              Recargar
            </button>
            <a className="btn btn-light" href="/">
              Volver al inicio
            </a>
          </div>
        </section>
      </main>
    )
  }
}
