from django.db import models
from django.conf import settings
from django.core.exceptions import FieldDoesNotExist


class DomainManager(models.Manager):
    """
    Определите экземпляр менеджера в классе вашей модели с помощью одного
    следующих обозначений::
        on_site = HostSiteManager()  # автоматически ищет site и sites
        on_site = HostSiteManager("author__site")
        on_site = HostSiteManager("author__blog__site")
        on_site = HostSiteManager("author__blog__site",
                                  select_related=False)
    Как использовать во view::
    def home_page(request):
        posts = BlogPost.on_site.by_request(request).all()
        return render(request, 'home_page.html', {'posts': posts})
    """
    use_in_migrations = False

    def __init__(self, field_name=None, select_related=True):
        super().__init__()
        self._field_name = field_name
        self._select_related = select_related
        self._depth = 1
        self._is_validated = False

    def _validate_field_name(self):
        field = None
        if self._field_name is not None:
            name_parts = self._field_name.split("__", 1)
            rel_depth = len(name_parts)
            if rel_depth > self._depth:
                self._depth = rel_depth
            field_name = name_parts[0]
            try:
                field = self.model._meta.get_field(field_name)
            except FieldDoesNotExist:
                pass
        else:
            for potential_name in ['site', 'sites']:
                try:
                    field = self.model._meta.get_field(potential_name)
                except FieldDoesNotExist:
                    field_name = None
                else:
                    self._field_name = field_name = potential_name
                    self._is_validated = True
                    break
        if field:
            if not isinstance(field, (models.ForeignKey,
                                      models.ManyToManyField)):
                raise TypeError("%s must be a ForeignKey or "
                                "ManyToManyField." % field_name)
        else:
            raise ValueError("%s couldn't find a field named %s in %s." %
                             (self.__class__.__name__, field_name,
                              self.model._meta.object_name))
        self._is_validated = True

    def get_queryset(self, site_id=None):
        if site_id is None:
            site_id = settings.SITE_ID
        if not self._is_validated:
            self._validate_field_name()
        qs = super().get_queryset()
        return qs.filter(**{'%s__id__exact' % self._field_name: site_id})

    def by_id(self, site_id=None):
        return self.get_queryset(site_id)

    def by_request(self, request):
        if not hasattr(request, "site") or request.site is None:
            return self.none()
        return self.by_site(request.site)

    def by_site(self, site):
        return self.by_id(site.id)
