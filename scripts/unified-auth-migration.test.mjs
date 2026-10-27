import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {migratePostgres} from '../server/db/migrate.ts'
import {createPostgresDatabase} from '../server/db/sql.ts'
const url=process.env.AUTH_TEST_DATABASE_URL_FILE ? readFileSync(process.env.AUTH_TEST_DATABASE_URL_FILE,'utf8').trim():undefined
test('isolated PostgreSQL migrations preserve admin identity, CRM audit links and never copy password hashes',{skip:!url},async()=>{
 const db=createPostgresDatabase(url)
 try{
  const before=await db.prepare('SELECT id,email,created_at FROM admin_users').all()
  const notes=await db.prepare('SELECT id,author_id FROM lead_notes ORDER BY id').all()
  const leads=await db.prepare('SELECT id,status_updated_by FROM leads ORDER BY id').all()
  await migratePostgres(url);await migratePostgres(url)
  const current=await db.prepare('SELECT id,email,role FROM auth_user').all()
  assert.ok(before.every(o=>current.some(n=>n.id===o.id&&n.email===o.email&&n.role==='admin')))
  assert.deepEqual(await db.prepare('SELECT id,author_id FROM lead_notes ORDER BY id').all(),notes)
  assert.deepEqual(await db.prepare('SELECT id,status_updated_by FROM leads ORDER BY id').all(),leads)
  assert.deepEqual((await db.prepare('SELECT version FROM sv_schema_migrations ORDER BY version').all()).map(r=>r.version),[1,2,3])
  for(const row of before) assert.equal((await db.prepare('SELECT password FROM auth_account WHERE "userId" = ?').all(row.id)).length,0)
 }finally{await db.close()}
})

import {Pool} from 'pg'
import {randomUUID} from 'node:crypto'
test('a failed migration rolls back earlier DDL and migration metadata atomically',{skip:!url},async()=>{
 const pool=new Pool({connectionString:url,max:1})
 const schema='sv_auth_rollback_'+randomUUID().replaceAll('-','')
 try{
  await pool.query(`CREATE SCHEMA ${schema}`)
  await pool.query(`CREATE TABLE ${schema}.auth_user (id TEXT PRIMARY KEY)`)
  const scoped=new URL(url);scoped.searchParams.set('options',`-c search_path=${schema}`)
  await assert.rejects(migratePostgres(scoped.toString()),/already exists/)
  const tables=await pool.query('SELECT tablename FROM pg_tables WHERE schemaname=$1 ORDER BY tablename',[schema])
  assert.deepEqual(tables.rows.map(r=>r.tablename),['auth_user'],'initial application tables and migration metadata must roll back')
 }finally{await pool.query(`DROP SCHEMA IF EXISTS ${schema} CASCADE`);await pool.end()}
})
