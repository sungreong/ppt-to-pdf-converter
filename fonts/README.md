# 폰트 디렉토리

이 디렉토리에 사용자 정의 폰트 파일을 추가할 수 있습니다.

## 사용 방법

1. 이 디렉토리에 폰트 파일(.ttf, .otf, .ttc 등)을 복사합니다.
2. Docker 컨테이너를 재시작합니다:
   ```bash
   docker-compose restart
   ```

## 지원 형식

- TrueType Font (.ttf)
- OpenType Font (.otf)
- TrueType Collection (.ttc)
- PostScript Type 1 (.pfb, .pfm)

## 폰트 설치 확인

컨테이너 내에서 폰트 목록 확인:
```bash
docker-compose exec ppt-converter fc-list
```

특정 폰트 검색:
```bash
docker-compose exec ppt-converter fc-list | grep "폰트이름"
```

## 주의사항

- 폰트 파일을 추가한 후에는 컨테이너를 재시작해야 합니다.
- 폰트 라이선스를 확인하고 사용하세요.
- 폰트 파일은 읽기 전용으로 마운트됩니다.

