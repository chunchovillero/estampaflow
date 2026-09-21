import { Link, NavLink, Outlet } from 'react-router-dom'

const links = [
  ['/', 'Inicio'],
  ['/#productos', 'Productos'],
  ['/#productos', 'Categorías'],
  ['/#emprendimientos', 'Emprendimientos'],
  ['/cotizar', 'Solicitar cotización'],
  ['/como-funciona', 'Cómo funciona'],
]

function closeMenu(event: React.MouseEvent<HTMLAnchorElement>) {
  event.currentTarget.closest('details')?.removeAttribute('open')
}

function PublicLinks({ mobile = false }: { mobile?: boolean }) {
  return <>{links.map(([to, label], index) => <NavLink end={to === '/'} key={`${label}-${index}`} to={to} onClick={mobile ? closeMenu : undefined}>{label}</NavLink>)}</>
}

export default function PublicLayout() {
  return <div className="public-layout">
    <header className="market-nav">
      <Link to="/" className="market-brand" aria-label="Ir al inicio de EstampaFlow"><img src="/brand/estampaflow-logo.png" alt="EstampaFlow" /></Link>
      <nav aria-label="Navegación principal"><PublicLinks /></nav>
      <div className="public-actions"><Link to="/ingresar">Ingresar</Link><Link className="btn btn-primary" to="/cotizar">Cotizar</Link><Link className="btn btn-outline-primary" to="/registro">Vender</Link></div>
      <details className="public-mobile-menu">
        <summary aria-label="Abrir menú"><i className="bi bi-list" /></summary>
        <nav aria-label="Navegación móvil"><PublicLinks mobile /><Link to="/ingresar" onClick={closeMenu}>Ingresar</Link><Link to="/registro" onClick={closeMenu}>Registrar mi emprendimiento</Link></nav>
      </details>
    </header>
    <div className="public-content"><Outlet /></div>
    <footer className="market-footer"><img src="/brand/estampaflow-logo.png" alt="EstampaFlow" /><p>Tus pedidos personalizados, bajo control.</p><small>© 2026 EstampaFlow · Hecho para emprendedores chilenos</small></footer>
  </div>
}
