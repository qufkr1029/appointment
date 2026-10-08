# 일정 알림 앱

Windows용 개인 일정 알림 앱입니다. 앱 파일, 전용 파이썬 환경, 설정은 이 `appointment` 폴더 안에서 관리합니다. SQLite DB는 이 폴더의 `data/appointment.db`에 저장됩니다.

## 처음 실행

PowerShell을 열고 **이 폴더를 현재 위치로** 설정합니다. 예를 들면:

```powershell
cd C:\Users\BaTang\Desktop\jbpark\project\appointment
```

아래 명령을 한 줄씩 실행합니다. PowerShell의 현재 폴더는 계속 `project\appointment`여야 합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m appointment
```

가상환경은 `appointment\.venv`에 만들어져 이 앱만 사용합니다. 활성화 명령은 필요하지 않습니다. 설치와 실행 모두 이 가상환경의 Python을 직접 지정합니다.

## 다음 실행부터

새 PowerShell 창을 열 때마다 `appointment` 폴더로 이동한 뒤 아래 실행 명령을 사용합니다. 가상환경 활성화나 라이브러리 재설치는 필요하지 않습니다.

```powershell
cd C:\Users\BaTang\Desktop\jbpark\project\appointment
.\.venv\Scripts\python.exe -m appointment
```

PowerShell 창을 닫지 않았다면 같은 창에서 앱을 다시 실행할 때도 위 실행 명령만 사용하면 됩니다.

## 사용법

- `+ 일정 추가`에서 제목, 날짜, 시간을 입력하고 저장합니다.
- 날짜는 `YYYYMMDD` 또는 `YYYY-MM-DD`, 시간은 `HHMM` 또는 `HH:MM` 형식으로 입력합니다.
- 목록 위의 검색창으로 제목을 찾고, 날짜순 버튼으로 오름차순/내림차순을 바꿉니다.
- 일정 행의 체크박스로 항목을 선택합니다. 한 건은 수정할 수 있고, 선택한 여러 건은 완료 또는 삭제할 수 있습니다.
- 완료 처리는 알림 팝업을 닫는 동작과 별개입니다.
- 알림 팝업에서 `5분 후 다시 알림`을 체크하면 해당 일정 시각을 클릭한 시점부터 5분 뒤로 변경하고, 알림 상태를 초기화합니다. 변경된 시각은 DB와 목록에 반영됩니다.
- 알림 팝업에서 `Tab`으로 목록 보기/확인 버튼에 포커스를 옮기고 `Enter`로 실행할 수 있습니다. `Esc`는 알림을 닫습니다.
- 메인 창에서 Esc를 누르거나 창 닫기 버튼을 누르면 시스템 트레이로 숨습니다.
- 트레이 메뉴에서 창을 다시 열거나 앱을 종료할 수 있습니다.

화면은 Python 기본 Tkinter/ttk 위젯으로 구성합니다. 외부 패키지는 시스템 트레이 아이콘에 필요한 `pystray`와 `Pillow`만 사용합니다.
