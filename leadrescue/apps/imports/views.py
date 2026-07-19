import io
import re
import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from .models import ImportJob
from .tasks import process_import_job


# ──────────────────────────────────────────────
# Smart Column-Mapping Engine
# ──────────────────────────────────────────────

LEAD_FIELD_ALIASES = {
    'name':     ['name', 'fullname', 'leadname', 'clientname', 'customername', 'contactname', 'firstname'],
    'phone':    ['phone', 'phonenumber', 'mobile', 'mobilenumber', 'contact', 'contactnumber', 'cell', 'whatsapp'],
    'email':    ['email', 'emailaddress', 'emailid', 'mail'],
    'budget':   ['budget', 'budgetinr', 'amount', 'budgetrange'],
    'bhk':      ['bhk', 'preferredbhk', 'bhkpreference', 'bedrooms', 'beds', 'rooms'],
    'location': ['location', 'city', 'area', 'locality', 'preferredlocation', 'areapreference', 'address', 'place'],
    'source':   ['source', 'leadsource', 'platform', 'channel', 'medium'],
    'status':   ['status', 'leadstatus', 'stage'],
    'notes':    ['notes', 'note', 'remark', 'remarks', 'comment', 'comments', 'description'],
}

PROPERTY_FIELD_ALIASES = {
    'title':       ['title', 'propertytitle', 'propertyname', 'name', 'heading'],
    'price':       ['price', 'amount', 'cost', 'rate', 'value', 'askingprice', 'sellingprice'],
    'city':        ['city', 'location', 'place', 'town'],
    'locality':    ['locality', 'area', 'sector', 'neighborhood', 'neighbourhood', 'subarea'],
    'bhk':         ['bhk', 'bedrooms', 'beds', 'rooms', 'configuration', 'type'],
    'description': ['description', 'desc', 'details', 'info', 'about', 'notes'],
}


def _normalize(text):
    return re.sub(r'[^a-z0-9]', '', str(text).lower())


def _auto_map_columns(headers, target_model):
    """
    3-pass intelligent column mapper:
      Pass 1: Exact normalized match
      Pass 2: Alias is a substring of header
      Pass 3: Header is a substring of alias (min 3 chars)
    """
    alias_map = LEAD_FIELD_ALIASES if target_model == ImportJob.TargetModel.LEAD else PROPERTY_FIELD_ALIASES
    mapped = {}
    used_headers = set()
    norm_headers = {h: _normalize(h) for h in headers}

    # Pass 1: Exact match
    for field, aliases in alias_map.items():
        for header, norm_h in norm_headers.items():
            if header in used_headers:
                continue
            if norm_h in aliases:
                mapped[field] = header
                used_headers.add(header)
                break

    # Pass 2: Alias contained in header (e.g. "budgetinr" in "budgetinr")
    for field, aliases in alias_map.items():
        if field in mapped:
            continue
        for header, norm_h in norm_headers.items():
            if header in used_headers:
                continue
            for alias in aliases:
                if alias in norm_h:
                    mapped[field] = header
                    used_headers.add(header)
                    break
            if field in mapped:
                break

    # Pass 3: Header found inside an alias
    for field, aliases in alias_map.items():
        if field in mapped:
            continue
        for header, norm_h in norm_headers.items():
            if header in used_headers or len(norm_h) < 3:
                continue
            for alias in aliases:
                if norm_h in alias:
                    mapped[field] = header
                    used_headers.add(header)
                    break
            if field in mapped:
                break

    return mapped


def _get_fields(target_model):
    if target_model == ImportJob.TargetModel.LEAD:
        return ['name', 'phone'], ['email', 'budget', 'bhk', 'location', 'source', 'status', 'notes']
    return ['title', 'price', 'city'], ['locality', 'bhk', 'description']


def _read_headers_from_bytes(file_bytes, filename):
    """Read headers from in-memory file bytes."""
    buf = io.BytesIO(file_bytes)
    if filename.endswith('.csv'):
        df = pd.read_csv(buf, nrows=0)
    else:
        df = pd.read_excel(buf, nrows=0)
    return list(df.columns)


# ──────────────────────────────────────────────
# Views
# ──────────────────────────────────────────────

@login_required
def import_upload(request):
    if request.method == "POST":
        target_model = request.POST.get("target_model")
        uploaded_file = request.FILES.get("file")
        if not target_model or not uploaded_file:
            return render(request, "imports/upload.html", {"error": "Target model and file are required."})

        # Read file content into memory BEFORE Django sends it to Cloudinary
        file_bytes = uploaded_file.read()
        uploaded_file.seek(0)  # Reset so Django can still save to Cloudinary

        # Read headers from the in-memory bytes
        try:
            headers = _read_headers_from_bytes(file_bytes, uploaded_file.name)
        except Exception as e:
            return render(request, "imports/upload.html", {"error": f"Cannot read file: {e}"})

        # Create the ImportJob (file goes to Cloudinary)
        job = ImportJob.objects.create(
            agency=request.user.agent_profile.agency,
            initiated_by=request.user.agent_profile,
            target_model=target_model,
            file=uploaded_file,
            cached_headers=headers,
            status=ImportJob.Status.MAPPING
        )

        # Save the Cloudinary URL for later download by Celery
        try:
            job.file_url = job.file.url
            job.save(update_fields=['file_url'])
        except Exception:
            pass  # URL will be empty; tasks will fall back to file.open()

        # Auto-map columns
        auto_mapped = _auto_map_columns(headers, target_model)
        required_fields, _ = _get_fields(target_model)

        # If all required fields matched, skip the mapping UI entirely
        if all(req in auto_mapped for req in required_fields):
            job.column_mapping = auto_mapped
            job.status = ImportJob.Status.PROCESSING
            job.save(update_fields=['column_mapping', 'status'])
            process_import_job.delay(job.id)
            return redirect("imports:import_progress", job_id=job.id)

        return redirect("imports:import_mapping", job_id=job.id)

    return render(request, "imports/upload.html")


@login_required
def import_mapping(request, job_id):
    job = get_object_or_404(ImportJob, id=job_id, agency=request.user.agent_profile.agency)
    if job.status not in (ImportJob.Status.MAPPING, ImportJob.Status.PENDING):
        return redirect("imports:import_progress", job_id=job.id)

    # Use cached headers (saved during upload)
    headers = job.cached_headers or []
    if not headers:
        return render(request, "imports/mapping.html", {
            "error": "Could not read file headers. Please re-upload.", "job": job
        })

    required_fields, optional_fields = _get_fields(job.target_model)
    auto_mapped = _auto_map_columns(headers, job.target_model)

    if request.method == "POST":
        mapping = {}
        for key in request.POST:
            if key.startswith("map_") and request.POST[key]:
                mapping[key[4:]] = request.POST[key]

        job.column_mapping = mapping
        job.status = ImportJob.Status.PROCESSING
        job.save(update_fields=['column_mapping', 'status'])
        process_import_job.delay(job.id)
        return redirect("imports:import_progress", job_id=job.id)

    req_data = [{"name": f, "label": f.replace('_', ' ').title(), "auto_mapped": auto_mapped.get(f, "")} for f in required_fields]
    opt_data = [{"name": f, "label": f.replace('_', ' ').title(), "auto_mapped": auto_mapped.get(f, "")} for f in optional_fields]

    return render(request, "imports/mapping.html", {
        "job": job,
        "headers": headers,
        "required_fields": req_data,
        "optional_fields": opt_data,
    })


@login_required
def import_progress(request, job_id):
    job = get_object_or_404(ImportJob, id=job_id, agency=request.user.agent_profile.agency)

    if request.htmx:
        return render(request, "imports/partials/progress_bar.html", {"job": job})

    return render(request, "imports/progress.html", {"job": job})
