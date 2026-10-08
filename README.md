# 일정 알림 앱

Windows에서 개인 일정을 등록하고, 예약한 시각에 알림을 받는 데스크톱 앱입니다. 일정은 SQLite 데이터베이스에 저장되며, 앱을 닫아도 시스템 트레이에서 계속 실행할 수 있습니다.

## 지원 환경

- **운영체제:** Windows 11에서 개발 및 실행을 확인했습니다. Windows 10 등 다른 Windows 버전은 테스트하지 않았습니다.
- **Python:** Python 3.14에서 실행을 확인했습니다. Python 3.10 이상을 권장하지만, 다른 버전은 확인하지 않았습니다.
- **필요 항목:** Python 설치 시 `Add python.exe to PATH` 옵션을 선택해야 합니다. 앱의 화면은 Python에 포함된 Tkinter를 사용합니다.
- **인터넷:** 최초 실행 시 `pystray`와 `Pillow` 패키지를 설치하기 위해 인터넷 연결이 필요합니다.

## 설치 및 첫 실행

### 1. Python 설치

[Python 공식 Windows 다운로드 페이지](https://www.python.org/downloads/windows/)에서 Python 3.14를 설치하세요. 설치 화면에서 **Add python.exe to PATH**를 선택한 뒤 설치를 완료합니다. 설치 후 새 PowerShell 창을 열고 다음 명령으로 확인합니다.

```powershell
python --version
```

`Python 3.14.x`와 같이 버전이 표시되면 준비된 것입니다. `python`을 찾을 수 없다는 메시지가 나오면 Python 설치를 확인하고 새 PowerShell 창에서 다시 시도하세요.

### 2. 프로젝트 받기

Git이 설치되어 있다면 PowerShell에서 프로젝트를 저장할 위치로 이동한 뒤 저장소를 복제합니다.

```powershell
cd $HOME\Desktop
git clone https://github.com/qufkr1029/appointment.git
cd appointment
```

Git을 사용하지 않는 경우 저장소 페이지에서 **Code → Download ZIP**을 선택해 내려받고 압축을 푼 다음, PowerShell에서 압축을 푼 `appointment` 폴더로 이동하세요.

### 3. 앱 실행

프로젝트 폴더 안에서 아래 명령을 한 줄씩 실행합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m appointment
```

첫 번째 명령은 프로젝트 전용 Python 환경을 만들고, 두 번째 명령은 필요한 패키지를 설치합니다. 세 번째 명령으로 앱을 실행합니다. 가상환경을 별도로 활성화할 필요는 없습니다.

앱은 프로젝트 폴더 안에 `data` 폴더와 `data/appointment.db` 데이터베이스를 자동으로 만듭니다. 일정 데이터는 이 파일에 저장됩니다. 이 데이터베이스는 개인 일정 정보가 들어갈 수 있으므로 저장소에 올리지 않도록 Git에서 제외되어 있습니다.

## 다음 실행부터

PowerShell에서 프로젝트 폴더로 이동해 다음 명령을 실행하세요. 매번 패키지를 다시 설치할 필요는 없습니다.

```powershell
cd $HOME\Desktop\appointment
.\.venv\Scripts\python.exe -m appointment
```

프로젝트를 다른 위치에 저장했다면 첫 번째 명령의 경로를 실제 위치로 바꾸세요. 이미 프로젝트 폴더 안에 있다면 `cd` 명령은 생략할 수 있습니다.

## 사용법

- **일정 추가:** `+ 일정 추가`를 눌러 제목, 날짜, 시간을 입력하고 저장합니다. 날짜는 `YYYYMMDD` 또는 `YYYY-MM-DD`, 시간은 `HHMM` 또는 `HH:MM` 형식으로 입력합니다.
- **검색 및 정렬:** 목록 위의 검색창으로 제목을 검색하고, 날짜순 버튼으로 오름차순과 내림차순을 바꿉니다.
- **수정 및 상태 변경:** 일정 행의 체크박스로 항목을 선택합니다. 한 건은 수정할 수 있고, 여러 건은 완료 처리하거나 삭제할 수 있습니다. 삭제한 일정은 삭제 목록에서 복구하거나 영구 삭제할 수 있습니다.
- **알림:** 예정 시각이 되면 알림 팝업이 표시됩니다. 팝업에서 `5분 후 다시 알림`을 선택하면 누른 시점부터 5분 뒤로 일정을 미루고 알림 상태를 초기화합니다.
- **키보드:** 알림 팝업에서 `Tab`으로 버튼을 이동하고 `Enter`로 실행할 수 있으며, `Esc`로 팝업을 닫습니다. 메인 창에서 `Esc`를 누르거나 닫기 버튼을 누르면 앱이 종료되지 않고 시스템 트레이로 숨습니다.
- **시스템 트레이:** 트레이 아이콘 메뉴에서 앱 창을 다시 열거나 앱을 종료할 수 있습니다.

## 문제 해결

- **`python` 명령을 찾을 수 없음:** Python을 다시 설치하거나 설치 프로그램에서 PATH 옵션을 선택한 뒤 새 PowerShell 창을 여세요.
- **`No module named tkinter` 오류:** Python 설치를 변경/복구해 Tcl/Tk 지원을 포함하세요. 일반적인 python.org Windows 설치에는 Tkinter가 포함됩니다.
- **패키지 설치 실패:** 인터넷 연결을 확인한 뒤 프로젝트 폴더에서 `python -m pip install -r requirements.txt`를 다시 실행하세요.
- **앱이 실행되지 않거나 일정 데이터가 보이지 않음:** 실행 중인 프로젝트 폴더가 맞는지 확인하세요. 데이터베이스는 각 프로젝트 폴더의 `data/appointment.db`에 저장됩니다.

## 개발 정보

화면은 Python 기본 Tkinter/ttk 위젯으로 구성합니다. 외부 Python 패키지는 시스템 트레이 아이콘을 위한 `pystray`와 `Pillow`입니다. 다른 운영체제와 Windows 11 이외의 Windows 버전은 테스트하지 않았습니다.
