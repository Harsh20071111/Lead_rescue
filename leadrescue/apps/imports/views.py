import io
import logging
import re
import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from kombu.exceptions import OperationalError

from .models import ImportJob
from .tasks import process_import_job
from .services.column_matcher import match_columns

logger = logging.getLogger(__name__)

def _normalize(text):
    return re.sub(r'[^a-z0-9]', '', str(text).lower())


def _get_fields(target_model):
    if target_model == ImportJob.TargetModel.LEAD:
        return ['name', 'phone'], ['email', 'budget', 'bhk', 'location', 'source', 'status', 'notes']
    return ['title', 'price', 'city'], ['locality', 'bhk', 'description']


def _read_headers_from_bytes(file_bytes, filename):
    """Read headers from in-memory file bytes."""
    buf = io.BytesIO(file_bytes)
    filename = filename.lower()
    if filename.endswith('.csv'):
        df = pd.read_csv(buf, nrows=0)
    else:
        df = pd.read_excel(buf, nrows=0)
    return list(df.columns)


def _queue_import_job(job):
    try:
        process_import_job.delay(job.id)
    except Exception as e:
        logger.error(f"Failed to queue import job {job.id}: {e}")
        from django.conf import settings
        if settings.DEBUG:
            logger.warning(f"Processing import job {job.id} inline due to broker failure.")
            process_import_job(job.id)
        else:
            job.status = ImportJob.Status.FAILED
            job.error_log.append({"row": 0, "error": f"Task queue (Redis) unavailable: {e}. Please check REDIS_URL."})
            job.save(update_fields=['status', 'error_log'])

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
        required_fields, optional_fields = _get_fields(target_model)
        auto_mapped, confidences = match_columns(headers, required_fields + optional_fields)

        # If all required fields matched, skip the mapping UI entirely
        if all(req in auto_mapped for req in required_fields):
            job.column_mapping = auto_mapped
            job.status = ImportJob.Status.PENDING
            job.save(update_fields=['column_mapping', 'status'])
            _queue_import_job(job)
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
    auto_mapped, confidences = match_columns(headers, required_fields + optional_fields)

    if request.method == "POST":
        mapping = {}
        for key in request.POST:
            if key.startswith("map_") and request.POST[key]:
                mapping[key[4:]] = request.POST[key]

        job.column_mapping = mapping
        job.status = ImportJob.Status.PENDING
        job.save(update_fields=['column_mapping', 'status'])
        _queue_import_job(job)
        return redirect("imports:import_progress", job_id=job.id)

    req_data = [{"name": f, "label": f.replace('_', ' ').title(), "auto_mapped": auto_mapped.get(f, ""), "confidence": confidences.get(f, 0)} for f in required_fields]
    opt_data = [{"name": f, "label": f.replace('_', ' ').title(), "auto_mapped": auto_mapped.get(f, ""), "confidence": confidences.get(f, 0)} for f in optional_fields]

    # Pre-generate mapping text for transparency
    auto_mapping_summary = []
    for f, header in auto_mapped.items():
        conf = confidences.get(f, 0)
        auto_mapping_summary.append({
            "header": header,
            "field": f.replace('_', ' ').title(),
            "confidence": round(conf * 100)
        })

    return render(request, "imports/mapping.html", {
        "job": job,
        "headers": headers,
        "required_fields": req_data,
        "optional_fields": opt_data,
        "auto_mapping_summary": auto_mapping_summary,
    })


@login_required
def import_progress(request, job_id):
    job = get_object_or_404(ImportJob, id=job_id, agency=request.user.agent_profile.agency)

    if request.htmx:
        return render(request, "imports/partials/progress_bar.html", {"job": job})

    return render(request, "imports/progress.html", {"job": job})


@login_required
def import_cancel(request, job_id):
    if request.method == "POST":
        job = get_object_or_404(ImportJob, id=job_id, agency=request.user.agent_profile.agency)
        if job.status in (ImportJob.Status.PENDING, ImportJob.Status.MAPPING, ImportJob.Status.PROCESSING):
            job.status = ImportJob.Status.CANCELED
            job.save(update_fields=['status'])
        return redirect("imports:import_progress", job_id=job.id)
    return redirect("imports:import_progress", job_id=job_id)
