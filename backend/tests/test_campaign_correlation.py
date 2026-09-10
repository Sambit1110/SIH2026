from app.core.campaigns.correlation import _is_correlatable_ioc
from app.models import IOC


def _ioc(type_, value):
    return IOC(type=type_, value=value)


def test_private_ip_is_not_correlatable():
    assert _is_correlatable_ioc(_ioc("ip", "10.10.4.12")) is False
    assert _is_correlatable_ioc(_ioc("ip", "172.16.5.9")) is False
    assert _is_correlatable_ioc(_ioc("ip", "192.168.1.1")) is False


def test_public_ip_is_correlatable():
    assert _is_correlatable_ioc(_ioc("ip", "91.219.237.244")) is True


def test_domain_and_url_always_correlatable():
    assert _is_correlatable_ioc(_ioc("domain", "evil.com")) is True
    assert _is_correlatable_ioc(_ioc("url", "http://evil.com/x")) is True


def test_invalid_ip_value_is_not_correlatable():
    assert _is_correlatable_ioc(_ioc("ip", "not-an-ip")) is False
