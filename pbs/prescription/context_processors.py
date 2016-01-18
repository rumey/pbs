from pbs.prescription.models import Prescription


def prescription(request):
    context = {}
    object_id = request.session.get('current_prescription', None)
    if object_id:
        prescription = Prescription.objects.get(pk=object_id)
        context['current'] = prescription
    return context
