import {createAuth} from '../../server/auth/better-auth.ts'
import {getMigrations} from 'better-auth/db/migration'
import {createOTP} from '@better-auth/utils/otp'
import {base32} from '@better-auth/utils/base32'
export function cookieHeader(response) {
 const values=response.headers['set-cookie'] || []
 return (Array.isArray(values)?values:[values]).map(value=>value.split(';')[0]).filter(value=>!value.endsWith('=')).join('; ')
}
export async function testAuth(database,config) {
 const auth=createAuth(config,database,async()=>{})
 await(await getMigrations(auth.options)).runMigrations()
 return auth
}
export async function signInAdmin(app,database,email='admin@example.com',password='a-long-test-password',origin='http://127.0.0.1:5173') {
 const post=(path,payload,cookie)=>app.inject({method:'POST',url:'/api/auth'+path,headers:{origin,...(cookie?{cookie}:{})},payload})
 await post('/sign-up/email',{name:'Administrator',email,password})
 database.prepare('UPDATE auth_user SET role = ?, emailVerified = 1 WHERE email = ?').run('admin',email)
 const user=database.prepare('SELECT * FROM auth_user WHERE email = ?').get(email)
 database.prepare('INSERT OR IGNORE INTO admin_users (id,email,password_hash,created_at) VALUES (?,?,?,?)').run(user.id,email,'fixture-not-a-password',new Date().toISOString())
 const first=await post('/sign-in/email',{email,password})
 if(first.statusCode!==200) throw new Error(first.body)
 const enabled=await post('/two-factor/enable',{password},cookieHeader(first))
 const code=await createOTP(base32.decode(new URL(enabled.json().totpURI).searchParams.get('secret'))).totp()
 const confirmed=await post('/two-factor/verify-totp',{code},cookieHeader(first))
 if(confirmed.statusCode!==200) throw new Error(confirmed.body)
 const challenged=await post('/sign-in/email',{email,password})
 const result=await post('/two-factor/verify-backup-code',{code:enabled.json().backupCodes[0]},cookieHeader(challenged))
 if(result.statusCode!==200) throw new Error(result.body)
 return {origin,cookie:cookieHeader(result)}
}
