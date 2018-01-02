import time
#from heatclient.common import template_utils
from api.v2.views.base import AuthViewSet, AuthOptionalViewSet

from core.models import AtmosphereUser, Identity
from keystoneauth1.identity import v3
from rtwo.drivers.openstack_network import NetworkManager
from rtwo.drivers.openstack_user import UserManager
from keystoneauth1 import session

from rest_framework.response import Response
from rest_framework import status

from rest_framework.decorators import detail_route

from threepio import logger


class ClusterViewSet(AuthViewSet):

    """
    API endpoint that allows cluster to be viewed or edited.
    """

    def create(self, request):
        user = self.request.user
        data = self.request.data
        plugin_name = data['pluginName']
        if plugin_name == "vanilla":
            hadoop_version = "2.7.1"
        elif plugin_name == "spark":
            hadoop_version = "1.6.0"
        elif plugin_name == "storm":
            hadoop_version = "1.0.1"
        else:
            raise Exception("Cannot find the plugin")
        name = data['clusterName']
        cluster_size = data['clusterSize']
        identity = Identity.objects.get(created_by=user)
        all_creds = identity.get_all_credentials()
        auth_url = all_creds.get('auth_url')
        worker_number = data['workerNum']
        if "/v3" not in auth_url:
            auth_url += "/v3"
        project_name = identity.project_name()
        token = all_creds['ex_force_auth_token']
        token_auth = v3.Token(
            auth_url=auth_url,
            token=token,
            project_name=project_name,
            project_domain_id="default")
        ses = session.Session(auth=token_auth)
        network_driver = NetworkManager(session=ses)
        user_driver = UserManager(auth_url=auth_url, auth_token=token, project_name=project_name, domain_name="default", session=ses, version='v3')
        kp = user_driver.nova.keypairs.list()[0]
        net_id = None
        for network in network_driver.neutron.list_networks()['networks']:
            if not network['router:external']:
                net_id = network['id']
        image = None
        for img in user_driver.glance.images.list():
            if plugin_name == "spark":
                if "Sahara: Spark 1.6.0, Trusty" in img.name:
                    image = img
                    break
            elif plugin_name == "vanilla":
                if "Sahara: Hadoop 2.7.1 + Spark 1.6.0 on YARN, Trusty" in img.name:
                    image = img
                    break
            elif plugin_name == "storm":
                if "Sahara: Storm 1.0.1, Trusty" in img.name:
                    image = img
                    break
            else:
                raise Exception("Cannot find an image for the plugin")
        image_id = image.id
        '''
        files, heat_template = template_utils.process_template_path("/opt/dev/atmosphere/{plugin}-template.yml".format(plugin=plugin_name))

        heat_template['parameters']['image']['default'] = str(image_id)
        heat_template['parameters']['flavor']['default'] = str(cluster_size['name'])
        heat_template['parameters']['key']['default'] = str(kp.name)
        heat_template['parameters']['private_net']['default'] = str(net_id)
        heat_template['parameters']['plugin']['default'] = str(plugin_name)
        heat_template['parameters']['version']['default'] = str(hadoop_version)
        heat_template['parameters']['worker_count']['default'] = str(worker_number)
        heat_template['parameters']['name']['default'] = str(name)

        try:
            stackCreate = network_driver.heat.stacks.create(stack_name=name, template=heat_template, files=files)
        except Exception as e:
            raise Exception(e)
        stack_id = str(stackCreate['stack']['id'])
        time.sleep(5)
        giji_cluster = network_driver.heat.resources.get(stack_id, "giji_cluster")
        cluster_id = str(giji_cluster.physical_resource_id)
        if not cluster_id:
            logger.debug("no cluster_id, going to sleep for 5 seconds")
            time.sleep(5)
            logger.debug("slept for 5 secs")
            giji_cluster = network_driver.heat.resources.get(stack_id, "giji_cluster")
            cluster_id = str(giji_cluster.physical_resource_id)
            if not cluster_id:
                raise Exception("No cluster_id")
        results = [{"id": cluster_id, "clusterName": name, "pluginName": plugin_name, "hadoop_version": hadoop_version, "stackID": stack_id}]
        '''
        results=[]
        return Response(results, status=status.HTTP_201_CREATED)


    def get(self, request, pk=None):
        return self.list(request)

    def list(self, request):
        user = self.request.user
        network_driver, user_driver = self.get_network_and_user_driver(user)
        stack_list = network_driver.heat.stacks.list()
        clusters_list = network_driver.sahara.clusters.list()
        results = []
        stack_id = None
        for cluster in clusters_list:
            for stack in stack_list:
                stackID = stack.id
                stack_parameter = network_driver.heat.stacks.get(stackID)
                if cluster.name == stack_parameter.parameters['name']:
                    stack_id = stackID
            try:
                ip = cluster.node_groups[0]['instances'][0]['management_ip']
                results.append({"clusterName": cluster.name, "id": cluster.id,
                "pluginName": cluster.plugin_name, "clusterStatus":
                cluster.status, "clusterMasterIP": ip, "stackID": stack_id})
            except:
                results.append({"clusterName": cluster.name, "id": cluster.id,
                "pluginName": cluster.plugin_name, "clusterStatus":
                cluster.status, "clusterMasterIP": "not associated", "stackID": stack_id})
        return Response(results, status=status.HTTP_200_OK)


    def retrieve(self, request, pk=None):
        url_list = request.path.split("/")
        cluster_id = url_list[-1]
        user = self.request.user
        network_driver, user_driver = self.get_network_and_user_driver(user)
        try:
            cluster = network_driver.sahara.clusters.get(cluster_id)
            results = []
            try:
                ip = cluster.node_groups[0]['instances'][0]['management_ip']
                results.append({"clusterName": cluster.name, "id": cluster.id, "pluginName": cluster.plugin_name, "clusterStatus": cluster.status, "clusterMasterIP": ip})
                return Response(results, status=status.HTTP_200_OK)
            except:
                results.append({"clusterName": cluster.name, "id": cluster.id,
                "pluginName": cluster.plugin_name, "clusterStatus":
                cluster.status, "clusterMasterIP": "not associated"})
                return Response(results, status=status.HTTP_200_OK)
        except:
            return Response({}, status=status.HTTP_404_NOT_FOUND)

    def update(self, request, pk=None):
        user = self.request.user
        network_driver, user_driver = self.get_network_and_user_driver(user)
        clusters_list = network_driver.sahara.clusters.list()
        results = []
        for cluster in clusters_list:
            results.append({"clusterName": cluster.name, "id": cluster.id, "pluginName": cluster.plugin_name, "clusterStatus": "Luanched"})
        return Response(results, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        user = self.request.user
        network_driver, user_driver = self.get_network_and_user_driver(user)
        url_list = request.path.split("/")
        stack_id = url_list[-1]
        network_driver.heat.stacks.delete(str(stack_id))
        return Response({}, status=status.HTTP_204_NO_CONTENT)

    def get_network_and_user_driver(self, user):
        identity = Identity.objects.get(created_by=user)
        all_creds = identity.get_all_credentials()
        auth_url = all_creds.get('auth_url')
        if "/v3" not in auth_url:
            auth_url += "/v3"
        project_name = identity.project_name()
        token = all_creds['ex_force_auth_token']
        token_auth=v3.Token(
            auth_url=auth_url,
            token=token,
            project_name=project_name,
            project_domain_id="default")
        ses = session.Session(auth=token_auth)
        network_driver = NetworkManager(session=ses)
        user_driver = UserManager(auth_url=auth_url, auth_token=token, project_name=project_name, domain_name="default", session=ses, version='v3')
        return network_driver, user_driver

