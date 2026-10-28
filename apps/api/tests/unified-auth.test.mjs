import test from 'node:test'
import assert from 'node:assert/strict'
import Database from 'better-sqlite3'
import { getMigrations } from 'better-auth/db/migration'
import { createAuth } from '../src/auth/better-auth.ts'
import { createServer } from '../src/app.ts'
const origin='http://127.0.0.1:5173'
const password='correct-test-password-2026'
export async function authFixture(t) {
 const database=new Database(':memory:')
 const emails=[]
 const config={port:0,origin,databasePath:':memory:',sessionSecret:'test-auth-secret-at-least-thirty-two-characters',secureCookies:false,zaiModel:'test',chatTimeoutMs:45000,idleTimeoutMs:15000}
 const auth=createAuth(config,database,async e=>{emails.push(e)})
 await(await getMigrations(auth.options)).runMigrations()
 const app=await createServer({config,auth,chatProvider:{async*stream(){throw Error('unused')}}})
 t.after(async()=>{await app.close();database.close()})
 const post=(path,payload,headers={})=>app.inject({method:'POST',url:'/api/auth'+path,headers:{origin,...headers},payload})
 return {app,auth,database,emails,post}
}
test('Better Auth registers user only, verifies email and persists official sessions',async t=>{
 const {post,emails,database}=await authFixture(t)
 const bad=await post('/sign-up/email',{name:'User',email:'test@example.com',password,role:'admin'})
 assert.equal(bad.statusCode,400,bad.body)
 const result=await post('/sign-up/email',{name:'User',email:'test@example.com',password})
 assert.equal(result.statusCode,200,result.body)
 assert.equal(result.json().user.role,'user')
 assert.equal(result.json().user.emailVerified,false)
 assert.equal(emails.length,1)
 assert.equal(emails[0].kind,'verify')
 assert.ok(!database.prepare('SELECT password FROM auth_account').get().password.includes(password))
})
test('Better Auth login refuses unverified addresses and foreign origins',async t=>{
 const {post}=await authFixture(t)
 await post('/sign-up/email',{name:'User',email:'test@example.com',password})
 assert.equal((await post('/sign-in/email',{email:'test@example.com',password})).statusCode,403)
 assert.equal((await post('/sign-in/email',{email:'test@example.com',password},{origin:'https://evil.example'})).statusCode,403)
})

function cookies(response) { return (response.headers['set-cookie'] || []).map(value=>value.split(';')[0]).join('; ') }
async function verifiedUser(f,email='test@example.com') {
 await f.post('/sign-up/email',{name:'Test User',email,password})
 const url=new URL(f.emails.find(e=>e.kind==='verify').url)
 const verified=await f.app.inject({url:url.pathname+url.search,headers:{origin}})
 assert.equal(verified.statusCode,302,verified.body)
 const signed=await f.post('/sign-in/email',{email,password})
 assert.equal(signed.statusCode,200,signed.body)
 return {cookie:cookies(signed)}
}
test('official sessions are revoked on sign out and recovery tokens are one-use',async t=>{
 const f=await authFixture(t)
 const headers=await verifiedUser(f)
 assert.equal((await f.app.inject({url:'/api/auth/get-session',headers})).json().user.email,'test@example.com')
 assert.equal((await f.post('/request-password-reset',{email:'test@example.com',redirectTo:origin+'/conta/redefinir-senha'})).statusCode,200)
 const token=new URL(f.emails.find(e=>e.kind==='reset').url).pathname.split('/').at(-1)
 assert.equal((await f.post('/reset-password',{token,newPassword:'a-new-password-for-testing'})).statusCode,200)
 assert.equal((await f.app.inject({url:'/api/auth/get-session',headers})).json(),null)
 assert.notEqual((await f.post('/reset-password',{token,newPassword:'another-new-password-for-testing'})).statusCode,200)
})
test('user and unenrolled admin cannot access administrative resources',async t=>{
 const f=await authFixture(t)
 const {requireAdmin}=await import('../src/auth/routes.ts')
 f.app.get('/protected',{preHandler:requireAdmin},async()=>({ok:true}))
 const headers=await verifiedUser(f)
 assert.equal((await f.app.inject({url:'/protected',headers})).statusCode,403)
 f.database.prepare('UPDATE auth_user SET role = ?').run('admin')
 const denied=await f.app.inject({url:'/protected',headers})
 assert.equal(denied.json().code,'MFA_SETUP_REQUIRED')
})

import {createOTP} from '@better-auth/utils/otp'
import {base32} from '@better-auth/utils/base32'
test('enrolling MFA revokes all prior sessions; new login requires TOTP and backup is single-use',async t=>{
 const f=await authFixture(t)
 const headers=await verifiedUser(f)
 const second=await f.post('/sign-in/email',{email:'test@example.com',password})
 const old={cookie:cookies(second)}
 const enabled=await f.post('/two-factor/enable',{password},headers)
 assert.equal(enabled.statusCode,200,enabled.body)
 const code=await createOTP(base32.decode(new URL(enabled.json().totpURI).searchParams.get('secret'))).totp()
 assert.equal((await f.post('/two-factor/verify-totp',{code},headers)).statusCode,200)
 assert.equal((await f.app.inject({url:'/api/auth/get-session',headers:old})).json(),null,'old session must be revoked')
 assert.equal((await f.app.inject({url:'/api/auth/get-session',headers})).json(),null)
 const challenged=await f.post('/sign-in/email',{email:'test@example.com',password})
 assert.equal(challenged.json().twoFactorRedirect,true)
 const challenge={cookie:cookies(challenged)}
 assert.notEqual((await f.post('/two-factor/verify-totp',{code:'000000'},challenge)).statusCode,200)
 const verified=await f.post('/two-factor/verify-backup-code',{code:enabled.json().backupCodes[0]},challenge)
 assert.equal(verified.statusCode,200,verified.body)
 const again=await f.post('/sign-in/email',{email:'test@example.com',password})
 assert.notEqual((await f.post('/two-factor/verify-backup-code',{code:enabled.json().backupCodes[0]},{cookie:cookies(again)})).statusCode,200)
})

test('administrative SDK endpoints also require verified MFA enrollment',async t=>{
 const f=await authFixture(t)
 const headers=await verifiedUser(f)
 f.database.prepare('UPDATE auth_user SET role = ?').run('admin')
 const denied=await f.app.inject({url:'/api/auth/admin/list-users',headers:{origin,...headers}})
 assert.equal(denied.statusCode,403,denied.body)
 assert.equal(denied.json().code,'MFA_SETUP_REQUIRED')
})

test('migrated administrator can set a fresh password without importing its legacy hash',async t=>{
 const f=await authFixture(t)
 f.database.prepare(`INSERT INTO auth_user (id,name,email,emailVerified,createdAt,updatedAt,role,banned,twoFactorEnabled) VALUES (?,?,?,FALSE,?,?,'admin',FALSE,FALSE)`).run('legacy-admin-id','Administrador','migrated@example.com',Date.now(),Date.now())
 const requested=await f.post('/request-password-reset',{email:'migrated@example.com',redirectTo:origin+'/conta/redefinir-senha'})
 assert.equal(requested.statusCode,200,requested.body)
 const token=new URL(f.emails.find(e=>e.kind==='reset').url).pathname.split('/').at(-1)
 const reset=await f.post('/reset-password',{token,newPassword:password})
 assert.equal(reset.statusCode,200,reset.body)
 assert.equal(f.database.prepare('SELECT userId FROM auth_account').get().userId,'legacy-admin-id')
 const denied=await f.post('/sign-in/email',{email:'migrated@example.com',password})
 assert.equal(denied.statusCode,403,'password reset must not verify email implicitly')
 assert.equal(f.emails.at(-1).kind,'verify')
})

test('password changes revoke other sessions even when the client requests otherwise',async t=>{
 const f=await authFixture(t)
 const headers=await verifiedUser(f)
 const another=await f.post('/sign-in/email',{email:'test@example.com',password})
 const changed=await f.post('/change-password',{currentPassword:password,newPassword:'a-changed-password-for-testing',revokeOtherSessions:false},headers)
 assert.equal(changed.statusCode,200,changed.body)
 assert.equal((await f.app.inject({url:'/api/auth/get-session',headers:{cookie:cookies(another)}})).json(),null)
})
