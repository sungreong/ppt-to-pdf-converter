FROM python:3.11-slim


RUN apt-get update && apt-get install -y \
    libreoffice \
    libreoffice-writer \
    libreoffice-calc \
    libreoffice-impress \
    fontconfig \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# LibreOffice 및 필요한 의존성 설치
# RUN apt-get update && apt-get install -y \
#     libreoffice \
#     libreoffice-writer \
#     libreoffice-calc \
#     libreoffice-impress \
#     fontconfig \
#     fonts-noto-cjk \
#     fonts-noto-core \
#     fonts-dejavu-core \
#     fonts-liberation \
#     --no-install-recommends \
#     && rm -rf /var/lib/apt/lists/*

# 사용자 정의 폰트 디렉토리 생성
RUN mkdir -p /usr/share/fonts/custom && \
    chmod 755 /usr/share/fonts/custom

# 폰트 디렉토리를 볼륨으로 마운트할 수 있도록 설정
VOLUME ["/usr/share/fonts/custom"]

# 작업 디렉토리 설정
WORKDIR /app

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY app/ ./app/

# 정적 파일 복사 (존재하는 경우)
COPY static/ ./static/

# 폰트 설치 및 캐시 업데이트 스크립트 생성
RUN echo '#!/bin/bash\n\
set -e\n\
echo "폰트 캐시 업데이트 중..."\n\
# 사용자 정의 폰트가 있으면 설치\n\
if [ -d /usr/share/fonts/custom ] && [ "$(ls -A /usr/share/fonts/custom 2>/dev/null)" ]; then\n\
    echo "사용자 정의 폰트 발견, 폰트 캐시 업데이트 중..."\n\
    fc-cache -fv /usr/share/fonts/custom || true\n\
fi\n\
# 시스템 폰트 캐시 업데이트\n\
fc-cache -fv || true\n\
echo "폰트 캐시 업데이트 완료"\n\
# 애플리케이션 실행\n\
exec "$@"\n\
' > /usr/local/bin/entrypoint.sh && \
    chmod +x /usr/local/bin/entrypoint.sh

# 포트 노출
EXPOSE 8000

# 엔트리포인트 설정
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# 애플리케이션 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

