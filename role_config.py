"""Validated public role settings; no credential values in task snapshots."""
import os,re
from urllib.parse import urlsplit
ROLES=('Coordinator','Worker','Tester','Reviewer')
FIELDS=('adapter','provider','model','effort','profile','codex_path','cli_path','toolsets','auto_approve','base_url','api_key_env','json_mode','max_tokens','token_parameter')
LOCAL_CLI=('codex_cli','hermes_cli','opencode_cli')
def validate_base(value):
    u=urlsplit(value)
    if u.scheme not in ('http','https') or not u.hostname or u.username or u.password or u.query or u.fragment:
        raise ValueError('Base URL không hợp lệ; không chứa key, query hoặc thông tin đăng nhập.')
    if u.scheme=='http' and u.hostname not in ('127.0.0.1','localhost','::1'):raise ValueError('API ngoài localhost phải dùng HTTPS.')
    if u.path.rstrip('/').endswith('/chat/completions'):raise ValueError('Nhập base URL, ví dụ https://provider/v1, không kèm /chat/completions.')
    return value.rstrip('/')
def roles_for(config):
    legacy={'adapter':'codex_cli','provider':'Codex CLI','model':config.get('model') or '', 'effort':config.get('effort') or 'medium','profile':'','codex_path':config.get('codex_path') or '', 'cli_path':'','toolsets':'','auto_approve':False,'base_url':'','api_key_env':'','json_mode':False,'max_tokens':2048,'token_parameter':'max_tokens'}
    result={}
    for role in ROLES:
        raw=config.get('roles',{}).get(role,{})
        if not isinstance(raw,dict):raise ValueError(role+': cấu hình phải là object')
        unknown=set(raw)-set(FIELDS)
        if unknown:raise ValueError(role+': trường không hỗ trợ '+', '.join(sorted(unknown)))
        r={**legacy,**raw}
        for field in ('adapter','provider','model','effort','profile','codex_path','cli_path','toolsets','base_url','api_key_env','token_parameter'):
            if not isinstance(r[field],str) or len(r[field])>2048 or any(c in r[field] for c in ('\n','\r','\0')):raise ValueError(role+': '+field+' không hợp lệ')
        if r['adapter'] not in (*LOCAL_CLI,'openai_compatible'):raise ValueError(role+': adapter chưa hỗ trợ')
        if type(r['auto_approve']) is not bool:raise ValueError(role+': auto_approve phải là boolean')
        if r['toolsets'] and (r['adapter']!='hermes_cli' or not re.fullmatch(r'[A-Za-z0-9_-]+(?:,[A-Za-z0-9_-]+)*',r['toolsets'])):
            raise ValueError(role+': Hermes toolsets phải là danh sách tên cách nhau bằng dấu phẩy')
        if r['effort'] not in ('default','low','medium','high'):raise ValueError(role+': effort không hợp lệ')
        if type(r['max_tokens']) is not int or not 128<=r['max_tokens']<=16384:raise ValueError(role+': max_tokens phải từ 128 đến 16384')
        if type(r['json_mode']) is not bool:raise ValueError(role+': json_mode phải là boolean')
        if r['token_parameter'] not in ('max_tokens','max_completion_tokens'):raise ValueError(role+': token_parameter không hợp lệ')
        if r['adapter']=='openai_compatible':
            r['base_url']=validate_base(r['base_url'])
            if not r['model'].strip():raise ValueError(role+': API cần model ID')
            if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',r['api_key_env']):raise ValueError(role+': cần tên biến key hợp lệ')
            # Not a local project executor; discard inapplicable CLI properties.
            r['profile']='';r['codex_path']='';r['cli_path']='';r['toolsets']='';r['auto_approve']=False
        else:
            r['base_url']='';r['api_key_env']=''
            if r['adapter']=='codex_cli':r['cli_path']='';r['toolsets']='';r['auto_approve']=False
            else:r['codex_path']='';r['profile']=''
            if r['adapter']=='hermes_cli':r['auto_approve']=False
            if r['adapter']=='opencode_cli':r['toolsets']=''
        result[role]=r
    return result

def team_enabled(config):return bool(config.get('agents_enabled',config.get('codex_enabled',False)))
