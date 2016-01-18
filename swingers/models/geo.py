from django.contrib.gis.db import models

from swingers.utils.geo import transform_geom


class PolygonModelMixin(models.Model):
    """
    Model mixin to provide a polygon field called the_geom having the default
    SRID of 4326 (WGS84).
    """
    the_geom = models.PolygonField(blank=True, null=True,
                                   verbose_name='the_geom')

    class Meta:
        abstract = True

    def area_ha(self):
        """
        Returns the area of the polygon field in hectares, transformed to a
        projection of GDA94/MGA zone 49 through 56.
        """
        if self.the_geom:
            return transform_geom(self.the_geom).area / 10000
        else:
            return None

    def perim_m(self):
        '''
        Returns the perimeter of the polygon field in metres, transformed to a
        projection of GDA94/MGA zone 49 through 56.
        '''
        if self.the_geom:
            return transform_geom(self.the_geom).boundary.length
        else:
            return None


class LineStringModelMixin(models.Model):
    """
    Model mixin to provide a linestring spatial field called the_geom having
    the default SRID of 4326 (WGS84).
    """
    the_geom = models.LineStringField(blank=True, null=True,
                                      verbose_name='the_geom')

    class Meta:
        abstract = True


class PointModelMixin(models.Model):
    """
    Model mixin to provide a point spatial field called the_geom having the
    default SRID of 4326 (WGS84).
    """
    the_geom = models.PointField(blank=True, null=True,
                                 verbose_name='the_geom')

    class Meta:
        abstract = True
