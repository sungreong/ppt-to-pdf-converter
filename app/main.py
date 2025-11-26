from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Tuple, Dict
import subprocess
import os
import uuid
import shutil
import json
from pathlib import Path
from datetime import datetime
import pytz

app = FastAPI(
    title="PPT Converter API",
    description="LibreOffice를 사용한 PPT 변환 API",
    version="1.0.0"
)

# CORS 설정 (HTML에서 API 호출을 위해)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 업로드 및 변환 디렉토리 설정
UPLOAD_DIR = Path("/tmp/uploads")
OUTPUT_DIR = Path("/tmp/outputs")
METADATA_DIR = Path("/tmp/metadata")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
METADATA_DIR.mkdir(exist_ok=True)

# 한국 시간대
KST = pytz.timezone('Asia/Seoul')


def load_metadata_index() -> Tuple[Dict[str, dict], Dict[str, dict]]:
    """메타데이터를 출력 파일명/파일 ID 기준으로 캐시"""
    metadata_by_output: Dict[str, dict] = {}
    metadata_by_id: Dict[str, dict] = {}

    if not METADATA_DIR.exists():
        return metadata_by_output, metadata_by_id

    for metadata_path in METADATA_DIR.glob("*.json"):
        try:
            with open(metadata_path, "r", encoding="utf-8") as metadata_fp:
                metadata = json.load(metadata_fp)
        except Exception:
            continue

        output_name = metadata.get("output_filename") or metadata_path.stem
        if output_name:
            metadata_by_output[output_name] = metadata

        file_id = metadata.get("file_id")
        if file_id:
            metadata_by_id[file_id] = metadata

    return metadata_by_output, metadata_by_id


def delete_metadata_for_output(filename: str) -> bool:
    """출력 파일에 해당하는 메타데이터 삭제"""
    deleted = False

    # 1) 출력 파일명 기반 메타데이터
    metadata_path = METADATA_DIR / f"{filename}.json"
    if metadata_path.exists():
        metadata_path.unlink()
        return True

    # 2) file_id 기반 레거시 메타데이터
    metadata_by_output, metadata_by_id = load_metadata_index()
    metadata = metadata_by_output.get(filename)
    if metadata:
        file_id = metadata.get("file_id")
        if file_id:
            legacy_metadata = METADATA_DIR / f"{file_id}.json"
            if legacy_metadata.exists():
                legacy_metadata.unlink()
                deleted = True

    return deleted

# 허용된 입력 형식
ALLOWED_INPUT_FORMATS = {".ppt", ".pptx", ".odp"}
# 허용된 출력 형식
ALLOWED_OUTPUT_FORMATS = {".pdf", ".odp", ".pptx", ".html"}

# 정적 파일 서빙 (HTML 페이지)
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """HTML 페이지 반환"""
    html_file = static_dir / "index.html"
    if html_file.exists():
        return html_file.read_text(encoding="utf-8")
    return """
    <html>
        <body>
            <h1>PPT Converter API</h1>
            <p>API 문서: <a href="/docs">/docs</a></p>
            <p>헬스 체크: <a href="/health">/health</a></p>
        </body>
    </html>
    """


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    try:
        # LibreOffice 설치 확인
        result = subprocess.run(
            ["libreoffice", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        libreoffice_available = result.returncode == 0
    except Exception:
        libreoffice_available = False

    # 폰트 시스템 확인
    try:
        font_result = subprocess.run(
            ["fc-list", "--format", "%{family}\n"],
            capture_output=True,
            text=True,
            timeout=5
        )
        font_count = len(set(font_result.stdout.strip().split('\n'))) if font_result.returncode == 0 else 0
    except Exception:
        font_count = 0

    return {
        "status": "healthy" if libreoffice_available else "degraded",
        "libreoffice_available": libreoffice_available,
        "font_count": font_count
    }


@app.get("/fonts")
async def list_fonts():
    """설치된 폰트 목록 조회"""
    try:
        result = subprocess.run(
            ["fc-list", "--format", "%{family}\\n"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail="폰트 목록 조회 실패"
            )
        
        fonts = sorted(set(result.stdout.strip().split('\n')))
        fonts = [f for f in fonts if f]  # 빈 문자열 제거
        
        return {
            "total_count": len(fonts),
            "fonts": fonts
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=500,
            detail="폰트 목록 조회 시간 초과"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"폰트 목록 조회 중 오류: {str(e)}"
        )


@app.get("/outputs")
async def list_outputs():
    """변환된 파일 목록 조회"""
    try:
        metadata_by_output, metadata_by_id = load_metadata_index()
        files = []
        if OUTPUT_DIR.exists():
            for file_path in OUTPUT_DIR.iterdir():
                if file_path.is_file():
                    stat = file_path.stat()
                    
                    metadata = metadata_by_output.get(file_path.name) or metadata_by_id.get(file_path.stem)
                    original_filename = metadata.get("original_filename", file_path.name) if metadata else file_path.name

                    # 한국 시간으로 변환
                    modified_time_kst = datetime.fromtimestamp(stat.st_mtime, tz=pytz.UTC).astimezone(KST)
                    
                    files.append({
                        "filename": file_path.name,
                        "original_filename": original_filename,
                        "size": stat.st_size,
                        "modified": modified_time_kst.isoformat(),
                        "modified_formatted": modified_time_kst.strftime("%Y-%m-%d %H:%M:%S"),
                        "download_url": f"/download/{file_path.name}"
                    })
        
        # 수정 시간 기준 내림차순 정렬 (최신 파일 먼저)
        files.sort(key=lambda x: x["modified"], reverse=True)
        
        return {
            "total_count": len(files),
            "files": files
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"파일 목록 조회 중 오류: {str(e)}"
        )


@app.get("/download/{filename}")
async def download_file(filename: str):
    """변환된 파일 다운로드"""
    try:
        file_path = OUTPUT_DIR / filename
        
        # 보안: 경로 탐색 공격 방지
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(
                status_code=404,
                detail="파일을 찾을 수 없습니다."
            )
        
        # 상위 디렉토리로 이동 시도 방지
        if not str(file_path.resolve()).startswith(str(OUTPUT_DIR.resolve())):
            raise HTTPException(
                status_code=403,
                detail="접근이 거부되었습니다."
            )
        
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type="application/octet-stream"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"파일 다운로드 중 오류: {str(e)}"
        )


@app.delete("/outputs/{filename}")
async def delete_output(filename: str):
    """변환된 파일 삭제"""
    file_path = OUTPUT_DIR / filename

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

    if not str(file_path.resolve()).startswith(str(OUTPUT_DIR.resolve())):
        raise HTTPException(status_code=403, detail="접근이 거부되었습니다.")

    try:
        file_path.unlink()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 삭제 중 오류: {str(e)}")

    metadata_removed = delete_metadata_for_output(filename)

    return {
        "message": "파일을 삭제했습니다.",
        "filename": filename,
        "metadata_removed": metadata_removed
    }


@app.post("/convert")
async def convert_ppt(
    file: UploadFile = File(...),
    output_format: str = "pdf"
):
    """
    PPT 파일을 지정된 형식으로 변환
    
    - **file**: 업로드할 PPT 파일 (.ppt, .pptx, .odp)
    - **output_format**: 출력 형식 (pdf, odp, pptx, html)
    """
    # 파일 확장자 검증
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_INPUT_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 입력 형식입니다. 허용된 형식: {', '.join(ALLOWED_INPUT_FORMATS)}"
        )

    # 출력 형식 검증
    if output_format not in [fmt.lstrip(".") for fmt in ALLOWED_OUTPUT_FORMATS]:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 출력 형식입니다. 허용된 형식: {', '.join([fmt.lstrip('.') for fmt in ALLOWED_OUTPUT_FORMATS])}"
        )

    # 고유한 파일명 생성
    file_id = str(uuid.uuid4())
    input_file = UPLOAD_DIR / f"{file_id}{file_ext}"
    output_file = OUTPUT_DIR / f"{file_id}.{output_format}"

    try:
        # 파일 저장
        with open(input_file, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # LibreOffice를 사용한 변환
        # headless 모드로 실행하여 GUI 없이 변환
        convert_cmd = [
            "libreoffice",
            "--headless",
            "--convert-to", output_format,
            "--outdir", str(OUTPUT_DIR),
            str(input_file)
        ]

        result = subprocess.run(
            convert_cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"변환 실패: {result.stderr}"
            )

        # 변환된 파일 확인
        if not output_file.exists():
            # LibreOffice는 원본 파일명을 기반으로 출력 파일명을 생성할 수 있음
            base_name = input_file.stem
            possible_output = OUTPUT_DIR / f"{base_name}.{output_format}"
            if possible_output.exists():
                output_file = possible_output
            else:
                raise HTTPException(
                    status_code=500,
                    detail="변환된 파일을 찾을 수 없습니다."
                )

        # 원본 파일명 메타데이터 저장
        metadata_file = METADATA_DIR / f"{output_file.name}.json"
        metadata = {
            "original_filename": file.filename,
            "output_filename": output_file.name,
            "file_id": file_id,
            "output_format": output_format,
            "created_at": datetime.now(KST).isoformat()
        }
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        # 변환된 파일 반환
        return FileResponse(
            path=str(output_file),
            filename=f"{Path(file.filename).stem}.{output_format}",
            media_type="application/octet-stream"
        )

    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=500,
            detail="변환 시간이 초과되었습니다."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"변환 중 오류 발생: {str(e)}"
        )
    finally:
        # 임시 파일 정리
        if input_file.exists():
            input_file.unlink()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

