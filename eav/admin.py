"""This module contains classes used for admin integration."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, ClassVar, Dict, List, Union

from django.contrib import admin
from django.contrib.admin.options import InlineModelAdmin, ModelAdmin
from django.forms.models import BaseInlineFormSet
from django.utils.safestring import mark_safe

from eav.models import Attribute, EnumGroup, EnumValue, Value

_FIELDSET_TYPE = List[Union[str, Dict[str, Any]]]  # type: ignore[misc]

some_attribute = ClassVar[Dict[str, str]]


class BaseEntityAdmin(ModelAdmin):
    """Custom admin model to support dynamic EAV fieldsets.

    Overrides the default rendering of the change form in the Django admin to
    dynamically integrate EAV fields into the form fieldsets. This approach
    allows EAV attributes to be rendered alongside standard model fields within
    the admin interface.

    Attributes:
        eav_fieldset_title (str): Title for the dynamically added EAV fieldset.
        eav_fieldset_description (str): Optional description for the EAV fieldset.
    """

    eav_fieldset_title: str = "EAV Attributes"
    eav_fieldset_description: str | None = None

    def render_change_form(self, request, context, *args, **kwargs):
        """Dynamically modifies the admin form to include EAV fields.

        Identifies EAV fields associated with the instance being edited and
        dynamically inserts them into the admin form's fieldsets. This method
        ensures EAV fields are appropriately displayed in a dedicated fieldset
        and avoids field duplication.

        Args:
            request: HttpRequest object representing the current request.
            context: Dictionary containing context data for the form template.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            HttpResponse object representing the rendered change form.
        """
        form = context["adminform"].form

        # Identify EAV fields based on the form instance's configuration.
        eav_fields = self._get_eav_fields(form.instance)

        # # Fallback to default if no EAV fields exist
        if not eav_fields:
            return super().render_change_form(request, context, *args, **kwargs)

        # Get the non-EAV fieldsets and then append our own
        fieldsets = list(self.get_fieldsets(request, kwargs["obj"]))
        fieldsets.append(self._get_eav_fieldset(eav_fields))

        # Reconstruct the admin form with updated fieldsets.
        adminform = admin.helpers.AdminForm(
            form,
            fieldsets,
            # Clear prepopulated fields on a view-only form to avoid a crash.
            (
                self.prepopulated_fields
                if self.has_change_permission(request, kwargs["obj"])
                else {}
            ),
            readonly_fields=self.readonly_fields,
            model_admin=self,
        )
        media = mark_safe(context["media"] + adminform.media)  # noqa: S308
        context.update(adminform=adminform, media=media)

        return super().render_change_form(request, context, *args, **kwargs)

    def _get_eav_fields(self, instance) -> list[str]:
        """Retrieves a list of EAV field slugs for the given instance.

        Args:
            instance: The model instance for which EAV fields are determined.

        Returns:
            A list of strings representing the slugs of EAV fields.
        """
        entity = getattr(instance, instance._eav_config_cls.eav_attr)  # noqa: SLF001
        return list(entity.get_all_attributes().values_list("slug", flat=True))

    def _get_eav_fieldset(self, eav_fields) -> _FIELDSET_TYPE:
        """Constructs an EAV Attributes fieldset for inclusion in admin form fieldsets.

        Generates a list representing a fieldset specifically for Entity-Attribute-Value
        (EAV) fields, intended to be appended to the admin form's fieldsets
        configuration. This facilitates the dynamic inclusion of EAV fields within the
        Django admin interface by creating a designated section for these attributes.

        Args:
            eav_fields (List[str]): A list of slugs representing the EAV fields to be
                included in the EAV Attributes fieldset.
        """
        return [
            self.eav_fieldset_title,
            {"fields": eav_fields, "description": self.eav_fieldset_description},
        ]


class BaseEntityInlineFormSet(BaseInlineFormSet):
    """
    An inline formset that correctly initializes EAV forms.
    """

    def add_fields(self, form, index):
        if self.instance:
            setattr(form.instance, self.fk.name, self.instance)
            form._build_dynamic_fields()  # noqa: SLF001

        super().add_fields(form, index)


class BaseEntityInline(InlineModelAdmin):
    """
    Inline model admin that works correctly with EAV attributes. You should mix
    in the standard ``StackedInline`` or ``TabularInline`` classes in order to
    define formset representation, e.g.::

        class ItemInline(BaseEntityInline, StackedInline):
            model = Item
            form = forms.ItemForm

    .. warning:: ``TabularInline`` does *not* work out of the box. There is,
        however, a patched template ``admin/edit_inline/tabular.html`` bundled
        with EAV-Django. You can copy or symlink the ``admin`` directory to
        your templates search path (see Django documentation).
    """

    formset = BaseEntityInlineFormSet

    def get_fieldsets(self, request, obj=None):
        if self.declared_fieldsets:
            return self.declared_fieldsets

        formset = self.get_formset(request)
        fk_name = self.fk_name or formset.fk.name
        kw = {fk_name: obj} if obj else {}
        instance = self.model(**kw)
        form = formset.form(request.POST, instance=instance)

        return [(None, {"fields": form.fields.keys()})]


class AttributeAdmin(ModelAdmin):
    list_display = ("name", "slug", "datatype", "description")
    prepopulated_fields: ClassVar[dict[str, Sequence[str]]] = {"slug": ("name",)}


admin.site.register(Attribute, AttributeAdmin)
admin.site.register(EnumValue)
admin.site.register(EnumGroup)
admin.site.register(Value)
