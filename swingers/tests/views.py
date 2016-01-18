from .models import Duck, Counter
from swingers.views.decorators import (cancel_view_m, log_view_dec_m,
                                       log_view_dec)

from django.http import HttpResponse
from django.views.generic import CreateView
from django.views.generic.edit import UpdateView
from django.views.decorators.csrf import csrf_exempt


def create_duck(request, name='donald'):
    """Creates a duck."""
    name = request.GET.get('name', name)
    Duck.objects.create(name=name)
    return HttpResponse()


@log_view_dec(logger_name='test_view_stats')
def create_duck2(request, name='donald'):
    """Creates a duck."""
    name = request.GET.get('name', name)
    Duck.objects.create(name=name)
    return HttpResponse()


class CreateDuck(CreateView):
    model = Duck
    success_url = "."
    template_name = "tests/dummy.html"

    @cancel_view_m
    @csrf_exempt
    def post(self, request, *args, **kwargs):
        return super(CreateDuck, self).post(request, *args, **kwargs)

    def get_success_url(self):
        # django's default method references self.object
        return self.success_url


class CreateDuck2(CreateDuck):
    @log_view_dec_m(logger_name='test_view_stats')
    def get(self, request, *args, **kwargs):
        return super(CreateDuck2, self).get(request, *args, **kwargs)


class CounterView(UpdateView):
    template_name = "tests/dummy.html"
    model = Counter
