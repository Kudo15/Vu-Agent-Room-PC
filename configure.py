"""Interactive local-only configuration. Never uploads credentials."""
import argparse,getpass,json,os,secrets,shutil,sys
from pathlib import Path
from urllib.parse import urlparse
from room import ROOT,password_hash
from role_config import ROLES,roles_for,team_enabled,validate_base
from key_store import read_keys,write_keys

def native_codex():
    p=shutil.which('codex.exe' if os.name=='nt' else 'codex')
    if p:return p
    if os.name=='nt':
        roots=[Path(os.getenv('APPDATA',''))/'npm/node_modules/@openai',Path(os.getenv('LOCALAPPDATA',''))/'Programs']
        for root in roots:
            if root.is_dir():
                matches=list(root.glob('codex*/**/codex.exe'))
                if matches:return str(matches[0])
    return ''

def native_cli(name):
    found=shutil.which(name+'.exe' if os.name=='nt' else name)
    if found:return found
    if os.name=='nt':
        roots=[Path(os.getenv('LOCALAPPDATA',''))/name/'bin',Path.home()/('.'+name)/'bin',Path.home()/'.local'/'bin',Path.home()/'.bun'/'bin']
        for root in roots:
            candidate=root/(name+'.exe')
            if candidate.is_file():return str(candidate)
    return ''

def ask(label,default=''):
    value=input(label+(' ['+str(default)+']' if default!='' else '')+': ').strip()
    return '' if value=='-' else (value or default)

def configure_roles(cfg,home):
    print('\n=== MODEL RIENG CHO TUNG VAI TRO ===')
    print('Enter giu gia tri; nhap - de xoa model/profile. API truc tiep khong co tool/file/shell.')
    if ask('Bat doi agent? y/n','y' if team_enabled(cfg) else 'n').lower()!='y':
        cfg['agents_enabled']=False;cfg['codex_enabled']=False;return
    previous=roles_for(cfg);updated={};keys=None;pending_keys={}
    for role in ROLES:
        old=previous[role];print('\n--- '+role+' ---')
        choices={'1':'codex_cli','2':'openai_compatible','3':'hermes_cli','4':'opencode_cli'}
        choice=ask('Adapter: 1=Codex CLI, 2=API OpenAI-compatible, 3=Hermes CLI, 4=OpenCode CLI',next((k for k,v in choices.items() if v==old['adapter']),'1'))
        if choice not in choices:raise SystemExit('Adapter khong hop le. Chua luu cau hinh.')
        adapter=choices[choice]
        changed=adapter!=old['adapter'];r={**old,'adapter':adapter}
        if adapter=='codex_cli':
            r['provider']=ask('Nhan provider (chi la ten hien thi)','Codex CLI' if changed else old['provider'])
            found=(old['codex_path'] if not changed else '') or cfg.get('codex_path') or native_codex()
            exe=ask('Duong dan codex.exe goc',found).strip('"')
            if not exe or not Path(exe).is_file() or (os.name=='nt' and Path(exe).suffix.lower()!='.exe'):
                raise SystemExit('Can executable Codex goc. Khong dung .cmd/.bat. Chua luu.')
            r['codex_path']=str(Path(exe).resolve())
            r['profile']=ask('Codex profile (bo trong = cau hinh CLI hien tai)','' if changed else old['profile'])
            r['model']=ask('Model ID (bo trong = mac dinh CLI)','' if changed else old['model'])
            r['effort']=ask('Effort: default/low/medium/high','medium' if changed else old['effort'])
        elif adapter in ('hermes_cli','opencode_cli'):
            name='hermes' if adapter=='hermes_cli' else 'opencode'
            r['provider']=ask('Nhan hien thi provider/harness',name.title()+' CLI' if changed else old['provider'])
            exe=ask('Duong dan '+name+' executable goc',(old['cli_path'] if not changed else '') or native_cli(name)).strip('"')
            if not exe or not Path(exe).is_file() or (os.name=='nt' and Path(exe).suffix.lower()!='.exe'):
                raise SystemExit('Can executable '+name+' goc. Khong dung .cmd/.bat. Chua luu.')
            r['cli_path']=str(Path(exe).resolve())
            r['model']=ask('Model ID (bo trong = mac dinh CLI)','' if changed else old['model'])
            r['effort']='default'
            if adapter=='hermes_cli':
                r['toolsets']=ask('Hermes toolsets (Enter giu mac dinh CLI; vd file,terminal,web)','' if changed else old['toolsets'])
                print('Hermes tu quan ly phe duyet cong cu theo cau hinh cua no. Room khong tu nang quyen.')
            else:
                r['auto_approve']=ask('OpenCode: tu duyet quyen chua bi deny sau khi duyet task? y/n','n' if changed else ('y' if old['auto_approve'] else 'n')).lower()=='y'
                print('OpenCode --auto co the chay lenh voi quyen tai khoan Windows; worktree khong phai sandbox.')
        else:
            print('Chi nhan task va ket qua cac vai tro truoc; KHONG tu doc/sua project hay chay test.')
            r['provider']=ask('Ten provider','API provider' if changed else old['provider'])
            r['base_url']=validate_base(ask('Base URL (thuong ket thuc /v1)','' if changed else old['base_url']))
            r['model']=ask('Model ID chinh xac','' if changed else old['model'])
            r['effort']=ask('Effort: default=khong gui, hoac low/medium/high','default' if changed else old['effort'])
            r['json_mode']=ask('Provider ho tro JSON mode? y/n','n' if changed else ('y' if old['json_mode'] else 'n')).lower()=='y'
            r['max_tokens']=int(ask('Gioi han output token (128-16384)',2048 if changed else old['max_tokens']))
            r['token_parameter']=ask('Ten tham so gioi han token','max_tokens' if changed else old['token_parameter'])
            r['api_key_env']=ask('Ten bien/ref key (khong nhap key o day)','ROOM_'+role.upper()+'_KEY' if changed else old['api_key_env'])
            if os.environ.get(r['api_key_env']):print('Bien moi truong da co key; bien nay duoc uu tien.')
            print('Co the nhap key an de luu rieng tren PC, hoac Enter de dung key/ENV cu.')
            print('Windows: DPAPI theo tai khoan. Linux: tep rieng quyen 0600.')
            key=getpass.getpass('API key (an, khong ghi vao config.json): ')
            if key:pending_keys[r['api_key_env']]=key
        updated[role]=r
    cfgnew={**cfg,'roles':updated,'agents_enabled':True,'codex_enabled':True}
    cfgnew['roles']=roles_for(cfgnew)
    if pending_keys:
        keys=read_keys(home);keys.update(pending_keys);write_keys(home,keys)
    cfg.update(cfgnew)
    print('\nDA CHON (co hieu luc sau khi khoi dong lai):')
    for role,r in cfg['roles'].items():print(role+' | '+r['adapter']+' | '+r['provider']+' | '+(r['model'] or '(CLI default)')+' | '+r['effort'])

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--if-needed',action='store_true');ap.add_argument('--roles-only',action='store_true');args=ap.parse_args()
    home=ROOT/'data';home.mkdir(exist_ok=True);path=home/'config.json'
    if args.if_needed and path.exists():return
    old=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    if args.roles_only:
        if not old:raise SystemExit('Chay START.cmd de tao cau hinh truoc.')
        configure_roles(old,home)
        temp=path.with_suffix('.tmp');temp.write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(temp,path)
        if os.name!='nt':path.chmod(0o600)
        print('Da luu cau hinh tung vai tro. Bam Cai dat Room > Khoi dong lai Room tren trang.');return
    print('VU AGENT ROOM - cau hinh tren PC. Kiem tra ket noi khong can key; API truc tiep can key provider.\nMat khau bao ve room, tach biet voi ChatGPT.')
    cfg={'port':8787,'allowed_hosts':['127.0.0.1:8787','localhost:8787'],'workspace':str(home/'workspace'),'codex_enabled':False,'allow_write':False,'codex_path':'','model':'','effort':'medium',**old}
    if not old or input('Doi mat khau? [y/N]: ').strip().lower()=='y':
        while True:
            pw=getpass.getpass('Mat khau room (it nhat 12 ky tu): ')
            if len(pw)>=12 and pw==getpass.getpass('Nhap lai: '):break
            print('Mat khau ngan hoac khong khop. Thu lai.')
        cfg['password_salt']=secrets.token_hex(16);cfg['password_hash']=password_hash(pw,cfg['password_salt'])
    print('Workspace hien tai: '+cfg['workspace'])
    workspace=input('Thu muc project (Enter de giu): ').strip().strip('"')
    if workspace:cfg['workspace']=str(Path(workspace).resolve())
    Path(cfg['workspace']).mkdir(parents=True,exist_ok=True)
    print('URL Tailscale HTTPS la URL hien sau khi chay tailscale serve. Co the bo qua va cau hinh lai sau.')
    phone=input('URL HTTPS dien thoai (Enter de giu/bo qua): ').strip()
    if phone:
        u=urlparse(phone)
        if u.scheme!='https' or not u.hostname or not u.hostname.endswith('.ts.net') or u.username or u.password or u.path not in ('','/'):
            raise SystemExit('Can URL goc https://ten-may.ten-tailnet.ts.net[:port]')
        cfg['allowed_hosts']=list(dict.fromkeys(['127.0.0.1:8787','localhost:8787',u.netloc.lower()]))
        cfg['phone_url']=phone.rstrip('/')
    configure_roles(cfg,home)
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(temp,path)
    if os.name!='nt':path.chmod(0o600)
    print('Da luu. Bam Cai dat Room > Khoi dong lai Room tren trang; neu Room chua chay thi mo START.cmd.')
if __name__=='__main__':main()
