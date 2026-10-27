import test from 'node:test'
import assert from 'node:assert/strict'
import { randomUUID } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { Pool } from 'pg'
import { createOTP } from '@better-auth/utils/otp'
import { base32 } from '@better-auth/utils/base32'
import { createPostgresDatabase } from '../server/db/sql.ts'
import { migratePostgres } from '../server/db/migrate.ts'
import { createAuth } from '../server/auth/better-auth.ts'
import { createServer } from '../server/app.ts'
import { origin, validLead } from './helpers/api-fixture.mjs'
const url = process.env.TEST_DATABASE_URL_FILE ? readFileSync(process.env.TEST_DATABASE_URL_FILE,'utf8').trim() : undefined
const cookies = r => (r.headers['set-cookie'] || []).map(c=>c.split(';')[0]).join('; ')

test('real PostgreSQL: official auth, MFA, durable sessions, CRM concurrency and rollback', { skip: !url }, async t => {
 await migratePostgres(url)
 await migratePostgres(url)
 const db=createPostgresDatabase(url)
 const connection=new URL(url)
 if(connection.searchParams.get('sslmode')==='require')connection.searchParams.set('sslmode','verify-full')
 const pool=new Pool({connectionString:connection.toString(),max:2})
 const config={origin,allowedOrigins:[origin],databasePath:':memory:',sessionSecret:'integration-session-secret-longer-than-32-characters',secureCookies:false,port:0,zaiModel:'unused',chatTimeoutMs:45000,idleTimeoutMs:15000}
 const emails=[]
 const auth=createAuth(config,pool,async message=>{emails.push(message)})
 const provider={async *stream(){throw new Error('Must not call LLM')}}
 let app=await createServer({config,database:db,auth,chatProvider:provider})
 const email=`auth-${randomUUID()}@example.com`
 const password='long-postgres-integration-password'
 let userId
 const ids=[]
 t.after(async()=>{
  await app.close()
  for(const id of ids){
   await db.prepare('DELETE FROM lead_notes WHERE lead_id = ?').run(id)
   await db.prepare('DELETE FROM lead_submissions WHERE lead_id = ?').run(id)
   await db.prepare('DELETE FROM leads WHERE id = ?').run(id)
  }
  if(userId) await pool.query('DELETE FROM auth_user WHERE id=$1',[userId])
  await db.close(); await pool.end()
 })
 const post=(path,payload,headers={})=>app.inject({method:'POST',url:'/api/auth'+path,headers:{origin,...headers},payload})
 const signup=await post('/sign-up/email',{name:'Integration Admin',email,password})
 assert.equal(signup.statusCode,200,signup.body)
 userId=signup.json().user.id
 assert.equal(signup.json().user.role,'user')
 assert.equal((await post('/sign-in/email',{email,password})).statusCode,403)
 const link=new URL(emails.find(e=>e.kind==='verify').url)
 assert.equal((await app.inject({url:link.pathname+link.search,headers:{origin}})).statusCode,302)
 await pool.query("UPDATE auth_user SET role='admin' WHERE id=$1",[userId])
 const login=await post('/sign-in/email',{email,password})
 const incomplete={cookie:cookies(login)}
 assert.equal((await app.inject({url:'/api/admin/leads',headers:{origin,...incomplete}})).json().code,'MFA_SETUP_REQUIRED')
 const setup=await post('/two-factor/enable',{password},incomplete)
 assert.equal(setup.statusCode,200,setup.body)
 const code=await createOTP(base32.decode(new URL(setup.json().totpURI).searchParams.get('secret'))).totp()
 assert.equal((await post('/two-factor/verify-totp',{code},incomplete)).statusCode,200)
 assert.equal((await app.inject({url:'/api/auth/get-session',headers:incomplete})).json(),null)
 const challenge=await post('/sign-in/email',{email,password})
 assert.equal(challenge.json().twoFactorRedirect,true)
 const verified=await post('/two-factor/verify-backup-code',{code:setup.json().backupCodes[0]},{cookie:cookies(challenge)})
 assert.equal(verified.statusCode,200,verified.body)
 const headers={origin,cookie:cookies(verified)}
 const key=randomUUID()
 const request={method:'POST',url:'/api/leads',headers:{origin,'idempotency-key':key},payload:validLead}
 const receipts=await Promise.all([app.inject(request),app.inject(request)])
 assert.deepEqual(receipts.map(r=>r.statusCode).sort(),[200,201])
 assert.equal(receipts[0].json().id,receipts[1].json().id)
 ids.push(receipts[0].json().id)
 assert.equal((await app.inject({...request,payload:{...validLead,name:'Different'}})).statusCode,422)
 const list=await app.inject({url:'/api/admin/leads?q=mArIa&status=new',headers})
 assert.equal(list.statusCode,200,list.body)
 assert.ok(list.json().items.some(l=>l.id===ids[0]))
 const changes=await Promise.all(['contacted','closed'].map(status=>app.inject({method:'PATCH',url:`/api/admin/leads/${ids[0]}`,headers,payload:{status,version:1}})))
 assert.deepEqual(changes.map(r=>r.statusCode).sort(),[200,409])
 const note=await app.inject({method:'POST',url:`/api/admin/leads/${ids[0]}/notes`,headers,payload:{text:'PostgreSQL validation note'}})
 assert.equal(note.statusCode,201,note.body)
 const detail=(await app.inject({url:`/api/admin/leads/${ids[0]}`,headers})).json()
 assert.equal(detail.notes[0].author,email)
 await app.close(); app=await createServer({config,database:db,auth,chatProvider:provider})
 assert.equal((await app.inject({url:'/api/auth/get-session',headers})).json().user.id,userId)
 const rollback=randomUUID()
 await assert.rejects(db.transaction(async()=>{
  await db.prepare('INSERT INTO admin_users VALUES (?, ?, ?, ?)').run(rollback,`${rollback}@example.com`,'unused-legacy-hash','now')
  throw new Error('forced rollback')
 }).immediate(),/forced rollback/)
 assert.equal(await db.prepare('SELECT id FROM admin_users WHERE id = ?').get(rollback),undefined)
 assert.equal((await post('/sign-out',{},headers)).statusCode,200)
 assert.equal((await app.inject({url:'/api/auth/get-session',headers})).json(),null)
 assert.equal((await app.inject('/api/health')).statusCode,200)
})
