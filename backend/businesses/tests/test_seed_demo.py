import pytest
from django.core.management import call_command

from businesses.models import Business
from operations.models import Customer, Order, Product, QuoteRequest


@pytest.mark.django_db(transaction=True)
def test_seed_demo_is_repeatable():
    options = {"customers": 2, "products": 3, "orders": 4, "quotes": 2, "verbosity": 0}

    call_command("seed_demo", **options)
    call_command("seed_demo", **options)

    businesses = Business.objects.filter(slug__in=["aurora", "tinta-sur", "color-norte"])
    assert businesses.count() == 3
    assert Customer.objects.filter(business__in=businesses).count() == 6
    assert Product.objects.filter(business__in=businesses).count() == 9
    assert Order.objects.filter(business__in=businesses).count() == 12
    assert QuoteRequest.objects.filter(contact_email__endswith="@demo.cl").count() == 2
