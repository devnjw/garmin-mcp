# 설치 및 API 키 설정

공식 Garmin Connect Personal API 조회 API 26개와 요약 도구 8개를 제공하는 독립적인 커뮤니티 MCP입니다. macOS·Windows·Linux에서 각자의 API 키로 실행합니다. Garmin 공식 제품이 아닙니다.

## 설치

Git과 [uv](https://docs.astral.sh/uv/getting-started/installation/)가 필요합니다. 다음 명령은 macOS/Linux 터미널과 Windows PowerShell에서 동일하게 실행합니다. uv가 Python 3.12 실행 환경을 준비합니다. 직접 Python을 준비한다면 3.12.4 이상이 필요합니다.

```sh
git clone https://github.com/devnjw/garmin-mcp.git
cd garmin-mcp
uv sync --frozen --no-dev --python 3.12 --no-editable
```

설치된 실행 파일은 macOS/Linux의 `.venv/bin/garmin-mcp`, Windows의 `.venv/Scripts/garmin-mcp.exe`입니다. MCP 클라이언트에는 이 파일의 절대 경로를 등록합니다. 저장소를 이동하면 등록한 경로도 수정해야 합니다. 이 프로젝트는 GitHub로 배포하며, PyPI의 동명 패키지를 설치하도록 안내하지 않습니다.

## API 키와 Codex 연결

1. [Garmin Connect API 키 설정](https://connect.garmin.com/app/settings/personalApiToken)에서 자신의 Personal API 키를 발급합니다.
2. Codex 사용자 설정 `~/.codex/config.toml`에서 아래 예시의 경로와 키를 직접 바꿉니다. 기존 `garmin` 항목이 있으면 중복 추가하지 말고 수정합니다.
3. Codex 설정 → MCP servers → `garmin` → Restart 후 `garmin_status(verify=true)`를 호출해 연결을 확인합니다.

```toml
[mcp_servers.garmin]
command = "/absolute/path/to/garmin-mcp/.venv/bin/garmin-mcp"
tool_timeout_sec = 180

[mcp_servers.garmin.env]
GARMIN_PERSONAL_API_KEY = "YOUR_GARMIN_PERSONAL_API_KEY"
GARMIN_MCP_TIMEZONE = "Asia/Seoul"
```

Windows에서는 command를 다음처럼 TOML 작은따옴표 문자열로 지정하면 역슬래시를 그대로 쓸 수 있습니다.

```toml
command = 'C:\Users\YOUR_USER\garmin-mcp\.venv\Scripts\garmin-mcp.exe'
```

**이 설정은 키를 로컬 설정 파일에 평문으로 저장합니다.** macOS/Linux에서는 `chmod 600 ~/.codex/config.toml`로 접근을 제한하고, Windows에서는 본인과 관리자만 접근할 수 있는 사용자 프로필 안에서 관리하세요. 키를 채팅·공개 저장소·이슈에 올리지 마세요.

키를 설정 파일에 넣지 않으려면 `env`의 키 항목을 빼고 `[mcp_servers.garmin]` 바로 아래에 `env_vars = ["GARMIN_PERSONAL_API_KEY"]`를 추가합니다. 이 경우 Codex 실행 환경에 이미 해당 변수가 있어야 합니다. 별도 터미널에서 변수를 설정해도 이미 실행 중인 데스크톱 앱에는 전달되지 않습니다. 비밀 관리 도구로 실행 시 주입하는 방식도 사용할 수 있습니다.

서버는 환경변수만 읽고 키를 따로 저장하지 않습니다. Keychain, 숨김 입력창, `.env` 자동 읽기를 사용하지 않으며 액세스 토큰은 메모리에만 유지합니다. 다른 MCP 클라이언트의 JSON 설정 예시는 [README](../README.md)에 있습니다.

## 확인과 사용

해당 터미널에도 환경변수로 키를 전달했다면 다음 명령으로 인증과 요약 조회를 확인할 수 있습니다. MCP 클라이언트에만 설정한 키가 터미널에 자동 전달되지는 않습니다.

```sh
uv run --frozen --no-dev garmin-mcp check
```

`check`는 상태와 건수만 출력합니다. 평소에는 “최근 7일 가민 수면·HRV·운동을 조회하고 누락된 날짜도 알려줘”처럼 요청하면 됩니다.

시간대는 `GARMIN_MCP_TIMEZONE`을 권장합니다. 생략하면 시스템 `/etc/localtime`의 IANA 시간대를 사용할 수 있을 때 읽고, 그렇지 않으면 UTC입니다. Windows 기본값도 UTC이므로 `Asia/Seoul`처럼 직접 지정하세요. 실제 Garmin 날짜는 보존하며 표시 시각만 선택한 시간대로 변환합니다.

기존 요약 도구 8개의 이름은 유지됩니다. `garmin_api_*` 상세 도구는 공식 응답 필드를 그대로 반환합니다. 요약 조회는 최대 90일, 상세 기간 조회는 최대 31일씩 가능합니다. 운동 검색은 페이지 단위로 더 오래된 기록도 조회할 수 있습니다. [API 대응표](API.md)를 참고하세요.

`partial`은 일부 날짜·항목에 기록이 없다는 뜻이고 `error`는 요청 실패입니다. 낮잠만 기록된 날의 야간 수면 시간을 0으로 채우지 않습니다. 특정 기기·계정에서 실제 데이터가 제공되는지는 API 구현 범위와 별개입니다.

실계정 검증에서 26개 중 25개 API가 정상 HTTP 응답을 반환했고 `weight/all`은 올바른 날짜에도 HTTP 400을 반환했습니다. 오류를 그대로 표시하면서 `garmin_api_weight_range(include_all=true)`를 명시적으로 호출하는 대안을 안내합니다. 응답 구조가 달라 자동 치환하지 않습니다. [검증 범위](VERIFICATION.md)를 확인하세요.

원본 결과에는 계정 식별자·위치·민감한 건강 데이터가 포함될 수 있으며 AI 클라이언트에 전달됩니다. ZIP 다운로드 위치는 macOS/Linux의 `~/.local/share/garmin-mcp/downloads`, Windows의 `%LOCALAPPDATA%/garmin-mcp/downloads/<고유 폴더>`입니다. 기존 파일을 덮어쓰거나 압축을 풀지 않습니다. Windows는 NTFS처럼 접근 권한을 지원하는 로컬 파일시스템을 사용하세요. 심박 존 조회의 `generate_defaults=true`는 Garmin 기본 존 설정을 생성할 수 있어 기본값이 false입니다.

## 업데이트와 기존 설치 전환

```sh
git pull --ff-only
uv sync --frozen --no-dev --python 3.12 --no-editable --reinstall-package garmin-mcp
```

업데이트 뒤 MCP 서버를 Restart합니다. 키 만료·폐기 시 `GARMIN_PERSONAL_API_KEY`를 새 키로 교체하고 재시작합니다.

초기 macOS 전용 버전에서 전환한다면 Git 이력이 초기화되었으므로 새로 clone하세요. 키를 MCP 클라이언트 환경변수에 넣어야 하며 `auth` 명령은 제거되었습니다. 새 설정이 정상 동작한 뒤 이전 `garmin-mcp` Keychain 항목을 지워도 됩니다. 서버는 이 항목을 읽지 않습니다. 기존 macOS/Linux용 `scripts/install.sh`와 `scripts/run.sh`도 호환용으로 유지되며 환경변수를 그대로 전달합니다.
