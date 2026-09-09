
## Verified failure from the supplied screenshot/video
The screenshot's `GoException: no routes for location: geo:0,0?q=...` is a
`go_router` route-match failure caused by Android delivering a `geo:` intent as
the platform route while the app only declared `/` and settings routes. The
same failure path was present in the supplied project before this combined fix.
The recording was also inspected: it is an external navigation app handing a
location/navigation intent to the receiving app, matching the failure mode.
