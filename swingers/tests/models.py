from swingers import models
from swingers.models import ActiveModel, Audit, Manager


class Duck(Audit):
    """A duck."""
    name = models.CharField(max_length=20)
    objects = Manager()


class ActiveDuck(ActiveModel):
    """An active duck."""
    name = models.CharField(max_length=20)


class ParentDuck(Audit):
    """A parent duck."""
    name = models.CharField(max_length=20)
    duck = models.ForeignKey(Duck)
    objects = Manager()


class GrandParentDuck(Audit):
    """A parent duck."""
    name = models.CharField(max_length=20)
    duck = models.ForeignKey(ParentDuck)
    objects = Manager()


class Counter(models.Model):
    num = models.IntegerField(default=0)

    def get_absolute_url(self):
        return "/"


if models.GIS_ENABLED:
    class GeoDuck(Audit):
        poly = models.PolygonField()
        objects = Manager()
