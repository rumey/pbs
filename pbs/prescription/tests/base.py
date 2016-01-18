import factory

from pbs.prescription.models import Prescription


class PrescriptionFactory(factory.Factory):

    class Meta:
        model = Prescription
