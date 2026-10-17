import base64,concurrent.futures,http.client,json,os,sys,tempfile,threading,time,unittest,uuid
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import room

class RoomTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.cfg={'workspace':str(self.home/'project'),'codex_enabled':False,'allow_write':False,'model':'','effort':'medium','codex_path':'','password_salt':'00'*16,'password_hash':room.password_hash('test-room-password','00'*16),'allowed_hosts':[]}
  self.app=room.Room(self.home,self.cfg)
 def tearDown(self):
  self.app.stop.set()
  if self.app.active:room.terminate(self.app.active)
  if self.app.thread.is_alive():self.app.thread.join(5)
  self.tmp.cleanup()
 def task(self):return self.app.create({'request_id':str(uuid.uuid4()),'prompt':'Check local runner','mode':'diagnostic'})
 def wait_done(self,tid,timeout=8):
  end=time.monotonic()+timeout
  while time.monotonic()<end:
   t=self.app.task_detail(tid)['task']
   if t['status'] in room.TERMINAL:return t
   time.sleep(.05)
  self.fail('Task did not finish')
 def test_real_four_processes_and_evidence(self):
  t=self.task();self.app.thread.start();result=self.wait_done(t['id']);self.assertEqual(result['status'],'COMPLETE')
  runs=self.app.task_detail(t['id'])['runs'];self.assertEqual([r['role'] for r in runs],list(room.ROLES));self.assertEqual(len({r['pid'] for r in runs}),4)
  self.assertTrue(all(r['exit_code']==0 and r['verdict']=='PASS' and json.loads(r['evidence']) for r in runs))
 def test_gate_denial_never_runs(self):
  t=self.task()
  with self.app.db() as db:db.execute("UPDATE tasks SET status='WAIT_APPROVAL' WHERE id=?",(t['id'],))
  self.app.thread.start();time.sleep(.4);self.assertEqual(self.app.task_detail(t['id'])['runs'],[])
  self.app.decision(t['id'],'deny');self.assertEqual(self.wait_done(t['id'])['status'],'DENIED');self.assertEqual(self.app.task_detail(t['id'])['runs'],[])
  with self.assertRaises(ValueError):self.app.decision(t['id'],'approve')
 def test_concurrent_approval_is_single_execution(self):
  t=self.task()
  with self.app.db() as db:db.execute("UPDATE tasks SET status='WAIT_APPROVAL' WHERE id=?",(t['id'],))
  with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:list(pool.map(lambda _:self.app.decision(t['id'],'approve'),range(6)))
  self.app.thread.start();self.assertEqual(self.wait_done(t['id'])['status'],'COMPLETE');self.assertEqual(len(self.app.task_detail(t['id'])['runs']),4)
 def test_create_retry_idempotent(self):
  data={'request_id':str(uuid.uuid4()),'prompt':'hello','mode':'diagnostic'};a=self.app.create(data);b=self.app.create(data);self.assertEqual(a['id'],b['id']);self.assertEqual(len(self.app.state()['tasks']),1)
 def test_attachment_reaches_task_and_all_stage_specs(self):
  uploaded=self.app.upload({'name':'brief.txt','data':base64.b64encode('Nội dung chung'.encode()).decode()})
  t=self.app.create({'request_id':str(uuid.uuid4()),'prompt':'','mode':'diagnostic','attachments':[uploaded['id']]})
  message=next(m for m in self.app.state()['messages'] if m['role']=='Bạn')
  self.assertEqual(message['attachments'][0]['name'],'brief.txt')
  with self.app.db() as db:attachments=self.app.task_attachments(db,t['id'])
  self.assertEqual(attachments[0]['extracted'],'Nội dung chung')
  self.assertEqual(Path(attachments[0]['path']).read_text(encoding='utf-8'),'Nội dung chung')
  with self.assertRaises(ValueError):self.app.create({'request_id':str(uuid.uuid4()),'prompt':'again','mode':'diagnostic','attachments':[uploaded['id']]})
  image=self.app.upload({'name':'pasted-image','mime':'image/png','data':base64.b64encode(b'\x89PNG\r\n\x1a\nfixture').decode()})
  self.assertEqual(image['mime'],'image/png')
 def test_incomplete_report_has_next_step(self):
  t=self.task()
  with self.app.db() as db:
   self.app.final_report(db,{**t,'mode':'conversation'},[{'role':'Coordinator','verdict':'FAIL','summary':'Thiếu dữ kiện','evidence':[]}],'FAILED')
  report=[m['text'] for m in self.app.state()['messages'] if m['text'].startswith('KẾT LUẬN CUỐI CÙNG')][-1]
  self.assertIn('Bước tiếp theo',report)
 def test_restart_does_not_replay(self):
  t=self.task();new=room.Room(self.home,self.cfg);self.assertEqual(new.task_detail(t['id'])['task']['status'],'INTERRUPTED');self.assertEqual(new.task_detail(t['id'])['runs'],[])
 def test_codex_disabled_is_rejected(self):
  with self.assertRaises(ValueError):self.app.create({'request_id':str(uuid.uuid4()),'prompt':'do work','mode':'codex'})
 def test_zero_exit_without_json_is_failure(self):
  fake=self.home/'fake';fake.mkdir();(fake/'diagnostic.py').write_text('print("not structured output")')
  t=self.task()
  with patch.object(room,'ROOT',fake):
   self.app.thread.start();self.assertEqual(self.wait_done(t['id'])['status'],'FAILED')
  self.assertEqual(len(self.app.task_detail(t['id'])['runs']),1)
 def test_cancel_running_child(self):
  fake=self.home/'fake';fake.mkdir();(fake/'diagnostic.py').write_text('import time; time.sleep(20)')
  t=self.task()
  with patch.object(room,'ROOT',fake):
   self.app.thread.start();end=time.monotonic()+5
   while not self.app.active and time.monotonic()<end:time.sleep(.05)
   proc=self.app.active;self.assertIsNotNone(proc);self.app.cancel(t['id'])
   end=time.monotonic()+5
   while proc.poll() is None and time.monotonic()<end:time.sleep(.05)
   self.assertIsNotNone(proc.poll());self.assertEqual(self.wait_done(t['id'])['status'],'CANCELLED')
 def test_deadline_kills_child(self):
  fake=self.home/'fake';fake.mkdir();(fake/'diagnostic.py').write_text('import time; time.sleep(20)')
  t=self.task()
  with self.app.db() as db:db.execute("UPDATE tasks SET status='RUNNING' WHERE id=?",(t['id'],))
  with patch.object(room,'ROOT',fake):r=self.app.run_stage(t,'Coordinator',json.loads(t['config']),[],time.monotonic()-.1)
  self.assertEqual(r['verdict'],'FAIL');self.assertIn('thời gian',r['summary'])
 def test_schema_and_role_fail_closed(self):
  good={'task_id':'a','role':'Tester','verdict':'PASS','summary':'ok','evidence':['ran checks']};room.validate_result(good,'a','Tester')
  for r in ({**good,'task_id':'b'},{**good,'evidence':[]},{**good,'verdict':'MAYBE'},{**good,'role':'Worker'}):
   with self.assertRaises(ValueError):room.validate_result(r,'a','Tester')
 def test_codex_adapter_with_fixture_cli(self):
  if os.name=='nt':self.skipTest('Fixture executable is POSIX; native Windows validation is separate')
  exe=self.home/'codex-fixture'
  exe.write_text('#!'+sys.executable+'\n'+"import sys,json\nspec=json.loads(sys.stdin.read().split('\\n',1)[1])\nargs=sys.argv[1:]\nassert args[:3]==['-a','never','exec']\nrole=spec['role']\nexpected='workspace-write' if role=='Worker' else 'read-only'\nassert args[args.index('--sandbox')+1]==expected\nresult={'task_id':spec['task_id'],'role':role,'verdict':'PASS','summary':'fixture only','evidence':['sandbox:'+expected]}\nopen(args[args.index('-o')+1],'w').write(json.dumps(result))\n")
  exe.chmod(0o700);self.cfg.update(codex_enabled=True,codex_path=str(exe),allow_write=True,model='fixture-model')
  t=self.app.create({'request_id':str(uuid.uuid4()),'prompt':'literal $(do-not-execute); & test','mode':'codex'})
  self.app.decision(t['id'],'approve');self.app.thread.start();self.assertEqual(self.wait_done(t['id'])['status'],'COMPLETE')
  self.assertEqual(len(self.app.task_detail(t['id'])['runs']),4)
 def test_redaction(self):
  result=room.redact('api_key=verysecret Authorization: Bearer abc123 password="hidden" sk-123456789abcdefgh')
  for s in ('verysecret','abc123','hidden','sk-123456789abcdefgh'):self.assertNotIn(s,result)

class HTTPTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();cfg={'workspace':self.tmp.name,'codex_enabled':False,'allow_write':False,'password_salt':'00'*16,'password_hash':room.password_hash('test-room-password','00'*16)}
  self.app=room.Room(Path(self.tmp.name),cfg);self.server=room.Server(('127.0.0.1',0),room.Handler);self.server.room=self.app;self.port=self.server.server_port;self.host=f'127.0.0.1:{self.port}';cfg['allowed_hosts']=[self.host]
  self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.cookie='';self.csrf=''
 def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join();self.tmp.cleanup()
 def req(self,path,body=None,headers=None):
  c=http.client.HTTPConnection('127.0.0.1',self.port,timeout=5);hs={'Host':self.host,'Origin':'http://'+self.host,'Cookie':self.cookie,'X-CSRF-Token':self.csrf,'Content-Type':'application/json',**(headers or {})}
  c.request('POST' if body is not None else 'GET',path,json.dumps(body) if body is not None else None,hs);r=c.getresponse();data=r.read();ret=(r.status,dict(r.getheaders()),data);c.close();return ret
 def login(self):
  code,headers,raw=self.req('/api/login',{'password':'test-room-password'});self.assertEqual(code,200);self.cookie=headers['Set-Cookie'].split(';')[0];self.csrf=json.loads(raw)['csrf'];return headers
 def test_auth_csrf_origin_and_cookie(self):
  self.assertEqual(self.req('/api/state')[0],401);headers=self.login();self.assertIn('HttpOnly',headers['Set-Cookie']);self.assertIn('SameSite=Strict',headers['Set-Cookie']);self.assertEqual(self.req('/api/state')[0],200)
  payload={'request_id':str(uuid.uuid4()),'prompt':'do diagnostic','mode':'diagnostic'}
  self.assertEqual(self.req('/api/tasks',payload,{'X-CSRF-Token':''})[0],403)
  self.assertEqual(self.req('/api/tasks',payload,{'Origin':'https://evil.test'})[0],403)
  self.assertEqual(self.req('/api/tasks',payload)[0],200)
  self.assertEqual(self.req('/api/logout',{})[0],200);self.assertEqual(self.req('/api/state')[0],401)
 def test_host_and_private_files(self):
  self.assertEqual(self.req('/',headers={'Host':'evil.test'})[0],403)
  for path in ('/data/config.json','/../room.py','/data/room.sqlite3'):self.assertEqual(self.req(path)[0],404)
 def test_bad_password_and_rate_limit(self):
  for i in range(8):self.assertEqual(self.req('/api/login',{'password':'wrong'})[0],401)
  self.assertEqual(self.req('/api/login',{'password':'wrong'})[0],429)
 def test_http_task_decision_idempotency(self):
  self.login();payload={'request_id':str(uuid.uuid4()),'prompt':'test','mode':'diagnostic'}
  a=json.loads(self.req('/api/tasks',payload)[2]);b=json.loads(self.req('/api/tasks',payload)[2]);self.assertEqual(a['id'],b['id'])
  with self.app.db() as db:db.execute("UPDATE tasks SET status='WAIT_APPROVAL' WHERE id=?",(a['id'],))
  p='/api/tasks/'+a['id']+'/decision';self.assertEqual(self.req(p,{'choice':'deny'})[0],200);self.assertEqual(self.req(p,{'choice':'approve'})[0],400)
 def test_upload_requires_login_and_exposes_only_bound_file(self):
  payload={'name':'note.txt','data':base64.b64encode(b'hello all roles').decode()}
  self.assertEqual(self.req('/api/attachments',payload)[0],401)
  self.login();uploaded=json.loads(self.req('/api/attachments',payload)[2]);url='/api/attachments/'+uploaded['id']
  self.assertEqual(self.req(url)[0],400)
  task=json.loads(self.req('/api/tasks',{'request_id':str(uuid.uuid4()),'prompt':'','mode':'diagnostic','attachments':[uploaded['id']]})[2])
  self.assertEqual(self.req(url)[2],b'hello all roles')
  self.assertEqual(json.loads(self.req('/api/state')[2])['messages'][0]['attachments'][0]['id'],uploaded['id'])
if __name__=='__main__':unittest.main()
