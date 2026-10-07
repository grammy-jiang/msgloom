"""Exercise notification protocol validation without application policy."""

import subprocess
import sys
import traceback

import pytest

from microsoft_graph.protocol.notifications import (
    GraphNotificationAuthenticationError,
    GraphNotificationError,
    notifications_from_payload,
)

SECRET = "private-client-state"
RESOURCE = "/users/private-user/messages/private-message"


def entry(**kwargs):
    return {
        "resource": RESOURCE,
        "subscriptionId": "private-subscription",
        "clientState": SECRET,
        "changeType": "updated",
        **kwargs,
    }


def parse(*entries, **kwargs):
    return notifications_from_payload(
        {"value": list(entries)}, expected_client_state=SECRET, **kwargs
    )


def test_protocol_imports_without_application_or_scrapy():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import sys
class BlockApplication:
    def find_spec(self, fullname, *args):
        if fullname.split('.')[0] in {'message_ingest', 'scrapy', 'sqlalchemy'}:
            raise RuntimeError('forbidden dependency: ' + fullname)
sys.meta_path.insert(0, BlockApplication())
from microsoft_graph.protocol.notifications import notifications_from_payload
if notifications_from_payload({'value': []}, expected_client_state='secret') != ():
    raise RuntimeError('empty envelope changed')
""",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    if result.returncode:
        pytest.fail(result.stderr)


@pytest.mark.parametrize("change_type", ["created", "updated", "deleted"])
def test_each_change_type_is_retained(change_type):
    notification = parse(entry(changeType=change_type))[0]
    if notification.change_type != change_type or notification.lifecycle_event:
        pytest.fail("Change event was not retained")


@pytest.mark.parametrize(
    "event,expected",
    [
        ("reauthorizationRequired", "reauthorizationRequired"),
        ("subscriptionRemoved", "subscriptionRemoved"),
        ("missed", "missed"),
        ("REAUTHORIZATION_REQUIRED", "reauthorizationRequired"),
    ],
)
def test_each_lifecycle_event_takes_precedence(event, expected):
    notification = parse(entry(lifecycleEvent=event))[0]
    if notification.lifecycle_event != expected or notification.change_type:
        pytest.fail("Lifecycle event precedence changed")


@pytest.mark.parametrize("client_state", [None, 7, "wrong", "non-ASCII-秘密"])
def test_client_state_mismatch(client_state):
    with pytest.raises(GraphNotificationAuthenticationError):
        parse(entry(clientState=client_state))


@pytest.mark.parametrize("payload", [{}, {"value": None}, {"value": {}}, []])
def test_value_must_be_a_list(payload):
    with pytest.raises(GraphNotificationError, match="value list"):
        notifications_from_payload(payload, expected_client_state=SECRET)


@pytest.mark.parametrize("value", [None, "private-entry", 3, []])
def test_entries_must_be_objects(value):
    with pytest.raises(GraphNotificationError, match="entries must be objects"):
        parse(value)


@pytest.mark.parametrize("resource", [None, "", 3])
def test_subscription_fallback_mapping(resource):
    notification = parse(
        entry(resource=resource),
        subscription_resources={"private-subscription": RESOURCE},
    )[0]
    if notification.resource != RESOURCE:
        pytest.fail("Subscription mapping did not resolve the resource")


def test_explicit_resource_wins_and_protocol_accepts_other_graph_resources():
    resource = "/users/private-user/contacts/private-contact"
    notification = parse(
        entry(resource=resource),
        subscription_resources={"private-subscription": RESOURCE},
    )[0]
    if notification.resource != resource or resource in repr(notification):
        pytest.fail("Resource precedence or privacy-safe repr changed")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"resource": None},
        {"changeType": "private-change"},
        {"changeType": []},
        {"lifecycleEvent": "private-lifecycle"},
        {"lifecycleEvent": {}},
        {"clientState": "private-wrong-state"},
    ],
)
def test_errors_and_exception_chains_never_include_provider_values(kwargs):
    with pytest.raises(GraphNotificationError) as caught:
        parse(entry(**kwargs))
    rendered = "".join(traceback.format_exception(caught.value))
    if "private-" in rendered:
        pytest.fail("Notification error exposed a private provider value")


def test_empty_client_state_configuration_is_rejected():
    with pytest.raises(ValueError, match="expected_client_state"):
        notifications_from_payload({"value": []}, expected_client_state="")
