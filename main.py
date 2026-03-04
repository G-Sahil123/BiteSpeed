from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import engine, get_db, Base
# import models  
from schemas import IdentifyRequest, IdentifyResponse
from crud import identify


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Bitespeed Identity Reconciliation",
    description="Links customer identities across multiple purchases for FluxKart.com",
    version="1.0.0",
)


@app.post("/identify", response_model=IdentifyResponse)
def identify_contact(payload: IdentifyRequest, db: Session = Depends(get_db)):
    if payload.email is None and payload.phoneNumber is None:
        raise HTTPException(
            status_code=400,
            detail="At least one of 'email' or 'phoneNumber' must be provided.",
        )

    result = identify(db, email=payload.email, phone=payload.phoneNumber)
    return result


@app.get("/health")
def health_check():
    return {"status": "ok"}