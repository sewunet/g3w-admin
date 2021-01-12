# coding=utf-8
""""

.. note:: This program is free software; you can redistribute it and/or modify
    it under the terms of the Mozilla Public License 2.0.

"""

__author__ = 'lorenzetti@gis3w.it'
__date__ = '2020-09-16'
__copyright__ = 'Copyright 2015 - 2020, Gis3w'


from django.urls import reverse
from django.test import override_settings
from django.test.client import encode_multipart
from qdjango.tests.base import QdjangoTestBase, CoreGroup, File, G3WSpatialRefSys, QgisProject, setup_testing_user
from qdjango.models import Layer, SessionTokenFilter, SingleLayerConstraint, ConstraintExpressionRule
from rest_framework.test import APIClient
from guardian.shortcuts import assign_perm
from qplotly.utils import get_qplotlywidget_for_project
from qplotly.models import QplotlyWidget
from qplotly.utils.models import get_qplotlywidgets4layer
from .test_utils import CURRENT_PATH, QGS_FILE, TEST_BASE_PATH, get_data_plotly_settings_from_file, DATASOURCE_PATH
import json
import copy


@override_settings(
    LOAD_QPLOTLY_FROM_PROJECT=True
)
class QplotlyTestAPI(QdjangoTestBase):

    @classmethod
    def setUpClass(cls):
        super(QplotlyTestAPI, cls).setUpClass()

        cls.client = APIClient()

    @classmethod
    def setUpTestData(cls):
        # main project group
        cls.project_group = CoreGroup(name='Group1', title='Group1', header_logo_img='',
                                      srid=G3WSpatialRefSys.objects.get(auth_srid=4326))

        cls.project_group.save()

        qgis_project_file = File(open('{}{}{}'.format(CURRENT_PATH, TEST_BASE_PATH, QGS_FILE), 'r', encoding='utf-8'))

        # Replace name property with only file name without path to simulate UploadedFileWithId instance.
        qgis_project_file.name = qgis_project_file.name.split('/')[-1]
        cls.project = QgisProject(qgis_project_file)
        cls.project.group = cls.project_group
        cls.project.save()
        qgis_project_file.close()


        file = File(open(f'{DATASOURCE_PATH}cities_scatter_plot_wrong_source_layer_id.xml', 'r'))
        cls.wrong_settings_source_layer_id_xml = file.read()
        file.close()

        file = File(open(f'{DATASOURCE_PATH}countries_pie_plot_with_title.xml', 'r'))
        cls.countries_plot_xml = file.read()
        file.close()

        file = File(open(f'{DATASOURCE_PATH}cities_histogram_plot.xml', 'r'))
        cls.cities_histogram_plot_xml = file.read()
        file.close()

    @classmethod
    def tearDownClass(cls):
        cls.project.instance.delete()
        super().tearDownClass()



    def _testApiCall(self, view_name, args, kwargs={}, data=None, method='POST', username='admin01'):
        """Utility to make test calls for admin01 user"""

        path = reverse(view_name, args=args)
        if kwargs:
            path += '?'
            parts = []
            for k,v in kwargs.items():
                parts.append(k + '=' + v)
            path += '&'.join(parts)

        # Auth
        self.assertTrue(self.client.login(username=username, password=username))
        if data:
            if method == 'POST':
                response = self.client.post(path, data=data)
            elif method == 'PUT':
                response = self.client.put(path, data=data, content_type='application/json')
            self.assertTrue(response.status_code in (200, 201))
        else:
            if method == 'DELETE':
                response = self.client.delete(path)
                self.assertEqual(response.status_code, 204)
            else:
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
        self.client.logout()
        return response

    def test_save_settings(self):
        """test saving data plotly settings into db"""

        qplotly_widgets = get_qplotlywidget_for_project(self.project.instance)
        self.assertEqual(len(qplotly_widgets), 1)

        # check project fk is saved
        self.assertEqual(qplotly_widgets[0].project, self.project.instance)

    def test_initconfig_plugin_start(self):
        """Test data added to API client config"""

        response = self._testApiCall('group-map-config',
                      args=[self.project_group.slug, 'qdjango', self.project.instance.pk])

        jcontent = json.loads(response.content)

        # check qplotly into plugins section
        self.assertTrue('qplotly' in jcontent['group']['plugins'])

        plugin = jcontent['group']['plugins']['qplotly']

        self.assertEqual(plugin['gid'], 'qdjango:{}'.format(
            self.project.instance.pk))

        self.assertEqual(plugin['jsscripts'],
                         ["/static/qplotly/polyfill.min.js", "/static/qplotly/plotly-1.52.2.min.js"])

        self.assertEqual(len(plugin['plots']), 1)

        plugin_plot = plugin['plots'][0]

        self.assertEqual(plugin_plot['qgs_layer_id'], 'countries_d53dfb9a_98e1_4196_a601_eed9a33f47c3')
        self.assertEqual(plugin_plot['id'], get_qplotlywidget_for_project(self.project.instance)[0].pk)
        self.assertFalse(plugin_plot['selected_features_only'])
        self.assertFalse(plugin_plot['visible_features_only'])

        self.assertEqual(plugin_plot['plot']['type'], 'histogram')
        self.assertTrue('layout' in plugin_plot['plot'])
        self.assertEqual(plugin_plot['plot']['layout']['title'], '')

    def test_trace_api(self):
        """/qplotly/api/trace API"""

        qplotlywidget_id = QplotlyWidget.objects.all()[0].pk

        response = self._testApiCall('qplotly-api-trace', args=[
            self.project.instance.pk,
            qplotlywidget_id
        ])

        jcontent = json.loads(response.content)
        trace_data = json.loads(response.content)['data']

        self.assertEqual(len(trace_data), 1)
        self.assertEqual(trace_data[0]['type'], 'histogram')
        self.assertEqual(len(trace_data[0]['x']), 51)
        self.assertIn('Italia', trace_data[0]['x'])

        # With a session token filter
        # ---------------------------

        countries = Layer.objects.get(project_id=self.project.instance.pk, qgs_layer_id='countries_d53dfb9a_98e1_4196_a601_eed9a33f47c3')

        # create a token filter
        session_token = SessionTokenFilter.objects.create(user=self.test_user1) # as admin01
        session_filter = session_token.stf_layers.create(layer=countries, qgs_expr="NAME_IT = 'Albania'")

        response = self._testApiCall('qplotly-api-trace', args=[
            self.project.instance.pk,
            qplotlywidget_id
        ], kwargs={
            'filtertoken': session_token.token
        })

        jcontent = json.loads(response.content)
        trace_data = json.loads(response.content)['data']

        self.assertEqual(len(trace_data), 1)
        self.assertEqual(trace_data[0]['type'], 'histogram')
        self.assertEqual(len(trace_data[0]['x']), 1)
        self.assertNotIn('Italia', trace_data[0]['x'])

        # Geometry contraint layer
        # ------------------------
        constraint = SingleLayerConstraint(layer=countries, active=True)
        constraint.save()

        rule = ConstraintExpressionRule(constraint=constraint, user=self.test_user1,
                                        rule="intersects_bbox( $geometry,  geom_from_wkt( 'POLYGON((8 51, 11 51, 11 52, 11 52, 8 51))') )")
        rule.save()

        response = self._testApiCall('qplotly-api-trace', args=[
            self.project.instance.pk,
            qplotlywidget_id
        ])

        jcontent = json.loads(response.content)
        trace_data = json.loads(response.content)['data']

        self.assertEqual(len(trace_data), 1)
        self.assertEqual(trace_data[0]['type'], 'histogram')
        self.assertEqual(len(trace_data[0]['x']), 1)
        self.assertIn('Germania', trace_data[0]['x'])

        # add new plotly widget for cities layer
        # ======================================
        cities = self.project.instance.layer_set.get(qgs_layer_id='cities10000eu_399beab0_e385_4ce1_9b59_688d02930517')
        widget = QplotlyWidget.objects.create(
            xml=self.cities_histogram_plot_xml,
            datasource=cities.datasource,
            type='histogram',
            title='',
            project=self.project.instance
        )

        widget.layers.add(cities)

        response = self._testApiCall('qplotly-api-trace', args=[
            self.project.instance.pk,
            widget.pk
        ])

        jcontent = json.loads(response.content)
        trace_data = json.loads(response.content)['data']

        self.assertEqual(len(trace_data), 1)
        self.assertEqual(trace_data[0]['type'], 'histogram')
        self.assertEqual(len(trace_data[0]['x']), 8965)
        self.assertIn('IT', trace_data[0]['x'])
        self.assertIn('DE', trace_data[0]['x'])

        # check relation one to many
        response = self._testApiCall('qplotly-api-trace', args=[
            self.project.instance.pk,
            widget.pk
        ], kwargs={
            'relationonetomany': 'cities1000_ISO2_CODE_countries__ISOCODE|18'
        })

        jcontent = json.loads(response.content)
        trace_data = json.loads(response.content)['data']

        self.assertEqual(len(trace_data), 1)
        self.assertEqual(trace_data[0]['type'], 'histogram')
        self.assertEqual(len(trace_data[0]['x']), 1124)
        self.assertIn('IT', trace_data[0]['x'])
        self.assertNotIn('DE', trace_data[0]['x'])

        # test in_bbox filter
        # -------------------------------------

        response = self._testApiCall('qplotly-api-trace', args=[
            self.project.instance.pk,
            widget.pk
        ], kwargs={
            'in_bbox': '9.7,41.4,13.0,45.6'
        })

        jcontent = json.loads(response.content)
        trace_data = json.loads(response.content)['data']

        self.assertEqual(len(trace_data), 1)
        self.assertEqual(trace_data[0]['type'], 'histogram')
        self.assertEqual(len(trace_data[0]['x']), 329)
        self.assertIn('IT', trace_data[0]['x'])
        self.assertNotIn('DE', trace_data[0]['x'])

        widget.delete()


    def test_get_qplotlywidgets4layer(self):
        """Test for homonimous util function"""

        layer_city = self.project.instance.layer_set.get(qgs_layer_id='countries_d53dfb9a_98e1_4196_a601_eed9a33f47c3')

        widgets = get_qplotlywidgets4layer(layer_city)

        self.assertEqual(len(widgets), 1)

    def _check_constraints(self, jcontent):
        self.assertEqual(jcontent['results'][0]['pk'], 1)
        self.assertFalse(jcontent['results'][0]['selected_features_only'])
        self.assertFalse(jcontent['results'][0]['visible_features_only'])
        self.assertEqual(jcontent['results'][0]['type'], 'histogram')
        self.assertEqual(jcontent['results'][0]['title'], '')
        self.assertTrue(len(jcontent['results'][0]['layers'])==1)

    def test_widgets(self):
        """Test API"""

        jcontent = json.loads(self._testApiCall('qplotly-widget-api-list', [], {}).content)
        self.assertEqual(jcontent['count'], 1)
        self._check_constraints(jcontent)
        layer_pk = jcontent['results'][0]['layers'][0]

        jcontent = json.loads(self._testApiCall('qplotly-widget-api-filter-by-layer-id', [layer_pk], {}).content)
        self.assertEqual(jcontent['count'], 1)
        self._check_constraints(jcontent)


        # TEST API VALIDATION
        # -------------------
        self.client.login(username=self.test_admin1.username, password=self.test_admin1.username)
        url = reverse('qplotly-widget-api-list')
        response = self.client.post(url, data={})
        self.assertEqual(response.status_code, 400)

        # required xml and layers
        jvcontent = json.loads(response.content)
        self.assertFalse(jvcontent['result'])
        self.assertEqual(jvcontent['error']['code'], 'validation')
        self.assertIn('xml', jvcontent['error']['data'])
        self.assertIn('layers', jvcontent['error']['data'])

        data = copy.copy(jcontent['results'][0])
        data['title'] = 'Test title create'
        data['xml'] = self.wrong_settings_source_layer_id_xml
        response = self.client.post(url, data=data)

        self.assertEqual(response.status_code, 400)

        # source_layer_id != qgs_layer_id
        jvcontent = json.loads(response.content)
        self.assertFalse(jvcontent['result'])
        self.assertEqual(jvcontent['error']['code'], 'validation')
        self.assertIn('non_field_errors', jvcontent['error']['data'])


        self.client.logout()

        # TEST CREATE
        # -----------
        data = jcontent['results'][0]
        data['title'] = 'Test title create'
        del(data['pk'])
        del(data['project'])

        # change type for test
        data['type'] = 'pie'
        jcontent = json.loads(self._testApiCall('qplotly-widget-api-list', [], {}, data=data).content)
        self.assertEqual(jcontent['pk'], 4)
        self.assertEqual(jcontent['type'], 'pie')
        self.assertEqual(jcontent['title'], 'Test title create')

        # check project instance into qplotlywidget not saved
        self.assertIsNone(QplotlyWidget.objects.get(pk=jcontent['pk']).project)


        jcontent = json.loads(self._testApiCall('qplotly-widget-api-filter-by-layer-id', [layer_pk], {}).content)
        self.assertEqual(jcontent['count'], 2)

        # TEST UPDATE
        # -----------

        # change type for test
        data['type'] = 'scatter'
        jcontent = json.loads(self._testApiCall('qplotly-widget-api-detail', [self.project.instance.pk, 4], {}, data=data, method='PUT').content)
        self.assertEqual(jcontent['pk'], 4)
        self.assertEqual(jcontent['type'], 'scatter')

        jcontent = json.loads(self._testApiCall('qplotly-widget-api-filter-by-layer-id', [layer_pk], {}).content)
        self.assertEqual(jcontent['count'], 2)
        self.assertEqual(jcontent['results'][1]['type'], 'scatter')

        # TEST DELETE
        # -----------
        self._testApiCall('qplotly-widget-api-detail', [self.project.instance.pk, 4], {}, data=None, method='DELETE')

        jcontent = json.loads(self._testApiCall('qplotly-widget-api-filter-by-layer-id', [layer_pk], {}).content)
        self.assertEqual(jcontent['count'], 1)
        self.assertEqual(jcontent['results'][0]['type'], 'histogram')

        # TEST CREATE XML WITH TITLE
        # ----------------------------------------
        data = {
            'xml': self.countries_plot_xml,
            'layers': data['layers']
        }

        # change type for test
        jcontent = json.loads(self._testApiCall('qplotly-widget-api-list', [], {}, data=data).content)
        self.assertEqual(jcontent['pk'], 5)
        self.assertEqual(jcontent['type'], 'pie')
        self.assertEqual(jcontent['title'], 'Pie countries test')


    def test_acl_widgets(self):
        """Test API ACL"""

        jcontent = json.loads(self._testApiCall('qplotly-widget-api-list', [], {}).content)
        self.assertEqual(jcontent['count'], 1)
        self._check_constraints(jcontent)
        pk = jcontent['results'][0]['pk']
        layer_pk = jcontent['results'][0]['layers'][0]

        # as viewer1 without grant
        self.client.login(username=self.test_viewer1.username, password=self.test_viewer1.username)
        url = reverse('qplotly-widget-api-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.client.logout()

        self.client.login(username=self.test_viewer1.username, password=self.test_viewer1.username)
        url = reverse('qplotly-widget-api-filter-by-layer-id', args=[layer_pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.client.logout()

        # as editor1
        self.client.login(username=self.test_editor1.username, password=self.test_editor1.username)
        url = reverse('qplotly-widget-api-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.client.logout()

        self.client.login(username=self.test_editor1.username, password=self.test_editor1.username)
        url = reverse('qplotly-widget-api-filter-by-layer-id', args=[layer_pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.client.logout()

        # give project change permission
        # ------------------------------
        assign_perm('change_project', self.test_editor1, self.project.instance)

        self.client.login(username=self.test_editor1.username, password=self.test_editor1.username)
        url = reverse('qplotly-widget-api-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.client.logout()

        self.client.login(username=self.test_editor1.username, password=self.test_editor1.username)
        url = reverse('qplotly-widget-api-filter-by-layer-id', args=[layer_pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()

        self.client.login(username=self.test_editor1.username, password=self.test_editor1.username)
        url = reverse('qplotly-widget-api-detail', args=[self.project.instance.pk, pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.client.logout()

        self.client.login(username=self.test_viewer1.username, password=self.test_viewer1.username)
        url = reverse('qplotly-widget-api-detail', args=[self.project.instance.pk, pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.client.logout()

        # Create
        data = jcontent['results'][0]
        data['type'] = 'pie'
        self.client.login(username=self.test_editor1.username, password=self.test_editor1.username)
        url = reverse('qplotly-widget-api-list')
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)

        url = reverse('qplotly-widget-api-filter-by-layer-id', args=[layer_pk])
        data['title'] = 'Test create'
        response = self.client.post(url, data=data)
        pk = json.loads(response.content)['pk']
        self.assertEqual(response.status_code, 201)

        # udate
        url = reverse('qplotly-widget-api-detail', args=[self.project.instance.pk, pk])
        del(data['pk'])
        data['type'] = 'scatter'
        response = self.client.put(url, data=data, content_type='application/json')
        self.assertEqual(response.status_code, 200)

        # delete
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)

        self.client.logout()







