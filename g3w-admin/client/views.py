from django.utils import six
from django.views.generic import TemplateView
from django.template import loader
from django.shortcuts import get_object_or_404
from django.http import Http404, HttpResponseForbidden
from django.conf import settings
from django.core.urlresolvers import reverse
from rest_framework.renderers import JSONRenderer
from core.api.serializers import GroupSerializer, Group
from django.contrib.auth.views import redirect_to_login
from django.apps import apps
from django.core.exceptions import PermissionDenied
from copy import deepcopy


class ClientView(TemplateView):

    template_name = "{}/index.html".format(settings.CLIENT_DEFAULT)
    project = None

    def dispatch(self, request, *args, **kwargs):

        # check permissions
        project_app = apps.get_app_config(kwargs['project_type'])
        Project = project_app.get_model('project')

        # get project model object
        self.project = Project.objects.get(pk=kwargs['project_id']) if 'project_id' in kwargs else \
            Project.objects.get(slug=kwargs['project_slug'])
        if not request.user.has_perm("{}.view_project".format(kwargs['project_type']), self.project):

            # redirect to login if Anonymous user
            if request.user.is_anonymous():
                return redirect_to_login(request.get_full_path(), settings.LOGIN_URL, 'next')
            else:
                raise PermissionDenied()

        return super(ClientView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        contextData = super(ClientView, self).get_context_data(**kwargs)

        # group serializer
        group = get_object_or_404(Group, slug=kwargs['group_slug'])
        groupSerializer = GroupSerializer(group, projectId=str(self.project.pk), projectType=kwargs['project_type'],
                                          request=self.request)

        groupData = deepcopy(groupSerializer.data)

        # choose client by querystring paramenters
        contextData['client_default'] = self.get_client_name()

        # add user login data
        u = self.request.user
        if not u.is_anonymous():
            user_data = JSONRenderer().render({
                'username': u.username,
                'first_name': u.first_name,
                'last_name': u.last_name,
                'groups': [g.name for g in u.groups.all()],
                'logout_url': reverse('logout'),
                'admin_url': reverse('home')
            })
        else:
            user_data = '{}'

        serializedGroup = JSONRenderer().render(groupData)
        if six.PY3:
            serializedGroup = str(serializedGroup, 'utf-8')

        # add baseUrl property
        contextData['group_config'] = 'var initConfig ={{ "staticurl":"{}", "client":"{}", ' \
                                      '"mediaurl":"{}", "user":{}, "group":{}, "baseurl":{} }}'.format(
            settings.STATIC_URL, "{}/".format(settings.CLIENT_DEFAULT), settings.MEDIA_URL, user_data, serializedGroup,
            "/{}".format(settings.SITE_PREFIX_URL if settings.SITE_PREFIX_URL else ''))

        # project by type(app)
        if not '{}-{}'.format(kwargs['project_type'], self.project.pk) in groupSerializer.projects.keys():
            raise Http404('No project type and/or project id present in group')

        # page title
        # todo: set page title by project name??
        contextData['page_title'] = 'g3w-client'

        return contextData
        
    def get_template_names(self):
        return '{}/index.html'.format(self.get_client_name())
        
    def get_client_name(self):
        if 'client' in self.request.GET and self.request.GET['client'] in settings.CLIENTS_AVAILABLE:
            client = self.request.GET['client']
            try:
                loader.get_template('{}/index.html'.format(client))
                return client
            except:
                return settings.CLIENT_DEFAULT
        return settings.CLIENT_DEFAULT

