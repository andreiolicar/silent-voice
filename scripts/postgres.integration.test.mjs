import test from 'node:test'
import assert from 'node:assert/strict'
import { randomUUID } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { mkdtemp, rm } from 'node:fs/promises'
import { join } from 'node:path'
import { tmpdir } from 'node:os'
import { createPostgresDatabase } from '../server/db/sql.ts'
import { migratePostgres } from '../server/db/migrate.ts'
import { createDatabase } from '../server/db/database.ts'
import { importSqlite } from '../server/scripts/import-sqlite.ts'
import { createServer } from '../server/app.ts'
import { provisionAdmin } from '../server/auth/password.ts'
import { cookie, origin, validLead } from './helpers/api-fixture.mjs'
const url = process.env.TEST_DATABASE_URL_FILE ? readFileSync(process.env.TEST_DATABASE_URL_FILE,'utf8').trim() : undefined

test('real PostgreSQL: migrations, import, sessions, receipts, filters, concurrency and rollback', { skip: !url }, async t => {
  await migratePostgres(url)
  await migratePostgres(url) // repeat safely
  const db = createPostgresDatabase(url)
  const directory = await mkdtemp(join(tmpdir(),'sv-pg-import-'))
  const email = `neon-${randomUUID()}@example.com`
  const password = 'long-neon-integration-password'
  const sqlite = createDatabase(join(directory,'source.sqlite'))
  const legacyAdmin = await provisionAdmin(sqlite,email,password)
  const legacyId = randomUUID()
  const now = new Date().toISOString()
  sqlite.prepare('INSERT INTO leads (id,name,email,objective,created_at,updated_at) VALUES (?,?,?,?,?,?)').run(legacyId,'Legacy imported contact',email,'Existing lead from SQLite backup',now,now)
  sqlite.prepare('INSERT INTO lead_notes VALUES (?,?,?,?,?)').run(randomUUID(),legacyId,'Existing note',legacyAdmin.id,now)
  sqlite.prepare('INSERT INTO lead_submissions VALUES (?,?,?,?)').run(randomUUID(),'existing-fingerprint',legacyId,now)
  sqlite.close()
  const first = await importSqlite(db,join(directory,'source.sqlite'))
  assert.equal(first.admin_users,1)
  assert.equal(first.leads,1)
  assert.equal(first.lead_notes,1)
  assert.equal(first.lead_submissions,1)
  assert.equal((await importSqlite(db,join(directory,'source.sqlite'))).admin_users,0)
  const config={origin,allowedOrigins:[origin],databasePath:':memory:',sessionSecret:'integration-session-secret-longer-than-32-characters',secureCookies:false,port:0,zaiModel:'unused',chatTimeoutMs:45000,idleTimeoutMs:15000}
  const provider={async *stream(){throw new Error('Must not call LLM')}}
  let app=await createServer({config,database:db,chatProvider:provider})
  const ids=[legacyId]
  t.after(async()=>{
    await app.close()
    for(const id of ids){
      await db.prepare('DELETE FROM lead_notes WHERE lead_id = ?').run(id)
      await db.prepare('DELETE FROM lead_submissions WHERE lead_id = ?').run(id)
      await db.prepare('DELETE FROM leads WHERE id = ?').run(id)
    }
    await db.prepare('DELETE FROM admin_sessions WHERE data LIKE ?').run(`%${email}%`)
    await db.prepare('DELETE FROM admin_users WHERE email = ?').run(email)
    await db.close();await rm(directory,{recursive:true,force:true})
  })
  const csrf=await app.inject('/api/auth/csrf')
  const logged=await app.inject({method:'POST',url:'/api/auth/login',headers:{origin,cookie:cookie(csrf),'x-csrf-token':csrf.json().csrfToken},payload:{email,password}})
  assert.equal(logged.statusCode,200,logged.body)
  const headers={origin,cookie:cookie(logged),'x-csrf-token':logged.json().csrfToken}
  const conflicting = createDatabase(join(directory,'source.sqlite'))
  const rolledBackAdmin = await provisionAdmin(conflicting,`conflict-${randomUUID()}@example.com`,password)
  conflicting.prepare('UPDATE leads SET name = ? WHERE id = ?').run('Conflict must not overwrite',legacyId)
  conflicting.close()
  await assert.rejects(importSqlite(db,join(directory,'source.sqlite')), /Import conflict/)
  assert.equal(await db.prepare('SELECT id FROM admin_users WHERE id = ?').get(rolledBackAdmin.id),undefined)
  assert.equal((await db.prepare('SELECT name FROM leads WHERE id = ?').get(legacyId)).name,'Legacy imported contact')
  const key=randomUUID()
  const request={method:'POST',url:'/api/leads',headers:{origin,'idempotency-key':key},payload:validLead}
  const receipts=await Promise.all([app.inject(request),app.inject(request)])
  assert.deepEqual(receipts.map(r=>r.statusCode).sort(),[200,201])
  assert.equal(receipts[0].json().id,receipts[1].json().id)
  ids.unshift(receipts[0].json().id)
  assert.equal((await app.inject({...request,payload:{...validLead,name:'Different'}})).statusCode,422)
  const list=await app.inject({url:'/api/admin/leads?q=mArIa&status=new',headers})
  assert.equal(list.statusCode,200,list.body)
  assert.ok(list.json().items.some(l=>l.id===ids[0]))
  assert.equal(typeof list.json().total,'number')
  const changes=await Promise.all(['contacted','closed'].map(status=>app.inject({method:'PATCH',url:`/api/admin/leads/${ids[0]}`,headers,payload:{status,version:1}})))
  assert.deepEqual(changes.map(r=>r.statusCode).sort(),[200,409])
  const note=await app.inject({method:'POST',url:`/api/admin/leads/${ids[0]}/notes`,headers,payload:{text:'PostgreSQL validation note'}})
  assert.equal(note.statusCode,201,note.body)
  const detail=(await app.inject({url:`/api/admin/leads/${ids[0]}`,headers})).json()
  assert.equal(detail.notes[0].createdAt,note.json().createdAt)
  assert.equal(detail.notes[0].author,email)
  await app.close();app=await createServer({config,database:db,chatProvider:provider})
  assert.equal((await app.inject({url:'/api/auth/session',headers})).statusCode,200)
  const rollback=randomUUID()
  await assert.rejects(db.transaction(async()=>{
    await db.prepare('INSERT INTO admin_users VALUES (?, ?, ?, ?)').run(rollback,`${rollback}@example.com`,'hash','now')
    throw new Error('forced rollback')
  }).immediate(),/forced rollback/)
  assert.equal(await db.prepare('SELECT id FROM admin_users WHERE id = ?').get(rollback),undefined)
  assert.equal((await app.inject({method:'POST',url:'/api/auth/logout',headers})).statusCode,200)
  assert.equal((await app.inject({url:'/api/auth/session',headers})).statusCode,401)
  assert.equal((await app.inject('/api/health')).statusCode,200)
})
