from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.accounts.models import AgentProfile
from apps.core.mixins import AgencyScopedViewMixin, OwnerRequiredMixin
from apps.leads.forms import ActivityForm, LeadAssignmentForm, LeadForm, TaskForm
from apps.leads.models import Activity, Lead, Task
from apps.properties.models import Property


class LeadListView(AgencyScopedViewMixin, ListView):
    model = Lead
    template_name = "leads/lead_list.html"
    context_object_name = "leads"
    paginate_by = 25

    def get_queryset(self):
        queryset = self.scope_queryset_for_profile(
            Lead.objects.select_related("agency", "assigned_agent__user", "linked_property")
        ).order_by("-created_at")

        status = self.request.GET.get("status")
        source = self.request.GET.get("source")
        assigned_agent = self.request.GET.get("assigned_agent")
        query = self.request.GET.get("q")

        if status:
            queryset = queryset.filter(status=status)
        if source:
            queryset = queryset.filter(source=source)
        if assigned_agent and self.is_owner():
            queryset = queryset.filter(assigned_agent_id=assigned_agent)
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(phone__icontains=query)
                | Q(email__icontains=query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "is_owner": self.is_owner(),
                "agents": self.get_agent_choices(),
                "status_choices": Lead.LeadStatus.choices,
                "source_choices": Lead.LeadSource.choices,
                "filters": self.request.GET,
            }
        )
        return context


class LeadDetailView(AgencyScopedViewMixin, DetailView):
    model = Lead
    template_name = "leads/lead_detail.html"
    context_object_name = "lead"

    def get_queryset(self):
        return self.scope_queryset_for_profile(
            Lead.objects.select_related("agency", "assigned_agent__user", "linked_property")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.matching.services import match_properties_for_lead

        activities = Activity.objects.for_agency(self.agency).filter(
            lead=self.object
        ).select_related("agent__user").order_by("-created_at")

        property_qs = self.scope_queryset_for_profile(Property.objects.all())
        matching_properties = match_properties_for_lead(self.object, qs=property_qs)

        context.update(
            {
                "activities": activities,
                "activity_form": ActivityForm(),
                "task_form": TaskForm(
                    agency=self.agency,
                    agent_profile=self.agent_profile,
                    is_owner=self.is_owner(),
                    initial={"assigned_agent": self.object.assigned_agent},
                ),
                "assignment_form": LeadAssignmentForm(instance=self.object, agency=self.agency)
                if self.is_owner()
                else None,
                "is_owner": self.is_owner(),
                "matching_properties": matching_properties,
            }
        )
        return context


class LeadCreateView(AgencyScopedViewMixin, CreateView):
    model = Lead
    form_class = LeadForm
    template_name = "leads/lead_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "agency": self.agency,
                "agent_profile": self.agent_profile,
                "is_owner": self.is_owner(),
            }
        )
        return kwargs

    def get_success_url(self):
        return reverse("leads:detail", kwargs={"pk": self.object.pk})


class LeadUpdateView(AgencyScopedViewMixin, UpdateView):
    model = Lead
    form_class = LeadForm
    template_name = "leads/lead_form.html"

    def get_queryset(self):
        return self.scope_queryset_for_profile(
            Lead.objects.select_related("agency", "assigned_agent__user", "linked_property")
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "agency": self.agency,
                "agent_profile": self.agent_profile,
                "is_owner": self.is_owner(),
            }
        )
        return kwargs

    def form_valid(self, form):
        old_status = self.get_queryset().get(pk=self.object.pk).status
        response = super().form_valid(form)
        if old_status != self.object.status:
            Activity.objects.create(
                agency=self.agency,
                lead=self.object,
                agent=self.agent_profile,
                activity_type=Activity.ActivityType.STATUS_CHANGE,
                content=f"Status changed: {old_status} -> {self.object.status}",
            )
        return response

    def get_success_url(self):
        return reverse("leads:detail", kwargs={"pk": self.object.pk})


class LeadDeleteView(AgencyScopedViewMixin, DeleteView):
    model = Lead
    template_name = "leads/lead_confirm_delete.html"
    success_url = reverse_lazy("leads:list")

    def get_queryset(self):
        return self.scope_queryset_for_profile(Lead.objects.select_related("agency"))


class LeadAssignView(OwnerRequiredMixin, UpdateView):
    model = Lead
    form_class = LeadAssignmentForm
    template_name = "leads/partials/assignment_form.html"

    def get_queryset(self):
        return Lead.objects.for_agency(self.agency).select_related("assigned_agent__user")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["agency"] = self.agency
        return kwargs

    def form_valid(self, form):
        old_agent = (
            Lead.objects.for_agency(self.agency)
            .select_related("assigned_agent__user")
            .get(pk=self.object.pk)
            .assigned_agent
        )
        response = super().form_valid(form)
        new_agent = self.object.assigned_agent
        if getattr(old_agent, "pk", None) != getattr(new_agent, "pk", None):
            old_name = old_agent.user.get_full_name() or old_agent.user.email if old_agent else "Unassigned"
            new_name = new_agent.user.get_full_name() or new_agent.user.email if new_agent else "Unassigned"
            Activity.objects.create(
                agency=self.agency,
                lead=self.object,
                agent=self.agent_profile,
                activity_type=Activity.ActivityType.STATUS_CHANGE,
                content=f"Reassigned from {old_name} to {new_name}",
            )
        if self.request.headers.get("HX-Request"):
            return render(
                self.request,
                "leads/partials/assignment_form.html",
                {"form": self.get_form(), "lead": self.object, "is_owner": True},
            )
        messages.success(self.request, "Lead assignment updated.")
        return redirect("leads:detail", pk=self.object.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["lead"] = self.object
        context["is_owner"] = True
        return context

    def get_success_url(self):
        return reverse("leads:detail", kwargs={"pk": self.object.pk})


@login_required
def add_activity(request, pk):
    profile = request.user.agent_profile
    agency = profile.agency
    queryset = Lead.objects.for_agency(agency)
    if profile.role != AgentProfile.Role.OWNER:
        queryset = queryset.filter(assigned_agent=profile)
    lead = get_object_or_404(queryset, pk=pk)

    if request.method != "POST":
        raise PermissionDenied

    form = ActivityForm(request.POST)
    if form.is_valid():
        activity = form.save(commit=False)
        activity.agency = agency
        activity.lead = lead
        activity.agent = profile
        activity.save()
        activities = Activity.objects.for_agency(agency).filter(
            lead=lead
        ).select_related("agent__user").order_by("-created_at")
        return render(
            request,
            "leads/partials/activity_timeline.html",
            {"activities": activities},
        )
    return render(request, "leads/partials/activity_form.html", {"form": form, "lead": lead})


@login_required
def add_task(request, pk):
    profile = request.user.agent_profile
    agency = profile.agency
    queryset = Lead.objects.for_agency(agency)
    if profile.role != AgentProfile.Role.OWNER:
        queryset = queryset.filter(assigned_agent=profile)
    lead = get_object_or_404(queryset, pk=pk)

    if request.method != "POST":
        raise PermissionDenied

    form = TaskForm(
        request.POST,
        agency=agency,
        agent_profile=profile,
        is_owner=profile.role == AgentProfile.Role.OWNER,
    )
    if form.is_valid():
        task = form.save(commit=False)
        task.lead = lead
        if not task.assigned_agent_id:
            task.assigned_agent = lead.assigned_agent or profile
        task.save()
        messages.success(request, "Follow-up created.")
    return redirect("leads:detail", pk=lead.pk)


class TaskListView(AgencyScopedViewMixin, ListView):
    model = Task
    template_name = "leads/task_list.html"
    context_object_name = "tasks"
    paginate_by = 25

    def get_queryset(self):
        queryset = Task.objects.filter(lead__agency=self.agency).select_related(
            "lead", "assigned_agent__user"
        )
        if not self.is_owner():
            queryset = queryset.filter(assigned_agent=self.agent_profile)

        assigned_agent = self.request.GET.get("assigned_agent")
        due = self.request.GET.get("due")
        today = timezone.localdate()

        if assigned_agent and self.is_owner():
            queryset = queryset.filter(assigned_agent_id=assigned_agent)
        if due == "missed":
            queryset = queryset.filter(is_completed=False, due_date__date__lt=today)
        elif due == "today":
            queryset = queryset.filter(is_completed=False, due_date__date=today)
        elif due == "upcoming":
            queryset = queryset.filter(is_completed=False, due_date__date__gt=today)
        return queryset.order_by("is_completed", "due_date")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tasks = list(context["tasks"])
        today = timezone.localdate()
        context.update(
            {
                "overdue_tasks": [
                    task for task in tasks if not task.is_completed and task.due_date.date() < today
                ],
                "today_tasks": [
                    task for task in tasks if not task.is_completed and task.due_date.date() == today
                ],
                "upcoming_tasks": [
                    task for task in tasks if not task.is_completed and task.due_date.date() > today
                ],
                "completed_tasks": [task for task in tasks if task.is_completed],
                "agents": self.get_agent_choices(),
                "is_owner": self.is_owner(),
            }
        )
        return context


@login_required
def complete_task(request, pk):
    profile = request.user.agent_profile
    agency = profile.agency
    queryset = Task.objects.filter(lead__agency=agency)
    if profile.role != AgentProfile.Role.OWNER:
        queryset = queryset.filter(assigned_agent=profile)
    task = get_object_or_404(queryset, pk=pk)

    if request.method != "POST":
        raise PermissionDenied

    task.is_completed = True
    task.save(update_fields=["is_completed"])
    if request.headers.get("HX-Request"):
        return render(request, "leads/partials/task_row.html", {"task": task})
    return redirect("leads:tasks")


@login_required
def link_property(request, lead_pk, property_pk):
    """Link a property to a lead and log an activity."""
    if request.method != "POST":
        raise PermissionDenied

    profile = request.user.agent_profile
    agency = profile.agency

    lead_queryset = Lead.objects.for_agency(agency)
    if profile.role != AgentProfile.Role.OWNER:
        lead_queryset = lead_queryset.filter(assigned_agent=profile)
    lead = get_object_or_404(lead_queryset, pk=lead_pk)

    property_obj = get_object_or_404(
        Property.objects.for_agency(agency), pk=property_pk
    )

    lead.linked_property = property_obj
    lead.save(update_fields=["linked_property"])

    Activity.objects.create(
        agency=agency,
        lead=lead,
        agent=profile,
        activity_type=Activity.ActivityType.NOTE,
        content=f"Linked property: {property_obj.title}",
    )

    messages.success(request, f"Linked {property_obj.title} to {lead.name}.")
    return redirect("leads:detail", pk=lead.pk)
