from api.v2.views.base import AuthViewSet
#from api.v2.serializers.post import SaharaPluginSerializer

from keystoneauth1.identity import v3
from rtwo.drivers.openstack_network import NetworkManager
from rtwo.drivers.openstack_user import UserManager
from keystoneauth1 import session

from core.models import AtmosphereUser, Identity
from rest_framework.response import Response
from rest_framework import status

class SaharaPluginViewSet(AuthViewSet):

    """
    API endpoint that allows Plugin to be viewed or edited.
    """

    #serializer_class = SaharaPluginSerializer

    def get(self, request, pk=None):
        return self.list(request)

    def list(self, request, *args, **kwargs):
        user = self.request.user
        network_driver, user_driver = self.get_network_and_user_driver(user)
        plugins_list = network_driver.sahara.plugins.list()
        results = []
        for plugin in plugins_list:
            results.append({"name": plugin.name, "versions": plugin.versions, "description": plugin.description})
        return Response(results, status=status.HTTP_200_OK)

    def get_network_and_user_driver(self, user):
        identity = Identity.objects.get(created_by=user)
        all_creds = identity.get_all_credentials()
        auth_url = all_creds.get('auth_url')
        project_name = identity.project_name()
        if "/v3" not in auth_url:
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

