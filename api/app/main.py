from fastapi import FastAPI, Depends, HTTPException, status, Form, Request, APIRouter
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Text
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, List
from datetime import datetime, timedelta
import os

# Configuración y constantes
SECRET_KEY = os.getenv("AUTH_SECRET", "secretdevkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 día

DATABASE_URL = os.getenv("DATABASE_URL")

# Intentar conectar a PostgreSQL, fallback a SQLite
try:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
    # Test connection
    with engine.connect() as conn:
        pass
except Exception:
    # Fallback a SQLite local
    DATABASE_URL = "sqlite:///./app.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Contexto para hashing de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

app = FastAPI(title="EDÉN - Asistente Empresarial Inteligente API")

# CORS (permitir frontend local y otros orígenes si es necesario)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción restringir a dominios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MODELOS DE BASE DE DATOS

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(128), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    cotizaciones = relationship("Cotizacion", back_populates="owner")
    proyectos = relationship("Proyecto", back_populates="owner")
    tareas = relationship("Tarea", back_populates="owner")
    gastos = relationship("Gasto", back_populates="owner")

class Cotizacion(Base):
    __tablename__ = "cotizaciones"
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(150), nullable=False)
    descripcion = Column(Text, default="")
    cliente = Column(String(150), default="")
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    estado = Column(String(50), default="pendiente")  # pendiente, aceptada, rechazada
    total = Column(Float, default=0.0)

    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="cotizaciones")

class Proyecto(Base):
    __tablename__ = "proyectos"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), nullable=False)
    descripcion = Column(Text, default="")
    fecha_inicio = Column(DateTime, default=datetime.utcnow)
    fecha_fin = Column(DateTime, nullable=True)
    estado = Column(String(50), default="activo")  # activo, finalizado, cancelado

    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="proyectos")

class Tarea(Base):
    __tablename__ = "tareas"
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(150), nullable=False)
    descripcion = Column(Text, default="")
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_vencimiento = Column(DateTime, nullable=True)
    completada = Column(Boolean, default=False)

    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="tareas")

class Gasto(Base):
    __tablename__ = "gastos"
    id = Column(Integer, primary_key=True, index=True)
    concepto = Column(String(150), nullable=False)
    monto = Column(Float, nullable=False)
    fecha = Column(DateTime, default=datetime.utcnow)
    descripcion = Column(Text, default="")

    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="gastos")

# Crear tablas si no existen
Base.metadata.create_all(bind=engine)

# UTILIDADES

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = get_user(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(lambda: SessionLocal())) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(db, username=username)
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    return user

# ROUTER PRINCIPAL CON PREFIJO /api
api_router = APIRouter(prefix="/api")

# RUTAS DE AUTENTICACIÓN

@api_router.post("/auth/register", status_code=201)
async def register(username: str = Form(...), password: str = Form(...), db: Session = Depends(lambda: SessionLocal())):
    username = username.strip()
    if len(username) < 3 or len(password) < 6:
        raise HTTPException(status_code=400, detail="Nombre de usuario o contraseña demasiado cortos")
    user = get_user(db, username)
    if user:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya existe")
    hashed_password = get_password_hash(password)
    new_user = User(username=username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"msg": "Usuario registrado correctamente"}

@api_router.post("/auth/login")
async def login(username: str = Form(...), password: str = Form(...), db: Session = Depends(lambda: SessionLocal())):
    user = authenticate_user(db, username, password)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@api_router.get("/auth/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat(),
    }

# RUTA HEALTHCHECK
@api_router.get("/health")
async def health():
    return {"status": "ok"}

# RUTAS CRUD PROTEGIDAS (Ejemplos para Cotizaciones, Proyectos, Tareas, Gastos)

# --- Cotizaciones ---

from pydantic import BaseModel, Field

class CotizacionCreate(BaseModel):
    titulo: str = Field(..., max_length=150)
    descripcion: Optional[str] = ""
    cliente: Optional[str] = ""
    estado: Optional[str] = "pendiente"
    total: Optional[float] = 0.0

class CotizacionUpdate(BaseModel):
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    cliente: Optional[str] = None
    estado: Optional[str] = None
    total: Optional[float] = None

class CotizacionOut(BaseModel):
    id: int
    titulo: str
    descripcion: str
    cliente: str
    fecha_creacion: datetime
    estado: str
    total: float

    class Config:
        orm_mode = True

@api_router.post("/cotizaciones", response_model=CotizacionOut)
async def create_cotizacion(cotizacion: CotizacionCreate, current_user: User = Depends(get_current_user), db: Session = Depends(lambda: SessionLocal())):
    db_cot = Cotizacion(
        titulo=cotizacion.titulo,
        descripcion=cotizacion.descripcion or "",
        cliente=cotizacion.cliente or "",
        estado=cotizacion.estado or "pendiente",
        total=cotizacion.total or 0.0,
        owner_id=current_user.id,
    )
    db.add(db_cot)
    db.commit()
    db.refresh(db_cot)
    return db_cot

@api_router.get("/cotizaciones", response_model=List[CotizacionOut])
async def list_cotizaciones(current_user: User = Depends(get_current_user), db: Session = Depends(lambda: SessionLocal())):
    cotizaciones = db.query(Cotizacion).filter(Cotizacion.owner_id == current_user.id).order_by(Cotizacion.fecha_creacion.desc()).all()
    return cotizaciones

@api_router.get("/cotizaciones/{cot_id}", response_model=CotizacionOut)
async def get_cotizacion(cot_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(lambda: SessionLocal())):
    cot = db.query(Cotizacion).filter(Cotizacion.id == cot_id, Cotizacion.owner_id == current_user.id).first()
    if not cot:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    return cot

@api_router.put("/cotizaciones/{cot_id}", response_model=CotizacionOut)
async def update_cotizacion(cot_id: int, cotizacion: CotizacionUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(lambda: SessionLocal())):
    cot = db.query(Cotizacion).filter(Cotizacion.id == cot_id, Cotizacion.owner_id == current_user.id).first()
    if not cot:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    update_data = cotizacion.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(cot, key, value)
    db.commit()
    db.refresh(cot)
    return cot

@api_router.delete("/cotizaciones/{cot_id}", status_code=204)
async def delete_cotizacion(cot_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(lambda: SessionLocal())):
    cot = db.query(Cotizacion).filter(Cotizacion.id == cot_id, Cotizacion.owner_id == current_user.id).first()
    if not cot:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    db.delete(cot)
    db.commit()
    return JSONResponse(status_code=204, content=None)

# --- Proyectos ---

class ProyectoCreate(BaseModel):
    nombre: str = Field(..., max_length=150)
    descripcion: Optional[str] = ""
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None
    estado: Optional[str] = "activo"

class ProyectoUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None
    estado: Optional[str] = None

class ProyectoOut(BaseModel):
    id: int
    nombre: str
    descripcion: str
    fecha_inicio: datetime
    fecha_fin: Optional[datetime]
    estado: str

    class Config:
        orm_mode = True

@api_router.post("/proyectos", response_model=ProyectoOut)
async def create_proyecto(proyecto: ProyectoCreate, current_user: User = Depends(get_current_user), db: Session = Depends(lambda: SessionLocal())):
    db_proy = Proyecto(
        nombre=proyecto.nombre,
        descripcion=proyecto.descripcion or "",
        fecha_inicio=proyecto.fecha_inicio or datetime.utcnow(),
        fecha_fin=proyecto.fecha_fin,
        estado=proyecto.estado or "activo",
        owner_id=current_user.id,
    )
    db.add(db_proy)
    db.commit()
    db.refresh(db_proy)
    return db_proy

@api_router.get("/proyectos", response_model=List[ProyectoOut])
async def list_proyectos(current_user: User = Depends(get_current_user), db: Session = Depends(lambda: SessionLocal())):
    proyectos = db.query(Proyecto).filter(Proyecto.owner_id == current_user.id).order_by(Proyecto.fecha_inicio.desc()).all()
    return proyectos

@api_router.get("/proyectos/{proy_id}", response_model=ProyectoOut)
async def get_proyecto(proy_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(lambda: SessionLocal())):
    proy = db.query(Proyecto).filter(Proyecto.id == proy_id, Proyecto.owner_id == current_user.id).first()
    if not proy:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return proy

@api_router.put("/proyectos/{proy_id}", response_model=ProyectoOut)
async def update_proyecto(proy_id: int, proyecto: ProyectoUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(lambda: SessionLocal())):
    proy = db.query(Proyecto).filter(Proyecto.id == proy_id, Proyecto.owner_id == current_user.id).first()
    if not proy:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    update_data = proyecto.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(proy, key, value)
    db.commit()
    db.refresh(proy)
    return proy

@api_router.delete("/proyectos/{proy_id}", status_code=204)
async def delete_proyecto(proy_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(lambda: SessionLocal())):
    proy = db.query(Proyecto).filter(Proyecto.id == proy_id, Proyecto.owner_id == current_user.id).first()
    if not proy:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    db.delete(proy)
    db.commit()
    return JSONResponse(status_code=204, content=None)

# --- Tareas ---

class TareaCreate(BaseModel):
    titulo: str = Field(..., max_length=150)
    descripcion: Optional[str] = ""
    fecha_vencimiento: Optional[datetime] = None

class TareaUpdate(BaseModel):
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    fecha_vencimiento: Optional[datetime] = None
    completada: Optional[bool] = None

class TareaOut(BaseModel):
    id: int
    titulo: str
    descripcion: str
    fecha_creacion: datetime
    fecha_vencimiento: Optional[datetime]
    completada: bool

    class Config:
        orm_mode = True

@api_router.post("/tareas", response_model=TareaOut)
async def create_tarea(tarea: TareaCreate, current_user: User = Depends(get_current_user), db: Session = Depends(lambda: SessionLocal())):
    db_tarea = Tarea(
        titulo=tarea.titulo,
        descripcion=tarea.descripcion or "",
        fecha_vencimiento=tarea.fecha_vencimiento,
        owner_id=current_user.id,
    )
    db.add(db_tarea)
    db.commit()
    db.refresh(db_tarea)
    return db_tarea

@api_router.get("/tareas", response_model=List[TareaOut])
async def list_tareas(current_user: User = Depends(get_current_user), db: Session = Depends(lambda: SessionLocal())):
    tareas = db.query(Tarea).filter(Tarea.owner_id == current_user.id).order_by(Tarea.fecha_creacion.desc()).all()
    return tareas

@api_router.get("/tareas/{tarea_id}", response_model=TareaOut)
async def get_tarea(tarea_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(lambda: SessionLocal())):
    tarea = db.query(Tarea).filter(Tarea.id == tarea_id, Tarea.owner_id == current_user.id).first()
    if not tarea:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return tarea

@api_router.put("/tareas/{tarea_id}", response_model=TareaOut)
async def update_tarea(tarea_id: int, tarea: TareaUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(lambda: SessionLocal())):
    db_tarea = db.query(Tarea).filter(Tarea.id == tarea_id, Tarea.owner_id == current_user.id).first()
    if not db_tarea:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    update_data = tarea.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_tarea, key, value)
    db.commit()
    db.refresh(db_tarea)
    return db_tarea

@api_router.delete("/tareas/{tarea_id}", status_code=204)
async def delete_tarea(tarea_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(lambda: SessionLocal())):
    tarea = db.query(Tarea).filter(Tarea.id == tarea_id, Tarea.owner_id == current_user.id).first()
    if not tarea:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    db.delete(tarea)
    db.commit()
    return JSONResponse(status_code=204, content=None)

# --- Gastos ---

class GastoCreate(BaseModel):
    concepto: str = Field(..., max_length=150)
    monto: float
    fecha: Optional[datetime] = None
    descripcion: Optional[str] = ""

class GastoUpdate(BaseModel):
    concepto: Optional[str] = None
    monto: Optional[float] = None
    fecha: Optional[datetime] = None
    descripcion: Optional[str] = None

class GastoOut(BaseModel):
    id: int
    concepto: str
    monto: float
    fecha: datetime
    descripcion: str

    class Config:
        orm_mode = True

@api_router.post("/gastos", response_model=GastoOut)
async def create_gasto(gasto: GastoCreate, current_user: User = Depends(get_current_user), db: Session = Depends(lambda: SessionLocal())):
    db_gasto = Gasto(
        concepto=gasto.concepto,
        monto=gasto.monto,
        fecha=gasto.fecha or datetime.utcnow(),
        descripcion=gasto.descripcion or "",
        owner_id=current_user.id,
    )
    db.add(db_gasto)
    db.commit()
    db.refresh(db_gasto)
    return db_gasto

@api_router.get("/gastos", response_model=List[GastoOut])
async def list_gastos(current_user: User = Depends(get_current_user), db: Session = Depends(lambda: SessionLocal())):
    gastos = db.query(Gasto).filter(Gasto.owner_id == current_user.id).order_by(Gasto.fecha.desc()).all()
    return gastos

@api_router.get("/gastos/{gasto_id}", response_model=GastoOut)
async def get_gasto(gasto_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(lambda: SessionLocal())):
    gasto = db.query(Gasto).filter(Gasto.id == gasto_id, Gasto.owner_id == current_user.id).first()
    if not gasto:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    return gasto

@api_router.put("/gastos/{gasto_id}", response_model=GastoOut)
async def update_gasto(gasto_id: int, gasto: GastoUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(lambda: SessionLocal())):
    db_gasto = db.query(Gasto).filter(Gasto.id == gasto_id, Gasto.owner_id == current_user.id).first()
    if not db_gasto:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    update_data = gasto.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_gasto, key, value)
    db.commit()
    db.refresh(db_gasto)
    return db_gasto

@api_router.delete("/gastos/{gasto_id}", status_code=204)
async def delete_gasto(gasto_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(lambda: SessionLocal())):
    gasto = db.query(Gasto).filter(Gasto.id == gasto_id, Gasto.owner_id == current_user.id).first()
    if not gasto:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    db.delete(gasto)
    db.commit()
    return JSONResponse(status_code=204, content=None)

# Incluir router en la app principal
app.include_router(api_router)