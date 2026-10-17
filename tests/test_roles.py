import base64,concurrent.futures,contextlib,json,os,sys,tempfile,threading,time,unittest,uuid
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import room,api_agent
from role_config import roles_for,validate_base
from key_store import write_keys,resolve_key

SECRET='fixture-key-do-not-persist'
class Provider(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_POST(self):
  body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));self.server.calls.append((self.path,self.headers.get('Authorization'),body))
  mode=self.server.mode
  if mode=='redirect':self.send_response(302);self.send_header('Location',self.server.url+'/must-not-follow');self.end_headers();return
  if mode=='error':self.send_response(429);self.end_headers();self.wfile.write(('error '+SECRET).encode());return
  user_content=body['messages'][1]['content'];spec=json.loads(user_content[0]['text'] if isinstance(user_content,list) else user_content);r={'task_id':spec['task_id'],'role':spec['role'],'verdict':'PASS','summary':'fixture '+SECRET,'evidence':['fixture evidence']}
  if mode=='wrong_role':r['role']='Intruder'
  content='not json' if mode=='invalid_json' else json.dumps(r)
  data={'model':'reported-'+body['model'],'choices':[{'finish_reason':'length' if mode=='truncated' else 'stop','message':{'content':content}}],'usage':{'prompt_tokens':10,'completion_tokens':20,'total_tokens':30}}
  self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(data).encode())

class RoleTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.cfg={'workspace':str(self.home/'project'),'codex_enabled':True,'allow_write':False,'model':'legacy','effort':'medium','codex_path':''}
  self.provider=ThreadingHTTPServer(('127.0.0.1',0),Provider);self.provider.mode='normal';self.provider.calls=[];self.provider.url=f'http://127.0.0.1:{self.provider.server_port}'
  self.pt=threading.Thread(target=self.provider.serve_forever,daemon=True);self.pt.start();self.app=None
 def tearDown(self):
  if self.app:
   self.app.stop.set()
   if self.app.active:room.terminate(self.app.active)
   if self.app.thread.is_alive():self.app.thread.join(5)
  self.provider.shutdown();self.provider.server_close();self.pt.join();self.tmp.cleanup()
 def api_settings(self,model='fixture-api'):
  return {'adapter':'openai_compatible','provider':'Fixture provider','base_url':self.provider.url+'/v1','api_key_env':'ROOM_TEST_KEY','model':model,'effort':'default','profile':'','codex_path':'','json_mode':False,'max_tokens':512,'token_parameter':'max_tokens'}
 def spec(self):return {'task_id':'abc','role':'Coordinator','task':'text analysis','history':[]}
 def wait(self,tid):
  until=time.monotonic()+8
  while time.monotonic()<until:
   t=self.app.task_detail(tid)['task']
   if t['status'] in room.TERMINAL:return t
   time.sleep(.05)
  self.fail('Timeout')
 def fixture_cli(self):
  exe=self.home/'fixture-cli'
  exe.write_text('#!'+sys.executable+'\n'+'''import sys,json
spec=json.loads(sys.stdin.read().split('\\n',1)[1]);a=sys.argv[1:]
r={'task_id':spec['task_id'],'role':spec['role'],'verdict':'PASS','summary':'fixture CLI','evidence':['argv:'+json.dumps(a)]}
open(a[a.index('-o')+1],'w').write(json.dumps(r))
''');exe.chmod(0o700);return str(exe)
 def test_legacy_global_mapping_and_no_mutation(self):
  r=roles_for(self.cfg);self.assertEqual(len(r),4);self.assertTrue(all(x['model']=='legacy' for x in r.values()));self.assertNotIn('roles',self.cfg)
 def test_per_role_cli_argv_and_snapshot(self):
  if os.name=='nt':self.skipTest('POSIX fixture only')
  exe=self.fixture_cli();settings=roles_for(self.cfg)
  for i,role in enumerate(room.ROLES):settings[role].update(codex_path=exe,model='m'+str(i),profile='p'+str(i),effort=['low','medium','high','default'][i])
  self.cfg['roles']=settings;self.app=room.Room(self.home,self.cfg)
  task=self.app.create({'request_id':str(uuid.uuid4()),'prompt':'work','mode':'agents'})
  self.cfg['roles']['Worker']['model']='changed-after-create'
  self.app.decision(task['id'],'approve');self.app.thread.start();self.assertEqual(self.wait(task['id'])['status'],'COMPLETE')
  for i,r in enumerate(self.app.task_detail(task['id'])['runs']):
   args=json.loads(json.loads(r['evidence'])[0][5:]);self.assertEqual(args[args.index('--model')+1],'m'+str(i));self.assertEqual(args[args.index('--profile')+1],'p'+str(i))
   self.assertEqual(r['requested_model'],'m'+str(i));self.assertEqual(r['profile'],'p'+str(i))
   if i==3:self.assertNotIn('-c',args)
 def test_api_parameters_and_exact_secret_scrub(self):
  settings=self.api_settings();result,meta=api_agent.execute(self.spec(),settings,SECRET)
  self.assertNotIn(SECRET,json.dumps(result));self.assertEqual(meta['usage']['total_tokens'],30)
  path,auth,body=self.provider.calls[-1];self.assertEqual(path,'/v1/chat/completions');self.assertEqual(auth,'Bearer '+SECRET)
  self.assertNotIn('reasoning_effort',body);self.assertNotIn('response_format',body)
  settings.update(effort='high',json_mode=True,token_parameter='max_completion_tokens')
  api_agent.execute(self.spec(),settings,SECRET);body=self.provider.calls[-1][2];self.assertEqual(body['reasoning_effort'],'high');self.assertEqual(body['response_format'],{'type':'json_object'});self.assertEqual(body['max_completion_tokens'],512);self.assertNotIn('max_tokens',body)
 def test_api_receives_image_for_each_role(self):
  image=self.home/'sample.png';image.write_bytes(b'\x89PNG\r\n\x1a\nfixture')
  spec={**self.spec(),'attachments':[{'id':'x','name':'sample.png','mime':'image/png','size':image.stat().st_size,'path':str(image),'extracted':None}]}
  for role in room.ROLES:
   api_agent.execute({**spec,'role':role},self.api_settings(),SECRET)
   content=self.provider.calls[-1][2]['messages'][1]['content']
   self.assertEqual(content[1]['type'],'image_url')
   self.assertTrue(content[1]['image_url']['url'].startswith('data:image/png;base64,'))
 def test_api_no_redirect_or_silent_retry(self):
  self.provider.mode='redirect'
  with self.assertRaises(RuntimeError):api_agent.execute(self.spec(),self.api_settings(),SECRET)
  self.assertEqual(len(self.provider.calls),1)
 def test_api_bad_outputs_fail_closed(self):
  for mode in ('wrong_role','invalid_json','truncated'):
   self.provider.mode=mode
   with self.assertRaises(ValueError):api_agent.execute(self.spec(),self.api_settings(),SECRET)
 def test_api_http_error_does_not_leak_body(self):
  self.provider.mode='error'
  with self.assertRaises(RuntimeError) as exc:api_agent.execute(self.spec(),self.api_settings(),SECRET)
  self.assertIn('429',str(exc.exception));self.assertNotIn(SECRET,str(exc.exception));self.assertEqual(len(self.provider.calls),1)
 def test_mixed_api_cli_pipeline_and_metadata(self):
  if os.name=='nt':self.skipTest('POSIX fixture only')
  settings=roles_for(self.cfg);exe=self.fixture_cli()
  for r in settings.values():r['codex_path']=exe
  for role in ('Coordinator','Reviewer'):settings[role]=self.api_settings('api-'+role)
  self.cfg['roles']=settings;write_keys(self.home,{'ROOM_TEST_KEY':SECRET});self.app=room.Room(self.home,self.cfg)
  t=self.app.create({'request_id':str(uuid.uuid4()),'prompt':'text review with fixture','mode':'agents'});self.assertNotIn(SECRET,json.dumps(t));self.app.decision(t['id'],'approve');self.app.thread.start();self.assertEqual(self.wait(t['id'])['status'],'COMPLETE')
  detail=self.app.task_detail(t['id']);self.assertNotIn(SECRET,json.dumps(detail));self.assertNotIn(SECRET,json.dumps(self.app.state()))
  self.assertEqual([r['adapter'] for r in detail['runs']],['openai_compatible','codex_cli','codex_cli','openai_compatible'])
  self.assertEqual(detail['runs'][0]['reported_model'],'reported-api-Coordinator');self.assertEqual(len(self.provider.calls),2)
 def test_missing_key_rejects_before_queue(self):
  self.cfg['roles']={r:self.api_settings() for r in room.ROLES};self.app=room.Room(self.home,self.cfg)
  with patch.dict(os.environ,{},clear=True):
   with self.assertRaises(ValueError):self.app.create({'request_id':str(uuid.uuid4()),'prompt':'work','mode':'agents'})
  self.assertEqual(len(self.app.state()['tasks']),0)
 def test_private_key_store_and_env_priority(self):
  write_keys(self.home,{'ROOM_TEST_KEY':SECRET})
  with patch.dict(os.environ,{},clear=True):self.assertEqual(resolve_key(self.home,'ROOM_TEST_KEY'),SECRET)
  with patch.dict(os.environ,{'ROOM_TEST_KEY':'environment-value'}):self.assertEqual(resolve_key(self.home,'ROOM_TEST_KEY'),'environment-value')
  if os.name!='nt':self.assertEqual((self.home/'keys.json').stat().st_mode&0o777,0o600)
 def test_endpoint_and_config_validation(self):
  for url in ('http://example.com/v1','https://user:secret@example.com/v1','https://example.com/v1?key=x','https://example.com/v1/chat/completions','file:///tmp/x'):
   with self.assertRaises(ValueError):validate_base(url)
  for bad in ({'adapter':'hermes'},{'api_key':'secret'},{'effort':'ultra'},{'max_tokens':-1}):
   with self.assertRaises(ValueError):roles_for({**self.cfg,'roles':{'Worker':bad}})
 def test_runs_migration_idempotent(self):
  self.app=room.Room(self.home,self.cfg);again=room.Room(self.home,self.cfg)
  with again.db() as db:
   cols=[r[1] for r in db.execute('PRAGMA table_info(runs)')]
  for c in ('adapter','provider','base_url','profile','reported_model','usage'):self.assertEqual(cols.count(c),1)
if __name__=='__main__':unittest.main()
