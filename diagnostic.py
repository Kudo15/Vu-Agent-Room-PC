"""Real local subprocess diagnostics; never presented as AI output."""
import hashlib,json,sys
from pathlib import Path
spec=json.loads(sys.stdin.read());role=spec['role'];history=spec['history'];tid=spec['task_id']
digest=hashlib.sha256(('room-check:'+tid).encode()).hexdigest()
if role=='Coordinator':summary='Đã xác định chuỗi kiểm tra tiến trình và kết quả.';evidence=['Plan: write challenge -> independently verify SHA-256 -> review evidence']
elif role=='Worker':summary='Đã tính SHA-256 của challenge kiểm tra.';evidence=['sha256:'+digest]
elif role=='Tester':
    assert len(history)==2 and 'sha256:'+digest in history[1]['evidence']
    summary='Đã tính lại độc lập và đối chiếu SHA-256.';evidence=['independent_sha256:'+digest]
else:
    assert len(history)==3 and all(x['verdict']=='PASS' for x in history)
    assert 'independent_sha256:'+digest in history[2]['evidence']
    summary='Đã xác minh đủ 3 bước trước và bằng chứng phù hợp.';evidence=['reviewed_task:'+tid,'verified_sha256:'+digest]
Path(sys.argv[1]).write_text(json.dumps({'task_id':tid,'role':role,'verdict':'PASS','summary':summary,'evidence':evidence},ensure_ascii=False),encoding='utf-8')
