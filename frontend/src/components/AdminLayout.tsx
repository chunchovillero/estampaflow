import {Link,Outlet} from 'react-router-dom'
import {useAuth} from '../auth'

export default function AdminLayout(){const {user,logout}=useAuth();return <div className="admin-shell"><header><Link to="/plataforma" className="market-brand"><img src="/brand/estampaflow-logo.png" alt="EstampaFlow"/></Link><div><span className="badge text-bg-dark">Superadministrador</span><span>{user?.email}</span><button className="btn btn-outline-secondary btn-sm" onClick={logout}>Cerrar sesión</button></div></header><main><Outlet/></main></div>}
