from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database.connection import get_db
from identity.auth import authenticate_request, get_or_create_authenticated_profile
from opportunities.models import JobApplication, JobPosting, MarketplaceInquiry, MarketplaceListing


router = APIRouter(tags=["jobs-marketplace"])


class JobCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    company: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=12000)
    location: str = Field(min_length=1, max_length=160)
    employment_type: str = Field(default="full_time", min_length=1, max_length=40)
    salary_min_npr: float | None = Field(default=None, ge=0, le=1_000_000_000_000)
    salary_max_npr: float | None = Field(default=None, ge=0, le=1_000_000_000_000)


class JobApplicationRequest(BaseModel):
    cover_note: str = Field(default="", max_length=5000)


class MarketplaceListingCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    category: str = Field(min_length=1, max_length=40)
    description: str = Field(min_length=1, max_length=12000)
    location: str = Field(min_length=1, max_length=160)
    price_npr: float = Field(gt=0, le=1_000_000_000_000)
    item_condition: str = Field(default="used", min_length=1, max_length=30)


class MarketplaceInquiryRequest(BaseModel):
    message: str = Field(min_length=1, max_length=3000)


def _profile_identity(claims: dict[str, Any]) -> tuple[str, str]:
    profile = get_or_create_authenticated_profile(claims)
    profile_id = str(profile.get("id") or "").strip()
    if not profile_id:
        raise HTTPException(status_code=401, detail="Authenticated profile could not be loaded.")
    display_name = str(profile.get("name") or claims.get("name") or "SAGE user").strip()
    return profile_id, display_name or "SAGE user"


def _clean(value: str, label: str) -> str:
    value = value.strip()
    if not value:
        raise HTTPException(status_code=422, detail=f"{label} is required.")
    return value


def _timestamp(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _job_dict(job: JobPosting) -> dict[str, Any]:
    return {
        "id": job.id,
        "employer_name": job.employer_name,
        "title": job.title,
        "company": job.company,
        "description": job.description,
        "location": job.location,
        "employment_type": job.employment_type,
        "salary_min_npr": job.salary_min_npr,
        "salary_max_npr": job.salary_max_npr,
        "status": job.status,
        "created_at": _timestamp(job.created_at),
    }


def _application_dict(application: JobApplication, job: JobPosting | None = None) -> dict[str, Any]:
    result = {
        "id": application.id,
        "job_id": application.job_id,
        "applicant_name": application.applicant_name,
        "cover_note": application.cover_note,
        "status": application.status,
        "created_at": _timestamp(application.created_at),
    }
    if job is not None:
        result["job"] = _job_dict(job)
    return result


def _listing_dict(listing: MarketplaceListing) -> dict[str, Any]:
    return {
        "id": listing.id,
        "seller_name": listing.seller_name,
        "title": listing.title,
        "category": listing.category,
        "description": listing.description,
        "location": listing.location,
        "price_npr": listing.price_npr,
        "item_condition": listing.item_condition,
        "status": listing.status,
        "created_at": _timestamp(listing.created_at),
    }


def _inquiry_dict(inquiry: MarketplaceInquiry, listing: MarketplaceListing | None = None) -> dict[str, Any]:
    result = {
        "id": inquiry.id,
        "listing_id": inquiry.listing_id,
        "buyer_name": inquiry.buyer_name,
        "message": inquiry.message,
        "status": inquiry.status,
        "created_at": _timestamp(inquiry.created_at),
    }
    if listing is not None:
        result["listing"] = _listing_dict(listing)
    return result


@router.get("/jobs")
def list_jobs(
    query: str | None = Query(default=None, max_length=160),
    location: str | None = Query(default=None, max_length=160),
    status: str = Query(default="open", pattern="^(open|closed|all)$"),
    limit: int = Query(default=50, ge=1, le=100),
    claims: dict[str, Any] = Depends(authenticate_request),
    db: Session = Depends(get_db),
):
    _profile_identity(claims)
    statement = db.query(JobPosting)
    if status != "all":
        statement = statement.filter(JobPosting.status == status)
    if query and query.strip():
        term = f"%{query.strip()}%"
        statement = statement.filter(
            JobPosting.title.ilike(term)
            | JobPosting.company.ilike(term)
            | JobPosting.description.ilike(term)
        )
    if location and location.strip():
        statement = statement.filter(JobPosting.location.ilike(f"%{location.strip()}%"))
    jobs = statement.order_by(JobPosting.created_at.desc()).limit(limit).all()
    return {"success": True, "jobs": [_job_dict(job) for job in jobs]}


@router.post("/jobs", status_code=201)
def create_job(
    request: JobCreateRequest,
    claims: dict[str, Any] = Depends(authenticate_request),
    db: Session = Depends(get_db),
):
    profile_id, display_name = _profile_identity(claims)
    title = _clean(request.title, "Job title")
    company = _clean(request.company, "Company")
    description = _clean(request.description, "Description")
    location = _clean(request.location, "Location")
    employment_type = _clean(request.employment_type, "Employment type").lower().replace(" ", "_")
    allowed_types = {"full_time", "part_time", "contract", "internship", "remote", "temporary"}
    if employment_type not in allowed_types:
        raise HTTPException(status_code=422, detail="Choose a supported employment type.")
    if (
        request.salary_min_npr is not None
        and request.salary_max_npr is not None
        and request.salary_max_npr < request.salary_min_npr
    ):
        raise HTTPException(status_code=422, detail="Maximum salary cannot be below minimum salary.")
    job = JobPosting(
        id=str(uuid.uuid4()),
        employer_profile_id=profile_id,
        employer_name=display_name,
        title=title,
        company=company,
        description=description,
        location=location,
        employment_type=employment_type,
        salary_min_npr=request.salary_min_npr,
        salary_max_npr=request.salary_max_npr,
        status="open",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return {"success": True, "job": _job_dict(job)}


@router.get("/jobs/mine")
def list_my_jobs(
    claims: dict[str, Any] = Depends(authenticate_request),
    db: Session = Depends(get_db),
):
    profile_id, _ = _profile_identity(claims)
    jobs = db.query(JobPosting).filter(
        JobPosting.employer_profile_id == profile_id
    ).order_by(JobPosting.created_at.desc()).all()
    return {"success": True, "jobs": [_job_dict(job) for job in jobs]}


@router.get("/jobs/applications/mine")
def list_my_job_applications(
    claims: dict[str, Any] = Depends(authenticate_request),
    db: Session = Depends(get_db),
):
    profile_id, _ = _profile_identity(claims)
    applications = db.query(JobApplication).filter(
        JobApplication.applicant_profile_id == profile_id
    ).order_by(JobApplication.created_at.desc()).all()
    items = []
    for application in applications:
        job = db.query(JobPosting).filter(JobPosting.id == application.job_id).first()
        items.append(_application_dict(application, job))
    return {"success": True, "applications": items}


@router.get("/jobs/{job_id}/applications")
def list_job_applications(
    job_id: str,
    claims: dict[str, Any] = Depends(authenticate_request),
    db: Session = Depends(get_db),
):
    profile_id, _ = _profile_identity(claims)
    job = db.query(JobPosting).filter(
        JobPosting.id == job_id,
        JobPosting.employer_profile_id == profile_id,
    ).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    applications = db.query(JobApplication).filter(
        JobApplication.job_id == job_id
    ).order_by(JobApplication.created_at.desc()).all()
    return {"success": True, "job": _job_dict(job), "applications": [_application_dict(item) for item in applications]}


@router.post("/jobs/{job_id}/applications", status_code=201)
def apply_for_job(
    job_id: str,
    request: JobApplicationRequest,
    claims: dict[str, Any] = Depends(authenticate_request),
    db: Session = Depends(get_db),
):
    profile_id, applicant_name = _profile_identity(claims)
    job = db.query(JobPosting).filter(JobPosting.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.status != "open":
        raise HTTPException(status_code=409, detail="This job is closed to applications.")
    if job.employer_profile_id == profile_id:
        raise HTTPException(status_code=409, detail="You cannot apply to your own job posting.")
    prior = db.query(JobApplication).filter(
        JobApplication.job_id == job_id,
        JobApplication.applicant_profile_id == profile_id,
    ).first()
    if prior is not None:
        raise HTTPException(status_code=409, detail="You have already applied to this job.")
    application = JobApplication(
        id=str(uuid.uuid4()),
        job_id=job_id,
        applicant_profile_id=profile_id,
        applicant_name=applicant_name,
        cover_note=request.cover_note.strip(),
        status="submitted",
    )
    db.add(application)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="You have already applied to this job.") from error
    db.refresh(application)
    return {"success": True, "application": _application_dict(application), "message": "Application submitted."}


@router.post("/jobs/{job_id}/close")
def close_job(
    job_id: str,
    claims: dict[str, Any] = Depends(authenticate_request),
    db: Session = Depends(get_db),
):
    profile_id, _ = _profile_identity(claims)
    job = db.query(JobPosting).filter(
        JobPosting.id == job_id,
        JobPosting.employer_profile_id == profile_id,
    ).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    job.status = "closed"
    db.commit()
    db.refresh(job)
    return {"success": True, "job": _job_dict(job)}


@router.get("/marketplace/listings")
def list_marketplace_listings(
    query: str | None = Query(default=None, max_length=160),
    category: str | None = Query(default=None, max_length=40),
    location: str | None = Query(default=None, max_length=160),
    status: str = Query(default="active", pattern="^(active|closed|all)$"),
    limit: int = Query(default=50, ge=1, le=100),
    claims: dict[str, Any] = Depends(authenticate_request),
    db: Session = Depends(get_db),
):
    _profile_identity(claims)
    statement = db.query(MarketplaceListing)
    if status != "all":
        statement = statement.filter(MarketplaceListing.status == status)
    if query and query.strip():
        term = f"%{query.strip()}%"
        statement = statement.filter(
            MarketplaceListing.title.ilike(term)
            | MarketplaceListing.description.ilike(term)
        )
    if category and category.strip():
        statement = statement.filter(MarketplaceListing.category == category.strip().lower())
    if location and location.strip():
        statement = statement.filter(MarketplaceListing.location.ilike(f"%{location.strip()}%"))
    listings = statement.order_by(MarketplaceListing.created_at.desc()).limit(limit).all()
    return {"success": True, "listings": [_listing_dict(item) for item in listings]}


@router.post("/marketplace/listings", status_code=201)
def create_marketplace_listing(
    request: MarketplaceListingCreateRequest,
    claims: dict[str, Any] = Depends(authenticate_request),
    db: Session = Depends(get_db),
):
    profile_id, display_name = _profile_identity(claims)
    title = _clean(request.title, "Listing title")
    category = _clean(request.category, "Category").lower()
    description = _clean(request.description, "Description")
    location = _clean(request.location, "Location")
    item_condition = _clean(request.item_condition, "Condition").lower().replace(" ", "_")
    allowed_categories = {"vehicles", "electronics", "property", "services", "courses", "home", "other"}
    allowed_conditions = {"new", "used", "service"}
    if category not in allowed_categories:
        raise HTTPException(status_code=422, detail="Choose a supported marketplace category.")
    if item_condition not in allowed_conditions:
        raise HTTPException(status_code=422, detail="Choose new, used, or service as the condition.")
    listing = MarketplaceListing(
        id=str(uuid.uuid4()),
        seller_profile_id=profile_id,
        seller_name=display_name,
        title=title,
        category=category,
        description=description,
        location=location,
        price_npr=request.price_npr,
        item_condition=item_condition,
        status="active",
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return {"success": True, "listing": _listing_dict(listing)}


@router.get("/marketplace/listings/mine")
def list_my_marketplace_listings(
    claims: dict[str, Any] = Depends(authenticate_request),
    db: Session = Depends(get_db),
):
    profile_id, _ = _profile_identity(claims)
    listings = db.query(MarketplaceListing).filter(
        MarketplaceListing.seller_profile_id == profile_id
    ).order_by(MarketplaceListing.created_at.desc()).all()
    return {"success": True, "listings": [_listing_dict(item) for item in listings]}


@router.get("/marketplace/inquiries/mine")
def list_my_marketplace_inquiries(
    claims: dict[str, Any] = Depends(authenticate_request),
    db: Session = Depends(get_db),
):
    profile_id, _ = _profile_identity(claims)
    inquiries = db.query(MarketplaceInquiry).filter(
        MarketplaceInquiry.buyer_profile_id == profile_id
    ).order_by(MarketplaceInquiry.created_at.desc()).all()
    items = []
    for inquiry in inquiries:
        listing = db.query(MarketplaceListing).filter(
            MarketplaceListing.id == inquiry.listing_id
        ).first()
        items.append(_inquiry_dict(inquiry, listing))
    return {"success": True, "inquiries": items}


@router.get("/marketplace/listings/{listing_id}/inquiries")
def list_listing_inquiries(
    listing_id: str,
    claims: dict[str, Any] = Depends(authenticate_request),
    db: Session = Depends(get_db),
):
    profile_id, _ = _profile_identity(claims)
    listing = db.query(MarketplaceListing).filter(
        MarketplaceListing.id == listing_id,
        MarketplaceListing.seller_profile_id == profile_id,
    ).first()
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found.")
    inquiries = db.query(MarketplaceInquiry).filter(
        MarketplaceInquiry.listing_id == listing_id
    ).order_by(MarketplaceInquiry.created_at.desc()).all()
    return {"success": True, "listing": _listing_dict(listing), "inquiries": [_inquiry_dict(item) for item in inquiries]}


@router.post("/marketplace/listings/{listing_id}/inquiries", status_code=201)
def create_marketplace_inquiry(
    listing_id: str,
    request: MarketplaceInquiryRequest,
    claims: dict[str, Any] = Depends(authenticate_request),
    db: Session = Depends(get_db),
):
    profile_id, buyer_name = _profile_identity(claims)
    listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found.")
    if listing.status != "active":
        raise HTTPException(status_code=409, detail="This listing is closed to inquiries.")
    if listing.seller_profile_id == profile_id:
        raise HTTPException(status_code=409, detail="You cannot inquire about your own listing.")
    prior = db.query(MarketplaceInquiry).filter(
        MarketplaceInquiry.listing_id == listing_id,
        MarketplaceInquiry.buyer_profile_id == profile_id,
    ).first()
    if prior is not None:
        raise HTTPException(status_code=409, detail="You have already contacted the seller about this listing.")
    message = _clean(request.message, "Message")
    inquiry = MarketplaceInquiry(
        id=str(uuid.uuid4()),
        listing_id=listing_id,
        buyer_profile_id=profile_id,
        buyer_name=buyer_name,
        message=message,
        status="open",
    )
    db.add(inquiry)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="You have already contacted the seller about this listing.") from error
    db.refresh(inquiry)
    return {"success": True, "inquiry": _inquiry_dict(inquiry), "message": "Interest sent to the seller."}


@router.get("/marketplace/listings/{listing_id}")
def get_marketplace_listing(
    listing_id: str,
    claims: dict[str, Any] = Depends(authenticate_request),
    db: Session = Depends(get_db),
):
    _profile_identity(claims)
    listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found.")
    return {"success": True, "listing": _listing_dict(listing)}


@router.post("/marketplace/listings/{listing_id}/close")
def close_marketplace_listing(
    listing_id: str,
    claims: dict[str, Any] = Depends(authenticate_request),
    db: Session = Depends(get_db),
):
    profile_id, _ = _profile_identity(claims)
    listing = db.query(MarketplaceListing).filter(
        MarketplaceListing.id == listing_id,
        MarketplaceListing.seller_profile_id == profile_id,
    ).first()
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found.")
    listing.status = "closed"
    db.commit()
    db.refresh(listing)
    return {"success": True, "listing": _listing_dict(listing)}
