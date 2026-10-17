"""Parse one-shot Hermes and OpenCode CLI output without accepting tool chatter as a result."""
import json


def _object(text):
    value=text.strip()
    if value.startswith('```'):
        lines=value.splitlines()
        if len(lines)<3 or not lines[-1].strip()=='```':raise ValueError('CLI không trả JSON thuần')
        value='\n'.join(lines[1:-1]).strip()
    return json.loads(value)


def parse_output(adapter,raw):
    text=raw.decode('utf-8',errors='replace')
    if adapter=='hermes_cli':
        events=[]
        for line in text.splitlines():
            try:event=json.loads(line)
            except json.JSONDecodeError:continue
            if isinstance(event,dict) and event.get('type') in ('result','system'):events.append(event)
        finals=[event for event in events if event.get('type')=='result']
        if finals:
            last=finals[-1]
            model=next((e.get('model') for e in events if e.get('type')=='system' and e.get('model')),None)
            if last.get('exit_code')!=0:
                error=str(last.get('error') or 'lượt chạy không hoàn tất').strip()[:500]
                identity=f'model {str(model)[:100]}, phiên {str(last.get("session_id") or "")[:80]}' if model else 'phiên CLI'
                raise ValueError(f'Hermes {identity} không hoàn tất (mã {last.get("exit_code")}): {error}')
            return _object(last.get('text','')),{'reported_model':model or '', 'usage':last.get('tokens') or {}}
        # Older Hermes versions may return one plain JSON answer without events.
        try:return _object(text),{}
        except (ValueError,json.JSONDecodeError) as exc:raise ValueError('Hermes không trả kết quả JSON; xem log.') from exc
    if adapter=='opencode_cli':
        parts=[];all_parts=[];error=None;usage={}
        for line in text.splitlines():
            try:event=json.loads(line)
            except json.JSONDecodeError:continue
            if not isinstance(event,dict):continue
            kind=event.get('type');part=event.get('part') or {}
            if kind=='error':error=event.get('error') or 'OpenCode báo lỗi'
            if kind=='step_start':parts=[]
            if kind=='text' and isinstance(part,dict) and isinstance(part.get('text'),str):
                parts.append(part['text']);all_parts.append(part['text'])
            if kind=='step_finish' and isinstance(part,dict):usage=part.get('tokens') or usage
        if error:raise ValueError('OpenCode báo lỗi: '+str(error)[:300])
        if not parts:parts=all_parts
        if not parts:raise ValueError('OpenCode không trả phần text cuối cùng')
        candidates=[parts[-1],''.join(parts),'\n'.join(parts)]
        for candidate in candidates:
            try:return _object(candidate),{'usage':usage}
            except (ValueError,json.JSONDecodeError):pass
        raise ValueError('OpenCode không trả JSON kết quả hợp lệ')
    raise ValueError('Adapter CLI không hỗ trợ')
