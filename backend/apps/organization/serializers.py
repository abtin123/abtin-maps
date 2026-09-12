from rest_framework import serializers

from .models import Branch, City, Company, Warehouse, Zone


class CompanySerializer(serializers.ModelSerializer):
    branches_count = serializers.IntegerField(source='branches.count', read_only=True)

    class Meta:
        model = Company
        fields = (
            'id', 'code', 'name', 'national_id', 'economic_code',
            'phone', 'address', 'is_active', 'branches_count', 'created_at',
        )


class BranchSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = Branch
        fields = (
            'id', 'company', 'company_name', 'code', 'name', 'manager_name',
            'phone', 'address', 'latitude', 'longitude', 'is_active', 'created_at',
        )


class WarehouseSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)

    class Meta:
        model = Warehouse
        fields = (
            'id', 'branch', 'branch_name', 'code', 'name', 'type',
            'address', 'keeper_name', 'is_active', 'allow_negative', 'created_at',
        )


class ZoneSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    cities_count = serializers.IntegerField(source='cities.count', read_only=True)

    class Meta:
        model = Zone
        fields = ('id', 'branch', 'branch_name', 'code', 'name', 'is_active', 'cities_count')


class CitySerializer(serializers.ModelSerializer):
    zone_name = serializers.CharField(source='zone.name', read_only=True)

    class Meta:
        model = City
        fields = ('id', 'zone', 'zone_name', 'name', 'province', 'postal_prefix')
