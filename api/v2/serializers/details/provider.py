from core.models import Provider, ProviderType, PlatformType
from rest_framework import serializers
from api.v2.serializers.summaries import SizeSummarySerializer


class ProviderTypeSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = ProviderType
        view_name = 'api:v2:providertype-detail'
        fields = ('id', 'url', 'name', 'start_date', 'end_date')


class PlatformTypeSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = PlatformType
        view_name = 'api:v2:platformtype-detail'
        fields = ('id', 'url', 'name', 'start_date', 'end_date')


class ProviderSerializer(serializers.HyperlinkedModelSerializer):
    name = serializers.CharField(source='location')
    type = ProviderTypeSerializer()
    virtualization = PlatformTypeSerializer()
    sizes = SizeSummarySerializer(source='size_set', many=True)
    is_admin = serializers.SerializerMethodField()

    def get_is_admin(self, provider):
        user = self.context['request'].user
        if user.is_staff or user.is_superuser:
            return True
        return False


    class Meta:
        model = Provider
        view_name = 'api:v2:provider-detail'
        fields = (
            'id',
            'is_admin',
            'url',
            'uuid',
            'name',
            'description',
            'type',
            'virtualization',
            'active',
            'public',
            'auto_imaging',
            'sizes',
            'start_date',
            'end_date',
        )
