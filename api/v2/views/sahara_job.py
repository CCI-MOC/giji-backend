from api.v2.views.base import AuthViewSet
#from api.v2.serializers.post import JobSerializer


from core.models import AtmosphereUser, Identity
from keystoneauth1.identity import v3
from rtwo.drivers.openstack_network import NetworkManager
from rtwo.drivers.openstack_user import UserManager
from keystoneauth1 import session

from rest_framework.response import Response
from rest_framework import status

class JobViewSet(AuthViewSet):

    """
    API endpoint that allows cluster to be viewed or edited.
    """

#    serializer_class = JobSerializer

    def create(self, request):
        user = self.request.user
        data = self.request.data
        type_name = data['typeName']
        job_name = data['jobName']
        identity = Identity.objects.get(created_by=user)
        all_creds = identity.get_all_credentials()
        auth_url = all_creds.get('auth_url')
        if not "/v3" in auth_url:
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
        container_name = data.get('containerName', None)
        input_path_user = data['inputPath']
        output_path = "swift://"+data['outputPath']
        if container_name is None:
            input_path = "swift://"+input_path_user
        else:
            input_path = "swift://"+container_name+"/"+input_path_user
        job_template = network_driver.sahara.jobs.list()[0]
        cluster = network_driver.sahara.clusters.list()[0]
        configs = {"edp.spark.adapt_for_swift":True, "edp.java.main_class":"sahara.edp.spark.SparkWordCount","fs.swift.service.sahara.password": "giji-test-user",
"fs.swift.service.sahara.username": "giji-test-user"}
        args = [input_path, output_path]
        job_configs = {"configs": configs, "args":args}
        job_execution= network_driver.sahara.job_executions.create(job_id=job_template.id, cluster_id=cluster.id, configs=job_configs)
        results = [{"jobID": job_execution.id, "clusterName": cluster.name}]
        return Response(results, status=status.HTTP_201_CREATED)

    def get(self, request, pk=None):
        return self.list(request)

    def list(self, request, *args, **kwargs):
        user = self.request.user
        network_driver, user_driver = self.get_network_and_user_driver(user)
        jobs_list = network_driver.sahara.job_executions.list()
        results = []
        for job in jobs_list:
            cluster = network_driver.sahara.clusters.get(job.cluster_id)
            results.append({"jobID": job.id, "clusterName": cluster.name})
        return Response(results, status=status.HTTP_200_OK)

    def get_network_and_user_driver(self, user):
    	identity = Identity.objects.get(created_by=user)
        all_creds = identity.get_all_credentials()
        auth_url = all_creds.get('auth_url')
        project_name = identity.project_name()
        if not "/v3" in auth_url:
            auth_url += "/v3"
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
