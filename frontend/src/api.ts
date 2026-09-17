import axios from 'axios'
const api=axios.create({baseURL:import.meta.env.VITE_API_URL??'http://localhost:8000/api/v1',withCredentials:true})
let csrfToken=''
export async function ensureCsrf(){if(!csrfToken){const {data}=await api.get('/auth/csrf/');csrfToken=data.csrfToken}return csrfToken}
api.interceptors.request.use(async config=>{if(config.method&&!['get','head','options'].includes(config.method)){config.headers['X-CSRFToken']=await ensureCsrf()}return config})
let refreshPromise:Promise<void>|null=null
async function refreshSession(){if(!refreshPromise)refreshPromise=api.post('/auth/refresh/').then(()=>undefined).finally(()=>{refreshPromise=null});return refreshPromise}
api.interceptors.response.use(r=>r,async error=>{const original=error.config;if(error.response?.status===401&&original&&!original._retry&&!original.url?.includes('/auth/')){original._retry=true;await refreshSession();return api(original)}return Promise.reject(error)})
export function apiError(error:unknown){if(axios.isAxiosError(error)){const details=error.response?.data?.error?.details;if(typeof details==='string')return details;if(details&&typeof details==='object')return Object.values(details).flat().join(' ')}return 'Ocurrió un error. Inténtalo nuevamente.'}
export default api
