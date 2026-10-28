import test from 'node:test'
import assert from 'node:assert/strict'
import { mkdtemp, mkdir, writeFile, rm } from 'node:fs/promises'
import { join } from 'node:path'
import { tmpdir } from 'node:os'
import { createServer } from '../src/app.ts'
import { origin } from './helpers/api-fixture.mjs'
const config={origin,databasePath:':memory:',sessionSecret:'test-secret-long-enough-for-session-cookie',secureCookies:false,port:0,zaiModel:'unused',chatTimeoutMs:45000,idleTimeoutMs:15000}
const chatProvider={async *stream(){ yield {type:'delta',text:'test'};yield {type:'done',finishReason:'stop'} }}
test('serves admin SPA and assets without exposing API paths or private files',async t=>{
 const dir=await mkdtemp(join(tmpdir(),'sv-backend-static-'))
 await mkdir(join(dir,'assets'));await mkdir(join(dir,'admin/assets'),{recursive:true});await writeFile(join(dir,'index.html'),'<html>landing shell</html>');await writeFile(join(dir,'admin/index.html'),'<html>admin shell</html>');await writeFile(join(dir,'admin/assets/test.js'),'admin asset');await writeFile(join(dir,'assets','test.js'),'ok');await writeFile(join(dir,'.env'),'private-secret')
 const app=await createServer({config:{...config,frontendPath:dir},chatProvider})
 t.after(async()=>{await app.close();await rm(dir,{recursive:true,force:true})})
 assert.equal((await app.inject('/')).body,'<html>landing shell</html>')
 for(const url of ['/admin','/admin/login','/admin/leads','/conta/redefinir-senha?token=fixture']) assert.equal((await app.inject(url)).body,'<html>admin shell</html>')
 assert.equal((await app.inject('/admin/assets/test.js')).body,'admin asset')
 assert.equal((await app.inject('/assets/test.js')).statusCode,200)
 for(const url of ['/api/unknown','/.env','/assets/../.env']) {const r=await app.inject(url);assert.equal(r.statusCode,404);assert.ok(!r.body.includes('private-secret'))}
})
test('CORS preflight is exact-origin and streamed replies preserve CORS headers',async t=>{
 const app=await createServer({config,chatProvider});t.after(()=>app.close())
 const good=await app.inject({method:'OPTIONS',url:'/api/chat',headers:{origin,'access-control-request-method':'POST','access-control-request-headers':'content-type'}})
 assert.equal(good.statusCode,204);assert.equal(good.headers['access-control-allow-origin'],origin)
 const bad=await app.inject({method:'OPTIONS',url:'/api/chat',headers:{origin:'https://evil.example'}})
 assert.equal(bad.statusCode,403);assert.equal(bad.headers['access-control-allow-origin'],undefined)
 const chat=await app.inject({method:'POST',url:'/api/chat',headers:{origin},payload:{requestId:'cors-test',messages:[{id:'user',role:'user',content:'O que é?'}]}})
 assert.equal(chat.headers['access-control-allow-origin'],origin);assert.match(chat.body,/"type":"done"/)
})
