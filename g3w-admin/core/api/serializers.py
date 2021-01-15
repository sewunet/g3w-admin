from django.conf import settings
from django.apps import apps
from django.contrib.gis.geos import GEOSGeometry, GEOSException
from django.contrib.gis.gdal import GDALException
from django.core.exceptions import ValidationError
from guardian.shortcuts import get_objects_for_user, get_user_model
from rest_framework import serializers
from rest_framework.fields import empty
from core.models import Group, BaseLayer
from core.signals import initconfig_plugin_start
from core.mixins.api.serializers import G3WRequestSerializer

from qgis.core import QgsCoordinateReferenceSystem
from copy import copy


def update_serializer_data(serializer_data, data):
    """
    update layerserializer data by type: update or append
    """
    # switch for operation_type:
    if data['operation_type'] == 'update':
        to_update = serializer_data[data['update_path']] if 'update_path' in data else serializer_data
        to_update.update(data['values'])
    elif data['operation_type'] == 'replace':
        serializer_data[data['replace_path']] = data['values']
    elif data['operation_type'] == 'append':
        if 'append_path' in data:
            if isinstance(data['append_path'], list):
                to_append = None
                for step in data['append_path']:
                    if not to_append:
                        to_append = serializer_data[step]
                    else:
                        to_append = to_append[step]
            else:
                to_append = serializer_data[data['append_path']]
            for value in data['values']:
                to_append.append(value)


class BaseLayerSerializer(serializers.ModelSerializer):
    """
    Serializer Class base for layer project
    """
    def to_representation(self, instance):
        ret = super(BaseLayerSerializer, self).to_representation(instance)
        ret.update(eval(instance.property))
        return ret

    class Meta:
        model = BaseLayer
        fields = (
            'id',
            'name',
            'title',
            'icon'
        )


class GroupSerializer(G3WRequestSerializer, serializers.ModelSerializer):
    """
    Serializer for Project Group
    """
    minscale = serializers.IntegerField(source='min_scale', read_only=True)
    maxscale = serializers.IntegerField(source='max_scale', read_only=True)
    crs = serializers.IntegerField(read_only=True)

    def __init__(self, instance=None, data=empty, **kwargs):
        self.projectId = kwargs['projectId']
        self.projectType = kwargs['projectType']
        del(kwargs['projectId'])
        del(kwargs['projectType'])
        super(GroupSerializer, self).__init__(instance, data, **kwargs)

    def to_representation(self, instance):
        ret = super(GroupSerializer, self).to_representation(instance)

        # add header_logo
        # before check macrogroups number anche if is equal to 1 use it
        try:
            macrogroup = instance.macrogroups.get(use_logo_client=True)
            ret['header_logo_img'] = macrogroup.logo_img.name
        except:
            ret['header_logo_img'] = instance.header_logo_img.name

        try:
            macrogroup = instance.macrogroups.get(use_title_client=True)
            ret['name'] = macrogroup.title
        except:
            # change groupData name with title for i18n app
            ret['name'] = instance.title

        # add crs:
        crs = QgsCoordinateReferenceSystem(f'EPSG:{self.instance.srid.srid}')

        ret['crs'] = {
            'epsg': crs.postgisSrid(),
            'proj4': crs.toProj4(),
            'geographic': crs.isGeographic(),
            'axisinverted': crs.hasAxisInverted()
        }

        # map controls
        ret['mapcontrols'] = [mapcontrol.name for mapcontrol in instance.mapcontrols.all()]

        # add projects to group
        ret['projects'] = []
        self.projects = {}

        anonymous_user = get_user_model().get_anonymous()

        for g3wProjectApp in settings.G3WADMIN_PROJECT_APPS:
            Project = apps.get_app_config(g3wProjectApp).get_model('project')
            projects = get_objects_for_user(self.request.user, '{}.view_project'.format(g3wProjectApp), Project) \
                .filter(group=instance)
            projects_anonymous = get_objects_for_user(anonymous_user, '{}.view_project'.format(g3wProjectApp),
                                                      Project).filter(group=instance)
            projects = list(set(projects) | set(projects_anonymous))
            for project in projects:
                self.projects[g3wProjectApp+'-'+str(project.id)] = project

                # project thumbnail
                project_thumb = project.thumbnail.name if bool(project.thumbnail.name) \
                    else '{}client/images/FakeProjectThumb.png'.format(settings.STATIC_URL)
                ret['projects'].append({
                    'id': project.id,
                    'title': project.title,
                    'description': project.description,
                    'thumbnail': project_thumb,
                    'type': g3wProjectApp,
                    'gid': "{}:{}".format(g3wProjectApp, project.id)
                })

        # baselayers
        ret['baselayers'] = []
        baselayers = instance.baselayers.all().order_by('order')
        for baselayer in baselayers:
            ret['baselayers'].append(BaseLayerSerializer(baselayer).data)

        # add vendorkeys if it is set into settings
        if settings.VENDOR_KEYS:
            ret['vendorkeys'] = settings.VENDOR_KEYS

        # add initproject and overviewproject
        ret['initproject'] = "{}:{}".format(self.projectType, self.projectId)

        # add overviewproject is present
        overviewproject = instance.project_panoramic.all()
        if overviewproject:
            overviewproject = overviewproject[0]
            ret['overviewproject'] = {
                'id': int(overviewproject.project_id),
                'type': overviewproject.project_type,
                'gid': "{}:{}".format(overviewproject.project_type, overviewproject.project_id)
            }
        else:
            ret['overviewproject'] = None

        ret['plugins'] = {}

        # plugins/module data
        dataPlugins = initconfig_plugin_start.send(sender=self, project=self.projectId, projectType=self.projectType)
        for dataPlugin in dataPlugins:
            if dataPlugin[1]:
                ret['plugins'] = copy(ret['plugins'])
                ret['plugins'].update(dataPlugin[1])

        # powerd_by
        ret['powered_by'] = settings.G3WSUITE_POWERD_BY

        # header customs links
        header_custom_links = getattr(settings, 'G3W_CLIENT_HEADER_CUSTOM_LINKS', None)
        ret['header_custom_links'] = []
        if header_custom_links:

            # check for possible callback
            for head_link in header_custom_links:
                if callable(head_link):
                    ret['header_custom_links'].append(head_link(self.request))
                else:
                    ret['header_custom_links'].append(head_link)

        # custom layout
        ret['layout'] = {}

        # add legend settings if set to layout
        layout_legend = getattr(settings, 'G3W_CLIENT_LEGEND', None)
        if layout_legend:
            ret['layout']['legend'] = layout_legend

        # add legend settings if set to layout
        layout_right_panel = getattr(settings, 'G3W_CLIENT_RIGHT_PANEL', None)
        if layout_right_panel:
            ret['layout']['rightpanel'] = layout_right_panel

        return ret

    class Meta:
        model = Group
        fields = (
            'id',
            'name',
            'slug',
            'minscale',
            'maxscale',
            'crs',
            'background_color',
            'header_logo_link',
            'header_terms_of_use_text',
            'header_terms_of_use_link'
        )


class G3WSerializerMixin(object):
    """
    Generic mixins for serializer model
    """

    relationsAttributes = None
    using_db = None

    def set_meta(self, kwargs):
        """
        Set meta properties for dinamical model
        :param kwargs: ditc params
        """
        self.Meta = self.Meta()
        self.Meta.model = kwargs['model']
        del (kwargs['model'])
        self.Meta.using = kwargs['using']
        del (kwargs['using'])

        if 'exclude' in kwargs:
            self.Meta.exclude = kwargs['exclude']
            del (kwargs['exclude'])

    def _get_meta_using(self):
        return self.Meta.using if hasattr(self.Meta, 'using') else None

    def create(self, validated_data):
        instance = self.Meta.model(**validated_data)
        instance.save(using=self._get_meta_using())
        return instance

    def update(self, instance, validated_data):
        using = self.Meta.using if hasattr(self.Meta, 'using') else None
        for field, value in list(validated_data.items()):
            setattr(instance, field, value)
        instance.save(using=self._get_meta_using())
        return instance

    @classmethod
    def delete(cls, instance):
        """
        Classmethod to delete model instance
        """
        instance.delete()