import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Contact

app = FastAPI(title="Contact Management API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Contact Management Backend is running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response

# Helper function to convert MongoDB documents to JSON serializable dicts

def serialize_contact(doc: dict) -> dict:
    if not doc:
        return {}
    return {
        "id": str(doc.get("_id")),
        "name": doc.get("name"),
        "email": doc.get("email"),
        "phone": doc.get("phone"),
        "company": doc.get("company"),
        "notes": doc.get("notes"),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }

# API Models for updates
class ContactUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    notes: Optional[str] = None

# Routes
@app.post("/api/contacts", response_model=dict)
def create_contact(contact: Contact):
    try:
        inserted_id = create_document("contact", contact)
        return {"id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/contacts", response_model=List[dict])
def list_contacts(q: Optional[str] = None, limit: int = 100):
    try:
        filter_dict = {}
        if q:
            # Simple text search across name/email/phone using $regex
            regex = {"$regex": q, "$options": "i"}
            filter_dict = {"$or": [{"name": regex}, {"email": regex}, {"phone": regex}]}
        docs = get_documents("contact", filter_dict, limit)
        return [serialize_contact(d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/contacts/{contact_id}", response_model=dict)
def get_contact(contact_id: str):
    try:
        doc = db["contact"].find_one({"_id": ObjectId(contact_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Contact not found")
        return serialize_contact(doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/contacts/{contact_id}", response_model=dict)
def update_contact(contact_id: str, update: ContactUpdate):
    try:
        payload = {k: v for k, v in update.model_dump().items() if v is not None}
        if not payload:
            return {"updated": False}
        payload["updated_at"] = __import__("datetime").datetime.utcnow()
        res = db["contact"].update_one({"_id": ObjectId(contact_id)}, {"$set": payload})
        return {"updated": res.modified_count > 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/contacts/{contact_id}", response_model=dict)
def delete_contact(contact_id: str):
    try:
        res = db["contact"].delete_one({"_id": ObjectId(contact_id)})
        return {"deleted": res.deleted_count > 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
