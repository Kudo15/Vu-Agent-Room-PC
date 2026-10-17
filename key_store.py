"""Environment first; optional local key vault. DPAPI user scope on Windows."""
import base64,ctypes,json,os,tempfile
from pathlib import Path

def dpapi(data,decrypt=False):
    from ctypes import wintypes
    class BLOB(ctypes.Structure):_fields_=[('cbData',wintypes.DWORD),('pbData',ctypes.POINTER(ctypes.c_ubyte))]
    buf=(ctypes.c_ubyte*len(data)).from_buffer_copy(data);src=BLOB(len(data),buf);out=BLOB()
    crypt=ctypes.WinDLL('crypt32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    if decrypt:
        fn=crypt.CryptUnprotectData;fn.argtypes=[ctypes.POINTER(BLOB),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(BLOB)]
        ok=fn(ctypes.byref(src),None,None,None,None,1,ctypes.byref(out))
    else:
        fn=crypt.CryptProtectData;fn.argtypes=[ctypes.POINTER(BLOB),wintypes.LPCWSTR,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(BLOB)]
        ok=fn(ctypes.byref(src),'Vu Agent Room',None,None,None,1,ctypes.byref(out))
    if not ok:raise OSError('Không thể mở/lưu key bằng Windows DPAPI trên tài khoản hiện tại.')
    kernel.LocalFree.argtypes=[ctypes.c_void_p];kernel.LocalFree.restype=ctypes.c_void_p
    try:return ctypes.string_at(out.pbData,out.cbData)
    finally:kernel.LocalFree(out.pbData)

def read_keys(home):
    p=Path(home)/'keys.json'
    if not p.exists():return {}
    doc=json.loads(p.read_text(encoding='utf-8'))
    if doc['format']=='dpapi-user':
        if os.name!='nt':raise ValueError('Kho key Windows cần cùng tài khoản Windows để mở.')
        return json.loads(dpapi(base64.b64decode(doc['payload']),True))
    if doc['format']=='local-0600':return doc['keys']
    raise ValueError('Định dạng kho key không hợp lệ')

def write_keys(home,keys):
    home=Path(home);home.mkdir(parents=True,exist_ok=True)
    if os.name=='nt':doc={'format':'dpapi-user','payload':base64.b64encode(dpapi(json.dumps(keys).encode())).decode()}
    else:doc={'format':'local-0600','keys':keys}
    fd,name=tempfile.mkstemp(prefix='.keys-',dir=home)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(doc,f)
        os.replace(name,home/'keys.json')
        if os.name!='nt':(home/'keys.json').chmod(0o600)
    finally:
        if os.path.exists(name):os.unlink(name)

def resolve_key(home,name):
    value=os.environ.get(name) or read_keys(home).get(name,'')
    if not value:raise ValueError('Chưa có key cho '+name+'. Chạy CONFIGURE.cmd hoặc đặt biến môi trường trên PC.')
    if not isinstance(value,str) or any(x in value for x in ('\r','\n')):raise ValueError('Key không hợp lệ')
    return value
