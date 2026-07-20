from django.db.models import Q
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView, View
from django.shortcuts import get_object_or_404
from django.http import HttpResponse

from apps.core.mixins import AgencyScopedViewMixin
from apps.leads.models import Lead
from apps.properties.forms import PropertyForm
from apps.properties.models import Property, PropertyImage


class PropertyListView(AgencyScopedViewMixin, ListView):
    model = Property
    template_name = "properties/property_list.html"
    context_object_name = "properties"
    paginate_by = 25

    def get_queryset(self):
        queryset = self.scope_queryset_for_profile(
            Property.objects.select_related("agency", "assigned_agent__user")
        ).order_by("-created_at")

        status = self.request.GET.get("status")
        listing_type = self.request.GET.get("listing_type")
        bhk = self.request.GET.get("bhk")
        city = self.request.GET.get("city")
        min_price = self.request.GET.get("min_price")
        max_price = self.request.GET.get("max_price")
        query = self.request.GET.get("q")

        if status:
            queryset = queryset.filter(status=status)
        if listing_type:
            queryset = queryset.filter(listing_type=listing_type)
        if bhk:
            queryset = queryset.filter(bhk=bhk)
        if city:
            queryset = queryset.filter(city__icontains=city)
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query)
                | Q(project_name__icontains=query)
                | Q(builder__icontains=query)
                | Q(locality__icontains=query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "is_owner": self.is_owner(),
                "status_choices": Property.PropertyStatus.choices,
                "listing_type_choices": Property.ListingType.choices,
                "bhk_choices": Property._meta.get_field("bhk").choices,
                "filters": self.request.GET,
            }
        )
        return context


class PropertyDetailView(AgencyScopedViewMixin, DetailView):
    model = Property
    template_name = "properties/property_detail.html"
    context_object_name = "property"

    def get_queryset(self):
        return self.scope_queryset_for_profile(
            Property.objects.select_related("agency", "assigned_agent__user")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.matching.services import match_leads_for_property

        linked_leads = Lead.objects.for_agency(self.agency).filter(
            linked_property=self.object
        ).select_related("assigned_agent__user")
        if not self.is_owner():
            linked_leads = linked_leads.filter(assigned_agent=self.agent_profile)

        lead_qs = self.scope_queryset_for_profile(Lead.objects.all())
        matching_leads = match_leads_for_property(self.object, qs=lead_qs)

        context["linked_leads"] = linked_leads
        context["matching_leads"] = matching_leads
        context["is_owner"] = self.is_owner()
        return context


class PropertyCreateView(AgencyScopedViewMixin, CreateView):
    model = Property
    form_class = PropertyForm
    template_name = "properties/property_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "agency": self.agency,
                "agent_profile": self.agent_profile,
                "is_owner": self.is_owner(),
                "request": self.request,
            }
        )
        return kwargs

    def get_success_url(self):
        return reverse("properties:detail", kwargs={"pk": self.object.pk})


class PropertyUpdateView(AgencyScopedViewMixin, UpdateView):
    model = Property
    form_class = PropertyForm
    template_name = "properties/property_form.html"

    def get_queryset(self):
        return self.scope_queryset_for_profile(Property.objects.select_related("agency"))

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "agency": self.agency,
                "agent_profile": self.agent_profile,
                "is_owner": self.is_owner(),
                "request": self.request,
            }
        )
        return kwargs

    def get_success_url(self):
        return reverse("properties:detail", kwargs={"pk": self.object.pk})


class PropertyDeleteView(AgencyScopedViewMixin, DeleteView):
    model = Property
    template_name = "properties/property_confirm_delete.html"
    success_url = reverse_lazy("properties:list")

    def get_queryset(self):
        return self.scope_queryset_for_profile(Property.objects.select_related("agency"))

class SetPrimaryImageView(AgencyScopedViewMixin, View):
    def post(self, request, *args, **kwargs):
        property_id = kwargs.get("pk")
        image_id = kwargs.get("image_id")
        prop = get_object_or_404(
            self.scope_queryset_for_profile(Property.objects.all()), pk=property_id
        )
        image = get_object_or_404(prop.images.all(), pk=image_id)
        image.is_primary = True
        image.save()
        return HttpResponse(status=200)

class DeleteImageView(AgencyScopedViewMixin, View):
    def delete(self, request, *args, **kwargs):
        property_id = kwargs.get("pk")
        image_id = kwargs.get("image_id")
        prop = get_object_or_404(
            self.scope_queryset_for_profile(Property.objects.all()), pk=property_id
        )
        image = get_object_or_404(prop.images.all(), pk=image_id)
        image.delete()
        return HttpResponse(status=200)
