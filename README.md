# Vũ Agent Room — PC v1.0.0

Giao diện đã chốt, chạy cùng backend trên PC Windows. Điện thoại truy cập cùng server qua Tailscale; dữ liệu SQLite không nằm trong trình duyệt.

## Chạy trong 3 bước trên PC

1. Giải nén toàn bộ thư mục `Vu-Agent-Room-PC`. Cần Python 3.11 trở lên (Python 3.13 hiện có dùng được). Không cần pip, Node hoặc API key cho bộ room.
2. Nhấp đúp `START.cmd`. Lần đầu sẽ hỏi mật khẩu room (ít nhất 12 ký tự), thư mục project, URL điện thoại và có bật Codex không. Có thể Enter bỏ qua URL, chọn N cho Codex để thử trước. Mật khẩu room do bạn tự đặt, không phải mật khẩu ChatGPT.
3. Mở http://127.0.0.1:8787, đăng nhập, bấm **Kiểm tra kết nối** → **Giao và chạy**. Kết quả dự kiến: COMPLETE với 4 vai trò và PID riêng. Đây là tiến trình Python chẩn đoán thật, không phải AI và không tốn token.

Giữ cửa sổ START mở. Khóa màn hình PC vẫn có thể chạy; sleep/hibernate hoặc tắt PC sẽ ngắt truy cập. Không tự thay đổi chế độ nguồn của máy.

## Truy cập trên điện thoại ngoài nhà

1. Cài và đăng nhập Tailscale trên PC và điện thoại vào cùng mạng Tailscale. Việc truy cập còn phụ thuộc ACL của mạng.
2. Trên PowerShell PC, xem cấu hình hiện có:

   ```powershell
   tailscale serve status
   ```

3. Nếu cổng HTTPS 8443 chưa dùng cho dịch vụ khác, chạy:

   ```powershell
   tailscale serve --bg --https=8443 http://127.0.0.1:8787
   ```

   Nếu Tailscale yêu cầu bật HTTPS, làm theo URL mà chính lệnh trả về. Không dùng `tailscale funnel`. Nếu 8443 đã được dùng, giữ dịch vụ cũ và chọn một cổng HTTPS khác được Tailscale hỗ trợ.
4. Sao chép **URL HTTPS thực tế mà Tailscale trả về** (bao gồm :8443). Chạy `CONFIGURE.cmd`, dán URL đó vào câu hỏi URL điện thoại, giữ các lựa chọn mong muốn. Không đoán URL từ tên PC.
5. Dừng START bằng Ctrl+C, chạy lại. Bật Tailscale trên điện thoại, mở URL vừa nhận và đăng nhập bằng mật khẩu room. Có thể thêm trang vào màn hình chính qua menu trình duyệt.

Không phải mở port router. Chỉ bind backend vào 127.0.0.1; không đổi thành 0.0.0.0. Các máy khác có quyền truy cập dịch vụ trong tailnet vẫn phải đăng nhập room. URL Sites xem mẫu không phải URL điều khiển PC.

Để dừng riêng cấu hình Serve này, tham khảo lệnh `tailscale serve --https=8443 off`; không dùng reset nếu máy đang có các dịch vụ Serve khác.

## Model, provider và effort RIÊNG từng vai trò (v0.3)

Chạy `CONFIGURE_MODELS.cmd` để chỉ thiết lập đội agent; không cần đặt lại mật khẩu/URL điện thoại. Có thể chạy `CONFIGURE.cmd` để chỉnh toàn bộ.

Lần lượt với Coordinator, Worker, Tester, Reviewer:

1. Chọn adapter: `1` = Codex CLI; `2` = API tương thích OpenAI Chat Completions; `3` = Hermes CLI; `4` = OpenCode CLI.
2. Chọn provider/profile hoặc base URL theo adapter.
3. Nhập model ID riêng; không có model tự chọn ngầm.
4. Chọn effort: `default`, `low`, `medium`, `high`. `default` = không gửi ghi đè effort.
5. Lưu xong thì bấm biểu tượng **⚙ Cài đặt Room → Khởi động lại Room** trên trang để nạp lại cấu hình; không cần chạy lại `START.cmd`. Đăng nhập lại sau khi Room khởi động. Mở tab **Đội agent** để xem lại.

Enter giữ giá trị đang hiện; nhập `-` để xóa model/profile. Mỗi vai trò có thể dùng model và provider khác nhau.

### Codex CLI

- Cần Codex CLI đã đăng nhập trên PC; executable `codex.exe` gốc trên Windows, không phải wrapper `.cmd/.bat`.
- `provider` là nhãn hiển thị, không tự thay đổi provider thật. `profile` truyền qua `--profile`, chọn một profile bạn đã cấu hình trong Codex; để trống dùng cấu hình CLI hiện tại.
- `model` truyền qua `--model`; để trống dùng mặc định CLI/profile. Effort khác default truyền qua `model_reasoning_effort`.
- Mỗi vai trò Codex CLI chạy trong thư mục Git worktree riêng dưới `data/worktrees/<task-id>/<role>`. Nhiệm vụ có nhánh riêng `agent-room/<task-id>`; checkpoint của mỗi vai trò được chuyển cho vai trò tiếp theo để Reviewer đọc đúng thay đổi của Worker.
- Workspace phải là Git repo sạch (không có thay đổi chưa commit) khi nhiệm vụ bắt đầu. Room không tự stash hoặc ghi đè thay đổi hiện có. Nếu workspace không phải Git repo hoặc còn thay đổi, nhiệm vụ dừng ở khâu khởi tạo.
- Có thể đổi workspace ngay tại **⚙ Cài đặt Room**. Nhập đường dẫn tuyệt đối tới thư mục gốc của Git repo sạch rồi bấm **Lưu workspace**; cấu hình mới áp dụng ngay cho nhiệm vụ tạo sau đó, còn nhiệm vụ cũ giữ snapshot ban đầu. Nút **Khởi động lại Room** tạo tiến trình Room mới để nạp lại cấu hình và mã mà không cần `START.cmd`; nút từ chối khi có nhiệm vụ đang chạy hoặc xếp hàng. Phiên đăng nhập hết hiệu lực sau khi khởi động lại. Lỗi khởi động sau restart được ghi ở `data/room-restart.log`.
- Codex CLI thường chạy trong sandbox `workspace-write`, có shell và tìm kiếm web trong worktree nếu executable hỗ trợ cờ global `--search`. Khi bạn duyệt một yêu cầu deploy cụ thể của Reviewer, lượt Worker tiếp theo dùng `danger-full-access` để có thể kết nối VPS; quyền này rộng ở cấp hệ điều hành, còn giới hạn đích và hành động được nêu trong chỉ dẫn cho agent và trace. Tìm kiếm web không phải trình duyệt đồ họa và không chia sẻ phiên đăng nhập trình duyệt.
- Thay đổi chỉ nằm trên nhánh worktree. Sau khi nhiệm vụ Sửa project hoàn tất, bấm **Áp dụng thay đổi vào project chính** để fast-forward; thao tác chỉ chạy khi project chính sạch và vẫn có thể fast-forward từ commit gốc. Các luồng khác không có nút áp dụng. Worktree và nhánh được giữ lại để xem xét; dừng task không tự hoàn tác.
- Model/effort thực tế phụ thuộc CLI và provider. Room ghi rõ giá trị yêu cầu; không tự khẳng định đã xác thực model chạy thực.
- API/provider dùng cho Codex phải được cấu hình qua Codex profile đúng yêu cầu của CLI. Đổi nhãn provider trong Room không đủ để đổi endpoint của Codex.

### Hermes CLI và OpenCode CLI

- Mỗi vai trò có thể chọn Hermes hoặc OpenCode độc lập. Nhập đường dẫn executable gốc (`.exe` trên Windows), model ID hoặc để trống để dùng model mặc định của CLI. Nhãn provider trong Room chỉ để hiển thị; đăng nhập, provider, model mặc định, MCP và quyền công cụ được cấu hình trong chính harness.
- Room chạy CLI bằng tiến trình riêng trong Git worktree của vai trò, chuyển commit checkpoint sang vai trò tiếp theo và chỉ nhận kết quả JSON đúng `task_id`/`role`/schema. Room không tự tạo session dùng chung giữa các vai trò. OpenCode nhận prompt qua tệp đính kèm; Hermes nhận prompt qua stdin.
- Hermes dùng `hermes chat --oneshot --query-file - --source cli --format stream-json` để các phiên Worker/Tester hiện trong danh sách phiên Hermes GUI và Room nhận sự kiện tiến triển. Prompt có tiền tố task ID, vai trò và tiêu đề task để dễ nhận diện trong phiên; tên hiển thị của session do Hermes tạo. Có thể nhập model ID và `toolsets` như `file,terminal,web`; nếu model để trống thì dùng model mặc định Hermes. Phê duyệt công cụ của Hermes do chính Hermes quản lý.
- OpenCode dùng `opencode run --format json --dir <worktree>` và tùy chọn `--model provider/model`. Tùy chọn **tự duyệt quyền** truyền `--auto`, mặc định tắt; nếu tắt mà harness hỏi quyền trong phiên không tương tác, bước có thể hết thời gian và báo lỗi. `--auto` chỉ tự duyệt quyền chưa bị deny theo cấu hình OpenCode.
- Hermes/OpenCode chạy với quyền tài khoản hệ điều hành của tiến trình CLI; Git worktree là cách tách thay đổi và bàn giao, **không phải sandbox bảo mật**. File/shell phụ thuộc cấu hình công cụ và quyền của harness. Tìm web/browser chỉ có nếu harness đã được cấu hình công cụ tương ứng; Room không tự cấp browser hay phiên đăng nhập Chrome.
- Trên máy này đã thấy `C:\Users\ANHVU\AppData\Local\hermes\bin\hermes.exe`. Nếu `opencode` chưa có trong PATH, tìm executable gốc của bản CLI đang cài rồi nhập thủ công; ứng dụng OpenCode Desktop không nhất thiết kèm CLI dùng được theo cách này.

- Khi Hermes trả `result` với exit code khác 0, Room hiển thị lỗi của harness/provider trong kết quả vai trò. Ví dụ HTTP 400 thiếu `reasoning_text` ở model thinking là yêu cầu bị provider từ chối sau khi Hermes đã thoát; chờ thêm không thể hoàn tất phiên đó. Đổi model/provider trong `CONFIGURE_MODELS.cmd` hoặc sửa cấu hình Hermes/gateway trước khi tạo nhiệm vụ mới. Room không tự chạy lại vì công cụ có thể đã thay đổi project hoặc hệ thống ngoài.

### API tương thích OpenAI

- Nhập base URL đúng của provider/gateway, thường có hậu tố `/v1`; không thêm `/chat/completions` vì adapter tự nối phần đó.
- Ngoài localhost phải dùng HTTPS. Có thể dùng gateway cục bộ dạng `http://127.0.0.1:PORT/v1`.
- Nhập model ID mà provider hỗ trợ. Khả năng tương thích thực tế của Kenari, CLIProxyAPI hoặc gateway khác phải kiểm chứng bằng tài khoản của bạn; chưa có provider nào được gọi thật trong bản đóng gói này.
- Effort mặc định là `default` (không gửi). Chỉ chọn low/medium/high nếu provider/model hỗ trợ `reasoning_effort`.
- JSON mode mặc định tắt. Bật nếu provider hỗ trợ `response_format: {type: json_object}`. Kết quả cuối vẫn bắt buộc đúng JSON schema kể cả khi tắt JSON mode.
- Giới hạn output 128–16384 token, mặc định 2048. Chọn tên tham số `max_tokens` hoặc `max_completion_tokens` theo provider. Không tự đổi tham số, model hoặc thử lại khi lỗi.
- Nhập tên tham chiếu key, ví dụ `ROOM_WORKER_KEY`; đây không phải key thật. Sau đó có thể nhập key vào ô nhập ẩn hoặc dùng biến môi trường cùng tên đã có trên PC.
- Biến môi trường được ưu tiên hơn key lưu cục bộ. Nếu ENV đang chứa key cũ, cập nhật/xóa ENV rồi khởi động lại; nhập key mới vào kho không ghi đè ENV.
- Key nhập ẩn lưu riêng ở `data/keys.json`. Trên Windows dùng DPAPI gắn với tài khoản Windows; không copy kho mã hóa sang tài khoản/máy khác và kỳ vọng tự mở được. Trên Linux lưu plaintext trong tệp quyền 0600; nếu không muốn lưu, chỉ dùng ENV.
- Key không nằm trong `config.json`, task snapshot, giao diện hoặc log thông thường. Các mẫu secret phổ biến và key API của bước hiện tại được che; không bảo đảm nhận biết mọi secret khác trong đầu ra model.
- API chỉ nhận task và kết quả bàn giao từ những bước trước. API **không có filesystem, shell, tool calling hoặc quyền sửa project**. Khi cần một kiểm tra bằng công cụ mà API không thể thực hiện, agent ghi `NEEDS_VERIFICATION`; code test không áp dụng ghi `NOT_APPLICABLE`. Không coi lời model nói đã test là bằng chứng thực thi.
- Nội dung task và kết quả bàn giao được gửi tới endpoint đã cấu hình. Xem provider/model và endpoint trong cấu hình vai trò trước khi gửi nhiệm vụ.
- Có thể dùng API cho lập kế hoạch/đánh giá nội dung và chọn Codex/Hermes/OpenCode CLI cho vai trò cần đọc workspace, sửa code hoặc chạy lệnh. API nhận văn bản trích xuất từ file đính kèm và ảnh qua định dạng vision của Chat Completions nếu model/provider hỗ trợ.

### Ràng buộc chung

- Khi giao nhiệm vụ, chọn luồng **Hướng dẫn / Phân tích**, **Review project** hoặc **Sửa project**. Hướng dẫn kiểm chứng thông tin/nguồn thay vì chạy code test; review chỉ đọc và chỉ chạy test nếu được yêu cầu; sửa project chạy kiểm tra phù hợp với thay đổi.
- Bốn vai trò chạy tuần tự, một nhiệm vụ hoạt động tại một thời điểm. `NOT_APPLICABLE` nghĩa bước kiểm tra không phù hợp với loại nhiệm vụ; `NEEDS_VERIFICATION` nghĩa còn kiểm tra liên quan chưa xác nhận được. Nếu các vai trò hoàn tất nhưng có bước cần xác minh, task có trạng thái `COMPLETE_UNVERIFIED` và Reviewer vẫn được chạy. `FAILED` dành cho kết quả lỗi hoặc blocker thực sự.
- Mỗi vai trò chờ tối đa 15 phút; không có đầu ra từ CLI trong 10 phút thì bước dừng vì không có tiến triển. Đầu ra CLI làm mới thời gian chờ im lặng; Room ghi heartbeat mỗi phút vào nhật ký điều phối và giữ giới hạn 30 phút cho cả nhiệm vụ. Khi hết giới hạn, Room dừng tiến trình và không tự chạy lại vì có thể lặp thay đổi. Hermes luôn dùng `--format stream-json`, kể cả model mặc định, để Room nhận sự kiện tiến triển. API có timeout mạng 120 giây và không tự retry. Dừng kết nối không bảo đảm provider đã ngừng tính token phía họ.
- Tham số Room được chụp lúc tạo task. Các task đã tồn tại không đổi model/endpoint theo cấu hình Room mới. Nội dung profile CLI, model mặc định bên trong CLI và giá trị key vẫn do cấu hình PC quyết định ở thời điểm chạy.
- Mỗi kết quả phải đúng task_id/role/verdict, PASS, NOT_APPLICABLE và NEEDS_VERIFICATION đều cần evidence hoặc lý do cụ thể. Exit 0 không đủ. JSON có cấu trúc không phải sự xác nhận độc lập rằng lời model là đúng.
- Tin nhắn chat và nút **Giao nhiệm vụ** chạy ngay khi tới lượt. Coordinator/Reviewer có thể dừng nhiệm vụ để hỏi bạn; câu trả lời tiếp theo trong chat nối tiếp cùng nhiệm vụ. Coordinator hoặc Reviewer hỏi phê duyệt VPS bằng đích và hành động cụ thể; chỉ nút **Cho phép deploy** mới mở quyền cho Worker, từ chối thì Reviewer kết luận. Quyền đã duyệt giữ nguyên phạm vi trong cùng nhiệm vụ qua các câu hỏi bổ sung và được xóa khi nhiệm vụ hoàn tất, lỗi, bị hủy hoặc gián đoạn. Hành động/đích mới cần gate mới. Các yêu cầu phê duyệt công cụ riêng bên trong CLI chưa được chuyển thành nút của Room.
- Chưa tích hợp Antigravity hoặc controller từ hai repo team cũ. Không tự push/deploy khi chưa có phê duyệt cụ thể.

## Nâng cấp từ v0.2

1. Dừng server bằng Ctrl+C.
2. Sao lưu toàn bộ thư mục `data/` khi server đã dừng.
3. Giải nén v0.3 vào thư mục mới, chép `data/` từ v0.2 sang thư mục này. Hoặc ghi đè các tệp chương trình, giữ nguyên `data/`.
4. Chạy `CONFIGURE_MODELS.cmd` để thiết lập riêng. Nếu chưa chạy, cấu hình model chung v0.2 vẫn được ánh xạ cho cả 4 vai trò.
5. Chạy START. Cột trace mới được bổ sung tự động, không xóa dữ liệu. Nhiệm vụ cũ giữ cấu hình cũ; tạo nhiệm vụ mới để dùng cấu hình mới.

## Dùng hàng ngày

### Đọc mailbox admin bằng Codex và Agent Room

Room và Codex CLI trên PC này dùng chung MCP `vuhocai_admin_mail`. Mailbox tự quản trị không có Gmail API; cầu nối này dùng IMAP TLS cổng 993 của `mail.vuhocai.shop` và chỉ cung cấp `list_admin_mail` (danh sách thư) cùng `read_admin_mail` (nội dung một thư theo UID). Các lệnh dùng `INBOX` ở chế độ chỉ đọc và `BODY.PEEK`, nên không đánh dấu thư đã đọc, tải nội dung tệp đính kèm hoặc gửi thư. Không cần mở cổng 25 để đọc.

1. Trong Room, bấm **⚙ Cài đặt Room → Đọc thư admin@vuhocai.shop → Lưu mật khẩu mailbox**. Sau khi cập nhật chương trình, bấm **Khởi động lại Room** một lần trước để nạp endpoint mới. Bạn cũng có thể chạy `CONFIGURE_MAIL.cmd` trên PC. **Không gửi mật khẩu qua chat.** Mật khẩu được lưu bằng Windows DPAPI trong `data/keys.json`; host và tên tài khoản nằm trong `data/mailbox.json`.
2. Mở phiên Codex mới để nạp cấu hình MCP. Room sẽ dùng cùng công cụ ở các vai trò chạy bằng Codex CLI trong nhiệm vụ mới. Có thể yêu cầu: “Liệt kê 10 thư mới nhất của admin@vuhocai.shop” rồi “Đọc UID ...”. Các vai trò dùng adapter API text-only, Hermes hoặc OpenCode không tự nhận công cụ Codex này.
3. Thư trả về công cụ sẽ được đưa vào ngữ cảnh của model đang xử lý yêu cầu. Chỉ giao nhiệm vụ đọc thư cho provider mà bạn muốn chia sẻ nội dung đó.

Nếu cấu hình MCP chưa xuất hiện trong phiên Codex đang mở, tạo phiên mới. Công cụ báo rõ khi chưa nhập mật khẩu, khi IMAP không kết nối hoặc đăng nhập được. Không dùng công cụ này cho gửi mail; cấu hình SMTP và cổng 25 là việc riêng.

- Gửi tin nhắn thường để đội agent tự nhận và chạy tuần tự, không cần `@Coordinator`. Worker có thể sửa file trong worktree ngay. Nếu một nhiệm vụ đang ở trạng thái **Chờ bạn trả lời**, tin nhắn tiếp theo là câu trả lời cho nhiệm vụ đó. Để giao việc mới khi đang có câu hỏi chờ, dùng nút **Giao nhiệm vụ**. SSH/deploy VPS cần Coordinator hoặc Reviewer hỏi và bạn duyệt đích cùng hành động bằng nút riêng.
- Trong ô chat, bấm **＋** để chọn file, paste ảnh từ clipboard hoặc kéo thả file. Có thể gửi chỉ file, không cần gõ chữ. Tối đa 4 file mỗi tin, 5 MB mỗi file. File lưu trong `data/attachments/` trên PC, gắn với nhiệm vụ và được gửi cho cả bốn vai trò. Ảnh PNG/JPEG/GIF/WebP được hiển thị trong chat. API nhận ảnh theo định dạng vision; nếu model không hỗ trợ ảnh, lượt đó sẽ báo lỗi. Text, mã nguồn, CSV, JSON, DOCX, XLSX, PPTX được trích nội dung cho API khi nội dung không quá 100.000 ký tự. PDF cần tiện ích `pdftotext` trên PC để vai trò API đọc được; nếu không có, Room yêu cầu chọn định dạng khác. File nhị phân khác chỉ dùng được khi tất cả vai trò là CLI và có công cụ đọc tương ứng.
- Sau khi gửi chat, giao diện ở lại phòng hội thoại. Nút **↓ Tin mới nhất** xuất hiện khi bạn cuộn lên để đưa bạn về cuối chat. Khi một nhiệm vụ mới bắt đầu, cả bốn vai trò nhận bản tóm tắt tối đa sáu nhiệm vụ trước: yêu cầu, trạng thái, kết luận và nhánh worktree. Thay đổi chưa áp dụng ở nhánh cũ không tự xuất hiện trong worktree mới; Worker phải đối chiếu và mang phần cần thiết sang nếu bạn yêu cầu làm tiếp.
- Khi nhiệm vụ hoàn tất, room đăng thẻ **KẾT LUẬN CUỐI CÙNG** của Reviewer ngay trong chat: kết luận ngắn, các bước chính, nguồn và điểm cần xác minh được tách rõ. Nếu kết quả chưa hoàn thành, Coordinator/Reviewer được yêu cầu nêu bước tiếp theo; báo cáo cuối luôn có mục bước tiếp theo. Căn cứ dài của Worker nằm trong mục mở rộng. Nếu nhiệm vụ lỗi trước Reviewer, Hệ thống đăng lý do dừng và nêu Reviewer chưa chạy.
- `/agent`: mở danh sách vai trò. `/trace`: mở trace nhiệm vụ đang chọn/gần nhất.
- Nhấn task trong hội thoại để xem PID, run ID, thời gian, exit code, bằng chứng và log. Model/effort yêu cầu được ghi; giá trị hiệu lực ghi chưa quan sát.
- Trace lưu snapshot năng lực thực tế runner cấp cho từng vai trò (adapter, sandbox, đường dẫn worktree, filesystem, shell, web search và browser đồ họa); prompt của agent nhắc không được tuyên bố vượt quá năng lực đó. API tương thích OpenAI chỉ nhận nội dung nhiệm vụ và file đính kèm đã xử lý, không được cấp worktree/filesystem/shell.
- Thẻ nhiệm vụ và phần tóm tắt hiển thị số vai trò đã bắt đầu; nếu dừng giữa chừng sẽ nêu vai trò dừng và ghi rõ Reviewer chưa chạy khi đúng như vậy.
- Bấm **Dừng nhiệm vụ** để kết thúc cây tiến trình do runner quản lý. Không tự hoàn tác file đã sửa. Tiến trình nền bị tách khỏi cây có thể cần kiểm tra thủ công; agent được chỉ dẫn không khởi chạy nền.
- Sau restart, nhiệm vụ RUNNING/QUEUED được đánh dấu INTERRUPTED; không tự chạy lại. Khi bị kill đột ngột, kiểm tra tiến trình CLI còn sót và thay đổi trên PC trước khi tạo nhiệm vụ mới. WAIT_USER và WAIT_APPROVAL cũ tiếp tục chờ bạn.
- Trang cập nhật khoảng 2 giây khi mở; tab nền chậm hơn. Không có push notification khi đóng trang và không có chế độ đọc offline. Mất kết nối được hiển thị rõ.
- Dữ liệu ở `data/room.sqlite3`; mật khẩu băm và cấu hình ở `data/config.json`. Để sao lưu, dừng server rồi sao chép toàn bộ `data/`. Không gửi thư mục này lên Git hoặc chia sẻ công khai. Giới hạn giao diện: 100 task/300 tin gần nhất; lịch sử cũ vẫn nằm trong SQLite, chưa có phân trang.
- Log có che các mẫu token/password phổ biến, nhưng không bảo đảm nhận biết mọi secret. Không đưa secret vào prompt. Quyền read-only vẫn cho phép agent đọc dữ liệu mà sandbox/CLI cấp; dùng một project riêng, giới hạn quyền phù hợp.

## Kiểm chứng

Chạy `TEST.cmd` hoặc `python -m unittest discover -s tests -v`.

Bản này đã đạt 31 test trên Windows/Python 3.13; 3 fixture chỉ dành cho POSIX được bỏ qua. Đã kiểm tra HTTP upload/download có xác thực, chia sẻ file với các vai trò API, và báo cáo có bước tiếp theo khi chưa hoàn tất. Paste/kéo thả trong trình duyệt, provider vision thực tế và CLI đọc file trong sandbox Windows vẫn cần kiểm tra trên môi trường sử dụng.

Xem `VALIDATION.md` để biết ranh giới kiểm chứng. Không coi việc giải nén gói này là đã cài hoặc đã kết nối PC.

## Tài liệu gốc đã đối chiếu

- https://tailscale.com/docs/reference/tailscale-cli/serve
- https://tailscale.com/docs/features/tailscale-serve
- https://learn.chatgpt.com/docs/non-interactive-mode
- https://learn.chatgpt.com/docs/developer-commands?surface=cli
- https://hermes-agent.nousresearch.com/docs/reference/cli-commands
- https://docs.opencode.ai/docs/cli/
- https://docs.opencode.ai/docs/permissions/
