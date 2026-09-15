import {createContext,useContext,ReactNode} from 'react'
import {useQuery,useQueryClient} from '@tanstack/react-query'
import api from './api'
import type {User} from './types'

type AuthValue={user:User|null;loading:boolean;reload:()=>Promise<unknown>;logout:()=>Promise<void>}
const AuthContext=createContext<AuthValue|null>(null)
export function AuthProvider({children}:{children:ReactNode}){const client=useQueryClient();const query=useQuery({queryKey:['profile'],queryFn:async()=>{const {data}=await api.get<User>('/auth/profile/');return data},retry:false});async function logout(){await api.post('/auth/logout/');client.setQueryData(['profile'],null)}return <AuthContext.Provider value={{user:query.data??null,loading:query.isLoading,reload:query.refetch,logout}}>{children}</AuthContext.Provider>}
export function useAuth(){const value=useContext(AuthContext);if(!value)throw new Error('AuthProvider no disponible');return value}

