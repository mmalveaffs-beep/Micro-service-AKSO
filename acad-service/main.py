from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime
from contextlib import contextmanager

app = FastAPI(title="Product Service", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'products'),
    'user': os.getenv('DB_USER', 'productuser'),
    'password': os.getenv('DB_PASSWORD', 'productpass')
}

def row_to_dict(row):
    if row is None:
        return None
    return dict(row)

class Mahasiswa(BaseModel):
    nim: str
    nama: str
    jurusan: str
    angkatan: int = Field(ge=0)

# Database connection pool
@contextmanager
def get_db_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

@app.on_event("startup")
async def startup_event():
    try:
        with get_db_connection() as conn:
            print("Acad Service: Connected to PostgreSQL")
    except Exception as e:
        print(f"Acad Service: PostgreSQL connection error: {e}")

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "Acad Service is running",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/acad/mahasiswa")
async def get_mahasiswas():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM mahasiswa"

            cursor.execute(query)
            rows = cursor.fetchall()

            return [{"nim": row[0], "nama": row[1], "jurusan": row[2], "angkatan": row[3]} for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/acad/ips")
async def get_ips(nim: str = Query(..., description="Nomor Induk Mahasiswa")):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT m.nim, m.nama, m.jurusan, krs.nilai, mk.sks 
                FROM mahasiswa m 
                JOIN krs ON krs.nim = m.nim 
                JOIN mata_kuliah mk ON mk.kode_mk = krs.kode_mk 
                WHERE m.nim = %s
            """
            cursor.execute(query, (nim,))
            results = cursor.fetchall()

            if not results:
                raise HTTPException(status_code=404, detail=f"Mahasiswa dengan NIM {nim} tidak ditemukan atau tidak memiliki KRS.")

            grade_points = {
                'A': 4.0, 'A-': 3.75, 'B+': 3.5, 'B': 3.0, 'B-': 2.75, 'C+': 2.5,
                'C': 2.0, 'D': 1.0, 'E': 0.0
            }

            total_bobot = 0
            total_sks = 0

            for row in results:
                nilai = row['nilai'].strip()  # buang spasi depan/belakang
                sks = row['sks']
                bobot = grade_points.get(nilai, 0) * sks
                print(f"Nilai: {nilai}, SKS: {sks}, Bobot: {bobot}")  # debug
                total_bobot += bobot
                total_sks += sks        
            
            ips = total_bobot / total_sks if total_sks > 0 else 0
            
            mahasiswa_info = results[0]
            return {"nim": mahasiswa_info['nim'], "nama": mahasiswa_info['nama'], "jurusan": mahasiswa_info['jurusan'], "ips": round(ips, 2)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))