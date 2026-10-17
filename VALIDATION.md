# Validation — v1.0.0

## v1.0.0 — 2026-10-17 (Asia/Bangkok)

First public source release. The Windows/Python 3.13 regression run below passed 31 tests with 3 POSIX-only fixtures skipped. This release retains the v0.4.0 feature set and validation limits described below.

## v0.4.0 — 2026-10-17 (Asia/Bangkok)

Windows/Python 3.13: `py -3.13 -m unittest discover -s tests -v` → 31 test pass, 3 fixture POSIX được bỏ qua. `node --check web/app.js` và `py -3.13 -m py_compile room.py api_agent.py` pass.

Đã kiểm tra upload qua HTTP cần đăng nhập, file chưa gắn nhiệm vụ không tải được, file gắn nhiệm vụ xuất hiện trong hội thoại và đường dẫn/nội dung trích xuất ở context, ảnh được gửi tới cả bốn role API theo định dạng vision, và báo cáo chưa hoàn tất có bước tiếp theo. Chưa kiểm tra paste/kéo thả trực tiếp trong trình duyệt, provider vision thực tế hoặc CLI đọc file đính kèm trong sandbox Windows.

## v0.3.0 — lịch sử

Date: 2026-10-15 (Asia/Ho_Chi_Minh)
Environment: Linux, Python 3.12.14, Node 24 (syntax checks only).

Result: 27/27 automated tests PASS.

- Four real diagnostic child processes; distinct PIDs; structured evidence.
- No execution before approval; denial remains terminal.
- Concurrent duplicate approvals produce one pipeline.
- Duplicate creation request_id produces one task.
- Restart converts queued/running to INTERRUPTED, does not replay.
- Disabled Codex adapter rejects work.
- Exit zero with missing JSON fails closed.
- Cancellation terminates active child.
- Deadline terminates child.
- Wrong task_id, wrong role, missing evidence or invalid verdict rejected.
- Common secret patterns redacted.
- Fixture CLI validates generated argv and role-specific sandbox choices.
- Missing session, CSRF token and foreign Origin rejected.
- Private runtime files/traversal not served; unknown Host rejected.
- Wrong password and login throttling tested.
- HTTP task retry and conflicting decisions tested.

JavaScript syntax: node --check PASS. No browser QA capability available; no visual browser tests claimed.

Not tested: Windows native process tree cancellation or .cmd launchers, real Codex authentication/models/quota, Tailscale end-to-end on user's devices, mobile keyboard layout. These are acceptance steps on the user's PC/phone, documented in README.

This is a local single-owner starter, not a multi-tenant production service. SQLite is authoritative; the published Sites page remains a demo and download entrypoint.

## v0.3 additional coverage

- Per-role CLI model/profile/effort argv; default effort omitted.
- Task snapshot unchanged after live role config mutation.
- Legacy global config maps to four roles without mutating input.
- Mixed API → CLI → CLI → API pipeline with isolated processes.
- Chat Completions auth, endpoint, token parameter, optional effort/JSON mode.
- API model/usage metadata recorded as provider-reported, not verified identity.
- Echoed exact API key scrubbed from result and state/trace.
- HTTP redirect rejected without forwarding credentials; no automatic retry.
- Invalid JSON, wrong role and truncated response fail closed.
- HTTP error bodies not persisted.
- Missing key rejected before creating a task.
- Local vault read/write and ENV priority; POSIX file mode 0600.
- Endpoint/schema validation and additive idempotent migration.

The API server and CLI in integration tests are local fixtures. No real provider requests, live models, or paid credits were used. Windows DPAPI code and native Windows CLI remain pending verification on the user's PC.
