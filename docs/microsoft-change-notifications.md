# Microsoft Graph change-notification trigger contract

Microsoft Graph change notifications are optional scheduling hints. They never
replace Mail or Calendar delta/sync as the correctness mechanism.

msgloom does not host a public webhook server or an in-package scheduler. The
deployment adapter owns the public HTTPS endpoint, subscription lifecycle and
delivery queue. After validation, it launches the existing finite msgloom
commands through the External scheduler.

## Recommended notification mode

Use basic notifications without resource data. msgloom only needs to know that
Mail or Calendar changed; it does not need message or event content in the
notification payload.

This keeps provider content on the normal acquisition/evidence path and avoids
the encryption-certificate and rich-notification resource-data machinery.
Outlook message/event subscriptions have a maximum lifetime of under seven
days. Rich notifications have a shorter maximum lifetime, so they provide no
benefit for this trigger-only design.

## Webhook adapter responsibilities

The deployment-owned HTTPS adapter must:

1. complete Microsoft Graph notificationUrl validation by returning the opaque
   validation token exactly as plain text within the provider deadline;
2. acknowledge notification delivery promptly;
3. validate the configured clientState before accepting a basic notification;
4. handle lifecycle events including reauthorizationRequired,
   subscriptionRemoved and missed;
5. renew subscriptions before expiration;
6. coalesce bursts into a bounded number of sync invocations;
7. keep provider IDs and notification payloads out of ordinary logs.

The package helper
message_ingest.acquisition.microsoft.outlook.notifications.sync_triggers_from_notification
validates clientState and reduces a notification collection to privacy-safe
Mail/Calendar sync hints.

A change hint launches the same normal operations used without notifications:

- Mail: scrapy microsoft outlook mail sync
- Calendar: scrapy microsoft outlook calendar sync with the deployment's
  configured fixed window

A missed or removed subscription also requires subscription recovery. Running
sync after recovery closes the correctness gap; replaying the notification
payload itself does not.

## Shared/delegated limitation

Delegated Mail.Read.Shared and Calendars.Read.Shared can read shared/delegated
resources, but Microsoft Graph does not allow those delegated shared scopes to
create change-notification subscriptions for items in another user's mailbox.

A deployment that requires notifications for shared/delegated mailboxes needs
an application-permission subscription adapter. That is intentionally separate
from msgloom's current delegated acquisition session and does not change the
read-only sync implementation.

## Security boundary

clientState is a secret shared between the subscription creator and webhook
adapter. Do not place it in command arguments, logs, stats, acceptance output or
catalog evidence.

The trigger helper uses constant-time comparison and returns only resource
class and recovery reason. It is not an HTTP server and does not validate rich
notification JWTs because this design does not request resource data.
