import {Navigate,Route,Routes} from 'react-router-dom'
import {AuthProvider,useAuth} from './auth'
import Layout from './components/Layout'
import BusinessSettings from './pages/BusinessSettings'
import Customers from './pages/Customers'
import Dashboard from './pages/Dashboard'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Marketplace from './pages/Marketplace'
import Orders from './pages/Orders'
import Payments from './pages/Payments'
import Products from './pages/Products'
import Production from './pages/Production'
import PublicStore from './pages/PublicStore'
import QuoteRequest from './pages/QuoteRequest'
import QuoteStatus from './pages/QuoteStatus'
import Quotes from './pages/Quotes'
import Designs from './pages/Designs'
import DesignApproval from './pages/DesignApproval'
import Messages from './pages/Messages'
import RecoverPassword from './pages/RecoverPassword'
import Register from './pages/Register'
import Team from './pages/Team'
import Reports from './pages/Reports'
import Documents from './pages/Documents'
import TokenAction from './pages/TokenAction'
import AdminLayout from './components/AdminLayout'
import AdminDashboard from './pages/AdminDashboard'
import PublicLayout from './components/PublicLayout'

function BusinessProtected({children}:{children:React.ReactNode}){const {user,loading}=useAuth();if(loading)return <div className="page-loader"><div className="spinner-border text-primary"/></div>;if(!user)return <Navigate to="/ingresar" replace/>;return user.is_superuser?<Navigate to="/plataforma" replace/>:<>{children}</>}
function AdminProtected({children}:{children:React.ReactNode}){const {user,loading}=useAuth();if(loading)return <div className="page-loader"><div className="spinner-border text-primary"/></div>;if(!user)return <Navigate to="/ingresar" replace/>;return user.is_superuser?<>{children}</>:<Navigate to="/app" replace/>}
function Guest({children}:{children:React.ReactNode}){const {user,loading}=useAuth();if(loading)return null;return user?<Navigate to={user.is_superuser?'/plataforma':'/app'} replace/>:<>{children}</>}
export default function App(){return <AuthProvider><Routes>
  <Route element={<PublicLayout/>}>
    <Route path="/" element={<Marketplace/>}/><Route path="/como-funciona" element={<Landing/>}/>
    <Route path="/tienda/:slug" element={<PublicStore/>}/><Route path="/tienda/:slug/:productSlug" element={<PublicStore/>}/>
    <Route path="/cotizar" element={<QuoteRequest/>}/><Route path="/cotizacion/:publicId" element={<QuoteStatus/>}/>
    <Route path="/aprobar/:token" element={<DesignApproval/>}/>
    <Route path="/ingresar" element={<Guest><Login/></Guest>}/><Route path="/registro" element={<Guest><Register/></Guest>}/>
    <Route path="/recuperar" element={<RecoverPassword/>}/><Route path="/restablecer/:uid/:token" element={<TokenAction mode="reset"/>}/><Route path="/verificar-correo/:uid/:token" element={<TokenAction mode="verify"/>}/>
  </Route>
  <Route path="/app" element={<BusinessProtected><Layout/></BusinessProtected>}><Route index element={<Dashboard/>}/><Route path="clientes" element={<Customers/>}/><Route path="productos" element={<Products/>}/><Route path="pedidos" element={<Orders/>}/><Route path="produccion" element={<Production/>}/><Route path="pagos" element={<Payments/>}/><Route path="reportes" element={<Reports/>}/><Route path="documentos" element={<Documents/>}/><Route path="cotizaciones" element={<Quotes/>}/><Route path="disenos" element={<Designs/>}/><Route path="mensajes" element={<Messages/>}/><Route path="empresa" element={<BusinessSettings/>}/><Route path="equipo" element={<Team/>}/></Route>
  <Route path="/plataforma" element={<AdminProtected><AdminLayout/></AdminProtected>}><Route index element={<AdminDashboard/>}/></Route>
  <Route path="*" element={<Navigate to="/"/>}/>
</Routes></AuthProvider>}
