# Linux 서버 계정 Google LDAP로 통합


```jsx
ansible_google_ldap/                 # 프로젝트 최상위 디렉토리
├── inventory.ini                    # 작업대상 서버의 정보
├── multipass_inventory.py           # test용 동적 인벤토리
├── google_ldap_sssd_integration.yml # playbook 파일
├── cloud-config.yml                 # test용 vm 생성
├── files/ldap/                      # 대상 서버로 복사할 정적 파일
│   └── Google_2027_12_17_20121.crt
│   └── Google_2027_12_17_20121.key 
└── templates/                       
    └── sssd.conf.j2                 # 노션의 /etc/sssd/sssd.conf 내용을 담을 템플릿
```

---

### `sudoers` 파일 관리 (Ansible & `visudo`)

1. **안전한 `sudo` 설정**: `/etc/sudoers` 파일을 직접 수정하지 않고, `/etc/sudoers.d/90-ldap-ssw-sudo`라는 별도 파일을 생성 또는 수정
2. **`visudo` 검증 활용**: `visudo -cf %s` 명령으로 변경 내용의 문법 오류를 미리 확인해서, 시스템 문제 방지
3. **권한 부여**: `ssw` 그룹 사용자에게 비밀번호 없이 `sudo` 명령을 쓸 수 있게 하고 (`NOPASSWD: ALL`), 파일 권한 설정 (`0440`)

### 권한 설정

- **개인 키 파일 (`/var/*.key`)**:
    - 권한: `0600`
    - 오직 `root` 사용자만 읽고 쓰기 가능.
- **공개 인증서 파일 (`/var/*.crt`)**:
    - 권한: `0644`
    - `root`는 읽기/쓰기, 다른 사용자는 읽기만 가능. 인증서는 공개 정보이므로 서비스가 읽을 수 있도록 하면서 무결성을 유지.
- **SSSD 설정 파일 (`/etc/sssd/sssd.conf`)**:
    - 권한: `0600`
    - 오직 `root` 사용자만 읽고 쓰기 가능.
- **`sudoers` 설정 파일 (`/etc/sudoers.d/90-ldap-ssw-sudo`)**:
    - 권한: `0440`
    - `root`와 `root` 그룹만 읽기 가능, 다른 사용자는 접근 불가. `sudo` 프로그램이 요구하는 보안 표준.
- `sshd` **설정 파일 (`/etc/ssh/sshd_config.d/99-ansible.conf`):**
    - 권한: `0600`

### 1. 테스트 환경 (VM 신규 생성)

- **목표**: Playbook이 잘 작동하는지 반복적으로, 깨끗한 환경에서 테스트.
- **해결책**: `cloud-init`, `multipass_inventory.py` (동적 인벤토리, 실행중인 vm을 찾음) 사용.
- **프로세스**: VM을 생성하는 단계에서부터 SSH 접속 준비를 자동화하여 테스트 환경 구축

```bash
multipass launch --name google-ldap --cloud-init cloud-config.yaml

ansible-playbook -i ./multipass_inventory.py google_ldap_sssd_integration.yml
```

### 2. 운영 환경 (기존 서버)

- **목표**: 이미 존재하고 운영 중인 서버에 테스트가 끝난 Playbook을 적용.
- **해결책**: `inventory.ini` 수동 변경
- **프로세스**: `cloud-init`을 쓸 수 없으므로, **최초 1회에 한해** 관리자에게 받은 비밀번호 등을 이용해 **수동으로** SSH 키를 복사해서 접속 준비를 해야 합니다.

```bash
ssh-copy-id 계정명@실제_서버_IP
# PW 입력
# inventory.ini 수정

# Dry Run
ansible-playbook -i inventory.ini google_ldap_sssd_integration.yml --check --diff

ansible-playbook -i inventory.ini google_ldap_sssd_integration.yml
```

### 로그인 속도 최적화

**1. DNS 조회 비활성화**

- **설정**: `/etc/ssh/sshd_config` 파일에 `UseDNS no` 추가
- **효과**: 로그인 지연의 주된 원인인 '리버스 DNS 조회'를 생략하여 접속 속도 향상
- **영향**: 로그에 접속자 호스트네임 대신 **IP가 기록됨**. 대부분의 환경에서 문제없으며 보안에 영향을 주지 않음.

**2. GSSAPI 인증 비활성화**

- **설정**: `/etc/ssh/sshd_config` 파일에 `GSSAPIAuthentication no` 추가
- **효과**: 현 환경에서 불필요한 Kerberos(GSSAPI) 인증 시도를 생략하여 약간의 지연 시간 감소.
- **영향**: Kerberos 기반 싱글 사인온(SSO)을 사용하지 않는 한 아무런 부작용이 없음.

### 결과

1. 필요한 패키지 `apt` 설치
2. `/var` 경로에 google ldap `.crt`, `.key` 복사
3. `sssd.conf` 생성
4. `nsswitch.conf`의 sssd 인증 우선순위 설정
5. 첫 로그인 시 `home` 디렉토리 생성
6. ssw 그룹 sudo 권한 추가
7. `sshd_config` 설정 변경
    - PasswordAuthentication yes
    - ChallengeResponseAuthentication yes
    - UseDNS no
    - GSSAPIAuthentication no
8. publicKey(`ubuntu`) 삭제 (적용할 서버 설정 확인 필요함)
