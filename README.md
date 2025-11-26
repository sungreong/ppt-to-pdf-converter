# PPT to PDF Converter

🚀 LibreOffice를 사용한 PPT/PPTX/ODP 파일을 PDF로 변환하는 Docker 기반 FastAPI 서비스

[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/)

## ✨ 주요 기능

- 📄 **PPT/PPTX/ODP → PDF 변환**: LibreOffice를 사용한 고품질 변환
- 🎨 **사용자 정의 폰트 지원**: 한글 폰트 포함, 폰트 추가 가능
- 🌐 **웹 인터페이스**: 드래그 앤 드롭으로 간편한 파일 업로드
- 📦 **Docker 배포**: Docker Compose로 간단한 설치 및 실행
- 🔄 **파일 관리**: 변환된 파일 목록 조회 및 삭제 기능
- ⚡ **RESTful API**: 프로그래밍 방식으로도 사용 가능

## 시작하기

### Docker Compose로 실행

```bash
docker-compose up -d
```

### API 접근

- API 서버: http://localhost:9999
- API 문서: http://localhost:9999/docs
- 헬스 체크: http://localhost:9999/health

## API 사용법

### 파일 변환

```bash
curl -X POST "http://localhost:9999/convert?output_format=pdf" \
  -F "file=@presentation.pptx"
```

### 변환 파일 관리

- 변환된 파일 목록: `GET /outputs`
- 개별 파일 삭제: `DELETE /outputs/{filename}`
- 변환 결과 다운로드: `GET /download/{filename}`

### 지원 형식

**입력 형식:**
- .ppt
- .pptx
- .odp

**출력 형식:**
- pdf
- odp
- pptx
- html

### 폰트 확인

```bash
curl http://localhost:9999/fonts
```

## 폰트 추가

LibreOffice가 특정 폰트를 인식하지 못하는 경우, 사용자 정의 폰트를 추가할 수 있습니다.

### 사용자 정의 폰트 추가 방법

1. `fonts/` 디렉토리에 폰트 파일(.ttf, .otf 등)을 복사합니다.
2. Docker 컨테이너를 재시작합니다:
   ```bash
   docker-compose restart
   ```

### 폰트 확인

설치된 폰트 목록 확인:
```bash
# API를 통해 확인
curl http://localhost:9999/fonts

# 컨테이너 내에서 확인
docker-compose exec ppt-converter fc-list
```

### 기본 설치된 폰트

- Noto CJK (한국어, 중국어, 일본어 지원)
- DejaVu (라틴 문자)
- Liberation (기본 라틴 폰트)

## 프로젝트 구조

```
PPTConvertor/
├── app/
│   └── main.py          # FastAPI 애플리케이션
├── fonts/               # 사용자 정의 폰트 디렉토리
├── docker-compose.yml   # Docker Compose 설정
├── Dockerfile           # Docker 이미지 빌드 설정
├── requirements.txt     # Python 의존성
└── README.md           # 프로젝트 문서
```

