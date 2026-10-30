from src.health import EndpointCheck, heal_service


def test_heal_service():
    r = heal_service()
    assert r is False
    broken_ec = EndpointCheck(url='http://127.0.0.1:3333')
    r = heal_service(broken_ec)
    assert r is True
